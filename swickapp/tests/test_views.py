import tempfile

from django.test import TestCase
from django.urls import reverse

from swickapp.models import Category, Restaurant, User

class RestaurantTest(TestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="john@gmail.com")
        self.client.force_login(user)
        self.restaurant = Restaurant.objects.get(user=user)

    def test_menu(self):
        # GET success
        resp = self.client.get(reverse('restaurant_menu'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/menu.html')
        categories = resp.context['categories']
        self.assertEqual(categories.count(), 2)
        self.assertEqual(categories[0].name, 'Drinks')
        self.assertEqual(categories[1].name, 'Entrees')

    def test_add_category(self):
        # GET success
        resp = self.client.get(reverse('restaurant_add_category'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/add_category.html')
        # POST success
        resp = self.client.post(reverse('restaurant_add_category'), data={'name': 'Appetizers'})
        self.assertRedirects(resp, reverse('restaurant_menu') + "#Appetizers")
        categories = Category.objects.filter(restaurant=self.restaurant)
        self.assertEqual(categories.count(), 3)

    def test_edit_category(self):
        # GET success
        resp = self.client.get(reverse('restaurant_edit_category', args=(12,)))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/edit_category.html')
        # GET error: category does not exist
        resp = self.client.get(reverse('restaurant_edit_category', args=(11,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: category does not belong to restaurant
        resp = self.client.get(reverse('restaurant_edit_category', args=(14,)))
        self.assertEqual(resp.status_code, 404)
        # POST success
        resp = self.client.post(
            reverse('restaurant_edit_category', args=(12,)),
            data={'name': 'Appetizers'}
        )
        self.assertRedirects(resp, reverse('restaurant_menu') + "#Appetizers")
        category = Category.objects.get(id=12)
        self.assertTrue(category.name, 'Appetizers')

    def test_delete_category(self):
        # GET success
        resp = self.client.get(reverse('restaurant_delete_category', args=(12,)))
        self.assertRedirects(resp, reverse('restaurant_menu'))
        # GET error: category does not exist
        resp = self.client.get(reverse('restaurant_delete_category', args=(11,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: category does not belong to restaurant
        resp = self.client.get(reverse('restaurant_delete_category', args=(14,)))
        self.assertEqual(resp.status_code, 404)
