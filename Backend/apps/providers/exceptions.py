"""Provider-specific API exceptions with stable machine-readable codes."""

from rest_framework.exceptions import APIException


class ProviderProfileNotFound(APIException):
    """The signed-in provider has not created their company profile yet."""

    status_code = 404
    default_detail = "You have not set up a provider profile yet."
    default_code = "provider_profile_missing"


class ProviderKycNotDeletable(APIException):
    """A KYC document can only be removed by the provider while still pending.

    Once an administrator has verified or rejected it the record is part of the
    review trail and is no longer the provider's to delete.
    """

    status_code = 409
    default_detail = "Only a pending document can be removed."
    default_code = "provider_kyc_not_deletable"


class ProviderMemberNotDisableable(APIException):
    """The requested member cannot be disabled (e.g. disabling one's own account)."""

    status_code = 409
    default_detail = "This member cannot be disabled."
    default_code = "provider_member_not_disableable"
