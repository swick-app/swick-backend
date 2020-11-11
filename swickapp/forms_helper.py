from io import BytesIO

from django.core.exceptions import ValidationError
from PIL import Image

from .models import User


def validate_no_restaurant(value):
    """
    Validate that email does not already have restaurant account linked
    """
    try:
        user = User.objects.get(email=value)
        if hasattr(user, 'restaurant'):
            raise ValidationError('Account with this email already exists')
    except User.DoesNotExist:
        pass


def formatted_image_blob(image, x, y, w, h):
    """
    Formats original form image to 1080p and 5/3 ratio and returns in byte blob
    """
    im = Image.open(image)
    if x is None:
        if im.width / im.height > 5 / 3:
            w = im.height * (5 / 3)
            h = im.height
            x = (im.width - w) / 2
            y = 0
        else:
            w = im.width
            h = im.width * 3 / 5
            x = 0
            y = (im.height - h) / 2

    cropped_image = im.crop((x, y, w + x, h + y))
    cropped_image.thumbnail((1920, 1152), Image.ANTIALIAS)

    blob = BytesIO()
    cropped_image.save(blob, im.format)
    return blob
