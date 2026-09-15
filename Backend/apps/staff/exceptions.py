"""Staff-management API exceptions with stable machine-readable codes."""

from rest_framework.exceptions import APIException


class StaffNotDisableable(APIException):
    """The staff account cannot be disabled.

    Raised when an administrator tries to disable their own account, or to
    disable the last active System Owner — either of which would risk locking
    the platform out of staff administration. The stable code lets the frontend
    surface the precise reason rather than a generic error.
    """

    status_code = 409
    default_detail = "This staff account cannot be disabled."
    default_code = "staff_not_disableable"
