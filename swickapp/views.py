from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.forms import formset_factory, modelformset_factory
from django.http import Http404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .forms import UserForm, RestaurantForm, UserUpdateForm, MealForm, \
    CustomizationForm
from .models import User, Restaurant, Meal, Customization, Order, Server
import pytz
import stripe
import json
from rest_framework.decorators import api_view

# Home page: redirect to restaurant home page
def home(request):
    return redirect(restaurant_home)

# Restaurant sign up page
def restaurant_sign_up(request):
    # Prefix required because both forms share a field with the same name
    user_form = UserForm(prefix="user")
    restaurant_form = RestaurantForm(prefix="restaurant")

    if request.method == "POST":
        # Get data from user and restaurant forms
        user_form = UserForm(request.POST, prefix="user")
        restaurant_form = RestaurantForm(request.POST, request.FILES, prefix="restaurant")

        # Create user and restaurant objects in database
        if user_form.is_valid() and restaurant_form.is_valid():
            email = user_form.cleaned_data["email"]
            users = User.objects.filter(email=email)
            # If a user already exists from mobile app login
            # Grab user and set name and password
            if users:
                user = users[0]
                user.name = user_form.cleaned_data["name"]
                user.set_password(user_form.cleaned_data["password"])
                user.save()
            # Otherwise create user
            else:
                user = User.objects.create_user(**user_form.cleaned_data)

            # Create restaurant
            new_restaurant = restaurant_form.save(commit=False)
            new_restaurant.user = user
            # Create Stripe account for new user
            try:
                new_restaurant.stripe_acct_id = stripe.Account.create(
                                                    type="standard",
                                                    email=user.email).id
            except stripe.error.StripeError as e:
                raise Http404("Unable to create account. Please try again")

            new_restaurant.save()

            # redirect to resturant menu if stripe api fails
            redirect_link = restaurant_menu

            # Create a link for restaurant to setup Stripe account
            try:
                stripe_connect_redirect = stripe.AccountLink.create(
                    account = new_restaurant.stripe_acct_id,
                    type = "account_onboarding",
                    refresh_url = request.build_absolute_uri('accounts/refresh_stripe_link/'),
                    return_url = request.build_absolute_uri('/restaurant/')
                    )
                redirect_link = stripe_connect_redirect.url
            except stripe.error.StripeError as e:
                pass

            # Login with user form data
            login(request, user)

            # redirect user to stripe account creation
            return redirect(redirect_link)

    # Display user form and restaurant form
    return render(request, 'registration/sign_up.html', {
        "user_form": user_form,
        "restaurant_form": restaurant_form,
    })

# Redirect to refresh stripe link
@login_required(login_url='/accounts/login/')
def refresh_stripe_link(request):
    try:
        stripe_connect_redirect = stripe.AccountLink.create(
            account =  Restaurant.objects.get(user=request.user).stripe_acct_id,
            type = "account_onboarding",
            refresh_url = request.build_absolute_uri('/refresh_stripe_link/'),
            return_url = request.build_absolute_uri('/restaurant/')
            )
    except stripe.error.StripeError as e:
        raise Http404("Unable to link stripe account. Please try again on dashboard")
    return redirect(stripe_connect_redirect.url)

# Restaurant home page
@login_required(login_url='/accounts/login/')
def restaurant_home(request):
    return redirect(restaurant_menu)

# Restaurant menu page
@login_required(login_url='/accounts/login/')
def restaurant_menu(request):
    meals = Meal.objects.filter(restaurant=request.user.restaurant).order_by("name")
    return render(request, 'restaurant/menu.html', {"meals": meals})

# Restaurant add meal page
@login_required(login_url='/accounts/login/')
def restaurant_add_meal(request):
    meal_form = MealForm()
    CustomizationFormset = formset_factory(CustomizationForm, extra=0)
    customization_formset = CustomizationFormset()

    # Add new meal and customizations
    if request.method == "POST":
        meal_form = MealForm(request.POST, request.FILES)
        customization_formset = CustomizationFormset(request.POST)

        if meal_form.is_valid() and customization_formset.is_valid():
            new_meal = meal_form.save(commit=False)
            new_meal.restaurant = request.user.restaurant
            new_meal.save()
            # Loop through each form in customization formset
            for form in customization_formset:
                new_customization = form.save(commit=False)
                new_customization.meal = new_meal
                new_customization.save()
            return redirect(restaurant_menu)

    return render(request, 'restaurant/add_meal.html', {
        "meal_form": meal_form,
        "customization_formset": customization_formset
    })

