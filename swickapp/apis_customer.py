import json
from decimal import ROUND_HALF_UP, Decimal

import pusher
import stripe
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from swick.settings import (PUSHER_APP_ID, PUSHER_CLUSTER, PUSHER_KEY,
                            PUSHER_SECRET, STRIPE_API_KEY)

from .apis_helper import (attempt_stripe_payment, get_stripe_fee,
                          retry_stripe_payment)
from .models import (Category, Customer, Customization, Meal, Order, OrderItem,
                     OrderItemCustomization, Request, RequestOption,
                     Restaurant)
from .pusher_events import (send_event_item_status_updated,
                            send_event_order_placed,
                            send_event_order_status_updated,
                            send_event_request_made, send_event_tip_added)
from .serializers import (CategorySerializer, CustomizationSerializer,
                          MealSerializer, OrderDetailsSerializer,
                          OrderSerializer, RequestOptionSerializer,
                          RestaurantSerializer)

stripe.api_key = STRIPE_API_KEY


@api_view(['POST'])
def login(request):
    """
    header:
        Authorization: Token ...
    return:
        id
        name_set
        status
    """
    if request.user.is_anonymous:
        return JsonResponse({"status": "invalid_token"})
    # Create customer account if not created
    customer = Customer.objects.get_or_create(user=request.user)[0]
    # Check if user's name is set
    name_set = False if not request.user.name else True
    return JsonResponse({"id": customer.id, "name_set": name_set, "status": "success"})


@api_view(['POST'])
def pusher_auth(request):
    """
    header:
        Authorization: Token ...
    params:
        channel_name
        socket_id
    return:
        channel_name
        socket_id
    """
    channel = request.POST['channel_name']
    try:
        if not channel.startswith("private-customer-"):
            raise AssertionError("Unknown channel requested " + channel)
        customer = Customer.objects.get(user=request.user)
        channel_id = int(channel.split('-')[2])
        if customer.id != channel_id:
            raise AssertionError("Requested unauthorized channnel")

        pusher_client = pusher.Pusher(app_id=PUSHER_APP_ID,
                                      key=PUSHER_KEY,
                                      secret=PUSHER_SECRET,
                                      cluster=PUSHER_CLUSTER)

        payload = pusher_client.authenticate(
            channel=request.POST['channel_name'],
            socket_id=request.POST['socket_id'])

        return JsonResponse(payload)
    except (Customer.DoesNotExist, ValueError, AssertionError, IndexError) as e:
        print(e)
        return HttpResponseForbidden()


def get_restaurants(request):
    """
    return:
        [restaurants]
            id
            name
            address
            image
        status
    """
    restaurants = RestaurantSerializer(
        Restaurant.objects.all().order_by("name"),
        many=True,
        # Needed to get absolute image url
        context={"request": request}
    ).data

    return JsonResponse({"restaurants": restaurants, "status": "success"})


def get_restaurant(request, restaurant_id):
    """
    return:
        restaurant
            id
            name
            address
            image
        [request_options]
            id
            name
        status
    """
    try:
        restaurant_object = Restaurant.objects.get(id=restaurant_id)
    except Restaurant.DoesNotExist:
        return JsonResponse({"status": "restaurant_does_not_exist"})
    restaurant = RestaurantSerializer(
        restaurant_object,
        context={"request": request}
    ).data
    request_options = RequestOptionSerializer(
        RequestOption.objects.filter(
            restaurant=restaurant_object).order_by("id"),
        many=True,
    ).data
    return JsonResponse({
        "restaurant": restaurant,
        "request_options": request_options,
        "status": "success"
    })


def get_categories(request, restaurant_id):
    """
    return:
        [categories]
            id
            name
        status
    """
    try:
        restaurant = Restaurant.objects.get(id=restaurant_id)
    except Restaurant.DoesNotExist:
        return JsonResponse({"status": "restaurant_does_not_exist"})
    categories = CategorySerializer(
        Category.objects.filter(restaurant=restaurant).order_by("name"),
        many=True,
    ).data
    return JsonResponse({"categories": categories, "status": "success"})


