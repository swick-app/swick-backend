from django.db import models
from django.contrib.auth.models import User

# Restaurant model
class Restaurant(models.Model):
    # One-to-one: one restaurant has one owner (user)
    user = models.OneToOneField(User, on_delete = models.CASCADE,
        related_name = 'restaurant')
    restaurant_name = models.CharField(max_length = 256)
    restaurant_phone_number = models.CharField(max_length = 32)
    restaurant_address = models.CharField(max_length = 256)
    restaurant_image = models.ImageField(upload_to = 'restaurant_images/',
        blank = False)

    # For displaying name in Django dashboard
    def __str__(self):
        return self.restaurant_name

# Customer model
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete = models.CASCADE,
        related_name = 'customer')

    def __str__(self):
        return self.user.get_full_name()

# Server model
class Server(models.Model):
    user = models.OneToOneField(User, on_delete = models.CASCADE,
        related_name = 'server')

    def __str__(self):
        return self.user.get_full_name()
