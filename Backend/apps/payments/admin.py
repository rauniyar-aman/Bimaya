from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("policy_purchase", "amount", "gateway", "status", "paid_at")
    list_filter = ("gateway", "status")
    search_fields = (
        "policy_purchase__customer__email",
        "policy_purchase__policy__name",
        "gateway_transaction_id",
    )
    autocomplete_fields = ("policy_purchase",)
    readonly_fields = ("gateway_transaction_id", "paid_at", "created_at", "updated_at")
