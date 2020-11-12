from django.templatetags.static import static
from rest_framework import serializers

from .models import (Category, Customization, Meal, Order, OrderItem,
                     OrderItemCustomization, Request, RequestOption,
                     Restaurant)


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ("id", "name", "address", "image")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        exclude = ("restaurant",)


class MealSerializer(serializers.ModelSerializer):
    tax = serializers.ReadOnlyField(source="tax_category.tax")
    image = serializers.SerializerMethodField()

    class Meta:
        model = Meal
        fields = ("id", "name", "description", "price", "tax", "image")

    def get_image(self, meal):
        if not meal.image:
            return
        request = self.context.get('request')
        return request.build_absolute_uri(meal.image.url)


class CustomizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customization
        fields = ("id", "name", "options", "price_additions", "min", "max")


class RequestOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestOption
        exclude = ("restaurant",)


class RequestSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source="customer.user.name")
    request_name = serializers.ReadOnlyField(source="request_option.name")
    time = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%Z", source="request_time")

    class Meta:
        model = Request
        fields = ("id", "table", "customer_name", "request_name", "time")

##### ORDER SERIALIZER HELPERS #####


class OrderItemCustomizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemCustomization
        fields = ("id", "customization_name", "options")


class OrderItemSerializer(serializers.ModelSerializer):
    order_item_cust = OrderItemCustomizationSerializer(many=True)
    status = serializers.ReadOnlyField(source="get_status_display")

    class Meta:
        model = OrderItem
        fields = ("id", "meal_name", "quantity",
                  "total", "status", "order_item_cust")

##### ORDER SERIALIZERS #####


class OrderSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.ReadOnlyField(source="restaurant.name")
    customer_name = serializers.ReadOnlyField(source="customer.user.name")
    status = serializers.ReadOnlyField(source="get_status_display")

    class Meta:
        model = Order
        fields = ("id", "restaurant_name",
                  "customer_name", "order_time", "status")


class OrderDetailsSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source="customer.user.name")
    cooking_order_items = serializers.SerializerMethodField()
    sending_order_items = serializers.SerializerMethodField()
    complete_order_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("id", "customer_name", "table", "order_time", "subtotal", "tax", "tip",
                  "total", "cooking_order_items", "sending_order_items", "complete_order_items")

    def get_order_items(self, order, status):
        order_items = order.order_item.filter(status=status).order_by('id')
        return OrderItemSerializer(order_items, many=True).data

    def get_cooking_order_items(self, instance):
        return self.get_order_items(instance, OrderItem.COOKING)

    def get_sending_order_items(self, instance):
        return self.get_order_items(instance, OrderItem.SENDING)

    def get_complete_order_items(self, instance):
        return self.get_order_items(instance, OrderItem.COMPLETE)


class OrderItemToCookSerializer(serializers.ModelSerializer):
    order_id = serializers.ReadOnlyField(source="order.id")
    order_item_cust = OrderItemCustomizationSerializer(many=True)

    class Meta:
        model = OrderItem
        fields = ("id", "order_id", "meal_name",
                  "quantity",  "order_item_cust")


class OrderItemToSendSerializer(serializers.ModelSerializer):
    order_id = serializers.ReadOnlyField(source="order.id")
    customer_name = serializers.ReadOnlyField(
        source="order.customer.user.name")
    table = serializers.ReadOnlyField(source="order.table")
    time = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", source="order.order_time")

    class Meta:
        model = OrderItem
        fields = ("id", "order_id", "customer_name",
                  "table", "meal_name", "time")
