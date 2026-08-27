"""Khalti ePayment integration (sandbox endpoints by default).

Docs: https://docs.khalti.com/khalti-epayment/

``purchase_order_id`` doubles as our own ``Payment`` reference
(``BIM-<payment id>``), same convention as the eSewa module, so the callback
can be matched back to a row. Confirmation is a server-to-server lookup by
``pidx`` rather than trusting the redirect alone.
"""

import requests
from django.conf import settings

INITIATE_URL = "https://dev.khalti.com/api/v2/epayment/initiate/"
LOOKUP_URL = "https://dev.khalti.com/api/v2/epayment/lookup/"


def _reference(payment):
    return f"BIM-{payment.id}"


def resolve_payment_id(payload):
    """Recover our ``Payment`` id from a callback's ``purchase_order_id``."""
    reference = str(payload.get("purchase_order_id", ""))
    try:
        return int(reference.removeprefix("BIM-"))
    except ValueError:
        return None


def _headers():
    return {"Authorization": f"Key {settings.KHALTI_SECRET_KEY}"}


def initiate(payment):
    """Ask Khalti to open a payment session and return the redirect URL."""
    purchase = payment.policy_purchase
    response = requests.post(
        INITIATE_URL,
        headers=_headers(),
        json={
            "return_url": f"{settings.FRONTEND_URL}/checkout/callback?gateway=khalti",
            "website_url": settings.FRONTEND_URL,
            "amount": int(payment.amount * 100),  # paisa
            "purchase_order_id": _reference(payment),
            "purchase_order_name": purchase.policy.name,
            "customer_info": {
                "name": purchase.nominee_name,
                "email": purchase.customer.email,
            },
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return {"payment_url": data["payment_url"], "pidx": data["pidx"]}


def verify(payload):
    """Confirm a callback's ``pidx`` actually settled, via Khalti's lookup API."""
    pidx = payload.get("pidx")
    if not pidx:
        return False

    response = requests.post(LOOKUP_URL, headers=_headers(), json={"pidx": pidx}, timeout=15)
    response.raise_for_status()
    return response.json().get("status") == "Completed"
