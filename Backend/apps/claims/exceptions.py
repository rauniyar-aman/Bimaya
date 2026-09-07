"""Claim-specific API exceptions with stable machine-readable codes."""

from rest_framework.exceptions import APIException


class ClaimNotDecidable(APIException):
    """The claim is not in a state the provider can act on right now."""

    status_code = 400
    default_detail = "This claim is not in a state that can be reviewed."
    default_code = "claim_not_decidable"


class ClaimNotResubmittable(APIException):
    """The claim is not awaiting more information from the customer."""

    status_code = 400
    default_detail = "Only a claim awaiting more information can be resubmitted."
    default_code = "claim_not_resubmittable"


class ClaimNotPayable(APIException):
    """The claim cannot have a payout initiated in its current state."""

    status_code = 400
    default_detail = "Only an approved claim without a payout can be paid out."
    default_code = "claim_not_payable"


class PayoutNotConfirmable(APIException):
    """There is no initiated payout on the claim to confirm."""

    status_code = 400
    default_detail = "This payout is not awaiting confirmation."
    default_code = "payout_not_confirmable"
