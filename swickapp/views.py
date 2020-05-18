from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from swickapp.forms import UserForm, RestaurantForm, UserUpdateForm, MealForm, CustomizationFormset
from swickapp.models import Meal, Customization, Order

# Home page: redirect to restaurant home page
def home(request):
    return redirect(restaurant_home)

# Restaurant sign up page
def restaurant_sign_up(request):
    user_form = UserForm()
    restaurant_form = RestaurantForm()

    if request.method == "POST":
        # Get data from user and restaurant forms
        user_form = UserForm(request.POST)
        restaurant_form = RestaurantForm(request.POST, request.FILES)

        # Create user and restaurant objects in database
        if user_form.is_valid() and restaurant_form.is_valid():
            new_user = User.objects.create_user(**user_form.cleaned_data)
            new_restaurant = restaurant_form.save(commit=False)
            new_restaurant.user = new_user
            new_restaurant.save()

            # Login with user form data
            login(request, authenticate(
                username = user_form.cleaned_data["username"],
                password = user_form.cleaned_data["password"]
            ))

            return redirect(restaurant_home)

    # Display user form and restaurant form
    return render(request, 'registration/sign_up.html', {
        "user_form": user_form,
        "restaurant_form": restaurant_form,
    })

# Restaurant home page
@login_required(login_url = '/accounts/login/')
def restaurant_home(request):
    return redirect(restaurant_menu)

# Restaurant menu page
@login_required(login_url = '/accounts/login/')
def restaurant_menu(request):
    # Get all of restaurant's meals from database
    meals = Meal.objects.filter(restaurant = request.user.restaurant).order_by("-id")
    return render(request, 'restaurant/menu.html', {"meals": meals})

# Restaurant add meal page
@login_required(login_url = '/accounts/login/')
def restaurant_add_meal(request):
    meal_form = MealForm()
    customization_formset = CustomizationFormset()

    if request.method == "POST":
        meal_form = MealForm(request.POST, request.FILES)
        customization_formset = CustomizationFormset(request.POST)

        if meal_form.is_valid() and customization_formset.is_valid():
            new_meal = meal_form.save(commit = False)
            new_meal.restaurant = request.user.restaurant
            new_meal.save()
            # Loop through each form in customization formset
            for form in customization_formset:
                new_customization = form.save(commit = False)
                new_customization.meal = new_meal
                new_customization.save()
            return redirect(restaurant_menu)

    return render(request, 'restaurant/add_meal.html', {
        "meal_form": meal_form,
        "customization_formset": customization_formset
    })

# Restaurant edit meal page
@login_required(login_url = '/accounts/login/')
def restaurant_edit_meal(request, meal_id):
    meal_form = MealForm(instance = Meal.objects.get(id = meal_id))

    # Request to update meal
    if request.method == "POST" and "update" in request.POST:
        meal_form = MealForm(request.POST, request.FILES,
            instance = Meal.objects.get(id = meal_id))

        if meal_form.is_valid():
            meal_form.save()
            return redirect(restaurant_menu)

    # Request to delete meal
    if request.method == "POST" and "delete" in request.POST:
        Meal.objects.filter(id = meal_id).delete()
        return redirect(restaurant_menu)

    return render(request, 'restaurant/edit_meal.html', {
        "meal_form": meal_form
    })

# Restaurant orders page
@login_required(login_url = '/accounts/login/')
def restaurant_orders(request):
    orders = Order.objects.filter(restaurant = request.user.restaurant).order_by("-id")
    return render(request, 'restaurant/orders.html', {"orders": orders})

# Restaurant servers page
@login_required(login_url='/accounts/login/')
def restaurant_servers(request):
    return render(request, 'restaurant/servers.html', {})

# Restaurant account page
@login_required(login_url = '/accounts/login/')
def restaurant_account(request):
    user_form = UserUpdateForm(instance = request.user)
    restaurant_form = RestaurantForm(instance = request.user.restaurant)

    # Update account info
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance = request.user)
        restaurant_form = RestaurantForm(request.POST, request.FILES, instance = request.user.restaurant)
        if user_form.is_valid() and restaurant_form.is_valid():
            user_form.save()
            restaurant_form.save()

    return render(request, 'restaurant/account.html', {
        "user_form": user_form,
        "restaurant_form": restaurant_form,
    })
