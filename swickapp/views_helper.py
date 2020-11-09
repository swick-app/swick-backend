from django.utils.timezone import localtime
from .models import RequestOption, Order, TaxCategory
from .forms import DateTimeRangeForm


def create_default_request_options(restaurant):
    """
    Create default request options for a restaurant
    """
    default_options = ["Water", "Fork", "Knife", "Spoon", "Napkins", "Help"]
    for o in default_options:
        RequestOption.objects.create(restaurant=restaurant, name=o)


def initalize_datetime_range_orders(request):
    """
    Initalizes datetime_range_form and orders queryset and
    returns map containing objects along with any error messages
    """
    curr_day_start = localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    curr_day_end = localtime().replace(
        hour=23, minute=59, second=59, microsecond=999999)
    datetime_range_form = DateTimeRangeForm(initial={'start_time': curr_day_start.strftime("%m/%d/%Y %I:%M%p"),
                                                     'end_time': curr_day_end.strftime("%m/%d/%Y %I:%M%p")})
    start_time_error = ""
    end_time_error = ""

    orders_in_range = Order.objects.filter(
        restaurant=request.user.restaurant,
        order_time__range=(curr_day_start, curr_day_end)
    ).exclude(status=Order.PROCESSING).order_by("id")
    if request.method == 'POST':
        datetime_range_form = DateTimeRangeForm(request.POST)
        if datetime_range_form.is_valid():
            orders_in_range = Order.objects.filter(
                restaurant=request.user.restaurant,
                order_time__range=(
                    datetime_range_form.cleaned_data['start_time'],
                    datetime_range_form.cleaned_data['end_time']
                )
            ).exclude(status=Order.PROCESSING).order_by("id")
        else:
            if datetime_range_form.has_error("start_time", "invalid"):
                start_time_error = datetime_range_form.errors["start_time"][0]
            if datetime_range_form.has_error("end_time", "invalid"):
                end_time_error = datetime_range_form.errors["end_time"][0]
            orders_in_range = Order.objects.none()

    return {"datetime_range_form": datetime_range_form,
            "orders_in_range": orders_in_range,
            "start_time_error": start_time_error,
            "end_time_error": end_time_error}


def get_tax_categories_list(restaurant):
    """
    Returns list of pair("name", "tax") of all tax categories
    """
    default = TaxCategory.objects.get(restaurant=restaurant, name="Default")
    categories = TaxCategory.objects.filter(restaurant=restaurant)
    data = []
    data.append(((default.name), str(default.tax).rstrip('0').rstrip('.')))
    for category in categories:
        if category.pk == default.pk:
            continue
        pair = (category.name, str(category.tax).rstrip('0').rstrip('.'))
        data.append(pair)
    return data
