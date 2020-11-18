from django.core.exceptions import ValidationError
from django.test import TestCase
from swickapp.forms_helper import validate_no_restaurant


class FormsHelperTest(TestCase):
    fixtures = ['testdata.json']

    def test_validate_no_restaurant(self):
        self.assertRaises(
            ValidationError, validate_no_restaurant, 'john@gmail.com')
