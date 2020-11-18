from operator import itemgetter

import stripe
from bootstrap_modal_forms.generic import BSModalCreateView
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.forms import formset_factory, modelformset_factory
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from .forms import (CategoryForm, CustomizationForm, MealForm, RequestDemoForm,
                    RequestForm, RestaurantForm, ServerRequestForm,
                    TaxCategoryForm, TaxCategoryFormBase, UserForm,
                    UserUpdateForm)
from .models import (Category, Customization, Meal, Order, RequestOption,
                     Restaurant, Server, ServerRequest, TaxCategory, User)
from .pusher_events import send_event_restaurant_added
from .views_helper import (create_default_request_options,
                           get_tax_categories_list,
                           initialize_datetime_range_orders)


def main_home(request):
    return render(request, 'main/home.html')


def request_demo(request):
    demo_form = RequestDemoForm()

    if request.method == "POST":
        demo_form = RequestDemoForm(request.POST)
        if demo_form.is_valid():
            name = demo_form.cleaned_data["name"]
            email = demo_form.cleaned_data["email"]
            restaurant = demo_form.cleaned_data["restaurant"]
            body = "Name: " + name + "\nEmail: " + email + "\nRestaurant: " + restaurant
            send_mail(
                'Swick Demo Request',
                body,
                None,
                ["seanlu99@gmail.com"]
            )
            return redirect('request_demo_done')
    return render(request, 'registration/request_demo.html', {
        "demo_form": demo_form
    })


def request_demo_done(request):
    return render(request, 'registration/request_demo_done.html')


