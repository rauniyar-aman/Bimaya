from django.contrib import admin

from .models import PolicyPurchase


@admin.register(PolicyPurchase)
class PolicyPurchaseAdmin(admin.ModelAdmin):
    list_display = ("customer", "policy", "status", "policy_number", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("customer__email", "policy__name", "policy_number", "nominee_name")
    autocomplete_fields = ("customer", "policy")
    readonly_fields = ("policy_number", "start_date", "end_date", "created_at", "updated_at")

    @admin.action(description="Mark selected purchases as cancelled")
    def mark_cancelled(self, request, queryset):
        updated = queryset.exclude(status=PolicyPurchase.Status.CANCELLED).update(
            status=PolicyPurchase.Status.CANCELLED
        )
        self.message_user(request, f"{updated} purchase(s) marked cancelled.")

    actions = ["mark_cancelled"]
