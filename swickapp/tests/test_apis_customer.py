import json
import stripe
import swickapp.apis_customer

from decimal import Decimal
from django.urls import reverse
from django.http import JsonResponse
from rest_framework.test import APITestCase
from swickapp.models import Request, User, Customer, Order, OrderItem, OrderItemCustomization
from unittest.mock import Mock, patch


class APICustomerTest(APITestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="seanlu99@gmail.com")
        self.client.force_authenticate(user)
        self.customer = user.customer

    @patch('stripe.Customer.create')
    def test_login(self, customer_create_mock):
        customer_create_mock.return_value.id = "mock_stripe_cust_id"
        # POST success: use existing customer, user has name
        resp = self.client.post(reverse('customer_login'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['name_set'], True)
        self.assertEqual(content['id'], 11)
        # POST success: create new customer, user has no name
        user = User.objects.get(email="simon@gmail.com")
        self.client.force_authenticate(user)
        resp = self.client.post(reverse('customer_login'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['name_set'], False)
        Customer.objects.get(user__email="simon@gmail.com")
        # POST error: invalid token
        self.client.force_authenticate(user=None)
        resp = self.client.post(reverse('customer_login'))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'invalid_token')

    @patch('pusher.Pusher')
    def test_pusher_auth(self, pusher_mock):
        pusher_mock.return_value.authenticate.return_value = {
            "pusher_payload": "mock_pusher_payload"}
        # POST success
        resp = self.client.post(reverse('customer_pusher_auth'), data={
            "channel_name": "private-customer-11",
            "socket_id": "1"
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content["pusher_payload"], "mock_pusher_payload")
        # POST error: channel does not start with "private-customer-"
        resp = self.client.post(reverse('customer_pusher_auth'), data={
            "channel_name": "private-restaurant-11",
            "socket_id": "1"
        })
        self.assertEqual(resp.status_code, 403)
        # POST error: channel is not of correct format
        resp = self.client.post(reverse('customer_pusher_auth'), data={
            "channel_name": "private-customer-11-35",
            "socket_id": "1"
        })
        self.assertEqual(resp.status_code, 403)
        # POST error: customer channel is not requested by user
        resp = self.client.post(reverse('customer_pusher_auth'), data={
            "channel_name": "private-customer-22",
            "socket_id": "1"
        })
        self.assertEqual(resp.status_code, 403)
        # POST error: channel number is not an integer
        resp = self.client.post(reverse('customer_pusher_auth'), data={
            "channel_name": "private-customer-22.2",
            "socket_id": "1"
        })
        self.assertEqual(resp.status_code, 403)

    def test_get_restaurants(self):
        # GET success
        resp = self.client.get(reverse('customer_get_restaurants'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        restaurants = content['restaurants']
        self.assertEqual(len(restaurants), 2)
        self.assertEqual(restaurants[0]['name'], 'Ice Cream Shop')
        self.assertEqual(restaurants[1]['name'], 'The Cozy Diner')

    def test_get_restaurant(self):
        # GET success
        resp = self.client.get(reverse('customer_get_restaurant', args=(26,)))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        restaurant = content['restaurant']
        self.assertEqual(restaurant['name'], 'Ice Cream Shop')
        options = content['request_options']
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0]['name'], 'Water')
        self.assertEqual(options[1]['name'], 'Fork')
        # GET error: restaurant does not exist
        resp = self.client.get(reverse('customer_get_restaurant', args=(25,)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'restaurant_does_not_exist')

    def test_get_categories(self):
        # GET success
        resp = self.client.get(reverse('customer_get_categories', args=(26,)))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        categories = content['categories']
        self.assertEqual(len(categories), 2)
        self.assertEqual(categories[0]['name'], 'Drinks')
        self.assertEqual(categories[1]['name'], 'Entrees')
        # GET error: restaurant does not exist
        resp = self.client.get(reverse('customer_get_categories', args=(25,)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'restaurant_does_not_exist')

    def test_get_meals(self):
        # GET success: all meals
        resp = self.client.get(reverse('customer_get_meals', args=(26, 0)))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        meals = content['meals']
        self.assertEqual(len(meals), 3)
        self.assertEqual(meals[0]['name'], 'Cheeseburger')
        self.assertEqual(meals[2]['name'], 'Wine')
        # GET success: specific category
        resp = self.client.get(reverse('customer_get_meals', args=(26, 12)))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        meals = content['meals']
        self.assertEqual(len(meals), 2)
        self.assertEqual(meals[0]['name'], 'Cheeseburger')
        self.assertEqual(meals[1]['name'], 'Pizza')
        # GET error: restaurant does not exist
        resp = self.client.get(reverse('customer_get_meals', args=(25, 0)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'restaurant_does_not_exist')
        # GET error: category does not exist
        resp = self.client.get(reverse('customer_get_meals', args=(26, 11)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'category_does_not_exist')
        # GET error: category does not belong to restaurant
        resp = self.client.get(reverse('customer_get_meals', args=(26, 14)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'category_does_not_exist')

    def test_get_meal(self):
        # GET success
        resp = self.client.get(reverse('customer_get_meal', args=(17,)))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        customizations = content['customizations']
        self.assertEqual(len(customizations), 2)
        self.assertEqual(customizations[0]['name'], 'Size')
        self.assertEqual(customizations[1]['name'], 'Toppings')
        # GET error: meal does not exist
        resp = self.client.get(reverse('customer_get_meal', args=(16,)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'meal_does_not_exist')
        # GET error: meal is disabled
        resp = self.client.get(reverse('customer_get_meal', args=(21,)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'meal_disabled')

    @patch('swickapp.apis_customer.attempt_stripe_payment')
    @patch('swickapp.apis_customer.get_stripe_fee')
    def test_place_order(self, get_stripe_fee_mock, attempt_stripe_payment_mock):
        basic_meal_1 = '{"meal_id": 17, "quantity": 1, "customizations":[]}'
        basic_meal_2 = '{"meal_id": 18, "quantity": 2, "customizations":[]}'
        basic_meal_3 = '{"meal_id": 19, "quantity": 3, "customizations":[]}'
        disabled_meal = '{"meal_id": 21, "quantity": 3, "customizations":[]}'
        customization_1 = '{"customization_id": 7, "options": [1]}'
        customization_2 = '{"customization_id": 8, "options": [1, 2, 3]}'
        # Meal with one customization with one option
        customized_meal_1 = '{"meal_id": 17, "quantity": 1, "customizations":[' \
            + customization_1 + ']}'
        # Meal with one customization with multiple options
        customized_meal_2 = '{"meal_id": 17, "quantity": 1, "customizations":[' \
            + customization_2 + ']}'
        # Meal with multiple customizations with multiple options
        customized_meal_3 = '{"meal_id": 17, "quantity": 1, "customizations":[' + \
            customization_1 + ',' + customization_2 + ']}'
        # POST error: meal is disabled
        resp = self.client.post(reverse('customer_place_order'), data={
            "order_items": "[" + basic_meal_1 + "," + disabled_meal + "," +
            basic_meal_3 + "]",
            "payment_method_id": "card_1HpGwPBnGfJIkyujLkbU6qXr",
            "restaurant_id": 26,
            "table": 1,
            "tip": "nil"
        })
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "meal_disabled")
        self.assertEqual(content["meal_name"], "Sandwich")
        # POST success: Basic meals and successful payment attempt
        attempt_stripe_payment_mock.return_value = JsonResponse({
            "intent_status": "succeeded",
            "payment_intent": "valid_payment_intent_id",
            "client_secret": "mock_client_secret",
            "status": "success"
        })
        get_stripe_fee_mock.return_value = Decimal("3.50")
        resp = self.client.post(reverse('customer_place_order'), data={
            "order_items": "[" + basic_meal_1 + "," + basic_meal_2 + "," + basic_meal_3 + "]",
            "payment_method_id": "mock_payment_method_id",
            "restaurant_id": 26,
            "table": 1,
            "tip": "nil"
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "succeeded")
        order = Order.objects.order_by('-id').first()
        self.assertEqual(order.status, Order.ACTIVE)
        self.assertEqual(order.stripe_fee, Decimal("3.50"))
        self.assertEqual(order.subtotal, Decimal("45.00"))
        self.assertEqual(order.tip, None)
        self.assertEqual(order.tax, Decimal("3.15"))
        self.assertEqual(order.total, Decimal("48.15"))
        order_items = OrderItem.objects.order_by('-id')[:3]
        for item in order_items:
            self.assertEqual(item.order.id, order.id)
        # POST success: Basic meals and payment_intent requires action
        attempt_stripe_payment_mock.return_value = JsonResponse({
            "intent_status": "requires_action",
            "payment_intent": "valid_payment_intent_id",
            "client_secret": "mock_client_secret",
            "status": "success"
        })
        resp = self.client.post(reverse('customer_place_order'), data={
            "order_items": "[" + basic_meal_1 + "," + basic_meal_1 + "," + basic_meal_3 + "]",
            "payment_method_id": "mock_payment_method_id",
            "restaurant_id": 26,
            "table": 1,
            "tip": "nil"
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "requires_action")
        order = Order.objects.order_by('-id').first()
        self.assertEqual(order.status, Order.PROCESSING)
        self.assertEqual(order.stripe_payment_id, "valid_payment_intent_id")
        # POST success: Basic meals and payment_intent card error
        attempt_stripe_payment_mock.return_value = JsonResponse({
            "intent_status": "card_error",
            "payment_intent": "invalid_payment_intent_id",
            "client_secret": "mock_client_secret",
            "status": "success"
        })
        resp = self.client.post(reverse('customer_place_order'), data={
            "order_items": "[" + basic_meal_1 + "," + basic_meal_1 + "," + basic_meal_3 + "]",
            "payment_method_id": "invalid_payment_intent_id",
            "restaurant_id": 26,
            "table": 1,
            "tip": "nil"
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "card_error")
        order = Order.objects.order_by('-id').first()
        self.assertNotEqual(order.stripe_payment_id,
                            "invalid_payment_intent_id")
        # POST success: Custom meals and successful payment attempt
        attempt_stripe_payment_mock.return_value = JsonResponse({
            "intent_status": "succeeded",
            "payment_intent": "valid_payment_intent_id",
            "client_secret": "mock_client_secret",
            "status": "success"
        })
        resp = self.client.post(reverse('customer_place_order'), data={
            "order_items": "[" + customized_meal_1 + "," + customized_meal_2 + "," + customized_meal_3 + "]",
            "payment_method_id": "mock_payment_method_id",
            "restaurant_id": 26,
            "table": 1,
            "tip": "4.00"
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        order = Order.objects.order_by('-id').first()
        # Get latest 3 order items from recently placed order
        order_items = OrderItem.objects.filter(order__id=order.id)
        self.assertEqual(order_items.count(), 3)
        # check customized_meal_1 properties
        customization_1 = OrderItemCustomization.objects.get(
            order_item__id=order_items[0].id)
        self.assertEqual(len(customization_1.options), 1)
        self.assertEqual(customization_1.price_additions[0], Decimal('2.00'))
        # check customized_meal_2 properties
        customization_2 = OrderItemCustomization.objects.get(
            order_item__id=order_items[1].id)
        self.assertEqual(len(customization_2.options), 3)
        self.assertEqual(customization_2.price_additions[2], Decimal('0.50'))
        total_cost = 0
        for price_addition in customization_2.price_additions:
            total_cost += price_addition
        self.assertEqual(total_cost, Decimal("1.50"))
        # check customized_meal_3 properties
        customization_3 = OrderItemCustomization.objects.filter(
            order_item__id=order_items[2].id)
        total_options = 0
        total_cost = 0
        for cust in customization_3:
            total_options += len(cust.options)
            for price_addition in cust.price_additions:
                total_cost += price_addition
        self.assertEqual(total_options, 4)
        self.assertEqual(total_cost, Decimal("3.50"))
        # check order properties
        self.assertEqual(order.status, Order.ACTIVE)
        self.assertEqual(order.stripe_fee, Decimal("3.50"))
        self.assertEqual(order.subtotal, Decimal("37.00"))
        self.assertEqual(order.tip, Decimal("4.00"))
        self.assertEqual(order.tax, Decimal("2.22"))
        self.assertEqual(order.total, Decimal("43.22"))

    @patch('stripe.PaymentMethod.retrieve')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('swickapp.apis_customer.attempt_stripe_payment')
    @patch('swickapp.apis_customer.get_stripe_fee')
    def test_add_tip(self, get_stripe_fee_mock, attempt_stripe_payment_mock, payment_intent_retrieve_mock, payment_method_retrieve_mock):
        # POST error: customer id is not valid
        resp = self.client.post(reverse('customer_add_tip'), data={
            "order_id": 38,
            "tip": "22.50"
        })
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "invalid_request")
        # POST error: tip is not valid
        resp = self.client.post(reverse('customer_add_tip'), data={
            "order_id": 35,
            "tip": "invalid_tip"
        })
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "invalid_request")
        # POST success: card has been deleted
        payment_intent_mock = Mock()
        payment_intent_mock.payment_method = Mock()
        payment_intent_mock.payment_method.customer = "invalid_customer_id"
        payment_intent_mock.metadata = {"order_id": 35, "payment_method_id": "invalid_payment_method_id"}
        payment_intent_retrieve_mock.return_value = payment_intent_mock
        payment_method_retrieve_mock.return_value.customer = 111
        resp = self.client.post(reverse('customer_add_tip'), data={
            "order_id": 35,
            "tip": "2.00"
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "card_error")
        self.assertEqual(content["error"],
                         "Card used for this order no longer exists")
        order = Order.objects.get(id=35)
        self.assertEqual(order.tip, Decimal("4.88"))
        # POST success: payment method requires_actions
        payment_intent_mock.payment_method.customer = self.customer.stripe_cust_id
        payment_intent_mock.metadata = {"order_id": 35, "payment_method_id": "valid_payment_method_id"}
        payment_method_retrieve_mock.return_value.customer = self.customer.stripe_cust_id
        attempt_stripe_payment_mock.return_value = JsonResponse({
            "intent_status": "requires_action",
            "payment_intent": "valid_payment_intent_id",
            "client_secret": "mock_client_secret",
            "status": "success"
        })
        resp = self.client.post(reverse('customer_add_tip'), data={
            "order_id": 35,
            "tip": "2.00"
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "requires_action")
        self.assertEqual(content["client_secret"], "mock_client_secret")
        order = Order.objects.get(id=35)
        self.assertEqual(order.tip_stripe_payment_id,
                         "valid_payment_intent_id")
        self.assertEqual(order.tip, Decimal("4.88"))
        # POST success: payment successful
        attempt_stripe_payment_mock.return_value = JsonResponse({
            "intent_status": "succeeded",
            "payment_intent": "valid_payment_intent_id",
            "status": "success"
        })
        get_stripe_fee_mock.return_value = Decimal("3.50")
        resp = self.client.post(reverse('customer_add_tip'), data={
            "order_id": 35,
            "tip": "2.00"
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "succeeded")
        order = Order.objects.get(id=35)
        self.assertEqual(order.tip_stripe_payment_id,
                         "valid_payment_intent_id")
        self.assertEqual(order.tip, Decimal("2.00"))
        self.assertEqual(order.stripe_fee, Decimal("4.94"))
        self.assertEqual(order.total, Decimal("41.48"))
        # POST error: stripe api error
        payment_intent_retrieve_mock.side_effect = stripe.error.StripeError(
            "mocK_stripe_error_message")
        resp = self.client.post(reverse('customer_add_tip'), data={
            "order_id": 35,
            "tip": "2.00"
        })
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "stripe_api_error")

    @patch('swickapp.apis_customer.retry_stripe_payment')
    @patch('swickapp.apis_customer.get_stripe_fee')
    def test_retry_order_payment(self, get_stripe_fee_mock, retry_stripe_payment_mock):
        # POST success: payment succeeds
        retry_stripe_payment_mock.return_value = JsonResponse({
            "intent_status": "succeeded",
            "order_id": 35,
            "status": "success"
        })
        get_stripe_fee_mock.return_value = Decimal("2.50")
        order = Order.objects.get(pk=35)
        order.status = Order.PROCESSING
        order.save()
        resp = self.client.post(reverse('customer_retry_order_payment'), data={
            "payment_intent_id": "valid_payment_intent_id",
            "restaurant_id": 26
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['intent_status'], 'succeeded')
        order = Order.objects.get(pk=35)
        self.assertEqual(order.status, Order.ACTIVE)
        self.assertEqual(order.stripe_fee, Decimal("2.50"))
        # POST success: card fails
        retry_stripe_payment_mock.return_value = JsonResponse({
            "intent_status": "card_error",
            "order_id": 35,
            "error": "mock_card_error_message",
            "status": "success"
        })
        resp = self.client.post(reverse('customer_retry_order_payment'), data={
            "payment_intent_id": "valid_payment_intent_id",
            "restaurant_id": 26
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['intent_status'], 'card_error')
        self.assertFalse(Order.objects.filter(pk=35).exists())

    @patch('stripe.PaymentIntent.retrieve')
    @patch('swickapp.apis_customer.retry_stripe_payment')
    @patch('swickapp.apis_customer.get_stripe_fee')
    def test_retry_tip_payment(self, get_stripe_fee_mock, retry_stripe_payment_mock, payment_intent_retrieve_mock):
        # POST success: payment succeeds
        retry_stripe_payment_mock.return_value = JsonResponse({
            "intent_status": "succeeded",
            "order_id": 35,
            "status": "success"
        })
        get_stripe_fee_mock.return_value = Decimal("0.50")
        payment_intent_retrieve_mock.return_value.amount = 300

        resp = self.client.post(reverse('customer_retry_tip_payment'), data={
            "payment_intent_id": "valid_payment_intent_id",
            "restaurant_id": 26
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content["intent_status"], 'succeeded')
        order = Order.objects.get(id=35)
        self.assertEqual(order.tip, Decimal("3.00"))
        self.assertEqual(order.total, Decimal("42.48"))
        # POST success: card fails
        retry_stripe_payment_mock.return_value = JsonResponse({
            "intent_status": "card_error",
            "order_id": 36,
            "error": "mock_card_error_message",
            "status": "success"
        })
        resp = self.client.post(reverse('customer_retry_tip_payment'), data={
            "payment_intent_id": "valid_payment_intent_id",
            "restaurant_id": 26
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content["intent_status"], 'card_error')
        order = Order.objects.get(id=36)
        self.assertEqual(order.tip, Decimal("1.13"))
        # POST error: stripe api error
        retry_stripe_payment_mock.return_value = JsonResponse({
            "intent_status": "succeeded",
            "order_id": 35,
            "status": "success"
        })
        payment_intent_retrieve_mock.side_effect = stripe.error.StripeError(
            "mock_stripe_error_message"
        )
        resp = self.client.post(reverse('customer_retry_tip_payment'), data={
            "payment_intent_id": "valid_payment_intent_id",
            "restaurant_id": 26
        })
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'stripe_api_error')

    def test_get_orders(self):
        # GET success
        resp = self.client.get(reverse('customer_get_orders'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        orders = content['orders']
        self.assertEqual(len(orders), 3)
        self.assertEqual(orders[0]['id'], 37)
        self.assertEqual(orders[2]['id'], 35)

    def test_get_order_details(self):
        # GET success
        resp = self.client.get(
            reverse('customer_get_order_details', args=(35,)))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        details = content['order_details']
        self.assertEqual(details['total'], '39.48')
        # GET error: order does not exist
        resp = self.client.get(
            reverse('customer_get_order_details', args=(34,)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'order_does_not_exist')
        # GET error: order does not belong to customer
        resp = self.client.get(
            reverse('customer_get_order_details', args=(38,)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'order_does_not_exist')

    def test_make_request(self):
        # POST success
        resp = self.client.post(
            reverse('customer_make_request'),
            data={'request_option_id': 5, 'table': 6}
        )
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        Request.objects.get(customer=self.customer, request_option=5)
        # POST error: request option does not exist
        resp = self.client.post(
            reverse('customer_make_request'),
            data={'request_option_id': 4, 'table': 6}
        )
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'request_option_does_not_exist')
        # POST error: request already placed
        resp = self.client.post(
            reverse('customer_make_request'),
            data={'request_option_id': 5, 'table': 6}
        )
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'request_in_progress')

    def test_get_info(self):
        # GET success
        resp = self.client.get(reverse('customer_get_info'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['name'], 'Sean Lu')
        self.assertEqual(content['email'], 'seanlu99@gmail.com')

    @patch('stripe.SetupIntent.create')
    def test_setup_card(self, setup_intent_create_mock):
        # POST success
        setup_intent_mock = Mock()
        setup_intent_mock.client_secret = "mock_client_secret"
        setup_intent_create_mock.return_value = setup_intent_mock
        resp = self.client.post(reverse('customer_setup_card'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["client_secret"], "mock_client_secret")
        # POST error: stripe api error
        setup_intent_create_mock.side_effect = stripe.error.StripeError(
            "mock_stripe_error_message")
        resp = self.client.post(reverse('customer_setup_card'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "stripe_api_error")

    @patch('stripe.PaymentMethod.list')
    def test_get_cards(self, payment_method_list_mock):
        card_1_mock = Mock()
        card_1_mock.id = "card_1_id"
        card_1_mock.card.brand = "visa"
        card_1_mock.card.exp_month = 3
        card_1_mock.card.exp_year = 2022
        card_1_mock.card.last4 = 1234

        card_2_mock = Mock()
        card_2_mock.id = "card_2_id"
        card_2_mock.card.brand = "mastercard"
        card_2_mock.card.exp_month = 11
        card_2_mock.card.exp_year = 2023
        card_2_mock.card.last4 = 4321

        payment_method_list_mock.return_value.data = [card_1_mock, card_2_mock]
        # GET success
        resp = self.client.get(reverse('customer_get_cards'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["cards"][0]["payment_method_id"], "card_1_id")
        self.assertEqual(content["cards"][1]["payment_method_id"], "card_2_id")
        # GET error: stripe api error
        payment_method_list_mock.side_effect = stripe.error.StripeError(
            "mocK_stripe_error_message")
        resp = self.client.get(reverse('customer_get_cards'))
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "stripe_api_error")

    @patch('stripe.PaymentMethod.retrieve')
    @patch('stripe.PaymentMethod.detach')
    def test_remove_card(self, payment_method_detach_mock, payment_method_retrieve_mock):
        # POST success
        payment_intent_mock = Mock()
        payment_intent_mock.customer = self.customer.stripe_cust_id
        payment_method_retrieve_mock.return_value = payment_intent_mock
        resp = self.client.post(reverse('customer_remove_card'), data={
            "payment_method_id": "valid_payment_intent_id"
        })
        content = json.loads(resp.content)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(content["status"], "success")
        # POST error: user does not own card
        payment_intent_mock.customer = "invalid_customer_id"
        resp = self.client.post(reverse('customer_remove_card'), data={
            "payment_method_id": "valid_payment_intent_id"
        })
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "invalid_stripe_id")
        # POST error: stripe api error
        payment_intent_mock.customer = self.customer.stripe_cust_id
        payment_method_detach_mock.side_effect = stripe.error.StripeError(
            "mocK_stripe_error_message")
        resp = self.client.post(reverse('customer_remove_card'), data={
            "payment_method_id": "valid_payment_intent_id"
        })
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "stripe_api_error")
