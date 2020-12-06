from decimal import ROUND_HALF_UP, Decimal

import stripe
from django.http import JsonResponse
from swick.settings import STRIPE_API_KEY

from .models import Restaurant

stripe.api_key = STRIPE_API_KEY


def create_stripe_customer(email):
    """
    Create customer in Stripe and return id
    """
    return stripe.Customer.create(email=email).id


def attempt_stripe_payment(restaurant_id, cust_stripe_id, cust_email, payment_method_id, amount, payment_intent_metadata):
    """
    STRIPE PAYMENT PROCESSING
    Note: Return value 'intent_status: String' can be refactored to boolean values
    at the cost of readability
    Note: Seems like stripe API allows payment_method to be either id or object
    """
    if amount < 50:
        return JsonResponse({"status": "invalid_charge_amount"})

    try:
        # Direct payments to stripe connected account
        stripe_acct_id = Restaurant.objects.get(
            id=restaurant_id).stripe_acct_id
        payment_method_clone = stripe.PaymentMethod.create(
            customer=cust_stripe_id,
            payment_method=payment_method_id,
            stripe_account=stripe_acct_id
        )
        payment_intent = stripe.PaymentIntent.create(amount=amount,
                                                     currency="usd",
                                                     payment_method=payment_method_clone.id,
                                                     receipt_email=cust_email,
                                                     use_stripe_sdk=True,
                                                     confirmation_method='manual',
                                                     confirm=True,
                                                     stripe_account=stripe_acct_id,
                                                     metadata=payment_intent_metadata)
    except stripe.error.CardError as e:
        error = e.user_message
        return JsonResponse({"intent_status": "card_error", "error": error, "status": "success"})
    except stripe.error.StripeError as e:
        return JsonResponse({"status": "stripe_api_error"})

    intent_status = payment_intent.status
    # Card requires further action
    if intent_status == 'requires_action' or intent_status == 'requires_source_action':
        # Card requires more action
        return JsonResponse({"intent_status": intent_status,
                             "payment_intent": payment_intent.id,
                             "client_secret": payment_intent.client_secret,
                             "status": "success"})

    # Card is invalid (this 'elif' branch should never occur due to previous card setup validation)
    elif intent_status == 'requires_payment_method':
        error = payment_intent.last_payment_error.message if payment_intent.get(
            'last_payment_error') else None
        return JsonResponse({"intent_status": intent_status,
                             "error": error,
                             "payment_intent": payment_intent.id,
                             "status": "success"})

    # Payment is successful
    elif intent_status == 'succeeded':
        return JsonResponse({"intent_status": intent_status,
                             "payment_intent": payment_intent.id,
                             "status": "success"})

    # should never reach this return
    return JsonResponse({"status": "unhandled_status"})


def retry_stripe_payment(customer, payment_intent_id):
    try:
        payment_intent = stripe.PaymentIntent.retrieve(
            payment_intent_id
        )
        if payment_intent.customer == customer.stripe_cust_id:
            payment_intent = stripe.PaymentIntent.confirm(payment_intent.id)
        else:
            return JsonResponse({"status": "invalid_stripe_id"})
    except stripe.error.CardError as e:
        return JsonResponse({"intent_status": "card_error", "order_id": payment_intent.metadata["order_id"], "error": e.user_message, "status": "success"})
    except stripe.error.StripeError:
        return JsonResponse({"status": "stripe_api_error"})
    intent_status = payment_intent.status
    # Card is invalid (this 'elif' branch should never occur due to previous card setup validation)
    if intent_status == 'requires_payment_method' or intent_status == 'requires_source':
        error = payment_intent.last_payment_error.message if payment_intent.get(
            'last_payment_error') else None
        return JsonResponse({"intent_status": intent_status, "order_id": payment_intent.metadata["order_id"], "error": error, "status": "success"})
    # Payment is successful
    elif intent_status == 'succeeded':
        return JsonResponse({"intent_status": "succeeded", "order_id": payment_intent.metadata["order_id"], "status": "success"})

    # should never reach this return
    return JsonResponse({"status": "unhandled_status"})


def get_stripe_fee(payment_intent_id):
    try:
        # Try determing stripe fee for order
        charge_data = stripe.PaymentIntent.retrieve(
            payment_intent_id).charges.data
        if not charge_data:
            # If should never reach since all successful payments must have a charge attached
            raise AssertionError(
                "Unable to find charge attached to payment_intent")
        expanded_charge = stripe.Charge.retrieve(
            charge_data[0].id, expand=['balance_transaction'])
        for fee in expanded_charge.balance_transaction.fee_details:
            if fee.type == 'stripe_fee':
                return Decimal((Decimal(fee.amount) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    except stripe.error.StripeError as e:
        # Even if there is an error, the payment still has gone through and order should be completed
        pass
    except AssertionError as e:
        # Should never occur yet still should check and pass
        # TODO: Perhaps create a log for fatal-esque errors
        pass
