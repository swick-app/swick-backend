from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from swickapp.models import RequestOption, Restaurant, User, TaxCategory
from swickapp.views_helper import (create_default_request_options,
                                   get_tax_categories_list,
                                   initialize_datetime_range_orders)


class ViewsHelperTest(TestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="john@gmail.com")
        self.client.force_login(user)
        self.restaurant = Restaurant.objects.get(user=user)

    def test_create_default_request_options(self):
        user = User.objects.get(id=29)
        restaurant = Restaurant.objects.create(
            user=user,
            name='Sandwich Place',
            address='1 S University Ave, Ann Arbor, MI 48104',
            image=SimpleUploadedFile(
                name='long-image.jpg',
                content=open("./swickapp/tests/long-image.jpg", 'rb').read()
            ),
            timezone='US/Eastern',
            default_sales_tax=6.250
        )
        create_default_request_options(restaurant)
        options = RequestOption.objects.filter(restaurant=restaurant)
        self.assertEqual(options.count(), 6)
        self.assertEqual(options[0].name, 'Water')

    def test_initialize_datetime_range_orders(self):
        # No datetime range given
        resp = self.client.get(reverse('restaurant_orders'))
        orders = resp.context["orders"]
        self.assertEqual(resp.context["start_time_error"], "")
        self.assertEqual(resp.context["end_time_error"], "")
        self.assertFalse(orders.exists())
        # Datetime range given
        resp = self.client.post(
            reverse('restaurant_orders'),
            data={'start_time': '11/14/2020 12:00AM',
                  'end_time': '11/14/2020 5:00AM'}
        )
        orders = resp.context["orders"]
        self.assertEqual(resp.context["start_time_error"], "")
        self.assertEqual(resp.context["end_time_error"], "")
        self.assertEqual(orders[0].stripe_payment_id,
                         "pi_1HnHCqBnGfJIkyujV9C6UV1U")
        self.assertEqual(orders.count(), 3)
        # Invalid datetime format given
        resp = self.client.post(
            reverse('restaurant_orders'),
            data={'start_time': '<invalid_format>',
                  'end_time': '<invalid_format>'}
        )
        start_time_error = resp.context["start_time_error"]
        end_time_error = resp.context["end_time_error"]
        self.assertEqual(start_time_error, "Enter a valid date/time.")
        self.assertEqual(end_time_error, "Enter a valid date/time.")

    def test_get_tax_categories_list(self):
        # Only default tax category
        tax_categories = get_tax_categories_list(Restaurant.objects.get(id=29))
        self.assertEqual(tax_categories[0], ("Default", "6"))
        # Multiple tax categories
        tax_categories = get_tax_categories_list(self.restaurant)
        self.assertEqual(len(tax_categories), 2)
        self.assertEqual(tax_categories[0], ("Default", "6"))
        self.assertEqual(tax_categories[1], ("Drinks", "8"))
        # Tax string formatting
        tax_category = TaxCategory.objects.get(
            restaurant=self.restaurant, name="Default")
        tax_category.tax = 6.50
        tax_category.save()
        tax_category = TaxCategory.objects.get(
            restaurant=self.restaurant, name="Drinks")
        tax_category.tax = 6.505
        tax_category.save()
        tax_categories = get_tax_categories_list(self.restaurant)
        self.assertEqual(tax_categories[0], ("Default", "6.5"))
        self.assertEqual(tax_categories[1], ("Drinks", "6.505"))
