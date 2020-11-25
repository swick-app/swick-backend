from decimal import Decimal
from unittest.mock import Mock, patch

import stripe
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponseRedirect
from django.test import TestCase
from django.urls import reverse
from swickapp.models import (Category, Customization, Meal, RequestOption,
                             Restaurant, Server, ServerRequest, TaxCategory,
                             User)


class ViewsTest(TestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="john@gmail.com")
        self.client.force_login(user)
        self.restaurant = Restaurant.objects.get(user=user)

    def test_main_home(self):
        resp = self.client.get(reverse('main_home'))
        self.assertTemplateUsed(resp, 'main/home.html')

    def test_request_demo(self):
        # GET success
        resp = self.client.get(reverse('request_demo'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'registration/request_demo.html')
        # POST success
        resp = self.client.post(
            reverse('request_demo'),
            data={
                'name': 'Dan',
                'email': 'dan@gmail.com',
                'restaurant': 'Sandwich Place'
            }
        )
        self.assertRedirects(resp, reverse('request_demo_done'))
        self.assertEqual(mail.outbox[0].subject, 'Swick Demo Request')

    def test_request_demo_done(self):
        # GET success
        resp = self.client.get(reverse('request_demo_done'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'registration/request_demo_done.html')

    @patch("stripe.Account.create")
    @patch("stripe.AccountLink.create")
    def test_sign_up(self, account_link_create_mock, account_create_mock):
        # GET success
        resp = self.client.get(reverse('sign_up'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'registration/sign_up.html')
        # POST success: create new user
        account_create_mock.return_value.id = "<mock_stripe_account_id>"
        account_link_create_mock.return_value.url = 'https://stripe.com'
        resp = self.client.post(
            reverse('sign_up'),
            data={
                'user-name': 'Ben',
                'user-email': 'ben@gmail.com',
                'user-password': 'password',
                'restaurant-name': 'Sandwich Place',
                'restaurant-address': '1 S University Ave, Ann Arbor, MI 48104',
                'restaurant-image': SimpleUploadedFile(
                    name='long-image.jpg',
                    content=open(
                        "./swickapp/tests/long-image.jpg", 'rb').read()
                ),
                'restaurant-timezone': 'US/Eastern',
                'restaurant-default_sales_tax': '6.250'
            }
        )
        user = User.objects.get(email="ben@gmail.com")
        restaurant = Restaurant.objects.get(name="Sandwich Place")
        self.assertEqual(restaurant.default_sales_tax, Decimal("6.250"))
        tax_category = TaxCategory.objects.get(
            restaurant=restaurant, name="Default")
        self.assertEqual(tax_category.name, "Default")
        self.assertEqual(resp.status_code, 302)
        # POST success: user already exists
        resp = self.client.post(
            reverse('sign_up'),
            data={
                'user-name': 'Sean',
                'user-email': 'seanlu99@gmail.com',
                'user-password': 'password',
                'restaurant-name': 'Burger Palace',
                'restaurant-address': '1 North St, Ann Arbor, MI 48104',
                'restaurant-image': SimpleUploadedFile(
                    name='long-image.jpg',
                    content=open(
                        "./swickapp/tests/long-image.jpg", 'rb').read()
                ),
                'restaurant-timezone': 'US/Eastern',
                'restaurant-default_sales_tax': '6'
            }
        )
        restaurant = Restaurant.objects.get(name="Burger Palace")
        # POST error: stripe account link create api error
        account_link_create_mock.side_effect = stripe.error.StripeError(
            "<mock_stripe_error_message>")
        resp = self.client.post(
            reverse('sign_up'),
            data={
                'user-name': 'Sean3',
                'user-email': 'seanlu99_3@gmail.com',
                'user-password': 'password3',
                'restaurant-name': 'Burger Palace3',
                'restaurant-address': '1 North St, Ann Arbor, MI 48104',
                'restaurant-image': SimpleUploadedFile(
                    name='long-image.jpg',
                    content=open(
                        "./swickapp/tests/long-image.jpg", 'rb').read()
                ),
                'restaurant-timezone': 'US/Eastern',
                'restaurant-default_sales_tax': '6'
            }
        )
        self.assertEqual(resp.status_code, 302)
        # POST error: stripe account create api error
        account_create_mock.side_effect = stripe.error.StripeError(
            "<mock_stripe_error_message>")
        resp = self.client.post(
            reverse('sign_up'),
            data={
                'user-name': 'Sean2',
                'user-email': 'seanlu99_2@gmail.com',
                'user-password': 'password2',
                'restaurant-name': 'Burger Palace2',
                'restaurant-address': '1 North St, Ann Arbor, MI 48104',
                'restaurant-image': SimpleUploadedFile(
                    name='long-image.jpg',
                    content=open(
                        "./swickapp/tests/long-image.jpg", 'rb').read()
                ),
                'restaurant-timezone': 'US/Eastern',
                'restaurant-default_sales_tax': '6'
            }
        )
        self.assertEqual(resp.status_code, 404)

    @patch('stripe.AccountLink.create')
    def test_refresh_stripe_link(self, account_link_create_mock):
        account_link_create_mock.return_value.url = 'https://stripe.com'
        # GET success
        resp = self.client.get(reverse('refresh_stripe_link'))
        self.assertEqual(resp.status_code, 302)
        # GET error: stripe api error
        account_link_create_mock.side_effect = stripe.error.StripeError(
            "mock_stripe_error_message")
        resp = self.client.get(reverse('refresh_stripe_link'))
        self.assertEqual(resp.status_code, 404)

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
                'image': '',
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
                'image': '',
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
        resp = self.client.get(reverse('restaurant_toggle_meal', args=(16,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: meal does not belong to restaurant
        resp = self.client.get(reverse('restaurant_toggle_meal', args=(20,)))
        self.assertEqual(resp.status_code, 404)

    def test_orders(self):
        # GET success
        resp = self.client.get(reverse("restaurant_orders"))
        orders = resp.context["orders"]
        self.assertFalse(orders.exists())
        # POST success
        resp = self.client.post(
            reverse('restaurant_orders'),
            data={'start_time': '11/14/2020 12:00AM',
                  'end_time': '11/14/2020 5:00AM'}
        )
        orders = resp.context["orders"]
        self.assertEqual(orders[0].stripe_payment_id,
                         "pi_1HnHCqBnGfJIkyujV9C6UV1U")
        self.assertEqual(orders.count(), 3)

    def test_view_order(self):
        # GET success
        resp = self.client.get(reverse("restaurant_view_order", args=(35,)))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/view_order.html')
        order = resp.context["order"]
        self.assertEqual(order.stripe_payment_id,
                         "pi_1HnHCqBnGfJIkyujV9C6UV1U")
        # GET error: restaurant does not own order
        resp = self.client.get(reverse("restaurant_view_order", args=(37,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: order id does not exist
        resp = self.client.get(reverse("restaurant_view_order", args=(15,)))
        self.assertEqual(resp.status_code, 404)

    def test_finances(self):
        # GET success
        resp = self.client.get(reverse('restaurant_finances'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/finances.html')
        default_category = resp.context["default_category"]
        tax_categories = resp.context["tax_categories"]
        gross_revenue = resp.context["gross_revenue"]
        total_tax = resp.context["total_tax"]
        total_tip = resp.context["total_tip"]
        stripe_fees = resp.context["stripe_fees"]
        revenue = resp.context["revenue"]
        self.assertEqual(default_category.name, "Default")
        self.assertEqual(tax_categories[0].name, "Drinks")
        self.assertEqual(gross_revenue, 0)
        self.assertEqual(total_tip, 0)
        self.assertEqual(stripe_fees, 0)
        self.assertEqual(revenue, 0)
        # GET success: default stripe link
        self.restaurant.stripe_acct_id = "invalid"
        self.restaurant.save()
        resp = self.client.get(reverse('restaurant_finances'))
        stripe_link = resp.context["stripe_link"]
        # POST success
        resp = self.client.post(
            reverse('restaurant_finances'),
            data={'start_time': '11/14/2020 12:00AM',
                  'end_time': '11/14/2020 5:00AM'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/finances.html')
        default_category = resp.context["default_category"]
        tax_categories = resp.context["tax_categories"]
        gross_revenue = resp.context["gross_revenue"]
        total_tax = resp.context["total_tax"]
        total_tip = resp.context["total_tip"]
        stripe_fees = resp.context["stripe_fees"]
        revenue = resp.context["revenue"]
        self.assertEqual(default_category.name, "Default")
        self.assertEqual(tax_categories[0].name, "Drinks")
        self.assertEqual(gross_revenue, Decimal("83.78"))
        self.assertEqual(total_tax, Decimal("4.22"))
        self.assertEqual(total_tip, Decimal("11.81"))
        self.assertEqual(stripe_fees, Decimal("1.97"))
        self.assertEqual(revenue, Decimal("65.78"))
        self.assertEqual(stripe_link, "https://dashboard.stripe.com")

    def test_add_tax_category(self):
        # GET success
        resp = self.client.get(reverse('restaurant_add_tax_category'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/add_tax_category.html')
        # POST success:
        resp = self.client.post(
            reverse('restaurant_add_tax_category'),
            data={'name': 'Baked Goods', 'tax': '0.05'}
        )
        self.assertRedirects(resp, reverse('restaurant_finances'))
        tax_categories = TaxCategory.objects.filter(restaurant=self.restaurant)
        self.assertEqual(tax_categories.count(), 3)
        # POST error: tax category name is repeated
        resp = self.client.post(
            reverse('restaurant_edit_tax_category', args=(4,)),
            data={'name': 'Default', 'tax': '0.3'}
        )
        self.assertContains(resp, 'Duplicate category name', 1, 200)

    def test_edit_tax_category(self):
        # GET success
        resp = self.client.get(
            reverse('restaurant_edit_tax_category', args=(4,)))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/edit_tax_category.html')
        # GET error: tax category does not exist
        resp = self.client.get(
            reverse('restaurant_edit_tax_category', args=(10,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: tax category does not belong to restaurant
        resp = self.client.get(
            reverse('restaurant_edit_tax_category', args=(3,)))
        self.assertEqual(resp.status_code, 404)
        # POST success
        resp = self.client.post(
            reverse('restaurant_edit_tax_category', args=(4,)),
            data={'name': 'New Drinks', 'tax': '0.4'}
        )
        self.assertRedirects(resp, reverse('restaurant_finances'))
        tax_category = TaxCategory.objects.get(id=4)
        self.assertEqual(tax_category.name, 'New Drinks')
        self.assertEqual(tax_category.tax, Decimal("0.4"))
        # POST success: Default tax category
        resp = self.client.post(
            reverse('restaurant_edit_tax_category', args=(1,)),
            data={'name': 'Default', 'tax': '0.26'}
        )
        default = TaxCategory.objects.get(id=1)
        self.assertEqual(default.name, "Default")
        self.assertEqual(default.tax, Decimal("0.26"))
        self.assertEqual(TaxCategory.objects.filter(
            restaurant=self.restaurant).count(), 2)
        # POST error: tax category named is repeated
        resp = self.client.post(
            reverse('restaurant_edit_tax_category', args=(4,)),
            data={'name': 'Default', 'tax': '0.3'}
        )
        self.assertContains(resp, 'Duplicate category name', 1, 200)

    def test_delete_tax_category(self):
        # GET success
        resp = self.client.get(
            reverse('restaurant_delete_tax_category', args=(4,)))
        self.assertRedirects(resp, reverse('restaurant_finances'))
        self.assertRaises(Category.DoesNotExist, Category.objects.get, id=4)
        # GET error: tax category does not exist
        resp = self.client.get(
            reverse('restaurant_delete_tax_category', args=(15,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: tax category is 'Default'
        resp = self.client.get(
            reverse('restaurant_delete_tax_category', args=(1,)))
        self.assertEqual(resp.status_code, 404)
        # GET error: tax category does not belong to restaurant
        resp = self.client.get(
            reverse('restaurant_delete_tax_category', args=(3,)))
        self.assertEqual(resp.status_code, 404)

    def test_tax_category_create_view(self):
        # GET success
        resp = self.client.get(reverse('popup_tax_category'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'helpers/popup_tax_category.html')
        # POST error: tax category named is repeated
        resp = self.client.post(
            reverse('popup_tax_category'),
            data={
                'name': 'Default',
                'tax': '0.3'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertContains(resp, 'Duplicate category name', 1, 200)
        # POST success
        resp = self.client.post(
            reverse('popup_tax_category'),
            data={
                'name': 'Baked Goods',
                'tax': '0.5'
            }
        )
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('restaurant_menu'))
        tax_categories = TaxCategory.objects.filter(restaurant=self.restaurant)
        self.assertEqual(tax_categories.count(), 3)

    def test_get_tax_categories(self):
        # GET success
        resp = self.client.get(reverse('get_tax_categories'))
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(
            resp.content, {"category": [["Default", "6"], ["Drinks", "8"]]})

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
        self.assertEqual(len(servers), 3)
        server1 = servers[0]
        server2 = servers[1]
        server3 = servers[2]
        self.assertEqual(server1['name'], 'Andrew Jiang')
        self.assertEqual(server1['status'], 'Pending')
        self.assertTrue(server1['request'])
        self.assertEqual(server2['name'], 'Chris')
        self.assertEqual(server2['status'], 'Accepted')
        self.assertTrue(server2['request'])
        self.assertEqual(server3['name'], 'Sean Lu')
        self.assertEqual(server3['status'], 'Accepted')
        self.assertFalse(server3['request'])

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

    def test_account(self):
        # GET success
        resp = self.client.get(reverse('restaurant_account'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'restaurant/account.html')
        # POST success
        resp = self.client.post(
            reverse('restaurant_account'),
            data={
                'user-name': 'Evan',
                'user-email': 'john@gmail.comm',
                'restaurant-name': 'Sandwich Place',
                'restaurant-address': '1 State St, Ann Arbor, MI 48104',
                'restaurant-image': SimpleUploadedFile(
                    name='long-image.jpg',
                    content=open(
                        "./swickapp/tests/long-image.jpg", 'rb').read()
                ),
                'restaurant-timezone': 'US/Eastern',
                'restaurant-default_sales_tax': '7.250'
            }
        )
        self.assertEqual(resp.status_code, 200)
        user = User.objects.get(id=28)
        self.assertEqual(user.name, 'Evan')
        restaurant = Restaurant.objects.get(id=26)
        self.assertEqual(restaurant.name, 'Sandwich Place')
        tax_category = TaxCategory.objects.get(id=1)
        self.assertEqual(tax_category.tax, 7.250)

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
