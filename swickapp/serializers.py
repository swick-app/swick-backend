from rest_framework import serializers
from swickapp.models import Restaurant, Customer, Server, Meal, Order, OrderMeal

# Serialize restaurant object to JSON
class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ("id", "name", "address", "image")

# Serialize customer object to JSON
class CustomerSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="user.get_full_name")
    email = serializers.ReadOnlyField(source="user.get_email")

    class Meta:
        model = Customer
        fields = ("id", "name", "email")

# Serialize server object to JSON
class ServerSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="user.get_full_name")
    email = serializers.ReadOnlyField(source="user.get_email")

    class Meta:
        model = Server
        fields = ("id", "name", "email")

# Serialize meal object to JSON
class MealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meal
        fields = ("id", "name", "description", "price", "image")


# Serialize order meal objects to JSON
class OrderMealSerializer(serializers.ModelSerializer):
    meal = MealSerializer()

    class Meta:
        model = OrderMeal
        fields = ("id", "meal", "quantity", "total")

# Serialize order object to JSON
class OrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer()
    chef = ServerSerializer()
    server = ServerSerializer()
    restaurant = RestaurantSerializer()
    server = ServerSerializer()
    status = serializers.ReadOnlyField(source = "get_status_display")
    order_meal = OrderMealSerializer(many = True)

    class Meta:
        model = Order
        fields = ("id", "customer", "chef", "server", "restaurant", "table",
        "total", "order_time", "status", "order_meal")
