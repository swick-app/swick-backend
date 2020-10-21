from rest_framework import serializers
from django.templatetags.static import static
from .models import Restaurant, Category, Meal, Customization, Order, OrderItem, \
    OrderItemCustomization, RequestOption, Request

# Serialize restaurant object to JSON
class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ("id", "name", "address", "image")

# Serialize meal category to JSON
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        exclude = ("restaurant",)

# Serialize meal object to JSON
class MealSerializer(serializers.ModelSerializer):
    tax = serializers.ReadOnlyField(source="tax_category.tax")
    image = serializers.SerializerMethodField()
    class Meta:
        model = Meal
        fields = ("id", "name", "description", "price", "tax", "image")

    def get_image(self, meal):
        if not meal.image:
            image_url = static("img/nullimage.png")
        else:
            image_url = meal.image.url
        request = self.context.get('request')
        return request.build_absolute_uri(image_url)

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
    customer_name = serializers.ReadOnlyField(source="customer.user.name")
    request_name = serializers.ReadOnlyField(source="request_option.name")
    time = serializers.ReadOnlyField(source="request_time")

    class Meta:
        model = Request
        fields = ("id", "table", "customer_name", "request_name", "time")

##### ORDER SERIALIZER HELPERS #####

# Serialize order item customization objects to JSON
class OrderItemCustomizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemCustomization
        fields = ("id", "customization_name", "options")

# Serialize order item objects to JSON
class OrderItemSerializer(serializers.ModelSerializer):
    order_item_cust = OrderItemCustomizationSerializer(many=True)
    status = serializers.ReadOnlyField(source="get_status_display")

    class Meta:
        model = OrderItem
        fields = ("id", "meal_name", "quantity", "total", "status", "order_item_cust")

# Get order items by status
def get_order_items(order, status):
    order_items = order.order_item.filter(status=status).order_by('id')
    return OrderItemSerializer(order_items, many=True).data


##### ORDER SERIALIZERS #####

# Serialize order object to JSON for customer
class OrderSerializerForCustomer(serializers.ModelSerializer):
    restaurant_name = serializers.ReadOnlyField(source="restaurant.name")
    status = serializers.ReadOnlyField(source="get_status_display")

    class Meta:
        model = Order
        fields = ("id", "restaurant_name", "order_time", "status")

# Serialize order details to JSON for customer
class OrderDetailsSerializerForCustomer(serializers.ModelSerializer):
    restaurant_name = serializers.ReadOnlyField(source="restaurant.name")
    cooking_order_items = serializers.SerializerMethodField()
    sending_order_items = serializers.SerializerMethodField()
    complete_order_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("id", "restaurant_name", "order_time", "subtotal", "tax", "tip", "total",
            "cooking_order_items", "sending_order_items", "complete_order_items")

    def get_cooking_order_items(self, instance):
        return get_order_items(instance, OrderItem.COOKING)

    def get_sending_order_items(self, instance):
        return get_order_items(instance, OrderItem.SENDING)

    def get_complete_order_items(self, instance):
        return get_order_items(instance, OrderItem.COMPLETE)

# Serialize orders to JSON for server
class OrderSerializerForServer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source="customer.user.name")
    status = serializers.ReadOnlyField(source="get_status_display")

    class Meta:
        model = Order
        fields = ("id", "customer_name", "order_time", "status")

# Serialize order details to JSON for server
class OrderDetailsSerializerForServer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source="customer.user.name")
    cooking_order_items = serializers.SerializerMethodField()
    sending_order_items = serializers.SerializerMethodField()
    complete_order_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("id", "customer_name", "table", "order_time", "subtotal", "tax", "tip", "total",
            "cooking_order_items", "sending_order_items", "complete_order_items")

    def get_cooking_order_items(self, instance):
        return get_order_items(instance, OrderItem.COOKING)

    def get_sending_order_items(self, instance):
        return get_order_items(instance, OrderItem.SENDING)

    def get_complete_order_items(self, instance):
        return get_order_items(instance, OrderItem.COMPLETE)

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
    customer_name = serializers.ReadOnlyField(source="order.customer.user.name")
    time = serializers.ReadOnlyField(source="order.order_time")

    class Meta:
        model = OrderItem
        fields = ("id", "order_id", "table", "customer_name", "meal_name", "time")
