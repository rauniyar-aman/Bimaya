from django.contrib import admin

from .models import ProviderLead


@admin.register(ProviderLead)
class ProviderLeadAdmin(admin.ModelAdmin):
    list_display = ("company_name", "contact_name", "email", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("company_name", "contact_name", "email", "phone")
    readonly_fields = ("created_at", "updated_at")

    @admin.action(description="Mark selected leads as contacted")
    def mark_contacted(self, request, queryset):
        updated = queryset.update(status=ProviderLead.Status.CONTACTED)
        self.message_user(request, f"{updated} lead(s) marked contacted.")

    @admin.action(description="Mark selected leads as onboarded")
    def mark_onboarded(self, request, queryset):
        updated = queryset.update(status=ProviderLead.Status.ONBOARDED)
        self.message_user(request, f"{updated} lead(s) marked onboarded.")

    actions = ["mark_contacted", "mark_onboarded"]
