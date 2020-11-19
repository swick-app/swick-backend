import json

from django.urls import reverse
from rest_framework.test import APITestCase
from swickapp.models import User


class APICustomerTest(APITestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="seanlu99@gmail.com")
        self.client.force_authenticate(user)

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
