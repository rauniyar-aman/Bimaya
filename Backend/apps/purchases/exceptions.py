"""Purchase-specific API exceptions with stable machine-readable codes."""

from rest_framework.exceptions import APIException


class PurchaseNotCancellable(APIException):
    """The purchase is not in a state that can be cancelled."""

    status_code = 400
    default_detail = "Only purchases pending payment can be cancelled."
    default_code = "purchase_not_cancellable"


class PurchaseNotIssuable(APIException):
    """The purchase is not in a state that can be issued by the provider."""

    status_code = 400
    default_detail = "Only purchases forwarded for issuance can be issued."
    default_code = "purchase_not_issuable"
