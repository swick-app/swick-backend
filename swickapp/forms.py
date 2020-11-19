from bootstrap_modal_forms.forms import BSModalModelForm
from django import forms
from django.core.exceptions import ValidationError
from django.core.files import File

from .forms_helper import formatted_image_blob, validate_no_restaurant
from .models import (Category, Customization, Meal, RequestOption, Restaurant,
                     ServerRequest, TaxCategory, User)
from .widgets import DateTimePickerInput


class RequestDemoForm(forms.Form):
    """
    Form for restaurant to request a demo
    """
    name = forms.CharField(max_length=256)
    email = forms.EmailField(validators=[validate_no_restaurant])
    restaurant = forms.CharField(max_length=256)


class UserForm(forms.Form):
    """
    Restaurant owner form
    """
    name = forms.CharField(max_length=256)
    email = forms.EmailField(validators=[validate_no_restaurant])
    password = forms.CharField(widget=forms.PasswordInput())


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("name", "email")


class RestaurantForm(forms.ModelForm):
    # Image cropping fields
    x = forms.FloatField(widget=forms.HiddenInput(), required=False)
    y = forms.FloatField(widget=forms.HiddenInput(), required=False)
    width = forms.FloatField(widget=forms.HiddenInput(), required=False)
    height = forms.FloatField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Restaurant
        exclude = ("user", "stripe_acct_id")

    def save(self, commit=True):
        restaurant = super(RestaurantForm, self).save(commit=commit)
        blob = formatted_image_blob(restaurant.image,
                                    self.cleaned_data.get('x'),
                                    self.cleaned_data.get('y'),
                                    self.cleaned_data.get('width'),
                                    self.cleaned_data.get('height'))
        restaurant.image.save(name=restaurant.image.name,
                              content=File(blob), save=commit)

        return restaurant


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
            raise ValidationError({'email': "Request has already been sent to this email"})
        except ServerRequest.DoesNotExist:
            pass

        return cleaned_data


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        exclude = ("restaurant",)


class MealForm(forms.ModelForm):
    # Image cropping fields
    x = forms.FloatField(widget=forms.HiddenInput(), required=False)
    y = forms.FloatField(widget=forms.HiddenInput(), required=False)
    width = forms.FloatField(widget=forms.HiddenInput(), required=False)
    height = forms.FloatField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Meal
        exclude = ("category", "enabled", "tax_category")

    def save(self, commit=True):
        meal = super(MealForm, self).save(commit=commit)
        if meal.image:
            blob = formatted_image_blob(meal.image,
                                        self.cleaned_data.get('x'),
                                        self.cleaned_data.get('y'),
                                        self.cleaned_data.get('width'),
                                        self.cleaned_data.get('height'))
            meal.image.save(name=meal.image.name, content=File(blob), save=False)
        return meal


class TaxCategoryFormBase(forms.ModelForm):
    class Meta:
        model = TaxCategory
        fields = ('name', 'tax')

    # Pass in request and save as a parameter
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(TaxCategoryFormBase, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        try:
            matching_category = TaxCategory.objects.get(restaurant=self.request.user.restaurant,
                                                        name=cleaned_data.get("name"))
            if self.instance.pk != matching_category.pk:
                raise ValidationError({'name': "Duplicate category name"})

        except TaxCategory.DoesNotExist:
            pass


class TaxCategoryForm(BSModalModelForm):
    def clean(self):
        cleaned_data = super().clean()
        # Check if combination of restaurant and name exists in database
        try:
            TaxCategory.objects.get(restaurant=self.request.user.restaurant,
                                    name=cleaned_data.get("name"))
            raise ValidationError({'name': "Duplicate category name"})
        except TaxCategory.DoesNotExist:
            pass

    class Meta:
        model = TaxCategory
        fields = ('name', 'tax',)
        error_messages = {
            'name': {
                'max_length': "Name is too long.",
                'required': "Please input a name"
            },
            'tax': {
                'required': 'Please input a number'
            }
        }


class CustomizationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prevent empty customization form
        self.empty_permitted = False
        # Set options and price additions array field delimiters to new line
        self.fields['options'].delimiter = '\n'
        self.fields['price_additions'].delimiter = '\n'

    def clean(self):
        cleaned_data = self.cleaned_data
        if len(cleaned_data.get('options') or []) != len(cleaned_data.get('price_additions') or []):
            raise ValidationError({'options':
                'The number of options and price additions must be equal'})
        if (cleaned_data.get('max') or 0) > len(cleaned_data.get('options') or []):
            raise ValidationError({'max':
                'Maximum number of selectable options cannot be greater than the number of options'})
        if (cleaned_data.get('min') or 0) > (cleaned_data.get('max') or 0):
            raise ValidationError({'min':
                'Minimum number of options cannot be greater than maximum number of options'})
        return cleaned_data

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


class RequestForm(forms.ModelForm):
    class Meta:
        model = RequestOption
        exclude = ("restaurant",)


class DateTimeRangeForm(forms.Form):
    start_time = forms.DateTimeField(
        input_formats=['%m/%d/%Y %I:%M%p'],
        widget=DateTimePickerInput()
    )
    end_time = forms.DateTimeField(
        input_formats=['%m/%d/%Y %I:%M%p'],
        widget=DateTimePickerInput()
    )
