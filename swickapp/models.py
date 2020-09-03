from decimal import Decimal
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from .signals import *

# Restaurant model
class Restaurant(models.Model):
    ALASKA = 'US/Alaska'
    ARIZONA = 'US/Arizona'
    CENTRAL = 'US/Central'
    EASTERN = 'US/Eastern'
    HAWAII = 'US/Hawaii'
    MOUNTAIN = 'US/Mountain'
    PACIFIC = 'US/Pacific'
    TIMEZONE_CHOICES = [
        (ALASKA, 'Alaska'),
        (ARIZONA, 'Arizona'),
        (EASTERN, 'Eastern'),
        (HAWAII, 'Hawaii'),
        (CENTRAL, 'Central'),
        (MOUNTAIN, 'Mountain'),
        (PACIFIC, 'Pacific'),
    ]
    # One-to-one: one restaurant has one owner (user)
    user = models.OneToOneField(User, on_delete=models.CASCADE,
        related_name='restaurant')
    name = models.CharField(max_length=256, verbose_name="restaurant name")
    address = models.CharField(max_length=256, verbose_name="restaurant address")
    image = models.FileField(verbose_name="restaurant image")
    timezone = models.CharField(max_length=16, choices=TIMEZONE_CHOICES)

    # For displaying name in Django dashboard
    def __str__(self):
        return self.name

# Customer model
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,
        related_name='customer')

    def __str__(self):
        return self.user.get_full_name()

# Server model
class Server(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,
        related_name='server')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL,
        blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name()

# Meal model
class Meal(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=256, verbose_name="meal name")
    description = models.CharField(max_length=512, blank=True, null=True)
    price = models.DecimalField(max_digits=7, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))])
    category = models.CharField(max_length=256, verbose_name="category (ex. Appetizers)")
    image = models.FileField(blank=True, null=True)

    def __str__(self):
        return self.name

# Customization model
class Customization(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE,
        related_name='customization')
    name = models.CharField(max_length=256, verbose_name="customization name")
    options = ArrayField(models.CharField(max_length=256),
        verbose_name="options (one on each line)")
    price_additions = ArrayField(models.DecimalField(
            max_digits=7,
            decimal_places=2,
            validators=[MinValueValidator(Decimal('0'))]),
        verbose_name="price additions (one on each line, insert 0 if no addition)")
    min = models.IntegerField(verbose_name="minimum selectable options",
        validators=[MinValueValidator(0)])
    max = models.IntegerField(verbose_name="maximum selectable options",
        validators=[MinValueValidator(0)])

    def __str__(self):
        return self.name

# Order model
class Order(models.Model):
    COOKING = 1
    SENDING = 2
    COMPLETE = 3
    STATUS_CHOICES = [
        (COOKING, "Cooking"),
        (SENDING, "Sending"),
        (COMPLETE, "Complete"),
    ]

    customer = models.ForeignKey(Customer, blank=True, null=True,
        on_delete=models.SET_NULL)
    chef = models.ForeignKey(Server, blank=True, null=True,
        on_delete=models.SET_NULL, related_name='chef')
    server = models.ForeignKey(Server, blank=True, null=True,
        on_delete=models.SET_NULL, related_name='server')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    table = models.IntegerField()
    total = models.DecimalField(max_digits=7, decimal_places=2,
        blank=True, null=True)
    order_time = models.DateTimeField(default=timezone.now)
    status = models.IntegerField(choices=STATUS_CHOICES)

    def __str__(self):
        return str(self.id)

# Order item model
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE,
        related_name='order_item')
    meal_name = models.CharField(max_length=256)
    meal_price = models.DecimalField(max_digits=7, decimal_places=2)
    quantity = models.IntegerField()
    total = models.DecimalField(max_digits=7, decimal_places=2,
        blank=True, null=True)

    def __str__(self):
        return str(self.id)

# Order item customization model
class OrderItemCustomization(models.Model):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE,
        related_name='order_item_cust')
    customization_name = models.CharField(max_length=256)
    options = ArrayField(models.CharField(max_length=256))
    price_additions = ArrayField(models.DecimalField(max_digits=7,
        decimal_places=2))

    def __str__(self):
        return str(self.id)
