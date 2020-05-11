from django import forms
from django.contrib.auth.models import User
from swickapp.models import Restaurant

# Restaurant owner form
class UserForm(forms.ModelForm):
    email = forms.CharField(max_length=100, required=True)
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        # Model imported from django
        model = User
        fields = ("username", "password", "first_name", "last_name", "email")

# Restaurant form
class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ("restaurant_name", "restaurant_phone_number",
        "restaurant_address", "restaurant_image")