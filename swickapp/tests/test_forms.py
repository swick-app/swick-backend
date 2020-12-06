from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from swickapp.forms import (CustomizationForm, MealForm, RestaurantForm,
                            TaxCategoryForm)
from swickapp.forms_helper import formatted_image_blob
from swickapp.models import Restaurant, User


class FormsTest(TestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="john@gmail.com")
        self.client.force_login(user)

    def test_restaurant_form(self):
        # Image greater in width than height
        long_image = SimpleUploadedFile(
            name='long-image.jpg',
            content=open("./swickapp/tests/long-image.jpg", 'rb').read()
        )
        # Tests given image conforms to specified ratio
        data = {
            'name': 'Sandwich Place',
            'address': '1 S University Ave, Ann Arbor, MI 48104',
            'timezone': 'US/Eastern',
            'default_sales_tax': '6.250'
        }
        form = RestaurantForm(data, {'image': long_image})
        restaurant = form.save(commit=False)
        image = Image.open(restaurant.image)
        self.assertEqual('%.2f' %
                         (image.width / image.height), '%.2f' % (5 / 3))
        self.assertTrue(restaurant.image.name.startswith("long-image"))

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
            'email',
            'Request has already been sent to this email'
        )

    def test_meal_form(self):
        # Image greater in width than height
        long_image = SimpleUploadedFile(
            name='long-image.jpg',
            content=open("./swickapp/tests/long-image.jpg", 'rb').read()
        )
        meal_data = {
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
        }
        form = MealForm(meal_data, {'image': long_image})
        meal = form.save(commit=False)
        image = Image.open(meal.image)
        self.assertEqual('%.2f' %
                         (image.width / image.height), '%.2f' % (5 / 3))
        self.assertTrue(meal.image.name.startswith("long-image"))

    def test_tax_category_form_base(self):
        # Test adding tax category with previously used name
        resp = self.client.post(
            reverse('restaurant_add_tax_category'),
            data={'name': 'Default', 'tax': '0.05'}
        )
        self.assertFormError(
            resp,
            'tax_category_form',
            'name',
            'Duplicate category name'
        )

    def test_tax_category_form(self):
        # Test adding tax category with previously used name
        resp = self.client.post(
            reverse('popup_tax_category'),
            data={
                'name': 'Default',
                'tax': '0.3'
            }
        )
        self.assertFormError(
            resp,
            'form',
            'name',
            'Duplicate category name'
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
            form.errors['options'],
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
            form.errors['max'],
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
            form.errors['min'],
            ['Minimum number of options cannot be greater than maximum number of options']
        )
