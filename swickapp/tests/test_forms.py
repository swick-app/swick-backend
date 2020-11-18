from django.test import TestCase
from django.urls import reverse
from swickapp.models import User, Restaurant

class FormsTest(TestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="john@gmail.com")
        self.client.force_login(user)
        self.restaurant = Restaurant.objects.get(user=user)
