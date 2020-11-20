import json

from django.urls import reverse
from rest_framework.test import APITestCase
from swickapp.models import Request, User


class APICustomerTest(APITestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="seanlu99@gmail.com")
        self.client.force_authenticate(user)
        self.customer = user.customer

    def test_login(self):
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
        # POST error: invalid token
        self.client.force_authenticate(user=None)
        resp = self.client.post(reverse('customer_login'))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'invalid_token')

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
        resp = self.client.get(reverse('customer_get_order_details', args=(35,)))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        details = content['order_details']
        self.assertEqual(details['total'], '39.48')
        # GET error: order does not exist
        resp = self.client.get(reverse('customer_get_order_details', args=(34,)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'order_does_not_exist')
        # GET error: order does not belong to customer
        resp = self.client.get(reverse('customer_get_order_details', args=(38,)))
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
