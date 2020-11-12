from enum import Enum

import pusher
from django.conf import settings
from swick.settings import (PUSHER_APP_ID, PUSHER_CLUSTER, PUSHER_KEY,
                            PUSHER_SECRET)

from .models import OrderItem, Server
from .serializers import (OrderItemSerializer, OrderItemToCookSerializer,
                          OrderItemToSendSerializer, OrderSerializer,
                          RequestSerializer)

"""
SUBSCRIPTION LAYOUT
==  Supported Channels =========================================================
    private-customer-<customer_id>
    private-server-<server_id>
    private-restaurant-<restaurant_id>

==  Channel Events =============================================================
Customer channels can receive following events:
    'order-status-updated'
    'item-status-updated'

Server channels can receive following events:
    'restaurant-added'

Restaurant channels can receive following events:
    'order-placed'
    'order-status-updated'
    'request-made'
    'request-deleted'
    'tip-added'
"""


def send_event_order_placed(order):
    order_serialized = OrderSerializer(order).data
    order_items_serialized = OrderItemToCookSerializer(
        OrderItem.objects.filter(order=order),
        many=True
    ).data

    trigger_pusher_event(get_customer_channel(order.customer.id),
                         "order-placed",
                         {"order": order_serialized})

    trigger_pusher_event(get_restaurant_channel(order.restaurant.id),
                         "order-placed",
                         {"order": order_serialized, "order_items": order_items_serialized})


def send_event_order_status_updated(order):
    trigger_pusher_event([get_customer_channel(order.customer.id), get_restaurant_channel(order.restaurant.id)],
                         "order-status-updated",
                         {"order_id": order.id, "new_status": order.get_status_display()})


def send_event_item_status_updated(item):
    if item.status == OrderItem.COOKING:
        serialized = OrderItemToCookSerializer(item).data
    elif item.status == OrderItem.SENDING:
        serialized = OrderItemToSendSerializer(item).data
    else:
        serialized = OrderItemSerializer(item).data

    trigger_pusher_event([get_customer_channel(item.order.customer.id), get_restaurant_channel(item.order.restaurant.id)],
                         "item-status-updated",
                         {"order_item": serialized, "id": item.id, "order_id": item.order.id, "status": item.status})


def send_event_tip_added(order):
    event = "tip-added-order-{id}".format(id=order.id)
    trigger_pusher_event([get_customer_channel(order.customer.id), get_restaurant_channel(order.restaurant.id)],
                         event,
                         {"updated_subtotal": str(order.subtotal),
                          "updated_tax": str(order.tax),
                          "updated_tip": str(order.tip),
                          "updated_total": str(order.total)})


def send_event_request_made(request):
    serialized = RequestSerializer(request).data
    trigger_pusher_event([get_customer_channel(request.customer.id), get_restaurant_channel(request.request_option.restaurant.id)],
                         "request-made",
                         {"request": serialized})


def send_event_request_deleted(request):
    trigger_pusher_event(get_restaurant_channel(request.request_option.restaurant.id),
                         "request-deleted",
                         {"request_id": request.id})


def send_event_restaurant_added(server):
    if server.restaurant is not None:
        trigger_pusher_event(get_server_channel(
            server.id), 'restaurant-added', {"restaurant_id": server.restaurant.id})

# HELPER FUNCTIONS


def trigger_pusher_event(channels, event, data):
    pusher_client = pusher.Pusher(
        app_id=PUSHER_APP_ID,
        key=PUSHER_KEY,
        secret=PUSHER_SECRET,
        cluster=PUSHER_CLUSTER
    )
    pusher_client.trigger(channels, event, data)


def get_customer_channel(customer_id):
    return "private-customer-{id}".format(id=customer_id)


def get_restaurant_channel(restaurant_id):
    return "private-restaurant-{id}".format(id=restaurant_id)


def get_server_channel(server_id):
    return "private-server-{id}".format(id=server_id)
