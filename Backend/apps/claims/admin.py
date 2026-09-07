from django.contrib import admin
from django.utils.html import format_html

from .models import Claim, ClaimDocument, ClaimPayout


class ClaimDocumentInline(admin.TabularInline):
    model = ClaimDocument
    extra = 0
    fields = ("file_link", "caption", "created_at")
    readonly_fields = ("file_link", "caption", "created_at")

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="File")
    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">{}</a>', obj.file.url, obj.file.name
            )
        return "—"


class ClaimPayoutInline(admin.TabularInline):
    model = ClaimPayout
    extra = 0
    fields = ("gateway", "amount", "status", "gateway_reference", "paid_at", "created_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "purchase",
        "status",
        "claimed_amount",
        "approved_amount",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = (
        "customer__email",
        "purchase__policy__name",
        "purchase__policy_number",
    )
    autocomplete_fields = ("customer", "purchase")
    readonly_fields = ("decided_at", "settled_at", "created_at", "updated_at")
    inlines = [ClaimDocumentInline, ClaimPayoutInline]


@admin.register(ClaimPayout)
class ClaimPayoutAdmin(admin.ModelAdmin):
    list_display = ("id", "claim", "gateway", "amount", "status", "gateway_reference", "paid_at")
    list_filter = ("status", "gateway")
    search_fields = ("claim__customer__email", "gateway_reference")
    readonly_fields = (
        "claim",
        "gateway",
        "amount",
        "status",
        "gateway_reference",
        "paid_at",
        "created_at",
        "updated_at",
    )
