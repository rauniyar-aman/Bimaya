"""KYC-specific API exceptions with stable machine-readable codes."""

from rest_framework.exceptions import APIException


class SelfKycNotFound(APIException):
    """The signed-in customer has not created their own KYC record yet."""

    status_code = 404
    default_detail = "You have not completed your KYC yet."
    default_code = "self_kyc_missing"
