"""Assistant-specific API exceptions with stable machine-readable codes.

These flow through ``apps.core.exceptions.api_exception_handler`` so the
frontend can branch on ``code`` (e.g. show a "coming soon" message when the
chat assistant is switched off versus a transient "try again" on an outage).
"""

from rest_framework.exceptions import APIException


class AssistantDisabled(APIException):
    """The chat assistant is switched off (no provider key configured yet)."""

    status_code = 400
    default_detail = "The chat assistant is not available yet."
    default_code = "assistant_disabled"


class AssistantUnavailable(APIException):
    """The chat provider could not be reached or returned an error."""

    status_code = 503
    default_detail = "The assistant is temporarily unavailable. Please try again."
    default_code = "assistant_unavailable"