def get_meals(request, restaurant_id, category_id):
    """
    return:
        [menu]
            id
            name
            description
            price
            tax
            image
        status
    """
    try:
        restaurant = Restaurant.objects.get(id=restaurant_id)
    except Restaurant.DoesNotExist:
        return JsonResponse({"status": "restaurant_does_not_exist"})
    if category_id != 0:
        try:
            category = Category.objects.get(
                restaurant=restaurant, id=category_id)
        except Category.DoesNotExist:
            return JsonResponse({"status": "category_does_not_exist"})
    # Get all meals if category_id is 0
    if category_id == 0:
        meals = MealSerializer(
            Meal.objects.filter(
                category__restaurant=restaurant,
                enabled=True
            ).order_by("name"),
            many=True,
            context={"request": request}
        ).data
    else:
        meals = MealSerializer(
            Meal.objects.filter(
                category=category,
                enabled=True
            ).order_by("name"),
            many=True,
            context={"request": request}
        ).data
    return JsonResponse({"meals": meals, "status": "success"})


def get_meal(request, meal_id):
    """
    return:
        [customizations]
            id
            name
            options
            price_additions
            min
            max
        status
    """
    try:
        meal = Meal.objects.get(id=meal_id)
    except Meal.DoesNotExist:
        return JsonResponse({"status": "meal_does_not_exist"})
    # Check if meal is disabled
    if not meal.enabled:
        return JsonResponse({"status": "meal_disabled"})

    customizations = CustomizationSerializer(
        Customization.objects.filter(meal_id=meal_id).order_by("name"),
        many=True,
        context={"request": request}
    ).data
    return JsonResponse({"customizations": customizations, "status": "success"})


@api_view(['POST'])
def place_order(request):
    """
    header:
        Authorization: Token ...
    params:
        restaurant_id
        table
        [order_items]
            meal_id
            quantity
            [customizations]
                customization_id
                [options]
        tip
        payment_method_id
    return:
        intent_status
        card_error (optional)
        payment_intent_id (optional)
        client_secret (optional)
        meal_name (if status == meal_disabled)
        status
    """
    order_items = json.loads(request.POST["order_items"])
    # Check if any meals are disabled
    for item in order_items:
        meal = Meal.objects.get(id=item["meal_id"])
        if not meal.enabled:
            return JsonResponse({"meal_name": meal.name, "status": "meal_disabled"})

    # Create order in database
    order = Order.objects.create(
        customer=request.user.customer,
        restaurant_id=request.POST["restaurant_id"],
        table=request.POST["table"]
    )

    # Variable for calculating order total
    order_total = 0
    order_subtotal = 0
    order_tax = 0

    # Loop through order items
    for item in order_items:
        # Create order item in database
        meal = Meal.objects.get(id=item["meal_id"])
        order_item = OrderItem.objects.create(
            order=order,
            meal_name=meal.name,
            meal_price=meal.price,
            quantity=item["quantity"],
        )
        # Variable for calculating price of one meal in order item
        meal_total = order_item.meal_price
        # Loop through customizations of order items
        for cust in item["customizations"]:
            cust_id = cust["customization_id"]
            cust_object = Customization.objects.get(id=cust_id)
            # Build options and price_additions arrays with option indices
            options = []
            price_additions = []
            for opt_idx in cust["options"]:
                options.append(cust_object.options[opt_idx])
                price_additions.append(cust_object.price_additions[opt_idx])
                meal_total += cust_object.price_additions[opt_idx]

            # Create order item customization in database
            order_item_customization = OrderItemCustomization.objects.create(
                order_item=order_item,
                customization_name=Customization.objects.get(id=cust_id).name,
                options=options,
                price_additions=price_additions
            )
        # Calculate order item total and update field
        order_item.total = meal_total * order_item.quantity
        order_item.save()

        meal_tax = meal.tax_category.tax
        order_subtotal += order_item.total
        order_tax += (meal_tax / 100) * order_item.total
        order_total += (order_item.total * meal_tax / 100)
    # Update order total field
    order.subtotal = order_subtotal
    order.tax = Decimal(order_tax.quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP))
    order.tip = Decimal(Decimal(request.POST["tip"]).quantize(Decimal(
        "0.01"), rounding=ROUND_HALF_UP)) if request.POST["tip"] != "nil" else None
    order.total = order.subtotal + order.tax + (order.tip or 0)

    response = attempt_stripe_payment(request.POST["restaurant_id"],
                                      request.user.customer.stripe_cust_id,
                                      request.user.email,
                                      request.POST["payment_method_id"],
                                      int(order.total * 100),
                                      {'order_id': order.id})

    content = json.loads(response.content)
    if content["status"] == "success":
        intent_status = content["intent_status"]
        if intent_status == "card_error" or intent_status == "requires_payment_method":
            order.delete()
        elif intent_status == "requires_action" or intent_status == "requires_source_action":
            order.stripe_payment_id = content["payment_intent"]
            order.save()
        elif intent_status == "succeeded":
            order.stripe_payment_id = content["payment_intent"]
            order.stripe_fee = get_stripe_fee(content["payment_intent"])
            order.status = Order.ACTIVE
            order.save()
            send_event_order_placed(order)
    return response


