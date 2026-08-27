"""Policy-specific API exceptions with stable machine-readable codes."""

from rest_framework.exceptions import APIException


class ProviderProfileRequired(APIException):
    """A provider tried to list a policy before creating their profile."""

    status_code = 400
    default_detail = "Create your provider profile before listing policies."
    default_code = "provider_profile_required"


class PolicyNotSubmittable(APIException):
    """The policy is not in a state that can be submitted for review."""

    status_code = 400
    default_detail = "Only draft or inactive policies can be submitted for review."
    default_code = "policy_not_submittable"
