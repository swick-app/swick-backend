from django.test import TestCase
from django.urls import reverse
from swickapp.models import User, Restaurant
from swickapp.forms import CustomizationForm

class FormsTest(TestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="john@gmail.com")
        self.client.force_login(user)
        self.restaurant = Restaurant.objects.get(user=user)

    def test_server_request_form(self):
        # Test sending request to same email
        resp = self.client.post(
            reverse('restaurant_add_server'),
            data={
                'name': 'John',
                'email': 'andrewjiang99@gmail.com'
            }
        )
        self.assertFormError(
            resp,
            'server_request_form',
            None,
            'Request has already been sent to this email'
        )

    def test_customization_form(self):
        # Test options and price additions have equal size
        form = CustomizationForm(
            data={
                'name': 'Size',
                'options': 'Small\nMedium\nLarge',
                'price_additions': '0\n1',
                'min': 0,
                'max': 1
            }
        )
        self.assertEquals(
            form.errors['__all__'],
            ['The number of options and price additions must be equal']
        )
