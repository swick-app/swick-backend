import json
import stripe

from decimal import Decimal
from rest_framework.test import APITestCase
from swickapp.models import Customer
from swickapp.apis_helper import (
    attempt_stripe_payment, retry_stripe_payment, get_stripe_fee)
from unittest.mock import Mock, patch


class APICustomerTest(APITestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        self.customer = Customer.objects.get(pk=11)

    @patch('stripe.PaymentMethod.create')
    @patch('stripe.PaymentIntent.create')
    def test_attempt_stripe_payment(self, payment_intent_create_mock, payment_method_create_mock):
        payment_intent_mock = Mock()
        payment_intent_mock.id = 22
        payment_intent_mock.client_secret = "client_secret_mock"
        payment_intent_mock.last_payment_error.message = "payment_error_message_mock"
        payment_intent_create_mock.return_value = payment_intent_mock
        payment_method_create_mock.return_value.id = "mock_payment_method_id"
        # Test amount less than 50
        resp = attempt_stripe_payment(0, "", "", "", 20, {})
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "invalid_charge_amount")
        # Test payment intent requires action
        payment_intent_mock.status = "requires_action"
        resp = attempt_stripe_payment(
            29, "cus_IQ793ueOulXMcC", "john@john.com", "card_1HpHZzBnGfJIkyujXRAmZB0A", 100, {})
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "requires_action")
        self.assertEqual(content["payment_intent"], 22)
        self.assertEqual(content["client_secret"], "client_secret_mock")
        # Test payment intent requires payment method
        payment_intent_mock.status = "requires_payment_method"
        payment_intent_mock.last_payment_error.message = "mock_last_payment_error_message"
        payment_intent_mock.get.return_value = True
        resp = attempt_stripe_payment(
            29, "cus_IQ793ueOulXMcC", "john@john.com", "card_1HpHZzBnGfJIkyujXRAmZB0A", 100, {})
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "requires_payment_method")
        self.assertEqual(content["payment_intent"], 22)
        self.assertEqual(content["error"], "mock_last_payment_error_message")
        # Test success
        payment_intent_mock.status = "succeeded"
        resp = attempt_stripe_payment(
            29, "cus_IQ793ueOulXMcC", "john@john.com", "card_1HpGwPBnGfJIkyujLkbU6qXr", 100, {"order_id": 22})
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "succeeded")
        self.assertEqual(content["payment_intent"], 22)
        # Test unhandled status
        payment_intent_mock.status = 'unhandled_status'
        resp = attempt_stripe_payment(
            29, "cus_IQ793ueOulXMcC", "john@john.com", "card_1HpGwPBnGfJIkyujLkbU6qXr", 100, {"order_id": 22})
        content = json.loads(resp.content)
        self.assertEqual(content["status"], 'unhandled_status')
        # Test card error
        payment_intent_create_mock.side_effect = stripe.error.CardError(
            "mock_card_error_message", None, None)
        resp = attempt_stripe_payment(
            29, "cus_IQ793ueOulXMcC", "john@john.com", "card_1HpHZzBnGfJIkyujXRAmZB0A", 100, {})
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "card_error")
        self.assertEqual(content["error"], "mock_card_error_message")
        # Test stripe error
        payment_intent_create_mock.side_effect = stripe.error.StripeError(
            "mocK_stripe_error_message")
        resp = attempt_stripe_payment(
            29, "cus_IQ793ueOulXMcC", "john@john.com", "card_1HpHZzBnGfJIkyujXRAmZB0A", 100, {})
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "stripe_api_error")

    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.confirm')
    def test_retry_stripe_payment(self, payment_intent_confirm_mock, payment_intent_retrieve_mock):
        # Define return response for mock retrieve
        intent_from_confirm = Mock()
        intent_from_confirm.metadata = {"order_id": 22}
        payment_intent_confirm_mock.return_value = intent_from_confirm

        def retrieve_response(payment_intent, stripe_account):
            intent_from_retrieve = Mock()
            if payment_intent == "non_customer_payment_intent":
                intent_from_retrieve.metadata = {"order_id": 22, "customer_id": "invalid_id"}
                intent_from_retrieve.customer = "invalid_stripe_id"
            elif payment_intent == "valid_cust_payment_intent":
                intent_from_retrieve.metadata = {"order_id": 22, "customer_id": str(self.customer.id)}
                intent_from_retrieve.id = 22
            return intent_from_retrieve
        payment_intent_retrieve_mock.side_effect = retrieve_response
        # Test customer does not own payment intent
        resp = retry_stripe_payment(
            self.customer, "non_customer_payment_intent", 26)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "invalid_stripe_id")
        # Test payment intent requires payment method
        intent_from_confirm.status = "requires_payment_method"
        intent_from_confirm.last_payment_error.message = "mock_last_payment_error_message"
        intent_from_confirm.get.return_value = True
        resp = retry_stripe_payment(
            self.customer, "valid_cust_payment_intent", 26)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "requires_payment_method")
        self.assertEqual(content["order_id"], 22)
        self.assertEqual(content["error"], "mock_last_payment_error_message")
        # Test successful attempt
        intent_from_confirm.status = 'succeeded'
        resp = retry_stripe_payment(
            self.customer, "valid_cust_payment_intent", 26)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "succeeded")
        self.assertEqual(content["order_id"], 22)
        # Test unhandled status
        intent_from_confirm.status = 'unhandled_status'
        resp = retry_stripe_payment(
            self.customer, "valid_cust_payment_intent", 26)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], 'unhandled_status')
        # Test card fails
        payment_intent_confirm_mock.side_effect = stripe.error.CardError(
            "mock_card_error_message", None, None)
        resp = retry_stripe_payment(
            self.customer, "valid_cust_payment_intent", 26)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "success")
        self.assertEqual(content["intent_status"], "card_error")
        self.assertEqual(content["error"], "mock_card_error_message")
        # Test raised StripeError
        payment_intent_retrieve_mock.side_effect = stripe.error.StripeError(
            "mock_stripe_error_message")
        resp = retry_stripe_payment(
            self.customer, "valid_cust_payment_intent", 26)
        content = json.loads(resp.content)
        self.assertEqual(content["status"], "stripe_api_error")

    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.Charge.retrieve')
    def test_get_stripe_fee(self, charge_retrieve_mock, payment_intent_retrieve_mock):
        # Define mock response for PaymentIntent.retrieve
        def response(payment_intent, stripe_account):
            response_mock = Mock()
            if payment_intent == "valid_payment_intent_id":
                mock_latest_charge = Mock()
                mock_latest_charge.id = 22
                response_mock.charges.data = [mock_latest_charge]
            else:
                response_mock.charges.data = None
            return response_mock
        payment_intent_retrieve_mock.side_effect = response
        # Test no stripe_fee exception
        other_mock_1 = other_mock_2 = Mock()
        fee_details_mock = [other_mock_1, other_mock_2]
        charge_retrieve_mock.return_value.balance_transaction.fee_details = fee_details_mock
        fee = get_stripe_fee("valid_payment_intent_id", 26)
        self.assertEqual(fee, None)
        # Test retrieving stripe fee of 2.50
        stripe_fee_mock = Mock()
        stripe_fee_mock.type = 'stripe_fee'
        stripe_fee_mock.amount = "250"
        fee_details_mock.append(stripe_fee_mock)
        charge_retrieve_mock.return_value.balance_transaction.fee_details = fee_details_mock
        fee = get_stripe_fee("valid_payment_intent_id", 26)
        self.assertEqual(fee, Decimal("2.50"))
        # Test failure with incomplete payment intent
        fee = get_stripe_fee("invalid_payment_intent_id", 26)
        self.assertEqual(fee, None)
        # Test stripe excpetion raised
        payment_intent_retrieve_mock.side_effect = stripe.error.StripeError(
            "Mock stripe error")
        fee = get_stripe_fee("some_payment_intent_id", 26)
        self.assertEqual(fee, None)
