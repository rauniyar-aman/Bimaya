"""A single, predictable error shape for the whole API.

Every error response looks like::

    {"detail": "human readable message", "code": "machine_readable_code"}

and, when individual fields failed validation, additionally::

    {"errors": {"email": ["This email is already registered."]}}

The frontend can therefore always show ``detail`` and branch on ``code``
without special-casing each endpoint.
"""

from rest_framework.views import exception_handler as drf_exception_handler


def _first_message(detail):
    """Pull the first human-readable string out of a nested DRF error detail."""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        for value in detail.values():
            message = _first_message(value)
            if message:
                return message
    if isinstance(detail, (list, tuple)):
        for item in detail:
            message = _first_message(item)
            if message:
                return message
    return None


def api_exception_handler(exc, context):
    """DRF ``EXCEPTION_HANDLER`` that normalises the response body."""
    response = drf_exception_handler(exc, context)
    if response is None:
        return None  # unhandled — let Django return a 500

    detail = getattr(exc, "detail", None)
    code = getattr(exc, "default_code", None) or "error"

    if isinstance(detail, dict):
        response.data = {
            "detail": _first_message(detail) or "Please correct the errors below.",
            "code": code,
            "errors": detail,
        }
    elif isinstance(detail, (list, tuple)):
        response.data = {
            "detail": _first_message(detail) or "The request could not be processed.",
            "code": code,
            "errors": {"detail": list(detail)},
        }
    else:
        response.data = {"detail": str(detail or "The request could not be processed."), "code": code}

    return response
