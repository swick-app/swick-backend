from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from swickapp.forms_helper import formatted_image_blob, validate_no_restaurant


class FormsHelperTest(TestCase):
    fixtures = ['testdata.json']

    def test_validate_no_restaurant(self):
        self.assertRaises(
            ValidationError, validate_no_restaurant, 'john@gmail.com')

    def test_formatted_image_blob(self):
        # Image greater in width than hieght
        long_image = SimpleUploadedFile(
            name='long-image.jpg',
            content=open("./swickapp/tests/long-image.jpg", 'rb').read()
        )
        # Image greater in height than width
        tall_image = SimpleUploadedFile(
            name='tall-image.jpg',
            content=open("./swickapp/tests/tall-image.jpg", 'rb').read()
        )
        # Image converts to given width and height
        blob = formatted_image_blob(long_image, 30, 10, 5, 20)
        im = Image.open(blob)
        self.assertEqual(im.width, 5)
        self.assertEqual(im.height, 20)
        # Long image conforms to aspect ratio
        blob = formatted_image_blob(long_image, None, None, None, None)
        im = Image.open(blob)
        self.assertEqual('%.2f' % (im.width / im.height), '%.2f' % (5 / 3))
        # Tall image conforms to aspect ratio
        blob = formatted_image_blob(tall_image, None, None, None, None)
        im = Image.open(blob)
        self.assertEqual('%.2f' % (im.width / im.height), '%.2f' % (5 / 3))
