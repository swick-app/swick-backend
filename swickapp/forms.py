from django import forms
from django.core.exceptions import ValidationError
from django.core.files import File
from .models import User, Restaurant, ServerRequest, Category, Meal, \
    Customization, RequestOption, TaxCategory
from .widgets import DateTimePickerInput
from bootstrap_modal_forms.forms import BSModalModelForm
from PIL import Image
from io import BytesIO

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

# Formats original form image to 1080p and 5/3 ratio and returns in byte blob
def formatted_image_blob(image, x, y, w, h):
    im = Image.open(image)
    if x is None:
        if im.width/im.height > 5/3:
            w = im.height * (5/3)
            h = im.height
            x = (im.width - w)/2
            y = 0
        else:
            w = im.width
            h = im.width * 3/5
            x = 0
            y = (im.height - h)/2

    cropped_image = im.crop((x, y, w+x, h+y))
    cropped_image.thumbnail((1920,1152), Image.ANTIALIAS)

    blob = BytesIO()
    cropped_image.save(blob, im.format)
    return blob

# Restaurant form
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
        restaurant.image.save(name=restaurant.image.name, content=File(blob), save=commit)

        return restaurant

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
        fields =  ('name', 'tax')

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
                raise ValidationError({'name' : ["Duplicate category name",]})

        except TaxCategory.DoesNotExist:
            pass

# Tax Category form
class TaxCategoryForm(BSModalModelForm):
    def clean(self):
        cleaned_data = super().clean()
        # Check if combination of restaurant and name exists in database
        try:
            TaxCategory.objects.get(restaurant=self.request.user.restaurant,
                                        name=cleaned_data.get("name"))
            raise ValidationError({'name' : ["Duplicate category name",]})
        except TaxCategory.DoesNotExist:
            pass

    class Meta:
        model = TaxCategory
        fields = ('name', 'tax',)
        error_messages = {
                    'name': {
                        'max_length': "Name is too long.",
                        'required' : "Please input a name"
                    },
                    'tax' : {
                        'required' : 'Please input a number'
                    }
                }

# Customization form
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
            raise ValidationError('The number of options and price additions must be equal')
        if (cleaned_data.get('max') or 0) > len(cleaned_data.get('options') or []):
            raise ValidationError('Maximum number of selectable options cannot be greater than the number of options')
        if (cleaned_data.get('min') or 0) > (cleaned_data.get('max') or 0):
            raise ValidationError('Minimum number of options cannot be greater than maximum number of options')
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

# Request form
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
