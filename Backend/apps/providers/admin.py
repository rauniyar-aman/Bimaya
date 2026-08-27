from django.contrib import admin

from .models import Provider


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("company_name", "user", "kyc_status", "is_approved", "created_at")
    list_filter = ("kyc_status", "is_approved")
    search_fields = ("company_name", "user__email", "registration_number")
    readonly_fields = ("slug", "created_at", "updated_at")
    autocomplete_fields = ("user",)

    @admin.action(description="Approve selected providers")
    def approve_providers(self, request, queryset):
        updated = queryset.update(is_approved=True, kyc_status=Provider.KycStatus.VERIFIED)
        self.message_user(request, f"{updated} provider(s) approved.")

    actions = ["approve_providers"]
