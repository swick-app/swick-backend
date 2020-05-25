from rest_framework import serializers
from swickapp.models import Restaurant, Customer, Server, Meal, Customization, \
    Order, OrderItem

# Serialize restaurant object to JSON
class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ("id", "name", "address", "image")

# Serialize meal object to JSON
class MealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meal
        fields = ("id", "name", "description", "price", "image")

# Serialize customization object to JSON
class CustomizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customization
        fields = ("id", "name", "options", "price_additions", "min", "max")

##### ORDER SERIALIZERS #####

# Serialize restaurant object to JSON
class OrderRestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ("name",)

# Serialize server object to JSON
class OrderServerSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="user.get_full_name")

    class Meta:
        model = Server
        fields = ("name",)

# Serialize meal object to JSON
class OrderMealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meal
        fields = ("name",)

# Serialize order item objects to JSON
class OrderItemSerializer(serializers.ModelSerializer):
    meal = OrderMealSerializer()

    class Meta:
        model = OrderItem
        fields = ("meal", "quantity", "total")

# Serialize order object to JSON
class OrderSerializer(serializers.ModelSerializer):
    restaurant = OrderRestaurantSerializer()
    server = OrderServerSerializer()
    order_item = OrderItemSerializer(many = True)
    status = serializers.ReadOnlyField(source = "get_status_display")

    class Meta:
        model = Order
        fields = ("restaurant", "server", "order_item", "status", "order_time",
        "total", "table")
