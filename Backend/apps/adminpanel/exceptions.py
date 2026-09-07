"""Admin-panel API exceptions with stable machine-readable codes."""

from rest_framework.exceptions import APIException


class PurchaseNotForwardable(APIException):
    """The purchase cannot be verified and forwarded to the provider.

    Raised when a purchase is not ``PAID`` or its covering KYC is not verified,
    so the frontend can surface a precise reason rather than a generic 400.
    """

    status_code = 400
    default_detail = "Only a paid purchase with verified KYC can be forwarded."
    default_code = "purchase_not_forwardable"
