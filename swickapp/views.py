from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from swickapp.forms import UserForm, RestaurantForm
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

# Home page: redirect to restaurant home page
def home(request):
    return redirect(restaurant_home)

# Restaurant home page
@login_required(login_url='/restaurant/login/')
def restaurant_home(request):
    return redirect(restaurant_menu)

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

# Restaurant menu page
@login_required(login_url='/restaurant/login/')
def restaurant_menu(request):
    return render(request, 'restaurant/menu.html', {})

# Restaurant order history page
@login_required(login_url='/restaurant/login/')
def restaurant_order_history(request):
    return render(request, 'restaurant/order_history.html', {})

# Restaurant servers page
@login_required(login_url='/restaurant/login/')
def restaurant_servers(request):
    return render(request, 'restaurant/servers.html', {})

# Restaurant account page
@login_required(login_url='/restaurant/login/')
def restaurant_account(request):
    return render(request, 'restaurant/account.html', {})
