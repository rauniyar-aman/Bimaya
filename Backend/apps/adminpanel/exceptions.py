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


class PolicyNotActionable(APIException):
    """The policy is not in a state that allows the requested transition."""

    status_code = 400
    default_detail = "This policy cannot change to that status from its current one."
    default_code = "policy_not_actionable"


class UserNotSuspendable(APIException):
    """The target user cannot be suspended (self, or another administrator)."""

    status_code = 400
    default_detail = "This account cannot be suspended."
    default_code = "user_not_suspendable"
