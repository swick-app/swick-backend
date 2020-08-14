import json
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.models import AccessToken
from swickapp.models import Restaurant, Meal, Customization, Order, OrderItem, \
    OrderItemCustomization, Server
from swickapp.serializers import RestaurantSerializer, CategorySerializer, MealSerializer, \
    CustomizationSerializer, OrderSerializerForCustomer, OrderDetailsSerializerForCustomer, \
    OrderSerializerForServer, OrderDetailsSerializerForServer
import stripe
from swick.settings import STRIPE_API_KEY

stripe.api_key = STRIPE_API_KEY

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
        status
    """
    restaurants = RestaurantSerializer(
        Restaurant.objects.all().order_by("name"),
        many = True,
        # Needed to get absolute image url
        context = {"request": request}
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
        restaurant_object = Restaurant.objects.get(id = restaurant_id)
    except Restaurant.DoesNotExist:
        return JsonResponse({"status": "restaurant_does_not_exist"})
    restaurant = RestaurantSerializer(
        restaurant_object,
        context = {"request": request}
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
        Meal.objects.all().order_by("category").distinct("category"),
        many = True,
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
            Meal.objects.filter(restaurant_id = restaurant_id).order_by("name"),
            many = True,
            context = {"request": request}
        ).data
    else:
        meals = MealSerializer(
            Meal.objects.filter(restaurant_id = restaurant_id, category = category).order_by("name"),
            many = True,
            context = {"request": request}
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
    customizations = CustomizationSerializer(
        Customization.objects.filter(meal_id = meal_id).order_by("name"),
        many = True,
        context = {"request": request}
    ).data
    return JsonResponse({"customizations": customizations, "status": "success"})

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
                meal_name = Meal.objects.get(id = item["meal_id"]).name,
                meal_price = Meal.objects.get(id = item["meal_id"]).price,
                quantity = item["quantity"]
            )
            # Variable for calculating price of one meal in order item
            meal_total = order_item.meal_price
            # Loop through customizations of order items
            for cust in item["customizations"]:
                cust_id = cust["customization_id"]
                cust_object = Customization.objects.get(id = cust_id)
                # Build options and price_additions arrays with option indices
                options = []
                price_additions = []
                for opt_idx in cust["options"]:
                    options.append(cust_object.options[opt_idx])
                    price_additions.append(cust_object.price_additions[opt_idx])
                    meal_total += cust_object.price_additions[opt_idx]

                # Create order item customization in database
                order_item_customization = OrderItemCustomization.objects.create(
                    order_item = order_item,
                    customization_name = Customization.objects.get(id = cust_id).name,
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

        # Create Stripe charge
        stripe_token = request.POST["stripe_token"]
        charge = stripe.Charge.create(
            amount = int(order_total * 100), # Amount in cents
            currency = "usd",
            source = stripe_token,
            description = "Swick order"
        )
        if charge.status == "failed":
            # Delete order if charge failed
            order.delete()
            return JsonResponse({"status": "failed", "error": "Stripe transaction error"})

        return JsonResponse({"status": "success"})

# GET request
# Get list of customer's orders
def customer_get_orders(request):
    """
    params:
        access_token
    return:
        [orders]
            id
            restaurant
                name
            status
            order_time
        status
    """
    access_token = AccessToken.objects.get(token = request.GET.get("access_token"),
        expires__gt = timezone.now())
    customer = access_token.user.customer
    orders = OrderSerializerForCustomer(
        Order.objects.filter(customer = customer, total__isnull = False).order_by("-id"),
        many = True
    ).data

    return JsonResponse({"orders": orders, "status": "success"})

# GET request
# Get customer's order details
def customer_get_order_details(request, order_id):
    """
    params:
        access_token
    return:
        order_details
            status
            table
            server
                name
            total
            [order_item]
                meal
                    name
                quantity
                total
        status
    """
    access_token = AccessToken.objects.get(token = request.GET.get("access_token"),
        expires__gt = timezone.now())
    order = Order.objects.get(id = order_id)
    # Check if order's customer is the customer making the request
    if order.customer == access_token.user.customer:
        order_details = OrderDetailsSerializerForCustomer(
            order
        ).data
        return JsonResponse({"order_details": order_details, "status": "success"})

# GET request
# Get customer's information
def customer_get_info(request):
    """
    params:
        access_token
    return:
        name
        email
        status
    """
    access_token = AccessToken.objects.get(token = request.GET.get("access_token"),
        expires__gt = timezone.now())
    name = access_token.user.get_full_name()
    email = access_token.user.email

    return JsonResponse({"name": name, "email": email, "status": "success"})

##### SERVER APIS #####

# GET request
# Get list of restaurant's orders
def server_get_orders(request, status):
    """
    params:
        access_token
    return:
        [orders]
            id
            customer
                name
            table
            order_time
        status
    """
    access_token = AccessToken.objects.get(token = request.GET.get("access_token"),
        expires__gt = timezone.now())
    restaurant = access_token.user.server.restaurant
    if restaurant is None:
        return JsonResponse({
            "status": "restaurant_not_set"
        })
    orders = OrderSerializerForServer(
        Order.objects.filter(restaurant = restaurant, status = status, total__isnull = False)
            .order_by("id"),
        many = True
    ).data

    return JsonResponse({"orders": orders, "status": "success"})

# GET request
# Get restaurant's order details
def server_get_order_details(request, order_id):
    """
    params:
        access_token
    return:
        order_details
            chef
                name
            server
                name
            total
            [order_item]
                meal
                    name
                quantity
                total
        status
    """
    access_token = AccessToken.objects.get(token = request.GET.get("access_token"),
        expires__gt = timezone.now())
    restaurant = access_token.user.server.restaurant
    order = Order.objects.get(id = order_id)
    # Check if a restaurant's server is making the request
    if order.restaurant == restaurant:
        order_details = OrderDetailsSerializerForServer(
            order
        ).data
        return JsonResponse({"order_details": order_details, "status": "success"})

# POST request: CSRF token not needed because access token is checked
# Update order status
@csrf_exempt
def server_update_order_status(request):
    """
    params:
        access_token
        order_id
        status

    return:
        status
    """
    if request.method == "POST":
        access_token = AccessToken.objects.get(token = request.POST.get("access_token"),
            expires__gt = timezone.now())
        restaurant = access_token.user.server.restaurant
        order = Order.objects.get(id = request.POST.get("order_id"))
        # Check if a restaurant's server is making the request
        if order.restaurant == restaurant:
            status = request.POST.get("status")
            order.status = status
            if status == "2":
                order.chef = access_token.user.server
            elif status == "3":
                order.server = access_token.user.server
            order.save()
            return JsonResponse({"status": "success"})

# GET request
# Get server's information
def server_get_info(request):
    """
    params:
        access_token
    return:
        name
        email
        restaurant_name
        status
    """
    access_token = AccessToken.objects.get(token = request.GET.get("access_token"),
        expires__gt = timezone.now())
    name = access_token.user.get_full_name()
    email = access_token.user.email
    restaurant = access_token.user.server.restaurant
    restaurant_name = "none"
    if restaurant is not None:
        restaurant_name = restaurant.name
    return JsonResponse({
        "name": name,
        "email": email,
        "restaurant_name": restaurant_name,
        "status": "success"
    })
