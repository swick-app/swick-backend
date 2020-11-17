import tempfile

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from swickapp.models import (Category, Customization, Meal, RequestOption,
                             Restaurant, Server, ServerRequest, User)


class RestaurantTest(TestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="john@gmail.com")
        self.client.force_login(user)
        self.restaurant = Restaurant.objects.get(user=user)

    def test_main_home(self):
        resp = self.client.get(reverse('main_home'))
        self.assertTemplateUsed(resp, 'main/home.html')

    def test_restaurant_home(self):
        resp = self.client.get(reverse('restaurant_home'))
        self.assertRedirects(resp, reverse('restaurant_menu'))

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
        resp = self.client.post(reverse('restaurant_add_category'), data={
                                'name': 'Appetizers'})
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
        self.assertEqual(category.name, 'Appetizers')

    def test_delete_category(self):
        # GET success
        resp = self.client.get(
            reverse('restaurant_delete_category', args=(12,)))
        self.assertRedirects(resp, reverse('restaurant_menu'))
        self.assertRaises(Category.DoesNotExist, Category.objects.get, id=12)
        # GET error: category does not exist
        resp = self.client.get(
            reverse('restaurant_delete_category', args=(11,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: category does not belong to restaurant
        resp = self.client.get(
            reverse('restaurant_delete_category', args=(14,)))
        self.assertEqual(resp.status_code, 404)

    def test_add_meal(self):
        # GET success
        resp = self.client.get(reverse('restaurant_add_meal', args=(12,)))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/add_meal.html')
        tax_categories = resp.context['tax_categories']
        tax_percentages = resp.context['tax_percentages']
        self.assertEqual(len(tax_categories), 2)
        self.assertEqual(len(tax_percentages), 2)
        # GET error: category does not exist
        resp = self.client.get(reverse('restaurant_add_meal', args=(11,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: category does not belong to restaurant
        resp = self.client.get(reverse('restaurant_add_meal', args=(14,)))
        self.assertEqual(resp.status_code, 404)
        # POST success
        resp = self.client.post(
            reverse('restaurant_add_meal', args=(12,)),
            data={
                'name': 'Filet mignon',
                'description': '11 ounces',
                'price': 22.50,
                'meal_tax_category': 'Default',
                'form-TOTAL_FORMS': 1,
                'form-INITIAL_FORMS': 0,
                'form-MIN_NUM_FORMS': 0,
                'form-MAX_NUM_FORMS': 1000,
                'form-0-name': 'Size',
                'form-0-options': 'Small\r\nMedium\r\nLarge',
                'form-0-price_additions': '1\r\n2\r\n3',
                'form-0-min': 1,
                'form-0-max': 1
            },
        )
        self.assertRedirects(resp, reverse('restaurant_menu') + '#Entrees')
        meal = Meal.objects.get(name="Filet mignon")
        self.assertEqual(meal.tax_category.name, 'Default')
        customization = Customization.objects.get(meal=meal)
        self.assertEqual(customization.name, "Size")

    def test_edit_meal(self):
        # GET success: default tax category
        resp = self.client.get(reverse('restaurant_edit_meal', args=(17,)))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/edit_meal.html')
        tax_categories = resp.context['tax_categories']
        tax_percentages = resp.context['tax_percentages']
        tax_category_index = resp.context['tax_category_index']
        self.assertEqual(len(tax_categories), 2)
        self.assertEqual(len(tax_percentages), 2)
        self.assertEqual(tax_category_index, 0)
        # GET success: non-default tax category
        resp = self.client.get(reverse('restaurant_edit_meal', args=(19,)))
        tax_category_index = resp.context['tax_category_index']
        self.assertEqual(tax_category_index, 1)
        # # GET error: meal does not exist
        resp = self.client.get(reverse('restaurant_edit_meal', args=(16,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: meal does not belong to restaurant
        resp = self.client.get(reverse('restaurant_edit_meal', args=(20,)))
        self.assertEqual(resp.status_code, 404)
        # POST success
        resp = self.client.post(
            reverse('restaurant_edit_meal', args=(17,)),
            data={
                'name': 'Vodka',
                'description': '1.5 ounces',
                'price': 22.50,
                'meal_tax_category': 'Drinks',
                'form-TOTAL_FORMS': 1,
                'form-INITIAL_FORMS': 0,
                'form-MIN_NUM_FORMS': 0,
                'form-MAX_NUM_FORMS': 1000,
                'form-0-name': 'Volume',
                'form-0-options': 'Small\r\nMedium\r\nLarge',
                'form-0-price_additions': '1\r\n2\r\n3',
                'form-0-min': 1,
                'form-0-max': 1
            },
        )
        self.assertRedirects(resp, reverse('restaurant_menu') + '#Entrees')
        meal = Meal.objects.get(id=17)
        self.assertEqual(meal.name, "Vodka")
        self.assertEqual(meal.tax_category.name, "Drinks")
        customization = Customization.objects.get(meal__id=17)
        self.assertEqual(customization.name, "Volume")

    def test_delete_meal(self):
        # GET success
        resp = self.client.get(reverse('restaurant_delete_meal', args=(17,)))
        self.assertRedirects(resp, reverse('restaurant_menu') + "#Entrees")
        self.assertRaises(Meal.DoesNotExist, Meal.objects.get, id=17)
        # GET error: meal does not exist
        resp = self.client.get(reverse('restaurant_delete_meal', args=(16,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: meal does not belong to restaurant
        resp = self.client.get(reverse('restaurant_delete_meal', args=(20,)))
        self.assertEqual(resp.status_code, 404)

    def test_toggle_meal(self):
        # GET success: disable meal
        resp = self.client.get(reverse('restaurant_toggle_meal', args=(17,)))
        self.assertRedirects(resp, reverse('restaurant_menu') + "#Entrees")
        meal = Meal.objects.get(id=17)
        self.assertFalse(meal.enabled)
        # GET success: enable meal
        resp = self.client.get(reverse('restaurant_toggle_meal', args=(17,)))
        meal = Meal.objects.get(id=17)
        self.assertTrue(meal.enabled)
        # GET error: meal does not exist
        resp = self.client.get(reverse('restaurant_delete_meal', args=(16,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: meal does not belong to restaurant
        resp = self.client.get(reverse('restaurant_delete_meal', args=(20,)))
        self.assertEqual(resp.status_code, 404)

    def test_requests(self):
        # GET success
        resp = self.client.get(reverse('restaurant_requests'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/requests.html')
        requests = resp.context['requests']
        self.assertEqual(requests.count(), 2)
        self.assertEqual(requests[0].name, 'Water')
        self.assertEqual(requests[1].name, 'Fork')

    def test_add_request(self):
        # GET success
        resp = self.client.get(reverse('restaurant_add_request'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/add_request.html')
        # POST success
        resp = self.client.post(
            reverse('restaurant_add_request'), data={'name': 'Spoon'})
        self.assertRedirects(resp, reverse('restaurant_requests'))
        requests = RequestOption.objects.filter(restaurant=self.restaurant)
        self.assertEqual(requests.count(), 3)

    def test_edit_request(self):
        # GET success
        resp = self.client.get(reverse('restaurant_edit_request', args=(1,)))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/edit_request.html')
        # GET error: request does not exist
        resp = self.client.get(reverse('restaurant_edit_request', args=(2,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: request does not belong to restaurant
        resp = self.client.get(reverse('restaurant_edit_request', args=(27,)))
        self.assertEqual(resp.status_code, 404)
        # POST success
        resp = self.client.post(
            reverse('restaurant_edit_request', args=(1,)),
            data={'name': 'Spoon'}
        )
        self.assertRedirects(resp, reverse('restaurant_requests'))
        request = RequestOption.objects.get(id=1)
        self.assertEqual(request.name, 'Spoon')

    def test_delete_request(self):
        # GET success
        resp = self.client.get(reverse('restaurant_delete_request', args=(1,)))
        self.assertRedirects(resp, reverse('restaurant_requests'))
        self.assertRaises(RequestOption.DoesNotExist,
                          RequestOption.objects.get, id=1)
        # GET error: request does not exist
        resp = self.client.get(reverse('restaurant_delete_request', args=(2,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: request does not belong to restaurant
        resp = self.client.get(
            reverse('restaurant_delete_request', args=(27,)))
        self.assertEqual(resp.status_code, 404)

    def test_servers(self):
        # GET success
        resp = self.client.get(reverse('restaurant_servers'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/servers.html')
        servers = resp.context['servers']
        server_request = servers[0]
        server = servers[2]
        self.assertEqual(len(servers), 3)
        self.assertEqual(server_request['name'], 'Andrew Jiang')
        self.assertEqual(server_request['status'], 'Pending')
        self.assertTrue(server_request['request'])
        self.assertEqual(server['name'], 'Sean Lu')
        self.assertEqual(server['status'], 'Accepted')
        self.assertFalse(server['request'])

    def test_add_server(self):
        # GET success
        resp = self.client.get(reverse('restaurant_add_server'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/add_server.html')
        # POST success
        resp = self.client.post(
            reverse('restaurant_add_server'),
            data={'name': 'Jake', 'email': 'seanlu@umich.edu'}
        )
        self.assertRedirects(resp, reverse('restaurant_servers'))
        requests = ServerRequest.objects.filter(restaurant=self.restaurant)
        self.assertEqual(requests.count(), 3)
        self.assertEqual(mail.outbox[0].subject, 'Swick Add Server Request')

    def test_delete_server(self):
        # GET success
        resp = self.client.get(reverse('restaurant_delete_server', args=(11,)))
        self.assertRedirects(resp, reverse('restaurant_servers'))
        server = Server.objects.get(id=11)
        self.assertEqual(server.restaurant, None)
        # GET error: server does not exist
        resp = self.client.get(reverse('restaurant_delete_server', args=(10,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: server does not belong to restaurant
        resp = self.client.get(reverse('restaurant_delete_server', args=(13,)))
        self.assertEqual(resp.status_code, 404)

    def test_delete_server_request(self):
        # GET success
        resp = self.client.get(
            reverse('restaurant_delete_server_request', args=(46,)))
        self.assertRedirects(resp, reverse('restaurant_servers'))
        self.assertRaises(ServerRequest.DoesNotExist,
                          ServerRequest.objects.get, id=46)
        # GET error: server request does not exist
        resp = self.client.get(
            reverse('restaurant_delete_server_request', args=(44,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: server request does not belong to restaurant
        resp = self.client.get(
            reverse('restaurant_delete_server_request', args=(45,)))
        self.assertEqual(resp.status_code, 404)

    def test_server_link_restaurant(self):
        # GET error: invalid token
        resp = self.client.get(
            reverse('server_link_restaurant', args=('123',)))
        self.assertEqual(resp.status_code, 404)
        # GET success: server account does exist
        resp = self.client.get(
            reverse(
                'server_link_restaurant',
                args=('fba4d1e7a36379d4466934c66619a42fea2e7c5c',)
            )
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(
            resp, 'registration/server_link_restaurant_confirm.html')
        server = Server.objects.get(id=14)
        self.assertNotEqual(server.restaurant, None)
        self.assertRaises(ServerRequest.DoesNotExist,
                          ServerRequest.objects.get, id=46)
        # GET success: server account does not exist
        resp = self.client.get(
            reverse(
                'server_link_restaurant',
                args=('965d251703b4f32190b132014c29749d0d657460',)
            )
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(
            resp, 'registration/server_link_restaurant_confirm.html')
        request = ServerRequest.objects.get(id=47)
        self.assertTrue(request.accepted)
