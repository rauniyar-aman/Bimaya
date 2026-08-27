"""eSewa ePay v2 integration (sandbox endpoints by default).

Docs: https://developer.esewa.com.np/pages/Epay#epay-v2

The merchant (us) signs ``total_amount,transaction_uuid,product_code`` with
the shared secret; eSewa echoes the same fields back on the callback so we can
verify the signature there too. ``transaction_uuid`` doubles as our own
``Payment`` reference (``BIM-<payment id>``) so the callback can be matched
back to a row without needing extra state.
"""

import base64
import hashlib
import hmac

from django.conf import settings

PAYMENT_URL = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
STATUS_URL = "https://rc.esewa.com.np/api/epay/transaction/status/"

SIGNED_FIELD_NAMES = ["total_amount", "transaction_uuid", "product_code"]


def _reference(payment):
    return f"BIM-{payment.id}"


def resolve_payment_id(payload):
    """Recover our ``Payment`` id from a callback's ``transaction_uuid``."""
    reference = str(payload.get("transaction_uuid", ""))
    try:
        return int(reference.removeprefix("BIM-"))
    except ValueError:
        return None


def _sign(total_amount, transaction_uuid, product_code):
    message = (
        f"total_amount={total_amount},"
        f"transaction_uuid={transaction_uuid},"
        f"product_code={product_code}"
    )
    digest = hmac.new(
        settings.ESEWA_SECRET_KEY.encode(), message.encode(), hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode()


def initiate(payment):
    """Build the form fields the frontend posts to eSewa to start payment."""
    amount = str(payment.amount)
    transaction_uuid = _reference(payment)
    product_code = settings.ESEWA_MERCHANT_CODE

    return {
        "payment_url": PAYMENT_URL,
        "fields": {
            "amount": amount,
            "tax_amount": "0",
            "total_amount": amount,
            "transaction_uuid": transaction_uuid,
            "product_code": product_code,
            "product_service_charge": "0",
            "product_delivery_charge": "0",
            "success_url": f"{settings.FRONTEND_URL}/checkout/callback?gateway=esewa",
            "failure_url": (
                f"{settings.FRONTEND_URL}/checkout/callback?gateway=esewa&status=failed"
            ),
            "signed_field_names": ",".join(SIGNED_FIELD_NAMES),
            "signature": _sign(amount, transaction_uuid, product_code),
        },
    }


def verify(payload):
    """Check a callback payload's signature and completion status."""
    try:
        total_amount = payload["total_amount"]
        transaction_uuid = payload["transaction_uuid"]
        product_code = payload["product_code"]
        signature = payload["signature"]
    except KeyError:
        return False

    expected = _sign(total_amount, transaction_uuid, product_code)
    if not hmac.compare_digest(expected, signature):
        return False
    return payload.get("status", "COMPLETE") == "COMPLETE"
