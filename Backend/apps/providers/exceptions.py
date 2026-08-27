"""Provider-specific API exceptions with stable machine-readable codes."""

from rest_framework.exceptions import APIException


class ProviderProfileNotFound(APIException):
    """The signed-in provider has not created their company profile yet."""

    status_code = 404
    default_detail = "You have not set up a provider profile yet."
    default_code = "provider_profile_missing"
