import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from swickapp.models import RequestOption, Restaurant, User
from swickapp.views_helper import (create_default_request_options,
                                   get_tax_categories_list,
                                   initialize_datetime_range_orders)


class ViewsTest(TestCase):
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
            image=tempfile.NamedTemporaryFile(suffix=".jpg").name,
            timezone='US/Eastern',
            default_sales_tax=6.250
        )
        create_default_request_options(restaurant)
        options = RequestOption.objects.filter(restaurant=restaurant)
        self.assertEqual(options.count(), 6)
        self.assertEqual(options[0].name, 'Water')
