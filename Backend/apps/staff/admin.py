"""Django-admin registration for staff RBAC.

The Django admin is the fallback console for managing role assignments until the
in-app staff-management UI lands. The audit log is registered read-only so the
trail cannot be edited or deleted from here either.
"""

from django.contrib import admin

from .models import AuditLogEntry, StaffRoleAssignment


@admin.register(StaffRoleAssignment)
class StaffRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "granted_by", "created_at")
    list_filter = ("role",)
    search_fields = ("user__email", "user__full_name")
    autocomplete_fields = ()
    raw_id_fields = ("user", "granted_by")


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "actor",
        "actor_role",
        "action",
        "entity_type",
        "entity_id",
    )
    list_filter = ("action", "module", "actor_role")
    search_fields = ("actor__email", "action", "entity_type", "entity_id", "reason")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
