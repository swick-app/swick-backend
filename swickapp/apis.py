import json
from django.utils import timezone
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User, Restaurant, Customer, Server, ServerRequest, Meal, \
    Customization, Order, OrderItem, OrderItemCustomization, RequestOption, Request
from .serializers import RestaurantSerializer, CategorySerializer, MealSerializer, \
    CustomizationSerializer, OrderSerializerForCustomer, \
    OrderDetailsSerializerForCustomer, OrderSerializerForServer, \
    OrderDetailsSerializerForServer, OrderItemToCookSerializer, \
    OrderItemToSendSerializer, RequestOptionSerializer, RequestSerializer

from rest_framework.decorators import api_view
from rest_framework.generics import GenericAPIView
import stripe
from swick.settings import STRIPE_API_KEY
from drf_multiple_model.mixins import FlatMultipleModelMixin

stripe.api_key = STRIPE_API_KEY

##### CUSTOMER AND SERVER SHARED API URLS #####

# GET request
# Update account information
@api_view(['POST'])
def update_info(request):
    """
    header:
        Authorization: Token ...
    params:
        name
        email
    return:
        status
    """
    # Update name
    request.user.name = request.POST["name"]
    request.user.save()
    # Update email if given
    email = request.POST["email"]
    if email != "":
        email = request.POST["email"]
        # Check if email is already taken
        try:
            user = User.objects.get(email=email)
            if user != request.user:
                return JsonResponse({"status": "email_already_taken"})
        # If email is not taken
        except User.DoesNotExist:
            request.user.email = email
            request.user.save()
    return JsonResponse({"status": "success"})

##### CUSTOMER APIS #####

# POST request
# Create customer account if not created
@api_view(['POST'])
def customer_create_account(request):
    """
    header:
        Authorization: Token ...
    return:
        status
    """
    Customer.objects.get_or_create(user=request.user)

    return JsonResponse({"status": "success"})

# GET request
# Get list of restaurants
def customer_get_restaurants(request):
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

