import json

from django.urls import reverse
from rest_framework.test import APITestCase
from swickapp.models import Order, Category, Customization, Meal, Restaurant, RequestOption, Request, OrderItemCustomization, OrderItem
from swickapp.serializers import (CategorySerializer, CustomizationSerializer,
                                  MealSerializer, OrderDetailsSerializer,
                                  OrderItemCustomizationSerializer,
                                  OrderItemSerializer,
                                  OrderItemToCookSerializer,
                                  OrderItemToSendSerializer, OrderSerializer,
                                  RequestOptionSerializer, RequestSerializer,
                                  RestaurantSerializer)


class SerializersTest(APITestCase):
    fixtures = ['testdata.json']

    def test_restaurant_serializer(self):
        restaurant = Restaurant.objects.get(id=26)
        data = RestaurantSerializer(restaurant).data
        self.assertEqual(set(data.keys()), {'id', 'name', 'address', 'image'})

    def test_category_serializer(self):
        category = Category.objects.get(id=12)
        data = CategorySerializer(category).data
        self.assertEqual(set(data.keys()), {'id', 'name'})

    def test_meal_serializer(self):
        # No image
        meal = Meal.objects.get(id=17)
        data = MealSerializer(meal).data
        self.assertEqual(set(data.keys()), {
                         "id", "name", "description", "price", "tax", "image"})
        self.assertEqual(data['tax'], 6.000)
        self.assertEqual(data['image'], None)
        # Image present
        resp = self.client.post(reverse('customer_get_meals', args=(26, 13)))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        meals = content['meals']
        self.assertEqual(meals[0]['image'],
                         'http://testserver/mediafiles/image.jpg')

    def test_customization_serializer(self):
        customization = Customization.objects.get(id=7)
        data = CustomizationSerializer(customization).data
        self.assertEqual(set(data.keys()), {
                         "id", "name", "options", "price_additions", "min", "max"})

    def test_request_option_serializer(self):
        option = RequestOption.objects.get(id=1)
        data = RequestOptionSerializer(option).data
        self.assertEqual(set(data.keys()), {'id', 'name'})

    def test_request_serializer(self):
        request = Request.objects.get(id=18)
        data = RequestSerializer(request).data
        self.assertEqual(set(data.keys()), {
                         "id", "table", "customer_name", "request_name", "time"})
        self.assertEqual(data['customer_name'], 'Sean Lu')
        self.assertEqual(data['request_name'], 'Water')
        self.assertEqual(data['time'], '2020-11-14T05:22:18Z')

    def test_order_item_customization_serializer(self):
        cust = OrderItemCustomization.objects.get(id=21)
        data = OrderItemCustomizationSerializer(cust).data
        self.assertEqual(set(data.keys()), {
                         "id", "customization_name", "options"})

    def test_order_item_serializer(self):
        item = OrderItem.objects.get(id=49)
        data = OrderItemSerializer(item).data
        self.assertEqual(set(data.keys()), {
                         "id", "meal_name", "quantity", "total", "status", "order_item_cust"})
        self.assertEqual(data['status'], "Cooking")
        custs = data['order_item_cust']
        self.assertEqual(custs[0]['id'], 21)
        self.assertEqual(custs[1]['id'], 22)

    def test_order_serializer(self):
        order = Order.objects.get(id=35)
        data = OrderSerializer(order).data
        self.assertEqual(set(data.keys()), {
                         "id", "restaurant_name", "customer_name", "order_time", "status"})
        self.assertEqual(data['restaurant_name'], "Ice Cream Shop")
        self.assertEqual(data['customer_name'], "Sean Lu")
        self.assertEqual(data['status'], "Active")

    def test_order_details_serializer(self):
        order = Order.objects.get(id=35)
        data = OrderDetailsSerializer(order).data
        self.assertEqual(set(data.keys()), {"id", "customer_name", "table", "order_time", "subtotal",
                                            "tax", "tip", "total", "cooking_order_items", "sending_order_items", "complete_order_items"})
        self.assertEqual(data['customer_name'], "Sean Lu")
        cooking_items = data['cooking_order_items']
        self.assertEqual(cooking_items[0]['id'], 49)
        sending_items = data['sending_order_items']
        self.assertEqual(sending_items[0]['id'], 50)
        complete_items = data['complete_order_items']
        self.assertEqual(complete_items[0]['id'], 51)

    def test_order_item_to_cook_serializer(self):
        item = OrderItem.objects.get(id=49)
        data = OrderItemToCookSerializer(item).data
        self.assertEqual(set(data.keys()), {
                         "id", "order_id", "meal_name", "quantity",  "order_item_cust"})
        self.assertEqual(data['order_id'], 35)
        custs = data['order_item_cust']
        self.assertEqual(custs[0]['id'], 21)
        self.assertEqual(custs[1]['id'], 22)

    def test_order_item_to_cook_serializer(self):
        item = OrderItem.objects.get(id=50)
        data = OrderItemToSendSerializer(item).data
        self.assertEqual(set(data.keys()), {
                         "id", "order_id", "customer_name", "table", "meal_name", "time"})
        self.assertEqual(data['order_id'], 35)
        self.assertEqual(data['customer_name'], 'Sean Lu')
        self.assertEqual(data['table'], 2)
        self.assertEqual(data['time'], '2020-11-14T05:21:47Z')