@api_view(['POST'])
def add_tip(request):
    """
    header:
        Authorization: Token ...
    params:
        order_id
        tip
    return:
        status
        intent_status
        card_error (optional)
        payment_intent_id (optional)
        client_secret (optional)
    """
    order_object = Order.objects.get(id=request.POST["order_id"])
    if request.user.customer != order_object.customer:
        return JsonResponse({"status": "invalid_request"})

    try:
        tip = Decimal(Decimal(request.POST["tip"]).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP))
    except ValueError:
        return JsonResponse({"status": "invalid_request"})

    try:
        payment_intent = stripe.PaymentIntent.retrieve(order_object.stripe_payment_id,
                                                       expand=['payment_method'])
    except stripe.error.StripeError as e:
        return JsonResponse({"status": "stripe_api_error"})

    # Check if user has deleted card
    if payment_intent.payment_method is not None and request.user.customer.stripe_cust_id != payment_intent.payment_method.customer:
        return JsonResponse({"intent_status": "card_error",
                             "error": "Card used for this order no longer exists",
                             "status": "success"})

    response = attempt_stripe_payment(order_object.restaurant.id,
                                      request.user.customer.stripe_cust_id,
                                      request.user.email,
                                      payment_intent.payment_method,
                                      int(tip * 100),
                                      {'order_id': order_object.id})

    content = json.loads(response.content)
    if content["status"] == "success":
        intent_status = content["intent_status"]
        if intent_status == "requires_action" or intent_status == "requires_source_action":
            order_object.tip_stripe_payment_id = content["payment_intent"]
            order_object.save()
        elif intent_status == "succeeded":
            order_object.tip = Decimal(request.POST["tip"])
            order_object.tip_stripe_payment_id = content["payment_intent"]
            order_object.stripe_fee += get_stripe_fee(
                content["payment_intent"])
            order_object.total += order_object.tip
            order_object.save()
            send_event_tip_added(order_object)

    return response


@api_view(['POST'])
def retry_order_payment(request):
    """
    Retry payment after client completes nextAction request on payment SetupIntent
    header:
        Authorization: Token ...
        params:
            payment_intent_id
        return:
            intent_status
            error
            order_id
            status
    """
    response = retry_stripe_payment(
        request.user.customer, request.POST["payment_intent_id"])
    content = json.loads(response.content)
    if content["status"] == "success":
        if content["intent_status"] == "card_error" or content["intent_status"] == 'requires_payment_method' or content["intent_status"] == 'requires_source':
            order = Order.objects.get(id=payment_intent.metadata["order_id"])
            order.delete()
        elif content["intent_status"] == "succeeded":
            order = Order.objects.get(id=content["order_id"])
            order.status = Order.ACTIVE
            order.stripe_fee = get_stripe_fee(order.stripe_payment_id)
            order.save()
            send_event_order_placed(order)

    return response


@api_view(['POST'])
def retry_tip_payment(request):
    """
    header:
        Authorization: Token ...
        params:
            payment_intent_id
        return:
            intent_status
            error
            order_id
            status
    """
    response = retry_stripe_payment(
        request.user.customer, request.POST["payment_intent_id"])
    content = json.loads(response.content)
    if content["status"] == "success":
        if content["intent_status"] == "succeeded":
            try:
                payment_intent = stripe.PaymentIntent.retrieve(
                    request.POST["payment_intent_id"])
                order = Order.objects.get(id=content["order_id"])
                order.tip = Decimal(payment_intent.amount / 100)
                order.total += order.tip
                order.stripe_fee += get_stripe_fee(
                    request.POST["payment_intent_id"])
                order.save()
                send_event_tip_added(order_object)
            except stripe.error.StripeError:
                return JsonResponse({"status": "stripe_api_error"})
    return response