# Restaurant edit meal page
@login_required(login_url='/accounts/login/')
def restaurant_edit_meal(request, meal_id):
    meal = Meal.objects.get(id=meal_id)
    # Checks if requested meal belongs to user's restaurant
    if request.user.restaurant != meal.restaurant:
        raise Http404("Meal does not exist")

    meal_form = MealForm(instance=meal)
    CustomizationFormset = modelformset_factory(Customization, form=CustomizationForm, extra=0)
    customization_objects = Customization.objects.filter(meal__id=meal_id)
    customization_formset = CustomizationFormset(queryset=customization_objects)

    # Update meal
    if request.method == "POST" and "update" in request.POST:
        meal_form = MealForm(request.POST, request.FILES,
            instance=meal)
        customization_formset = CustomizationFormset(request.POST)

        if meal_form.is_valid() and customization_formset.is_valid():
            meal_form.save()
            # Delete previous customizations
            Customization.objects.filter(meal__id=meal_id).delete()
            # Add updated customizations
            for form in customization_formset:
                new_customization = form.save(commit=False)
                new_customization.meal_id = meal_id
                new_customization.save()
            return redirect(restaurant_menu)

    # Delete meal
    if request.method == "POST" and "delete" in request.POST:
        Meal.objects.filter(id=meal_id).delete()
        return redirect(restaurant_menu)

    return render(request, 'restaurant/edit_meal.html', {
        "meal_form": meal_form,
        "customization_formset": customization_formset
    })

# Restaurant orders page
@login_required(login_url='/accounts/login/')
def restaurant_orders(request):
    orders = Order.objects.filter(restaurant=request.user.restaurant, payment_completed=True).order_by("-id")
    return render(request, 'restaurant/orders.html', {"orders": orders})

# Restaurant view order page
@login_required(login_url='/accounts/login/')
def restaurant_view_order(request, order_id):
    order = Order.objects.get(id=order_id)
    # Checks if requested order belongs to user's restaurant
    if request.user.restaurant != order.restaurant:
        raise Http404("Order does not exist")

    return render(request, 'restaurant/view_order.html', {"order": order})

# Restaurant servers page
@login_required(login_url='/accounts/login/')
def restaurant_servers(request):
    servers = Server.objects.filter(restaurant=request.user.restaurant)
    return render(request, 'restaurant/servers.html', {"servers": servers})

# Restaurant account page
@login_required(login_url='/accounts/login/')
def restaurant_account(request):
    # Prefix required because both forms share a field with the same name
    user_form = UserUpdateForm(prefix="user", instance=request.user)
    restaurant_form = RestaurantForm(prefix="restaurant", instance=request.user.restaurant)

    # Update account info
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, prefix="user", instance=request.user)
        restaurant_form = RestaurantForm(
            request.POST,
            request.FILES,
            prefix="restaurant",
            instance=request.user.restaurant
        )
        if user_form.is_valid() and restaurant_form.is_valid():
            user_form.save()
            restaurant_form.save()
            timezone.activate(pytz.timezone(request.POST["restaurant-timezone"]))

    # Create link for Stripe access
    stripe_url = "https://dashboard.stripe.com"
    try:
        stripe_account = stripe.Account.retrieve(Restaurant.objects.get(user=request.user).stripe_acct_id)
        if not stripe_account.details_submitted:
            new_link = stripe.AccountLink.create(
                account =  Restaurant.objects.get(user=request.user).stripe_acct_id,
                type = "account_onboarding",
                refresh_url = request.build_absolute_uri('accounts/refresh_stripe_link/'),
                return_url = request.build_absolute_uri('/restaurant/')
                )
            stripe_url = new_link.url
    except stripe.error.StripeError:
        pass

    return render(request, 'restaurant/account.html', {
        "user_form": user_form,
        "restaurant_form": restaurant_form,
        "stripe_link": stripe_url,
    })
