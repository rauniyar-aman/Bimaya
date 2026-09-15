"""Policy-specific API exceptions with stable machine-readable codes."""

from rest_framework.exceptions import APIException


class PolicyNotSubmittable(APIException):
    """The policy is not in a state that can be submitted for review."""

    status_code = 400
    default_detail = "Only draft or inactive policies can be submitted for review."
    default_code = "policy_not_submittable"


class PolicyNotDeactivatable(APIException):
    """The policy is not live, so it cannot be deactivated."""

    status_code = 400
    default_detail = "Only an approved (live) policy can be deactivated."
    default_code = "policy_not_deactivatable"
