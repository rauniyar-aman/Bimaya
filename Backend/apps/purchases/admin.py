from django.contrib import admin, messages

from .models import PolicyPurchase, ProviderPayout


@admin.register(PolicyPurchase)
class PolicyPurchaseAdmin(admin.ModelAdmin):
    list_display = ("customer", "policy", "status", "policy_number", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("customer__email", "policy__name", "policy_number", "nominee_name")
    autocomplete_fields = ("customer", "policy")
    readonly_fields = ("policy_number", "start_date", "end_date", "created_at", "updated_at")

    @admin.action(description="Verify KYC + payment and forward to provider")
    def verify_and_forward(self, request, queryset):
        """Move eligible purchases to FORWARDED.

        Only purchases that are ``PAID`` **and** whose linked KYC is verified
        qualify; anything else is reported back so the admin knows why.
        """
        forwarded = 0
        skipped = 0
        for purchase in queryset.select_related("kyc"):
            if purchase.status != PolicyPurchase.Status.PAID:
                skipped += 1
                continue
            if purchase.kyc is None or not purchase.kyc.is_verified:
                skipped += 1
                continue
            purchase.forward_to_provider()
            forwarded += 1

        if forwarded:
            self.message_user(request, f"{forwarded} purchase(s) forwarded to provider.")
        if skipped:
            self.message_user(
                request,
                f"{skipped} purchase(s) skipped — must be paid with verified KYC.",
                level=messages.WARNING,
            )

    @admin.action(description="Mark selected purchases as cancelled")
    def mark_cancelled(self, request, queryset):
        updated = queryset.exclude(status=PolicyPurchase.Status.CANCELLED).update(
            status=PolicyPurchase.Status.CANCELLED
        )
        self.message_user(request, f"{updated} purchase(s) marked cancelled.")

    actions = ["verify_and_forward", "mark_cancelled"]


@admin.register(ProviderPayout)
class ProviderPayoutAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "purchase",
        "gross_amount",
        "commission_rate",
        "commission_amount",
        "net_amount",
        "status",
        "paid_at",
    )
    list_filter = ("status", "provider")
    search_fields = (
        "provider__company_name",
        "purchase__policy__name",
        "purchase__policy_number",
    )
    readonly_fields = (
        "purchase",
        "provider",
        "gross_amount",
        "commission_rate",
        "commission_amount",
        "net_amount",
        "paid_at",
        "created_at",
        "updated_at",
    )

    @admin.action(description="Mark selected payouts as paid")
    def mark_paid(self, request, queryset):
        paid = 0
        for payout in queryset.exclude(status=ProviderPayout.Status.PAID):
            payout.mark_paid()
            paid += 1
        self.message_user(request, f"{paid} payout(s) marked paid.")

    actions = ["mark_paid"]
