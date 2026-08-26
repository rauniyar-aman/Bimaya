"""Account-specific API exceptions with stable machine-readable codes."""

from rest_framework.exceptions import APIException


class AccountNotVerified(APIException):
    """Credentials were correct, but the account has not confirmed its OTP."""

    status_code = 403
    default_detail = (
        "Your account is not verified yet. Enter the code we emailed you to "
        "finish signing up."
    )
    default_code = "account_unverified"
