import binascii
import os

import stripe
from swick.settings import STRIPE_API_KEY

stripe.api_key = STRIPE_API_KEY


def generate_token():
    return binascii.hexlify(os.urandom(20)).decode()
