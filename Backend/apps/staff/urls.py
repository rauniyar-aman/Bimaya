"""Staff-management routes, mounted at ``/api/v1/admin/``.

Shares the ``admin/`` prefix with :mod:`apps.adminpanel.urls`; the sub-paths
(``staff/``, ``roles/``, ``audit/``) do not collide with the admin panel's.
Reverse names are prefixed ``staff-`` to stay distinct.
"""

from django.urls import path

from .views import (
    AuditLogListView,
    RolesCatalogView,
    StaffDetailView,
    StaffDisableView,
    StaffEnableView,
    StaffListCreateView,
    StaffRolesView,
)

urlpatterns = [
    # Staff accounts
    path("staff/", StaffListCreateView.as_view(), name="staff-list"),
    path("staff/<int:pk>/", StaffDetailView.as_view(), name="staff-detail"),
    path("staff/<int:pk>/roles/", StaffRolesView.as_view(), name="staff-roles"),
    path(
        "staff/<int:pk>/disable/",
        StaffDisableView.as_view(),
        name="staff-disable",
    ),
    path(
        "staff/<int:pk>/enable/",
        StaffEnableView.as_view(),
        name="staff-enable",
    ),
    # Roles & permissions (read-only matrix)
    path("roles/", RolesCatalogView.as_view(), name="staff-roles-catalog"),
    # Audit trail
    path("audit/", AuditLogListView.as_view(), name="staff-audit-log"),
]
