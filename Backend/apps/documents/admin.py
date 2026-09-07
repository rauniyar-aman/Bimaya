from django.contrib import admin
from django.utils.html import format_html

from .models import CustomerKyc


@admin.register(CustomerKyc)
class CustomerKycAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "full_name",
        "is_self",
        "document_type",
        "status",
        "created_at",
    )
    list_filter = ("status", "document_type", "is_self")
    search_fields = ("customer__email", "full_name", "document_number")
    autocomplete_fields = ("customer",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "document_front_preview",
        "document_back_preview",
    )

    @admin.display(description="Front image")
    def document_front_preview(self, obj):
        if obj.document_front:
            return format_html(
                '<img src="{}" style="max-height:240px;" />', obj.document_front.url
            )
        return "—"

    @admin.display(description="Back image")
    def document_back_preview(self, obj):
        if obj.document_back:
            return format_html(
                '<img src="{}" style="max-height:240px;" />', obj.document_back.url
            )
        return "—"

    @admin.action(description="Mark selected KYC as verified")
    def mark_verified(self, request, queryset):
        updated = queryset.update(status=CustomerKyc.Status.VERIFIED, review_note="")
        self.message_user(request, f"{updated} KYC record(s) verified.")

    @admin.action(description="Mark selected KYC as rejected")
    def mark_rejected(self, request, queryset):
        updated = queryset.update(status=CustomerKyc.Status.REJECTED)
        self.message_user(request, f"{updated} KYC record(s) rejected.")

    actions = ["mark_verified", "mark_rejected"]
