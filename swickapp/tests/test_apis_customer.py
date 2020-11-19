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
        resp = self.client.get(reverse('customer_get_restaurants'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        restaurants = content['restaurants']
        self.assertEqual(len(restaurants), 2)
        self.assertEqual(restaurants[0]['name'], 'Ice Cream Shop')
        self.assertEqual(restaurants[1]['name'], 'The Cozy Diner')

    def test_get_orders(self):
        resp = self.client.get(reverse('customer_get_orders'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        orders = content['orders']
        self.assertEqual(len(orders), 3)
        self.assertEqual(orders[0]['id'], 37)
        self.assertEqual(orders[2]['id'], 35)
