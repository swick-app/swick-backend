from rest_framework import serializers
from django.templatetags.static import static
from .models import Restaurant, Meal, Customization, Order, OrderItem, \
    OrderItemCustomization, RequestOption, Request

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
    image = serializers.SerializerMethodField()

    class Meta:
        model = Meal
        fields = ("id", "name", "description", "price", "image")

    def get_image(self, meal):
        if not meal.image:
            return static("img/nullimage.png")
        else:
            return meal.image.url

# Serialize customization object to JSON
class CustomizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customization
        fields = ("id", "name", "options", "price_additions", "min", "max")

# Serialize request option object to JSON
class RequestOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestOption
        exclude = ("restaurant",)

# Serialize request object to JSON
class RequestSerializer(serializers.ModelSerializer):
    customer = serializers.ReadOnlyField(source="customer.user.name")
    request_name = serializers.ReadOnlyField(source="request_option.name")
    time = serializers.ReadOnlyField(source="request_time")

    class Meta:
        model = Request
        fields = ("id", "table", "customer", "request_name", "time")

##### ORDER SERIALIZER HELPERS #####

# Serialize order item customization objects to JSON
class OrderItemCustomizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemCustomization
        fields = ("customization_name", "options")

# Serialize order item objects to JSON
class OrderItemSerializer(serializers.ModelSerializer):
    order_item_cust = OrderItemCustomizationSerializer(many=True)
    status = serializers.ReadOnlyField(source="get_status_display")

    class Meta:
        model = OrderItem
        fields = ("id", "meal_name", "quantity", "total", "status", "order_item_cust")

##### ORDER SERIALIZERS #####

# Serialize order object to JSON for customer
class OrderSerializerForCustomer(serializers.ModelSerializer):
    restaurant = serializers.ReadOnlyField(source="restaurant.name")
    status = serializers.ReadOnlyField(source="get_status_display")

    class Meta:
        model = Order
        fields = ("id", "restaurant", "order_time", "status")

# Serialize order details to JSON for customer
class OrderDetailsSerializerForCustomer(serializers.ModelSerializer):
    restaurant = serializers.ReadOnlyField(source="restaurant.name")
    order_item = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("restaurant", "order_time", "total", "order_item")

    # Needed to order order items
    def get_order_item(self, instance):
        order_items = instance.order_item.all().order_by('id')
        return OrderItemSerializer(order_items, many=True).data

# Serialize orders to JSON for server
class OrderSerializerForServer(serializers.ModelSerializer):
    customer = serializers.ReadOnlyField(source="customer.user.name")
    status = serializers.ReadOnlyField(source="get_status_display")

    class Meta:
        model = Order
        fields = ("id", "customer", "order_time", "status")

# Serialize order details to JSON for server
class OrderDetailsSerializerForServer(serializers.ModelSerializer):
    customer = serializers.ReadOnlyField(source="customer.user.name")
    order_item = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("customer", "table", "order_time", "total", "order_item")

    # Needed to order order items
    def get_order_item(self, instance):
        order_items = instance.order_item.all().order_by('id')
        return OrderItemSerializer(order_items, many=True).data

# Serialize order item for "to cook" display to JSON for server
class OrderItemToCookSerializer(serializers.ModelSerializer):
    order_id = serializers.ReadOnlyField(source="order.id")
    table = serializers.ReadOnlyField(source="order.table")
    order_item_cust = OrderItemCustomizationSerializer(many=True)

    class Meta:
        model = OrderItem
        fields = ("id", "order_id", "table", "meal_name", "quantity", "order_item_cust")

# Serialize order item for "to send" display JSON for server
class OrderItemToSendSerializer(serializers.ModelSerializer):
    order_id = serializers.ReadOnlyField(source="order.id")
    table = serializers.ReadOnlyField(source="order.table")
    customer = serializers.ReadOnlyField(source="order.customer.user.name")
    time = serializers.ReadOnlyField(source="order.order_time")

    class Meta:
        model = OrderItem
        fields = ("id", "order_id", "table", "customer", "meal_name", "time")
