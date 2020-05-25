import json
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.models import AccessToken
from swickapp.models import Restaurant, Meal, Customization, Order, OrderItem, \
    OrderItemCustomization
from swickapp.serializers import RestaurantSerializer, MealSerializer, \
    CustomizationSerializer, OrderSerializer
import stripe

##### CUSTOMER APIS #####

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
    """
    restaurants = RestaurantSerializer(
        Restaurant.objects.all().order_by("-id"),
        many = True,
        # Needed to get absolute image url
        context = {"request": request}
    ).data

    return JsonResponse({"restaurants": restaurants})

# GET request
# Get menu associated with restaurant_id
def customer_get_menu(request, restaurant_id):
    """
    return:
        [menu]
            id
            name
            description
            price
            image
    """
    meals = MealSerializer(
        Meal.objects.filter(restaurant_id = restaurant_id).order_by("-id"),
        many = True,
        context = {"request": request}
    ).data
    return JsonResponse({"menu": meals})

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
    """
    customizations = CustomizationSerializer(
        Customization.objects.filter(meal_id = meal_id).order_by("-id"),
        many = True,
        context = {"request": request}
    ).data
    return JsonResponse({"customizations": customizations})

# POST request: CSRF token not needed because access token is checked
# Create order in database
@csrf_exempt
def customer_place_order(request):
    """
    params:
        access_token
        restaurant_id
        table
        [order_items]
            meal_id
            quantity
            [customizations]
                customization_id
                [options]
        stripe_token (test tokens at https://stripe.com/docs/testing#cards)

    return:
        status
        error (if status == failed)
    """
    if request.method == "POST":
        # Try to get unexpired Django access token object from database with
        # access token from POST request
        access_token = AccessToken.objects.get(token = request.POST.get("access_token"),
            expires__gt = timezone.now())

        # Create order in database
        order = Order.objects.create(
            customer = access_token.user.customer,
            restaurant_id = request.POST["restaurant_id"],
            table = request.POST["table"],
            status = Order.COOKING
        )
        # Variable for calculating order total
        order_total = 0
        order_items = json.loads(request.POST["order_items"])
        # Loop through order items
        for item in order_items:
            # Create order item in database
            order_item = OrderItem.objects.create(
                order = order,
                meal_id = item["meal_id"],
                meal_price = Meal.objects.get(id = item["meal_id"]).price,
                quantity = item["quantity"]
            )
            # Variable for calculating price of one meal in order item
            meal_total = order_item.meal_price
            # Loop through customizations of order items
            for cust in item["customizations"]:
                cust_id = cust["customization_id"]
                cust_object = Customization.objects.get(id = cust_id)
                options = cust["options"]

                options = []
                price_additions = []
                for opt_idx in cust["options"]:
                    options.append(cust_object.options[opt_idx])
                    price_additions.append(cust_object.price_additions[opt_idx])
                    meal_total += cust_object.price_additions[opt_idx]

                # Extract price additions corresponding with options
                # price_additions = []
                # for option in options:
                #     for i, opt in enumerate(cust_object.options):
                #         if option == opt:
                #             price_additions.append(cust_object.price_additions[i])
                #             meal_total += cust_object.price_additions[i]
                # Create order item customization in database
                order_item_customization = OrderItemCustomization.objects.create(
                    order_item = order_item,
                    customization_id = cust_id,
                    options = options,
                    price_additions = price_additions
                )
            # Calculate order item total and update field
            order_item.total = meal_total * order_item.quantity
            order_item.save()
            order_total += order_item.total
        # Update order total field
        order.total = order_total
        order.save()

        # INSERT STRIPE PAYMENT HERE
        # If it fails, delete order from database

        return JsonResponse({"status": "success"})

# GET request
# Get list of customer's orders
def customer_get_orders(request):
    """
    params:
        access_token
    return:
        restaurant
            name
        server
            name
        [order_item]
            meal
                name
            quantity
            total
        status
        order_time
        total
        table
    """
    access_token = AccessToken.objects.get(token = request.GET.get("access_token"),
        expires__gt = timezone.now())
    customer = access_token.user.customer
    orders = OrderSerializer(
        Order.objects.filter(customer = customer).order_by("-id"),
        many = True,
        context = {"request": request}
    ).data

    return JsonResponse({"orders": orders})

# GET request
# Get user's information
def get_user_info(request):
    """
    params:
        access_token
    return:
        name
        email
    """
    access_token = AccessToken.objects.get(token = request.GET.get("access_token"),
        expires__gt = timezone.now())
    name = access_token.user.get_full_name()
    email = access_token.user.email

    return JsonResponse({"name": name, "email": email})
