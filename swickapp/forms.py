from django import forms
from django.core.exceptions import ValidationError
from .models import User, Restaurant, ServerRequest, Category, Meal, \
    Customization, RequestOption

# Validate that email does not already have restaurant account linked
def validate_no_restaurant(value):
    try:
        user = User.objects.get(email=value)
        if hasattr(user, 'restaurant'):
            raise ValidationError('Account with this email already exists')
    except User.DoesNotExist:
        pass

# Restaurant owner form
class UserForm(forms.Form):
    name = forms.CharField(max_length=256)
    email = forms.EmailField(validators=[validate_no_restaurant])
    password = forms.CharField(widget=forms.PasswordInput())

# Restaurant owner update form
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("name", "email")

# Restaurant form
class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        exclude = ("user", "stripe_acct_id")

# Server request form
class ServerRequestForm(forms.ModelForm):
    class Meta:
        model = ServerRequest
        fields = ("name", "email")

    # Pass in request and save as a parameter
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(ServerRequestForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data
        # Only allow one server request per email per restaurant
        try:
            ServerRequest.objects.get(
                email=cleaned_data['email'],
                restaurant=self.request.user.restaurant
            )
            raise ValidationError('Request has already been sent to this email')
        except ServerRequest.DoesNotExist:
            pass

        return cleaned_data

# Category form
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        exclude = ("restaurant",)

# Meal form
class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        exclude = ("category", "enabled")

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
                attrs={'placeholder': 'Example:\nSmall\nMedium\nLarge\n', 'rows': 6}),
            'price_additions': forms.Textarea(
                attrs={'placeholder': 'Example:\n0\n1.25\n2.50', 'rows': 6}),
        }
        exclude = ("meal",)

# Request form
class RequestForm(forms.ModelForm):
    class Meta:
        model = RequestOption
        exclude = ("restaurant",)