# GET request
# Get restaurant associated with restaurant_id
def customer_get_restaurant(request, restaurant_id):
    """
    return:
        restaurant
            id
            name
            address
            image
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
    return JsonResponse({"restaurant": restaurant, "status": "success"})

# GET request
# Get categories associated with restaurant_id
def customer_get_categories(request, restaurant_id):
    """
    return:
        [categories]
    """
    categories = CategorySerializer(
        Meal.objects.filter(restaurant_id=restaurant_id, enabled=True).order_by("category")
            .distinct("category"),
        many=True,
    ).data
    return JsonResponse({"categories": categories, "status": "success"})

# GET request
# Get menu associated with category
def customer_get_menu(request, restaurant_id, category):
    """
    return:
        [menu]
            id
            name
            description
            price
            image
        status
    """
    if category == "All":
        meals = MealSerializer(
            Meal.objects.filter(
                restaurant_id=restaurant_id,
                enabled=True
            ).order_by("name"),
            many=True,
            context={"request": request}
        ).data
    else:
        meals = MealSerializer(
            Meal.objects.filter(
                restaurant_id=restaurant_id,
                category=category,
                enabled=True
            ).order_by("name"),
            many=True,
            context={"request": request}
        ).data
    return JsonResponse({"menu": meals, "status": "success"})

# GET request
# Get meal associated with meal_id
def customer_get_meal(request, meal_id):
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

# POST request
# Create order in database
@api_view(['POST'])
def customer_place_order(request):
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

    # Loop through order items
    for item in order_items:
        # Create order item in database
        order_item = OrderItem.objects.create(
            order=order,
            meal_name=Meal.objects.get(id=item["meal_id"]).name,
            meal_price=Meal.objects.get(id=item["meal_id"]).price,
            quantity=item["quantity"]
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

        order_total += order_item.total
    # Update order total field
    order.total = order_total

    # STRIPE PAYMENT PROCESSING
    # Note: Return value 'intent_status: String' can be refactored to boolean values
    # at the cost of readability
    try:
        # Direct payments to stripe connected account if in production
        if request.is_secure():
            stripe_acct_id = Restaurant.objects.get(id=request.POST["restaurant_id"]).stripe_acct_id
            payment_intent = stripe.PaymentIntent.create(amount = int(order.total * 100),
                                                    currency="usd",
                                                    customer=request.user.customer.stripe_cust_id,
                                                    payment_method=request.POST["payment_method_id"],
                                                    receipt_email=request.user.email,
                                                    use_stripe_sdk=True,
                                                    confirmation_method='manual',
                                                    confirm=True,
                                                    transfer_data={
                                                        'destination' : stripe_acct_id
                                                    },
                                                    metadata={'order_id': order.id})
        # Direct payments to developer Stripe account if in development
        else:
            payment_intent = stripe.PaymentIntent.create(amount = int(order.total * 100),
                                                     currency="usd",
                                                     customer=request.user.customer.stripe_cust_id,
                                                     payment_method=request.POST["payment_method_id"],
                                                     receipt_email=request.user.email,
                                                     use_stripe_sdk=True,
                                                     confirmation_method='manual',
                                                     confirm=True,
                                                     metadata={'order_id': order.id})
    except stripe.error.CardError as e:
        error = e.user_message
        order.delete()
        return JsonResponse({"intent_status" : "card_error", "error" : error, "status" : "success"})
    except stripe.error.StripeError as e:
        print(e)
        return JsonResponse({"status" : "stripe_api_error"})

    intent_status = payment_intent.status
    # Card requires further action
    if intent_status == 'requires_action' or intent_status == 'requires_source_action':
        # Card requires more action
        order.stripe_payment_id = payment_intent.id
        order.save()
        return JsonResponse({"intent_status" : intent_status,
                             "payment_intent" : payment_intent.id,
                             "client_secret": payment_intent.client_secret,
                             "status" : "success"})

    # Card is invalid (this 'elif' branch should never occur due to previous card setup validation)
    elif intent_status == 'requires_payment_method':
        error = payment_intent.last_payment_error.message if payment_intent.get('last_payment_error') else None
        order.delete()
        return JsonResponse({"intent_status" : intent_status, "error" : error, "status" : "success"})

    # Payment is succesful
    elif intent_status == 'succeeded':
        order.stripe_payment_id = payment_intent.id
        order.status = Order.ACTIVE
        order.save()
        return JsonResponse({"intent_status" : intent_status, "status" : "success"})

    # should never reach this return
    return JsonResponse({"status": "unhandled_status"})

# POST requires_action
# Retry payment after client completes nextAction request on payment SetupIntent
@api_view(['POST'])
def customer_retry_payment(request):
    """
    header:
        Authorization: Token ...
        params:
            payment_intent_id
        return:
            intent_status
            error
            status
    """
    try:
        payment_intent = stripe.PaymentIntent.retrieve(
            request.POST["payment_intent_id"]
        )
        payment_intent = stripe.PaymentIntent.confirm(payment_intent.id)
    except stripe.error.CardError as e:
        order = Order.objects.get(id = payment_intent.metadata["order_id"])
        order.delete()
        return JsonResponse({"intent_status" : "card_error", "error" : e.user_message, "status" : "success"})
    except stripe.error.StripeError:
        return JsonResponse({"status" : "stripe_api_error"})

    intent_status = payment_intent.status

    # Card is invalid (this 'elif' branch should never occur due to previous card setup validation)
    if intent_status == 'requires_payment_method' or intent_status == 'requires_source':
        error = payment_intent.last_payment_error.message if payment_intent.get('last_payment_error') else None
        order.delete()
        return JsonResponse({"intent_status" : intent_status, "error" : error, "status" : "success"})
    # Payment is succesful
    elif intent_status == 'succeeded':
        order = Order.objects.get(id = payment_intent.metadata["order_id"])
        order.status = Order.ACTIVE
        order.save()
        return JsonResponse({"intent_status" : "succeeded", "status" : "success"})

    # should never reach this return
    return JsonResponse({"status": "unhandled_status"})

# GET request
# Get list of customer's orders
@api_view()
def customer_get_orders(request):
    """
    header:
        Authorization: Token ...
    return:
        [orders]
            id
            restaurant
            order_time
            status
        status
    """
    orders = OrderSerializerForCustomer(
        Order.objects
            .filter(customer=request.user.customer).exclude(status=Order.PROCESSING)
            .order_by("-id"),
        many=True
    ).data[:10]

    return JsonResponse({"orders": orders, "status": "success"})

# GET request
# Get customer's order details
@api_view()
def customer_get_order_details(request, order_id):
    """
    header:
        Authorization: Token ...
    return:
        order_details
            restaurant
            order_time
            total
            [order_item]
                meal_name
                quantity
                total
                status
                [order_item_cust]
                    name
                    [options]
        status
    """
    order = Order.objects.get(id=order_id)
    # Check if order's customer is the customer making the request
    if order.customer == request.user.customer:
        order_details=OrderDetailsSerializerForCustomer(order).data
        return JsonResponse({"order_details": order_details, "status": "success"})
    else:
        return JsonResponse({"status": "invalid_order_id"})

# GET request
# Get request options
def customer_get_request_options(request, restaurant_id):
    """
    return:
        [request_options]
            id
            name
        status
    """
    try:
        restaurant = Restaurant.objects.get(id=restaurant_id)
    except Restaurant.DoesNotExist:
        return JsonResponse({"status": "restaurant_does_not_exist"})

    request_options = RequestOptionSerializer(
        RequestOption.objects.filter(restaurant=restaurant),
        many=True,
    ).data
    return JsonResponse({
        "request_options": request_options,
        "status": "success"
    })

# POST request
# Make request
@api_view(['POST'])
def customer_make_request(request):
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
        request_option = RequestOption.objects.get(id=request.POST["request_option_id"])
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

    Request.objects.create(
        customer=request.user.customer,
        request_option=request_option,
        table=request.POST["table"]
    )
    return JsonResponse({"status": "success"})

# GET request
# Get customer's information
@api_view()
def customer_get_info(request):
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

@api_view()
def customer_setup_card(request):
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
        return JsonResponse({"status" : "stripe_api_error"})

    return JsonResponse({"client_secret": setup_intent.client_secret, "status": "success"})

@api_view(['POST'])
def customer_remove_card(request):
    """
    header:
        Authorization: Token ...
    params:
        payment_method_id
    """
    try:
        stripe.PaymentMethod.detach(request.POST["payment_method_id"])
    except stripe.error.StripeError as e:
        return JsonResponse({"status" : "stripe_api_error"})

    return JsonResponse({"status": "success"})

@api_view()
def customer_get_cards(request):
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
        return JsonResponse({"status" : "stripe_api_error"})

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


##### SERVER APIS #####

# POST request
# Create server account if not created
@api_view(['POST'])
def server_create_account(request):
    """
    header:
        Authorization: Token ...
    return:
        status
    """
    if not Server.objects.filter(user=request.user).exists():
        server = Server.objects.create(user=request.user)
        # Set server's restaurant if server has already accepted request
        # from restaurant
        try:
            server_request = ServerRequest.objects.get(
                email=request.user.email,
                accepted=True
            )
            server.restaurant = server_request.restaurant
            server.save()
            server_request.delete()
        except ServerRequest.DoesNotExist:
            pass

    return JsonResponse({"status": "success"})

# GET request
# Get list of restaurant's orders
@api_view()
def server_get_orders(request):
    """
    header:
        Authorization: Token ...
    return:
        [orders]
            id
            customer
            order_time
            status
        status
    """
    restaurant = request.user.server.restaurant
    if restaurant is None:
        return JsonResponse({
            "status": "restaurant_not_set"
        })
    orders = OrderSerializerForServer(
        Order.objects.filter(restaurant=restaurant)
            .order_by("-id")[:20],
        many=True
    ).data
    return JsonResponse({"orders": orders, "status": "success"})

# GET request
# Get order associated with order id
@api_view()
def server_get_order(request, order_id):
    """
    header:
        Authorization: Token ...
    return:
        order
            id
            customer
            order_time
            status
        status
    """
    restaurant = request.user.server.restaurant
    if restaurant is None:
        return JsonResponse({
            "status": "restaurant_not_set"
        })
    try:
        order_object = Order.objects.get(id=order_id)
    except Restaurant.DoesNotExist:
        return JsonResponse({"status": "order_does_not_exist"})
    order = OrderSerializerForServer(order_object).data
    return JsonResponse({"order": order, "status": "success"})

# GET request
# Get order details associated with order id
@api_view()
def server_get_order_details(request, order_id):
    """
    header:
        Authorization: Token ...
    return:
        order_details
            customer
            table
            order_time
            total
            [order_item]
                meal_name
                quantity
                total
                status
                [order_item_cust]
                    name
                    [options]
        status
    """
    restaurant = request.user.server.restaurant
    order = Order.objects.get(id=order_id)
    # Check if a restaurant's server is making the request
    if order.restaurant != restaurant:
        return JsonResponse({"status": "invalid_request"})

    order_details = OrderDetailsSerializerForServer(
        order
    ).data
    return JsonResponse({"order_details": order_details, "status": "success"})

# GET request
# Get list of restaurant's order items to cook
@api_view()
def server_get_order_items_to_cook(request):
    """
    header:
        Authorization: Token ...
    return:
        [order_items]
            id
            order_id
            table
            meal_name
            quantity
            [order_item_cust]
                name
                [options]
    """
    restaurant = request.user.server.restaurant
    if restaurant is None:
        return JsonResponse({
            "status": "restaurant_not_set"
        })
    order_items = OrderItemToCookSerializer(
        OrderItem.objects.filter(order__restaurant=restaurant, status=OrderItem.COOKING)
            .order_by("id"),
        many=True
    ).data
    return JsonResponse({"order_items": order_items, "status": "success"})

# Get list of restaurant's order items to send and requests
# Uses django-rest-multiple-models to sort and send different models together
class ServerGetItemsToSend(FlatMultipleModelMixin, GenericAPIView):
    """
    header:
        Authorization: Token ...
    return:
        [OrderItem or Request]
            id
            order_id (only for OrderItem)
            table
            customer
            meal_name or request_name
            time
            type
    """

    # Sort combined query list by time
    sorting_fields = ['time']

    # Overrided function to build combined query list
    def get_querylist(self):
        restaurant = self.request.user.server.restaurant
        order_items = OrderItem.objects.filter(
            order__restaurant=restaurant,
            status=OrderItem.SENDING
        )
        requests = Request.objects.filter(request_option__restaurant=restaurant)

        querylist = [
            {'queryset': order_items, 'serializer_class': OrderItemToSendSerializer},
            {'queryset': requests, 'serializer_class': RequestSerializer}
        ]
        return querylist

    # GET request
    def get(self, request, *args, **kwargs):
        restaurant = request.user.server.restaurant
        if restaurant is None:
            return JsonResponse({
                "status": "restaurant_not_set"
            })
        return self.list(request, *args, **kwargs)

# POST request
# Update order item status
@api_view(['POST'])
def server_update_order_item_status(request):
    """
    header:
        Authorization: Token ...
    params:
        order_item_id
        status
    return:
        status
    """
    restaurant = request.user.server.restaurant
    item = OrderItem.objects.get(id=request.POST.get("order_item_id"))

    # Check if a restaurant's server is making the request
    if item.order.restaurant != restaurant:
        return JsonResponse({"status": "invalid_request"})

    order = item.order
    new_status = request.POST.get("status")

    # Update item with new status
    item.status = new_status
    item.save()

    # Check if order status needs to be updated
    if new_status == OrderItem.COMPLETE:
        if not OrderItem.objects.filter(order=order).exclude(status=OrderItem.COMPLETE).exists():
            order.status = Order.COMPLETE
            order.save()
    else:
        order.status = Order.ACTIVE
        order.save()

    return JsonResponse({"status": "success"})

# POST request
# Delete request
@api_view(['POST'])
def server_delete_request(request):
    """
    header:
        Authorization: Token ...
    params:
        id
    return:
        status
    """
    restaurant = request.user.server.restaurant
    request_object = Request.objects.get(id=request.POST.get("id"))

    # Check if a restaurant's server is making the request
    if request_object.request_option.restaurant != restaurant:
        return JsonResponse({"status": "invalid_request"})

    request_object.delete()

    return JsonResponse({"status": "success"})

# GET request
# Get server's information
@api_view()
def server_get_info(request):
    """
    header:
        Authorization: Token ...
    return:
        name
        email
        restaurant_name
        status
    """
    name = request.user.name
    email = request.user.email
    restaurant = request.user.server.restaurant
    restaurant_name = "none"
    if restaurant is not None:
        restaurant_name = restaurant.name
    return JsonResponse({
        "name": name,
        "email": email,
        "restaurant_name": restaurant_name,
        "status": "success"
    })
