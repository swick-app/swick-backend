import os
import binascii
from decimal import Decimal
from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from .signals import *

def generate_token():
    return binascii.hexlify(os.urandom(20)).decode()

# Custom user model manager where email is the unique identifiers
# for authentication instead of usernames
class UserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)

# Custom user model with email as username
# and name instead of separate first and last name fields
class User(AbstractUser):
    username = None
    first_name = None
    last_name = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=256, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

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
        return self.user.email

# Server model
class Server(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,
        related_name='server')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL,
        blank=True, null=True)

    def __str__(self):
        return self.user.email

# Temporary model for request to add server
class ServerRequest(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=256)
    email = models.EmailField()
    token = models.CharField(max_length=40, default=generate_token)
    created_time = models.DateTimeField(default=timezone.now)
    accepted = models.BooleanField(default=False)

    def __str__(self):
        return self.email

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
