from decimal import Decimal

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .models_helper import create_stripe_customer, generate_token


class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames
    """

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


class User(AbstractUser):
    """
    Custom user model with email as username
    and name instead of separate first and last name fields
    """
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
    address = models.CharField(
        max_length=256, verbose_name="restaurant address")
    image = models.ImageField(verbose_name="restaurant image")
    timezone = models.CharField(max_length=16, choices=TIMEZONE_CHOICES)
    stripe_acct_id = models.CharField(max_length=255)
    default_sales_tax = models.DecimalField(max_digits=5, decimal_places=3, verbose_name="default sales tax (%)",
                                            validators=[MinValueValidator(Decimal('0'))])

    # For displaying name in Django dashboard
    def __str__(self):
        return self.name


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name='customer')
    stripe_cust_id = models.CharField(
        max_length=255, default=create_stripe_customer)

    def __str__(self):
        return self.user.email


class Server(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name='server')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL,
                                   blank=True, null=True)

    def __str__(self):
        return self.user.email


class ServerRequest(models.Model):
    """
    Temporary model for request to add server
    """
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=256)
    email = models.EmailField()
    token = models.CharField(max_length=40, default=generate_token)
    created_time = models.DateTimeField(default=timezone.now)
    accepted = models.BooleanField(default=False)

    def __str__(self):
        return self.email


class TaxCategory(models.Model):
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=256)
    tax = models.DecimalField(max_digits=5, decimal_places=3, validators=[
                              MinValueValidator(Decimal('0'))], verbose_name="Sales tax (%)")

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('restaurant', 'name')


class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=256)

    def __str__(self):
        return self.name


class Meal(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="meal")
    name = models.CharField(max_length=256, verbose_name="meal name")
    description = models.CharField(max_length=512, blank=True, null=True)
    price = models.DecimalField(max_digits=7, decimal_places=2,
                                validators=[MinValueValidator(Decimal('0.01'))])
    image = models.ImageField(blank=True, null=True)
    tax_category = models.ForeignKey(
        TaxCategory, on_delete=models.SET_NULL, null=True, verbose_name="Sales tax category")
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name


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


class Order(models.Model):
    PROCESSING = 'PROCESSING'
    ACTIVE = 'ACTIVE'
    COMPLETE = 'COMPLETE'
    STATUS_CHOICES = [
        (PROCESSING, "Payment processing"),
        (ACTIVE, "Active"),
        (COMPLETE, "Complete"),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    order_time = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES,
                              default=PROCESSING)
    table = models.IntegerField()
    subtotal = models.DecimalField(max_digits=7, decimal_places=2,
                                   blank=True, null=True)
    tax = models.DecimalField(max_digits=7, decimal_places=2,
                              blank=True, null=True)
    tip = models.DecimalField(max_digits=7, decimal_places=2,
                              blank=True, null=True)
    total = models.DecimalField(max_digits=7, decimal_places=2,
                                blank=True, null=True)
    stripe_fee = models.DecimalField(max_digits=7, decimal_places=2,
                                     blank=True, null=True)
    # Need to couple paymentIntent and order together
    stripe_payment_id = models.CharField(max_length=255, null=True)
    tip_stripe_payment_id = models.CharField(max_length=255, null=True)

    def __str__(self):
        return str(self.id)


class OrderItem(models.Model):
    COOKING = 'COOKING'
    SENDING = 'SENDING'
    COMPLETE = 'COMPLETE'
    STATUS_CHOICES = [
        (COOKING, "Cooking"),
        (SENDING, "Sending"),
        (COMPLETE, "Complete"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE,
                              related_name='order_item')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES,
                              default=COOKING)
    meal_name = models.CharField(max_length=256)
    meal_price = models.DecimalField(max_digits=7, decimal_places=2)
    quantity = models.IntegerField()
    total = models.DecimalField(max_digits=7, decimal_places=2,
                                blank=True, null=True)

    def __str__(self):
        return str(self.id)


class OrderItemCustomization(models.Model):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE,
                                   related_name='order_item_cust')
    customization_name = models.CharField(max_length=256)
    options = ArrayField(models.CharField(max_length=256))
    price_additions = ArrayField(models.DecimalField(max_digits=7,
                                                     decimal_places=2))

    def __str__(self):
        return str(self.id)


class RequestOption(models.Model):
    """
    Request option added by restaurant
    """
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=32)

    def __str__(self):
        return self.name


class Request(models.Model):
    """
    Temporary model for request sent by customer
    """
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    request_option = models.ForeignKey(RequestOption, on_delete=models.CASCADE)
    request_time = models.DateTimeField(default=timezone.now)
    table = models.IntegerField()

    def __str__(self):
        return str(self.id)