@api_view()
def get_orders(request):
    """
    Get list of customer's last 10 orders
    header:
        Authorization: Token ...
    return:
        [orders]
            id
            restaurant_name
            customer_name (unused)
            order_time
            status
        status
    """
    orders = OrderSerializer(
        Order.objects
        .filter(customer=request.user.customer).exclude(status=Order.PROCESSING)
        .order_by("-id"),
        many=True
    ).data[:10]

    return JsonResponse({"orders": orders, "status": "success"})


@api_view()
def get_order_details(request, order_id):
    """
    header:
        Authorization: Token ...
    return:
        order_details
            id
            customer_name (unused)
            table (unused)
            order_time
            subtotal
            tax
            tip
            total
            [cooking_order_items] / [sending_order_items] / [complete_order_items]
                id
                meal_name
                quantity
                total
                status
                [order_item_cust]
                    id
                    name
                    [options]
        status
    """
    try:
        order = Order.objects.get(id=order_id, customer=request.user.customer)
    except Order.DoesNotExist:
        return JsonResponse({"status": "order_does_not_exist"})
    if order.customer == request.user.customer:
        order_details = OrderDetailsSerializer(order).data
        return JsonResponse({"order_details": order_details, "status": "success"})


@api_view(['POST'])
def make_request(request):
    """
    header:
        Authorization: Token ...
    params:
        request_option_id
        table
    return:
        status
    """
    try:
        request_option = RequestOption.objects.get(
            id=request.POST["request_option_id"])
    except:
        return JsonResponse({"status": "request_option_does_not_exist"})

    # Check if customer already made this request
    try:
        Request.objects.get(
            customer=request.user.customer,
            request_option=request_option
        )
        return JsonResponse({"status": "request_in_progress"})
    except Request.DoesNotExist:
        pass

    request_obj = Request.objects.create(
        customer=request.user.customer,
        request_option=request_option,
        table=request.POST["table"]
    )
    send_event_request_made(request_obj)
    return JsonResponse({"status": "success"})


@api_view()
def get_info(request):
    """
    header:
        Authorization: Token ...
    return:
        name
        email
        status
    """
    name = request.user.name
    email = request.user.email
    return JsonResponse({"name": name, "email": email, "status": "success"})


@api_view(['POST'])
def setup_card(request):
    """
    header:
        Authorization: Token ...
    return:
        client_secret
        status
    """
    stripe_cust_id = request.user.customer.stripe_cust_id

    try:
        setup_intent = stripe.SetupIntent.create(customer=stripe_cust_id)
    except stripe.error.StripeError as e:
        return JsonResponse({"status": "stripe_api_error"})

    return JsonResponse({"client_secret": setup_intent.client_secret, "status": "success"})


@api_view(['POST'])
def remove_card(request):
    """
    header:
        Authorization: Token ...
    params:
        payment_method_id
    """
    try:
        payment_method = stripe.PaymentMethod.retrieve(
            request.POST["payment_method_id"])
        if payment_method.customer == request.user.customer.stripe_cust_id:
            stripe.PaymentMethod.detach(request.POST["payment_method_id"])
        else:
            return JsonResponse({"status": "invalid_stripe_id"})
    except stripe.error.StripeError as e:
        return JsonResponse({"status": "stripe_api_error"})

    return JsonResponse({"status": "success"})


@api_view()
def get_cards(request):
    """
    header:
        Authorization: Token ...
    return:
        [cards]
            payment_method_id
            brand
            exp_month
            exp_year
            last4
        status
    """
    stripe_cust_id = request.user.customer.stripe_cust_id
    try:
        payment_methods = stripe.PaymentMethod.list(
            customer=stripe_cust_id,
            type="card").data
    except stripe.error.StripeError:
        return JsonResponse({"status": "stripe_api_error"})

    cards = []
    for payment_method in payment_methods:
        card = {
            "payment_method_id": payment_method.id,
            "brand": payment_method.card.brand,
            "exp_month": payment_method.card.exp_month,
            "exp_year": payment_method.card.exp_year,
            "last4": payment_method.card.last4
        }
        cards.append(card)

    return JsonResponse({"cards": cards, "status": "success"})
