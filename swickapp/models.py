from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone

# Restaurant model
class Restaurant(models.Model):
    # One-to-one: one restaurant has one owner (user)
    user = models.OneToOneField(User, on_delete = models.CASCADE,
        related_name = 'restaurant')
    name = models.CharField(max_length = 256, verbose_name = "restaurant name")
    address = models.CharField(max_length = 256, verbose_name = "restaurant address")
    image = models.ImageField(verbose_name = "restaurant image (displayed in app)")

    # For displaying name in Django dashboard
    def __str__(self):
        return self.name

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
    restaurant = models.ForeignKey(Restaurant, on_delete = models.SET_NULL,
        null = True)

    def __str__(self):
        return self.user.get_full_name()

# Meal model
class Meal(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete = models.CASCADE)
    name = models.CharField(max_length = 256)
    description = models.CharField(max_length = 512)
    price = models.DecimalField(max_digits = 8, decimal_places = 2,
        validators = [MinValueValidator(Decimal('0.01'))])
    image = models.ImageField(blank = True, null = True)

    def __str__(self):
        return self.name

# Order model
class Order(models.Model):
    COOKING = 1
    SENDING = 2
    COMPLETE = 3

    STATUS_CHOICES = (
        (COOKING, "Cooking"),
        (SENDING, "Sending"),
        (COMPLETE, "Complete")
    )

    customer = models.ForeignKey(Customer, null = True, on_delete = models.SET_NULL)
    chef = models.ForeignKey(Server, null = True, on_delete = models.SET_NULL,
        related_name = 'chef')
    server = models.ForeignKey(Server, null = True, on_delete = models.SET_NULL,
        related_name = 'server')
    restaurant = models.ForeignKey(Restaurant, on_delete = models.CASCADE)
    table = models.IntegerField()
    total = models.DecimalField(max_digits = 8, decimal_places = 2)
    order_time = models.DateTimeField(default = timezone.now)
    status = models.IntegerField(choices = STATUS_CHOICES)

    def __str__(self):
        return str(self.id)

# Meals in order model
class OrderMeal(models.Model):
    order = models.ForeignKey(Order, on_delete = models.CASCADE,
        related_name = 'order_meal')
    meal = models.ForeignKey(Meal, null = True, on_delete = models.SET_NULL)
    quantity = models.IntegerField()
    total = models.DecimalField(max_digits = 8, decimal_places = 2)

    def __str__(self):
        return str(self.id)
