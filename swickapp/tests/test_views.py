import tempfile

from django.test import TestCase
from django.urls import reverse
from swickapp.models import Category, Customization, Meal, Restaurant, User


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
        self.assertEqual(category.name, 'Appetizers')

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
