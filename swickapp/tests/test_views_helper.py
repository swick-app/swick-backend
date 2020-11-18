from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from swickapp.models import RequestOption, Restaurant, User


class ViewsTest(TestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="john@gmail.com")
        self.client.force_login(user)
        self.restaurant = Restaurant.objects.get(user=user)

    def test_create_default_request_options(self):
        resp = self.client.post(
            reverse('sign_up'),
            data={
                'user-name': 'Ben',
                'user-email': 'ben@gmail.com',
                'user-password': 'password',
                'restaurant-name': 'Sandwich Place',
                'restaurant-address': '1 S University Ave, Ann Arbor, MI 48104',
                'restaurant-image': SimpleUploadedFile(
                    'mock.jpg',
                    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
                ),
                'restaurant-timezone': 'US/Eastern',
                'restaurant-default_sales_tax': '6.250'
            }
        )
        restaurant = Restaurant.objects.get(name="Sandwich Place")
        options = RequestOption.objects.filter(restaurant=restaurant)
        self.assertEqual(options.count(), 6)
        self.assertEqual(options[0].name, 'Water')
