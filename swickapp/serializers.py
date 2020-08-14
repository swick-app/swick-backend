from rest_framework import serializers
from swickapp.models import Restaurant, Customer, Server, Meal, Customization, \
    Order, OrderItem, OrderItemCustomization

# Serialize restaurant object to JSON
class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ("id", "name", "address", "image")

# Serialize meal category to JSON
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Meal
        fields = ("category",)

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

##### ORDER SERIALIZER HELPERS #####

# Serialize order item customization objects to JSON
class OrderItemCustomizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemCustomization
        fields = ("customization_name", "options")

# Serialize order item objects to JSON
class OrderItemSerializer(serializers.ModelSerializer):
    order_item_cust = OrderItemCustomizationSerializer(many = True)

    class Meta:
        model = OrderItem
        fields = ("meal_name", "quantity", "total", "order_item_cust")


# Serialize restaurant object to JSON
class OrderRestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ("name",)

# Serialize customer object to JSON
class OrderCustomerSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="user.get_full_name")

    class Meta:
        model = Customer
        fields = ("name",)

# Serialize server object to JSON
class OrderServerSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="user.get_full_name")

    class Meta:
        model = Server
        fields = ("name",)

##### ORDER SERIALIZERS #####

# Serialize order object to JSON for customer
class OrderSerializerForCustomer(serializers.ModelSerializer):
    restaurant = OrderRestaurantSerializer()
    status = serializers.ReadOnlyField(source = "get_status_display")

    class Meta:
        model = Order
        fields = ("id", "restaurant", "status", "order_time")

# Serialize order object to JSON for server
class OrderSerializerForServer(serializers.ModelSerializer):
    customer = OrderCustomerSerializer()

    class Meta:
        model = Order
        fields = ("id", "customer", "table", "order_time")

# Serialize order details to JSON for customer
class OrderDetailsSerializerForCustomer(serializers.ModelSerializer):
    status = serializers.ReadOnlyField(source = "get_status_display")
    server = OrderServerSerializer()
    order_item = OrderItemSerializer(many = True)

    class Meta:
        model = Order
        fields = ("status", "table", "server", "total", "order_item")

# Serialize order details to JSON for server
class OrderDetailsSerializerForServer(serializers.ModelSerializer):
    chef = OrderServerSerializer()
    server = OrderServerSerializer()
    order_item = OrderItemSerializer(many = True)

    class Meta:
        model = Order
        fields = ("chef", "server", "total", "order_item")
