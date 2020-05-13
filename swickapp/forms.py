from django import forms
from django.contrib.auth.models import User
from swickapp.models import Restaurant, Meal

# Restaurant owner form
class UserForm(forms.ModelForm):
    email = forms.CharField(max_length = 256)
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        # Model imported from django
        model = User
        fields = ("username", "password", "first_name", "last_name", "email")

# Restaurant owner update form
class UserUpdateForm(forms.ModelForm):
    email = forms.CharField(max_length = 256)

    class Meta:
        # Model imported from django
        model = User
        fields = ("username", "first_name", "last_name", "email")

# Restaurant form
class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ("name", "address", "image")

# Meal form
class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        # Exlude restaurant form from meal form
        exclude = ("restaurant",)
