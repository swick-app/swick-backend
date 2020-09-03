from django.contrib.auth import user_logged_in
from django.dispatch import receiver
from django.utils import timezone
import pytz

@receiver(user_logged_in)
def post_login(sender, user, request, **kwargs):
    timezone.activate(pytz.timezone(user.restaurant.timezone))
