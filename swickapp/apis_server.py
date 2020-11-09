from django.http import JsonResponse
from drf_multiple_model.mixins import FlatMultipleModelMixin
from rest_framework.decorators import api_view
from rest_framework.generics import GenericAPIView

from .models import Order, OrderItem, Restaurant, Server, ServerRequest
from .serializers import (OrderDetailsSerializerForServer,
                          OrderItemToCookSerializer, OrderItemToSendSerializer,
                          OrderSerializerForServer, RequestSerializer)


@api_view(['POST'])
def login(request):
    """
    header:
        Authorization: Token ...
    return:
        status
    """
    # Create server account if not created
    if not Server.objects.filter(user=request.user).exists():
        server = Server.objects.create(user=request.user)
        # Set server's restaurant if server has already accepted request
        # from restaurant
        try:
            server_request = ServerRequest.objects.get(
                email=request.user.email,
                accepted=True
            )
            server.restaurant = server_request.restaurant
            server.save()
            server_request.delete()
        except ServerRequest.DoesNotExist:
            pass

    # Check that user's name is set
    if not request.user.name:
        return JsonResponse({"status": "name_not_set"})
    return JsonResponse({"status": "success"})


@api_view()
def get_orders(request):
    """
    Get list of restaurant's last 20 orders
    header:
        Authorization: Token ...
    return:
        [orders]
            id
            customer_name
            order_time
            status
        status
    """
    restaurant = request.user.server.restaurant
    if restaurant is None:
        return JsonResponse({
            "status": "restaurant_not_set"
        })
    orders = OrderSerializerForServer(
        Order.objects.filter(restaurant=restaurant)
        .order_by("-id")[:20],
        many=True
    ).data
    return JsonResponse({"orders": orders, "status": "success"})


@api_view()
def get_order(request, order_id):
    """
    header:
        Authorization: Token ...
    return:
        order
            id
            customer_name
            order_time
            status
        status
    """
    restaurant = request.user.server.restaurant
    if restaurant is None:
        return JsonResponse({
            "status": "restaurant_not_set"
        })
    try:
        order_object = Order.objects.get(id=order_id)
    except Restaurant.DoesNotExist:
        return JsonResponse({"status": "order_does_not_exist"})
    order = OrderSerializerForServer(order_object).data
    return JsonResponse({"order": order, "status": "success"})


@api_view()
def get_order_details(request, order_id):
    """
    header:
        Authorization: Token ...
    return:
        order_details
            id
            customer_name
            table
            order_time
            total
            [cooking_order_items] / [sending_order_items] / [complete_order_items]
                id
                meal_name
                quantity
                total
                status
                [order_item_cust]
                    id
                    name
                    [options]
        status
    """
    restaurant = request.user.server.restaurant
    order = Order.objects.get(id=order_id)
    # Check if a restaurant's server is making the request
    if order.restaurant != restaurant:
        return JsonResponse({"status": "invalid_request"})

    order_details = OrderDetailsSerializerForServer(
        order
    ).data
    return JsonResponse({"order_details": order_details, "status": "success"})


@api_view()
def get_order_items_to_cook(request):
    """
    header:
        Authorization: Token ...
    return:
        [order_items]
            id
            order_id
            table
            meal_name
            quantity
            [order_item_cust]
                id
                name
                [options]
    """
    restaurant = request.user.server.restaurant
    if restaurant is None:
        return JsonResponse({
            "status": "restaurant_not_set"
        })
    order_items = OrderItemToCookSerializer(
        OrderItem.objects.filter(
            order__restaurant=restaurant, status=OrderItem.COOKING)
        .order_by("id"),
        many=True
    ).data
    return JsonResponse({"order_items": order_items, "status": "success"})


class ServerGetItemsToSend(FlatMultipleModelMixin, GenericAPIView):
    """
    Get list of restaurant's order items to send and requests
    Uses django-rest-multiple-models to sort and send different models together
    header:
        Authorization: Token ...
    return:
        [OrderItem or Request]
            id
            order_id (only for OrderItem)
            table
            customer_name
            meal_name or request_name
            time
            type
    """

    # Sort combined query list by time
    sorting_fields = ['time']

    # Overrided function to build combined query list
    def get_querylist(self):
        restaurant = self.request.user.server.restaurant
        order_items = OrderItem.objects.filter(
            order__restaurant=restaurant,
            status=OrderItem.SENDING
        )
        requests = Request.objects.filter(
            request_option__restaurant=restaurant)

        querylist = [
            {'queryset': order_items, 'serializer_class': OrderItemToSendSerializer},
            {'queryset': requests, 'serializer_class': RequestSerializer}
        ]
        return querylist

    # GET request
    def get(self, request, *args, **kwargs):
        restaurant = request.user.server.restaurant
        if restaurant is None:
            return JsonResponse({
                "status": "restaurant_not_set"
            })
        return self.list(request, *args, **kwargs)


@api_view(['POST'])
def update_order_item_status(request):
    """
    header:
        Authorization: Token ...
    params:
        order_item_id
        status
    return:
        status
    """
    restaurant = request.user.server.restaurant
    item = OrderItem.objects.get(id=request.POST.get("order_item_id"))

    # Check if a restaurant's server is making the request
    if item.order.restaurant != restaurant:
        return JsonResponse({"status": "invalid_request"})

    order = item.order
    new_status = request.POST.get("status")

    # Update item with new status
    item.status = new_status
    item.save()

    # Check if order status needs to be updated
    if new_status == OrderItem.COMPLETE:
        if not OrderItem.objects.filter(order=order).exclude(status=OrderItem.COMPLETE).exists():
            order.status = Order.COMPLETE
            order.save()
    else:
        order.status = Order.ACTIVE
        order.save()

    return JsonResponse({"status": "success"})


@api_view(['POST'])
def delete_request(request):
    """
    header:
        Authorization: Token ...
    params:
        id
    return:
        status
    """
    restaurant = request.user.server.restaurant
    request_object = Request.objects.get(id=request.POST.get("id"))

    # Check if a restaurant's server is making the request
    if request_object.request_option.restaurant != restaurant:
        return JsonResponse({"status": "invalid_request"})

    request_object.delete()

    return JsonResponse({"status": "success"})


@api_view()
def get_info(request):
    """
    header:
        Authorization: Token ...
    return:
        name
        email
        restaurant_name
        status
    """
    name = request.user.name
    email = request.user.email
    restaurant = request.user.server.restaurant
    restaurant_name = "none"
    if restaurant is not None:
        restaurant_name = restaurant.name
    return JsonResponse({
        "name": name,
        "email": email,
        "restaurant_name": restaurant_name,
        "status": "success"
    })
