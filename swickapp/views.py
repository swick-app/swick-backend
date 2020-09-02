from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.forms import formset_factory, modelformset_factory
from django.http import Http404
from swickapp.forms import UserForm, RestaurantForm, UserUpdateForm, MealForm, \
    CustomizationForm
from swickapp.models import Meal, Customization, Order, Server

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
    meals = Meal.objects.filter(restaurant = request.user.restaurant).order_by("name")
    return render(request, 'restaurant/menu.html', {"meals": meals})

# Restaurant add meal page
@login_required(login_url = '/accounts/login/')
def restaurant_add_meal(request):
    meal_form = MealForm()
    CustomizationFormset = formset_factory(CustomizationForm, extra = 0)
    customization_formset = CustomizationFormset()

    # Add new meal and customizations
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
    meal = Meal.objects.get(id = meal_id)
    # Checks if requested meal belongs to user's restaurant
    if request.user.restaurant != meal.restaurant:
        raise Http404("Meal does not exist")

    meal_form = MealForm(instance = meal)
    CustomizationFormset = modelformset_factory(Customization, form = CustomizationForm, extra = 0)
    customization_objects = Customization.objects.filter(meal__id = meal_id)
    customization_formset = CustomizationFormset(queryset = customization_objects)

    # Update meal
    if request.method == "POST" and "update" in request.POST:
        meal_form = MealForm(request.POST, request.FILES,
            instance = meal)
        customization_formset = CustomizationFormset(request.POST)

        if meal_form.is_valid() and customization_formset.is_valid():
            meal_form.save()
            # Delete previous customizations
            Customization.objects.filter(meal__id = meal_id).delete()
            # Add updated customizations
            for form in customization_formset:
                new_customization = form.save(commit = False)
                new_customization.meal_id = meal_id
                new_customization.save()
            return redirect(restaurant_menu)

    # Delete meal
    if request.method == "POST" and "delete" in request.POST:
        Meal.objects.filter(id = meal_id).delete()
        return redirect(restaurant_menu)

    return render(request, 'restaurant/edit_meal.html', {
        "meal_form": meal_form,
        "customization_formset": customization_formset
    })

# Restaurant orders page
@login_required(login_url = '/accounts/login/')
def restaurant_orders(request):
    orders = Order.objects.filter(restaurant = request.user.restaurant).order_by("-id")
    return render(request, 'restaurant/orders.html', {"orders": orders})

# Restaurant view order page
@login_required(login_url = '/accounts/login/')
def restaurant_view_order(request, order_id):
    order = Order.objects.get(id = order_id)
    # Checks if requested order belongs to user's restaurant
    if request.user.restaurant != order.restaurant:
        raise Http404("Order does not exist")
        
    return render(request, 'restaurant/view_order.html', {"order": order})

# Restaurant servers page
@login_required(login_url='/accounts/login/')
def restaurant_servers(request):
    servers = Server.objects.filter(restaurant = request.user.restaurant)
    return render(request, 'restaurant/servers.html', {"servers": servers})

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