def restaurant_sign_up(request):
    # Prefix required because both forms share a field with the same name
    user_form = UserForm(prefix="user")
    restaurant_form = RestaurantForm(prefix="restaurant")

    if request.method == "POST":
        # Get data from user and restaurant forms
        user_form = UserForm(request.POST, prefix="user")
        restaurant_form = RestaurantForm(
            request.POST, request.FILES, prefix="restaurant")

        # Create user and restaurant objects in database
        if user_form.is_valid() and restaurant_form.is_valid():
            email = user_form.cleaned_data["email"]
            # If a user already exists from mobile app login
            # Grab user and set name and password
            try:
                user = User.objects.get(email=email)
                user.name = user_form.cleaned_data["name"]
                user.set_password(user_form.cleaned_data["password"])
                user.save()
            # Otherwise create user
            except User.DoesNotExist:
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

            # Initialize default sales tax model for new restaurant
            default_tax_category = TaxCategory.objects.create(
                restaurant=new_restaurant,
                name="Default",
                tax=new_restaurant.default_sales_tax
            )

            # Create default request options
            create_default_request_options(new_restaurant)

            # redirect to resturant menu if stripe api fails
            redirect_link = restaurant_menu

            # Create a link for restaurant to setup Stripe account
            try:
                stripe_connect_redirect = stripe.AccountLink.create(
                    account=new_restaurant.stripe_acct_id,
                    type="account_onboarding",
                    refresh_url=request.build_absolute_uri(
                        'accounts/refresh_stripe_link/'),
                    return_url=request.build_absolute_uri('/restaurant/')
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


@login_required(login_url='/main/')
def refresh_stripe_link(request):
    """
    Redirect to refresh stripe link
    """
    try:
        stripe_connect_redirect = stripe.AccountLink.create(
            account=Restaurant.objects.get(user=request.user).stripe_acct_id,
            type="account_onboarding",
            refresh_url=request.build_absolute_uri('/refresh_stripe_link/'),
            return_url=request.build_absolute_uri('/restaurant/')
        )
    except stripe.error.StripeError as e:
        raise Http404(
            "Unable to link stripe account. Please try again on dashboard")
    return redirect(stripe_connect_redirect.url)


@login_required(login_url='/main/')
def restaurant_home(request):
    return redirect(restaurant_menu)


@login_required(login_url='/main/')
def restaurant_menu(request):
    categories = Category.objects.filter(
        restaurant=request.user.restaurant).order_by("name")
    return render(request, 'restaurant/menu.html', {"categories": categories})


@login_required(login_url='/main/')
def restaurant_add_category(request):
    category_form = CategoryForm()

    if request.method == "POST":
        category_form = CategoryForm(request.POST)

        if category_form.is_valid():
            category = category_form.save(commit=False)
            category.restaurant = request.user.restaurant
            category.save()

            # Redirect to category fragment identifier
            return redirect(reverse(restaurant_menu) + '#' + category.name)

    return render(request, 'restaurant/add_category.html', {
        "category_form": category_form,
    })


@login_required(login_url='/main/')
def restaurant_edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if category.restaurant != request.user.restaurant:
        raise Http404()

    category_form = CategoryForm(instance=category)

    # Update request
    if request.method == "POST":
        category_form = CategoryForm(request.POST, instance=category)

        if category_form.is_valid():
            category_form.save()
            # Redirect to category fragment identifier
            return redirect(reverse(restaurant_menu) + '#' + category.name)

    return render(request, 'restaurant/edit_category.html', {
        "category_form": category_form,
        "category_id": category.id,
    })


@login_required(login_url='/main/')
def restaurant_delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if category.restaurant != request.user.restaurant:
        raise Http404()
    category.delete()
    return redirect(restaurant_menu)


@login_required(login_url='/main/')
def restaurant_add_meal(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    # Checks if requested category belongs to user's restaurant
    if request.user.restaurant != category.restaurant:
        raise Http404()

    meal_form = MealForm(initial={'tax': Restaurant.objects.get(
        user=request.user).default_sales_tax})
    CustomizationFormset = formset_factory(CustomizationForm, extra=0)
    customization_formset = CustomizationFormset()

    # Add new meal and customizations
    if request.method == "POST":
        meal_form = MealForm(request.POST, request.FILES)
        customization_formset = CustomizationFormset(request.POST)

        if meal_form.is_valid() and customization_formset.is_valid():
            new_meal = meal_form.save(commit=False)
            new_meal.category = category
            new_meal.tax_category = TaxCategory.objects.get(restaurant=request.user.restaurant,
                                                            name=request.POST["meal_tax_category"])
            new_meal.save()
            # Loop through each form in customization formset
            for form in customization_formset:
                new_customization = form.save(commit=False)
                new_customization.meal = new_meal
                new_customization.save()
            # Redirect to category fragment identifier
            return redirect(reverse(restaurant_menu) + '#' + category.name)

    # Generate tax categories for html dropdown
    tax_categories_list = get_tax_categories_list(request.user.restaurant)
    # Sent as two seperate arrays due to javascript incompatiblities with double indexing
    tax_categories = []
    tax_percentages = []
    for item in tax_categories_list:
        tax_categories.append(item[0])
        tax_percentages.append(item[1])

    return render(request, 'restaurant/add_meal.html', {
        "meal_form": meal_form,
        "customization_formset": customization_formset,
        "tax_categories": tax_categories,
        "tax_percentages": tax_percentages
    })


@login_required(login_url='/main/')
def restaurant_edit_meal(request, meal_id):
    meal = get_object_or_404(Meal, id=meal_id)
    # Checks if requested meal belongs to user's restaurant
    if request.user.restaurant != meal.category.restaurant:
        raise Http404()

    meal_form = MealForm(instance=meal)
    CustomizationFormset = modelformset_factory(
        Customization, form=CustomizationForm, extra=0)
    customization_objects = Customization.objects.filter(meal__id=meal_id)
    customization_formset = CustomizationFormset(
        queryset=customization_objects)

    # Update meal
    if request.method == "POST":
        meal_form = MealForm(request.POST, request.FILES,
                             instance=meal)
        customization_formset = CustomizationFormset(request.POST)

        if meal_form.is_valid() and customization_formset.is_valid():
            update_meal = meal_form.save(commit=False)
            update_meal.tax_category = TaxCategory.objects.get(restaurant=request.user.restaurant,
                                                               name=request.POST["meal_tax_category"])
            update_meal.save()
            # Delete previous customizations
            Customization.objects.filter(meal__id=meal_id).delete()
            # Add updated customizations
            for form in customization_formset:
                new_customization = form.save(commit=False)
                new_customization.meal_id = meal_id
                new_customization.save()
            # Redirect to category fragment identifier
            return redirect(reverse(restaurant_menu) + '#' + meal.category.name)

    tax_categories_list = get_tax_categories_list(request.user.restaurant)
    # Sent as two seperate arrays due to javascript incompatiblities with double indexing
    tax_categories = []
    tax_percentages = []
    meal_category = "Default" if meal.tax_category == None else meal.tax_category.name
    tax_category_index = 0
    for index, item in enumerate(tax_categories_list):
        tax_categories.append(item[0])
        tax_percentages.append(item[1])
        if meal_category == item[0]:
            tax_category_index = index

    return render(request, 'restaurant/edit_meal.html', {
        "meal_form": meal_form,
        "customization_formset": customization_formset,
        "meal_id": meal_id,
        "tax_categories": tax_categories,
        "tax_percentages": tax_percentages,
        "tax_category_index": tax_category_index
    })


@login_required(login_url='/main/')
def restaurant_delete_meal(request, meal_id):
    meal = get_object_or_404(Meal, id=meal_id)
    # Checks if requested meal belongs to user's restaurant
    if request.user.restaurant != meal.category.restaurant:
        raise Http404()
    meal.delete()
    # Redirect to category fragment identifier
    return redirect(reverse(restaurant_menu) + '#' + meal.category.name)


@login_required(login_url='/main/')
def restaurant_toggle_meal(request, meal_id):
    meal = get_object_or_404(Meal, id=meal_id)
    # Checks if requested meal belongs to user's restaurant
    if request.user.restaurant != meal.category.restaurant:
        raise Http404()
    meal.enabled = not meal.enabled
    meal.save()
    # Redirect to category fragment identifier
    return redirect(reverse(restaurant_menu) + '#' + meal.category.name)


@login_required(login_url='/main/')
def restaurant_orders(request):
    data = initialize_datetime_range_orders(request)
    return render(request, 'restaurant/orders.html', {"orders": data["orders_in_range"],
                                                      "datetime_range_form": data["datetime_range_form"],
                                                      "start_time_error": data["start_time_error"],
                                                      "end_time_error": data["end_time_error"]})


@login_required(login_url='/main/')
def restaurant_view_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # Checks if requested order belongs to user's restaurant
    if request.user.restaurant != order.restaurant:
        raise Http404()

    return render(request, 'restaurant/view_order.html', {"order": order})


@login_required(login_url='/main/')
def restaurant_finances(request):
    default_category = TaxCategory.objects.get(
        restaurant=request.user.restaurant, name="Default")
    tax_categories = TaxCategory.objects.filter(
        restaurant=request.user.restaurant).exclude(name="Default").order_by("name")
    data = initialize_datetime_range_orders(request)

    gross_revenue = 0
    total_tax = 0
    total_tip = 0
    stripe_fees = 0

    for order in data["orders_in_range"]:
        try:
            gross_revenue += order.total
            total_tax += order.tax
            total_tip += order.tip
            stripe_fees += order.stripe_fee
        except TypeError:
            # Critical Error: Catching TypeError means null field was accessed
            # error would be raised by improper handling of dead orders
            pass

    revenue = gross_revenue - total_tax - total_tip - stripe_fees

    # Create link for Stripe access
    stripe_url = "https://dashboard.stripe.com"
    try:
        stripe_account = stripe.Account.retrieve(
            Restaurant.objects.get(user=request.user).stripe_acct_id)
        if not stripe_account.details_submitted:
            new_link = stripe.AccountLink.create(
                account=Restaurant.objects.get(
                    user=request.user).stripe_acct_id,
                type="account_onboarding",
                refresh_url=request.build_absolute_uri(
                    'accounts/refresh_stripe_link/'),
                return_url=request.build_absolute_uri('/restaurant/')
            )
            stripe_url = new_link.url
    except stripe.error.StripeError:
        pass

    return render(request, 'restaurant/finances.html', {"default_category": default_category,
                                                        "tax_categories": tax_categories,
                                                        "datetime_range_form": data["datetime_range_form"],
                                                        "start_time_error": data["start_time_error"],
                                                        "end_time_error": data["end_time_error"],
                                                        "gross_revenue": gross_revenue,
                                                        "total_tax": total_tax,
                                                        "total_tip": total_tip,
                                                        "stripe_fees": stripe_fees,
                                                        "revenue": revenue,
                                                        "stripe_link": stripe_url})


@login_required(login_url='/main/')
def restaurant_add_tax_category(request):
    tax_category_form = TaxCategoryFormBase()
    if request.method == "POST":
        tax_category_form = TaxCategoryFormBase(request.POST, request=request)

        if tax_category_form.is_valid():
            tax_category_object = tax_category_form.save(commit=False)
            tax_category_object.restaurant = request.user.restaurant
            tax_category_object.save()
            return redirect(restaurant_finances)

    return render(request, 'restaurant/add_tax_category.html', {
        "tax_category_form": tax_category_form,
    })


@login_required(login_url='/main/')
def restaurant_edit_tax_category(request, id):
    tax_category_object = get_object_or_404(TaxCategory, id=id)
    # Checks if request belongs to user's restaurant
    if tax_category_object.restaurant != request.user.restaurant:
        raise Http404()

    tax_category_form = TaxCategoryFormBase(
        instance=tax_category_object, request=request)

    # Update request
    if request.method == "POST":
        tax_category_form = TaxCategoryFormBase(
            request.POST, instance=tax_category_object, request=request)

        if tax_category_form.is_valid():
            instance = tax_category_form.save()
            if instance.name == "Default":
                Restaurant.objects.filter(pk=request.user.restaurant.pk).update(
                    default_sales_tax=instance.tax)
            return redirect(restaurant_finances)

    return render(request, 'restaurant/edit_tax_category.html', {
        "tax_category_form": tax_category_form,
        "tax_category_id": id,
        "tax_category_name": tax_category_object.name
    })


@login_required(login_url='/main/')
def restaurant_delete_tax_category(request, id):
    tax_category_object = get_object_or_404(TaxCategory, id=id)
    if tax_category_object.restaurant != request.user.restaurant or tax_category_object.name == "Default":
        raise Http404()
    # Set meals in tax category to default tax
    coupled_meals = Meal.objects.filter(tax_category=tax_category_object)
    # INVARIANT: Default should only be destroyed (thus invalid) when restaurant is deleted
    coupled_meals.update(tax_category=TaxCategory.objects.get_or_create(
        restaurant=request.user.restaurant, name="Default")[0])
    tax_category_object.delete()
    return redirect(restaurant_finances)


class TaxCategoryCreateView(BSModalCreateView):
    """
    Class view to create popup with tax category model
    BSModalCreateView inherits CreateUpdateAjaxMixin and ModelForm from bootstrap modal form
    Parent 'form_valid(self, form)' call will save TaxCategory to database
    """
    template_name = 'helpers/popup_tax_category.html'
    form_class = TaxCategoryForm
    success_message = 'Success: Tax Category was added'
    success_url = reverse_lazy('restaurant_menu')

    @method_decorator(login_required(login_url='/accounts/login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        form.instance.restaurant = self.request.user.restaurant
        tax_category = super().form_valid(form)
        return tax_category


@login_required(login_url='/main/')
def get_tax_categories(request):
    """
    Returns json response for tax_categories
    """
    tax_categories = get_tax_categories_list(request.user.restaurant)
    return JsonResponse({"category": get_tax_categories_list(request.user.restaurant)})


@login_required(login_url='/main/')
def restaurant_requests(request):
    requests = RequestOption.objects.filter(restaurant=request.user.restaurant)
    return render(request, 'restaurant/requests.html', {"requests": requests})


@login_required(login_url='/main/')
def restaurant_add_request(request):
    request_form = RequestForm()

    if request.method == "POST":
        request_form = RequestForm(request.POST)

        if request_form.is_valid():
            request_object = request_form.save(commit=False)
            request_object.restaurant = request.user.restaurant
            request_object.save()

            return redirect(restaurant_requests)

    return render(request, 'restaurant/add_request.html', {
        "request_form": request_form,
    })


@login_required(login_url='/main/')
def restaurant_edit_request(request, id):
    request_object = get_object_or_404(RequestOption, id=id)
    # Checks if request belongs to user's restaurant
    if request_object.restaurant != request.user.restaurant:
        raise Http404()

    request_form = RequestForm(instance=request_object)

    # Update request
    if request.method == "POST":
        request_form = RequestForm(request.POST, instance=request_object)

        if request_form.is_valid():
            request_form.save()
            return redirect(restaurant_requests)

    return render(request, 'restaurant/edit_request.html', {
        "request_form": request_form,
        "request_id": id,
    })


@login_required(login_url='/main/')
def restaurant_delete_request(request, id):
    request_object = get_object_or_404(RequestOption, id=id)
    if request_object.restaurant != request.user.restaurant:
        raise Http404()
    request_object.delete()
    return redirect(restaurant_requests)


@login_required(login_url='/main/')
def restaurant_servers(request):
    servers = Server.objects.filter(restaurant=request.user.restaurant)
    server_requests = ServerRequest.objects.filter(
        restaurant=request.user.restaurant)
    # Combine server and server requests to send to template
    all_servers = []
    for s in servers:
        new_server = {}
        new_server["id"] = s.id
        new_server["name"] = s.user.name
        new_server["email"] = s.user.email
        new_server["status"] = "Accepted"
        new_server["request"] = False
        all_servers.append(new_server)
    for s in server_requests:
        new_server = {}
        new_server["id"] = s.id
        new_server["name"] = s.name
        new_server["email"] = s.email
        if s.accepted:
            new_server["status"] = "Accepted"
        else:
            new_server["status"] = "Pending"
        new_server["request"] = True
        all_servers.append(new_server)
    all_servers = sorted(all_servers, key=itemgetter("name"))
    return render(request, 'restaurant/servers.html', {"servers": all_servers})


@login_required(login_url='/main/')
def restaurant_add_server(request):
    # Pass in request so it can be used in form validation
    server_request_form = ServerRequestForm(request=request)

    if request.method == "POST":
        server_request_form = ServerRequestForm(request.POST, request=request)

        if server_request_form.is_valid():
            # Create server request object
            server_request = server_request_form.save(commit=False)
            server_request.restaurant = request.user.restaurant
            server_request.save()

            # Send email to server
            body = render_to_string(
                'registration/server_link_restaurant_email.txt', {
                    'restaurant': server_request.restaurant,
                    'url': request.build_absolute_uri(
                        reverse('server_link_restaurant',
                                args=[server_request.token])
                    )
                }
            )
            send_mail(
                'Swick Add Server Request',
                body,
                None,
                [server_request.email]
            )
            return redirect(restaurant_servers)

    return render(request, 'restaurant/add_server.html', {
        "server_request_form": server_request_form,
    })


@login_required(login_url='/main/')
def restaurant_delete_server(request, id):
    server = get_object_or_404(Server, id=id)
    if server.restaurant != request.user.restaurant:
        raise Http404()
    server.restaurant = None
    server.save()
    return redirect(restaurant_servers)


@login_required(login_url='/main/')
def restaurant_delete_server_request(request, id):
    server_request = get_object_or_404(ServerRequest, id=id)
    if server_request.restaurant != request.user.restaurant:
        raise Http404()
    server_request.delete()
    return redirect(restaurant_servers)


@login_required(login_url='/main/')
def restaurant_account(request):
    # Prefix required because both forms share a field with the same name
    user_form = UserUpdateForm(prefix="user", instance=request.user)
    restaurant_form = RestaurantForm(
        prefix="restaurant", instance=request.user.restaurant)
    # Update account info
    if request.method == "POST":
        user_form = UserUpdateForm(
            request.POST, prefix="user", instance=request.user)
        restaurant_form = RestaurantForm(
            request.POST,
            request.FILES,
            prefix="restaurant",
            instance=request.user.restaurant
        )
        if user_form.is_valid() and restaurant_form.is_valid():
            user_form.save()
            restaurant_form.save()

        # Update default sales tax model for this Restaurant
        # INVARIANT: Default should only be destroyed (thus invalid) when restaurant is deleted:
        TaxCategory.objects.filter(restaurant=request.user.restaurant, name="Default").update(
            tax=request.user.restaurant.default_sales_tax)

    return render(request, 'restaurant/account.html', {
        "user_form": user_form,
        "restaurant_form": restaurant_form
    })


def server_link_restaurant(request, token):
    """
    When server clicks on url to link restaurant
    """
    server_request = get_object_or_404(ServerRequest, token=token)
    # Set server's restaurant if they have already created account
    try:
        server = Server.objects.get(user__email=server_request.email)
        server.restaurant = server_request.restaurant
        server.save()
        server_request.delete()
        send_event_restaurant_added(server)
    except Server.DoesNotExist:
        server_request.accepted = True
        server_request.save()

    return render(request, 'registration/server_link_restaurant_confirm.html', {
        "restaurant": server_request.restaurant.name
    })
