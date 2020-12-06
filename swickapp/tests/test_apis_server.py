import json

from django.urls import reverse
from rest_framework.test import APITestCase
from swickapp.models import Order, OrderItem, Request, Server, User
from unittest.mock import Mock, patch


class APIServerTest(APITestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        self.user = User.objects.get(email="seanlu99@gmail.com")
        self.client.force_authenticate(self.user)

    def test_login(self):
        # POST success: use existing server, server has restaurant, user has name
        resp = self.client.post(reverse('server_login'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['restaurant_id'], 26)
        self.assertEqual(content['name_set'], True)
        self.assertEqual(content['id'], 11)
        # POST success: create new server, server has no restaurant, user has no name
        user = User.objects.get(email="simon@gmail.com")
        self.client.force_authenticate(user)
        resp = self.client.post(reverse('server_login'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['restaurant_id'], None)
        self.assertEqual(content['name_set'], False)
        # POST success: create new server, server has accepted server request
        user = User.objects.get(email="chris@gmail.com")
        self.client.force_authenticate(user)
        resp = self.client.post(reverse('server_login'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['restaurant_id'], 26)
        # POST error: invalid token
        self.client.force_authenticate(user=None)
        resp = self.client.post(reverse('server_login'))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'invalid_token')

    @patch('pusher.Pusher')
    def test_pusher_auth(self, pusher_mock):
        pusher_mock.return_value.authenticate.return_value = {
            "pusher_payload": "mock_pusher_payload"}
        # POST success: server with restaurant
        resp = self.client.post(reverse('server_pusher_auth'), data={
            "channel_name": "private-restaurant-26",
            "socket_id": "1"
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content["pusher_payload"], "mock_pusher_payload")
        # POST error: server does have access to restaurant
        resp = self.client.post(reverse('server_pusher_auth'), data={
            "channel_name": "private-restaurant-29",
            "socket_id": "1"
        })
        self.assertEqual(resp.status_code, 403)
        # POST success: server without restaurant
        self.user.server.restaurant = None
        resp = self.client.post(reverse('server_pusher_auth'), data={
            "channel_name": "private-server-11",
            "socket_id": "1"
        })
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content["pusher_payload"], "mock_pusher_payload")
        # POST error: channel does not start with valid channel type
        resp = self.client.post(reverse('server_pusher_auth'), data={
            "channel_name": "private-customer-11",
            "socket_id": "1"
        })
        self.assertEqual(resp.status_code, 403)
        # POST error: channel is not of correct format
        resp = self.client.post(reverse('server_pusher_auth'), data={
            "channel_name": "private-restaurant_account-11-35",
            "socket_id": "1"
        })
        self.assertEqual(resp.status_code, 403)
        # POST error: server channel is not requested by user
        resp = self.client.post(reverse('server_pusher_auth'), data={
            "channel_name": "private-server-22",
            "socket_id": "1"
        })
        self.assertEqual(resp.status_code, 403)
        # POST error: channel number is not an integer
        resp = self.client.post(reverse('server_pusher_auth'), data={
            "channel_name": "private-server-22.2",
            "socket_id": "1"
        })
        self.assertEqual(resp.status_code, 403)

    def test_get_orders(self):
        # GET success
        resp = self.client.get(reverse('server_get_orders'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        orders = content['orders']
        self.assertEqual(len(orders), 3)
        self.assertEqual(orders[0]['id'], 38)
        self.assertEqual(orders[1]['id'], 36)
        self.assertEqual(orders[2]['id'], 35)

    def test_get_order(self):
        # GET success
        resp = self.client.get(reverse('server_get_order', args=(38,)))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        order = content['order']
        self.assertEqual(order['customer_name'], 'Sean Two')
        # GET error: order does not exist
        resp = self.client.get(reverse('server_get_order', args=(34,)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'order_does_not_exist')
        # GET error: order does not belong to restaurant
        resp = self.client.get(reverse('server_get_order', args=(37,)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'order_does_not_exist')

    def test_get_order_details(self):
        # GET success
        resp = self.client.get(reverse('server_get_order_details', args=(38,)))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        details = content['order_details']
        self.assertEqual(details['customer_name'], 'Sean Two')
        self.assertEqual(details['total'], '36.54')
        # GET error: order does not exist
        resp = self.client.get(reverse('server_get_order_details', args=(34,)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'order_does_not_exist')
        # GET error: order does not belong to restaurant
        resp = self.client.get(reverse('server_get_order_details', args=(37,)))
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'order_does_not_exist')

    def test_get_order_items_to_cook(self):
        # GET success
        resp = self.client.get(reverse('server_get_order_items_to_cook'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        items = content['order_items']
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['id'], 49)
        self.assertEqual(items[1]['id'], 54)

    def test_get_order_items_to_send(self):
        # GET success
        resp = self.client.get(reverse('server_get_order_items_to_send'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(len(content), 4)
        self.assertEqual(content[0]['id'], 50)
        self.assertEqual(content[0]['type'], 'OrderItem')
        self.assertEqual(content[1]['id'], 52)
        self.assertEqual(content[1]['type'], 'OrderItem')
        self.assertEqual(content[2]['id'], 18)
        self.assertEqual(content[2]['type'], 'Request')
        self.assertEqual(content[3]['id'], 20)
        self.assertEqual(content[3]['type'], 'Request')

    def test_server_update_order_item_status(self):
        # POST success
        resp = self.client.post(
            reverse('server_update_order_item_status'),
            data={'order_item_id': 49, 'status': OrderItem.SENDING}
        )
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        OrderItem.objects.get(id=49, status=OrderItem.SENDING)
        # POST success: new status is complete but order not complete
        resp = self.client.post(
            reverse('server_update_order_item_status'),
            data={'order_item_id': 49, 'status': OrderItem.COMPLETE}
        )
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        Order.objects.get(id=35, status=Order.ACTIVE)
        # POST success: new status is complete and order is complete
        resp = self.client.post(
            reverse('server_update_order_item_status'),
            data={'order_item_id': 50, 'status': OrderItem.COMPLETE}
        )
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        Order.objects.get(id=35, status=Order.COMPLETE)
        # POST success: new status is cooking/sending but order was complete
        resp = self.client.post(
            reverse('server_update_order_item_status'),
            data={'order_item_id': 50, 'status': OrderItem.SENDING}
        )
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        Order.objects.get(id=35, status=Order.ACTIVE)
        # POST success: new status is cooking/sending and order already active
        esp = self.client.post(
            reverse('server_update_order_item_status'),
            data={'order_item_id': 49, 'status': OrderItem.SENDING}
        )
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        Order.objects.get(id=35, status=Order.ACTIVE)
        # POST error: order item does not exist
        resp = self.client.post(
            reverse('server_update_order_item_status'),
            data={'order_item_id': 48, 'status': OrderItem.SENDING}
        )
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'order_item_does_not_exist')
        # POST error: order item does not belong to restaurant
        resp = self.client.post(
            reverse('server_update_order_item_status'),
            data={'order_item_id': 53, 'status': OrderItem.SENDING}
        )
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'order_item_does_not_exist')

    def test_delete_request(self):
        # POST success
        resp = self.client.post(
            reverse('server_delete_request'),
            data={'id': 18}
        )
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertRaises(Request.DoesNotExist, Request.objects.get, id=18)
        # POST error: request does not exist
        resp = self.client.post(
            reverse('server_delete_request'),
            data={'id': 17}
        )
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'request_does_not_exist')
        # POST error: request does not belong to restaurant
        resp = self.client.post(
            reverse('server_delete_request'),
            data={'id': 19}
        )
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'request_does_not_exist')

    def test_get_info(self):
        # GET success
        resp = self.client.get(reverse('server_get_info'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['name'], 'Sean Lu')
        self.assertEqual(content['email'], 'seanlu99@gmail.com')
        self.assertEqual(content['restaurant_name'], 'Ice Cream Shop')
        # GET success: no restaurant
        server = self.user.server
        server.restaurant = None
        server.save()
        resp = self.client.get(reverse('server_get_info'))
        self.assertEqual(resp.status_code, 200)
        content = json.loads(resp.content)
        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['restaurant_name'], 'none')
