import json
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.models import AccessToken
from swickapp.models import Restaurant, Meal, Order, OrderItem
from swickapp.serializers import RestaurantSerializer, MealSerializer, OrderSerializer
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

        # Calculate order total
        order_items = json.loads(request.POST["order_items"])
        order_total = 0
        for item in order_items:
            order_total += Meal.objects.get(id = item["meal_id"]).price * item["quantity"]

        # INSERT STRIPE PAYMENT HERE

        # Create an order in database
        order = Order.objects.create(
            customer = access_token.user.customer,
            restaurant_id = request.POST["restaurant_id"],
            table = request.POST["table"],
            total = order_total,
            status = Order.COOKING
        )
        # Create order items in database
        for item in order_items:
            # Calculate item total
            item_total = Meal.objects.get(id = item["meal_id"]).price * item["quantity"]
            OrderItem.objects.create(
                order = order,
                meal_id = item["meal_id"],
                quantity = item["quantity"],
                total = item_total
            )

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
