from django.test import TestCase
from django.urls import reverse
from swickapp.forms import CustomizationForm
from swickapp.models import User


class FormsTest(TestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="john@gmail.com")
        self.client.force_login(user)

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
        # If options and price additions don't have equal size
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
        # If options is empty
        form = CustomizationForm(
            data={
                'name': 'Size',
                'options': '',
                'price_additions': '0',
                'min': 0,
                'max': 1
            }
        )
        self.assertEquals(
            form.errors['__all__'],
            ['The number of options and price additions must be equal']
        )
        # If price additions is empty
        form = CustomizationForm(
            data={
                'name': 'Size',
                'options': 'Small',
                'price_additions': '',
                'min': 0,
                'max': 1
            }
        )
        self.assertEquals(
            form.errors['__all__'],
            ['The number of options and price additions must be equal']
        )
        # If max is greater than options size
        form = CustomizationForm(
            data={
                'name': 'Size',
                'options': 'Small\nMedium\nLarge',
                'price_additions': '0\n1\n2',
                'min': 0,
                'max': 4
            }
        )
        self.assertEquals(
            form.errors['__all__'],
            ['Maximum number of selectable options cannot be greater than the number of options']
        )
        # If max is greater than options size
        form = CustomizationForm(
            data={
                'name': 'Size',
                'options': 'Small\nMedium\nLarge',
                'price_additions': '0\n1\n2',
                'min': 1,
                'max': 0
            }
        )
        self.assertEquals(
            form.errors['__all__'],
            ['Minimum number of options cannot be greater than maximum number of options']
        )
