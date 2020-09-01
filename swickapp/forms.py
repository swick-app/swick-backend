from django import forms
from django.contrib.auth.models import User
from swickapp.models import Restaurant, Meal, Customization

# Restaurant owner form
class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        # Model imported from django
        model = User
        fields = ("username", "password", "first_name", "last_name", "email")

# Restaurant owner update form
class UserUpdateForm(forms.ModelForm):
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

# Customization form
class CustomizationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prevent empty customization form
        self.empty_permitted = False
        # Set options and price additions array field delimiters to new line
        self.fields['options'].delimiter = '\n'
        self.fields['price_additions'].delimiter = '\n'

    class Meta:
        model = Customization
        widgets = {
            # Display placeholder text and use text area instead of text input
            # for options and price additions fields
            'options': forms.Textarea(
                attrs = {'placeholder': 'Example:\nSmall\nMedium\nLarge\n', 'rows': 6}),
            'price_additions': forms.Textarea(
                attrs = {'placeholder': 'Example:\n0\n1.25\n2.50', 'rows': 6}),
        }
        exclude = ("meal",)
