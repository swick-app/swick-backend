import json

from django.urls import reverse
from rest_framework.test import APITestCase
from swickapp.models import User


class APITest(APITestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        user = User.objects.get(email="seanlu99@gmail.com")
        self.client.force_authenticate(user)

    def test_update_info(self):
        # POST success
        resp = self.client.post(
            reverse('update_info'),
            data={'name': 'Jean-Paul', 'email': 'jeanpaul@gmail.com'}
        )
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        User.objects.get(email='jeanpaul@gmail.com', name='Jean-Paul')
        self.assertRaises(User.DoesNotExist, User.objects.get,
                          email='seanlu99@gmail.com')
        # POST success: no email
        resp = self.client.post(
            reverse('update_info'),
            data={'name': 'Jean', 'email': ''}
        )
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        User.objects.get(email='jeanpaul@gmail.com', name='Jean')
        self.assertRaises(User.DoesNotExist, User.objects.get,
                          email='seanlu99@gmail.com')
        # POST error: email already taken
        resp = self.client.post(
            reverse('update_info'),
            data={'name': 'Jean-Paul', 'email': 'seanlu@umich.edu'}
        )
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'email_already_taken')
