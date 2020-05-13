import json
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.models import AccessToken
from swickapp.models import Restaurant, Meal, Order, OrderMeal
from swickapp.serializers import RestaurantSerializer, MealSerializer, OrderSerializer
import stripe
from swick.settings import STRIPE_API_KEY
stripe.api_key = STRIPE_API_KEY

##### CUSTOMER APIS #####

# GET request
# Get list of restaurants
def customer_get_restaurants(request):
    """
    return:
        restaurants
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
        meals
    """
    meals = MealSerializer(
        Meal.objects.filter(restaurant_id = restaurant_id).order_by("-id"),
        many = True,
        context = {"request": request}
    ).data
    return JsonResponse({"meals": meals})

# POST request: CSRF token not needed because access token is checked
# Create order in database
@csrf_exempt
def customer_add_order(request):
    """
    params:
        access_token
        restaurant_id
        table
        details
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
        # Django server is in UTC time
        try:
            access_token = AccessToken.objects.get(token = request.POST.get("access_token"),
                expires__gt = timezone.now())
        except:
            return JsonResponse({"status": "failed", "error": "Invalid access token."})

        # Calculate order total
        details = json.loads(request.POST["details"])
        order_total = 0
        for meal in details:
            order_total += Meal.objects.get(id = meal["meal_id"]).price * meal["quantity"]

        # Execute a Stripe charge
        stripe_token = request.POST["stripe_token"]
        charge = stripe.Charge.create(
            # Amount in cents
            amount = int(order_total * 100),
            currency = "usd",
            source = stripe_token,
            description = "Swick order"
        )

        # Return error if Stripe charge failed
        if charge.status == "failed":
            return JsonResponse({"status": "failed", "error": "Failed to connect to Stripe."})

        # Create an order in database
        order = Order.objects.create(
            customer = access_token.user.customer,
            restaurant_id = request.POST["restaurant_id"],
            table = request.POST["table"],
            total = order_total,
            status = Order.COOKING
        )
        # Create order meals in database
        for meal in details:
            # Calculate meal total
            meal_total = Meal.objects.get(id = meal["meal_id"]).price * meal["quantity"]
            OrderMeal.objects.create(
                order = order,
                meal_id = meal["meal_id"],
                quantity = meal["quantity"],
                total = meal_total
            )

        return JsonResponse({"status": "success"})

# GET request: Check access token because private info
# Get list of customer's orders
def customer_get_orders(request):
    access_token = AccessToken.objects.get(token = request.GET.get("access_token"),
        expires__gt = timezone.now())
    customer = access_token.user.customer
    orders = OrderSerializer(
        Order.objects.filter(customer = customer),
        many = True,
        context = {"request": request}
    ).data

    return JsonResponse({"orders": orders})
