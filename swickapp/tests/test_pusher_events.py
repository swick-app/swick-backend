from unittest.mock import Mock, call, patch

import pusher
from django.test import TestCase
from swickapp.models import Order, OrderItem, Request, Server
from swickapp.pusher_events import (send_event_item_status_updated,
                                    send_event_order_placed,
                                    send_event_order_status_updated,
                                    send_event_request_deleted,
                                    send_event_request_made,
                                    send_event_restaurant_added,
                                    send_event_tip_added,
                                    get_customer_channel,
                                    get_restaurant_channel,
                                    get_server_channel)
from swickapp.serializers import (OrderItemSerializer,
                                  OrderItemToCookSerializer,
                                  OrderItemToSendSerializer, OrderSerializer,
                                  RequestSerializer)


@patch('swickapp.pusher_events.trigger_pusher_event')
class PusherEventsTest(TestCase):
    fixtures = ['testdata.json']

    def test_send_event_order_placed(self, pusher_mock):
        order = Order.objects.get(pk=35)
        order_serialzied = OrderSerializer(order).data
        order_items_serialized = OrderItemToCookSerializer(
            OrderItem.objects.filter(order=order), many=True).data
        send_event_order_placed(order)
        customer_call = call(
            'private-customer-11',
            'order-placed',
            {'order': order_serialzied}
        )
        restaurant_call = call(
            'private-restaurant-26',
            'order-placed',
            {'order': order_serialzied, 'order_items': order_items_serialized}
        )
        pusher_mock.assert_has_calls(
            [customer_call, restaurant_call], any_order=True)

    def test_send_event_order_status_updated(self, pusher_mock):
        order = Order.objects.get(pk=35)
        send_event_order_status_updated(order)
        pusher_mock.assert_called_with(
            ['private-customer-11', 'private-restaurant-26'],
            'order-status-updated',
            {'order_id': order.id, 'new_status': order.get_status_display()}
        )

    def test_send_event_item_status_updated(self, pusher_mock):
        cooking_item = OrderItem.objects.get(pk=49)
        sending_item = OrderItem.objects.get(pk=50)
        complete_item = OrderItem.objects.get(pk=51)
        # Test updated 'COOKING' status
        serialized = OrderItemToCookSerializer(cooking_item).data
        send_event_item_status_updated(cooking_item)
        pusher_mock.assert_called_with(
            ['private-customer-11', 'private-restaurant-26'],
            'item-status-updated',
            {'order_item': serialized, 'id': 49,
                'order_id': 35, 'status': 'COOKING'}
        )
        # Test updated 'SENDING' status
        serialized = OrderItemToSendSerializer(sending_item).data
        send_event_item_status_updated(sending_item)
        pusher_mock.assert_called_with(
            ['private-customer-11', 'private-restaurant-26'],
            'item-status-updated',
            {'order_item': serialized, 'id': 50,
                'order_id': 35, 'status': 'SENDING'}
        )
        # Test updated 'COMPLETE' status
        serialized = OrderItemSerializer(complete_item).data
        send_event_item_status_updated(complete_item)
        pusher_mock.assert_called_with(
            ['private-customer-11', 'private-restaurant-26'],
            'item-status-updated',
            {'order_item': serialized, 'id': 51,
                'order_id': 35, 'status': 'COMPLETE'}
        )

    def test_send_event_tip_added(self, pusher_mock):
        order = Order.objects.get(pk=35)
        send_event_tip_added(order)
        pusher_mock.assert_called_with(
            ['private-customer-11', 'private-restaurant-26'],
            'tip-added-order-35',
            {'updated_subtotal': "32.50", 'updated_tax': "2.10",
                'updated_tip': "4.88", 'updated_total': "39.48"}
        )

    def test_send_event_request_made(self, pusher_mock):
        request = Request.objects.get(pk=18)
        serialized = RequestSerializer(request).data
        send_event_request_made(request)
        pusher_mock.assert_called_with(
            ['private-customer-11', 'private-restaurant-26'],
            'request-made',
            {'request': serialized}
        )

    def test_send_event_request_deleted(self, pusher_mock):
        request = Request.objects.get(pk=18)
        send_event_request_deleted(request)
        pusher_mock.assert_called_with(
            'private-restaurant-26',
            'request-deleted',
            {'request_id': 18}
        )

    def test_send_event_restaurant_added(self, pusher_mock):
        # Test server without restaurant
        server = Server.objects.get(pk=14)
        send_event_restaurant_added(server)
        pusher_mock.assert_not_called()
        # Test server with restaurant
        server = Server.objects.get(pk=11)
        send_event_restaurant_added(server)
        pusher_mock.assert_called_with(
            'private-server-11',
            'restaurant-added',
            {'restaurant_id': server.restaurant.id}
        )

    def test_get_channel_methods(self, pusher_mock):
        customer_channel = get_customer_channel(22)
        restaurant_channel = get_restaurant_channel(221)
        server_channel = get_server_channel(9182)
        self.assertEqual(customer_channel, "private-customer-22")
        self.assertEqual(restaurant_channel, "private-restaurant-221")
        self.assertEqual(server_channel, "private-server-9182")
