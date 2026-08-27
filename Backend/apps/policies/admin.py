from django.contrib import admin

from .models import InsuranceCategory, Policy


@admin.register(InsuranceCategory)
class InsuranceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "provider",
        "category",
        "premium",
        "premium_frequency",
        "status",
        "is_featured",
    )
    list_filter = ("status", "category", "is_featured", "premium_frequency")
    search_fields = ("name", "summary", "provider__company_name")
    autocomplete_fields = ("provider", "category")
    readonly_fields = ("slug", "created_at", "updated_at")

    @admin.action(description="Approve selected policies")
    def approve_policies(self, request, queryset):
        updated = queryset.update(status=Policy.Status.APPROVED)
        self.message_user(request, f"{updated} policy(ies) approved.")

    @admin.action(description="Mark selected policies as pending review")
    def mark_pending(self, request, queryset):
        updated = queryset.update(status=Policy.Status.PENDING)
        self.message_user(request, f"{updated} policy(ies) marked pending.")

    @admin.action(description="Deactivate selected policies")
    def deactivate_policies(self, request, queryset):
        updated = queryset.update(status=Policy.Status.INACTIVE)
        self.message_user(request, f"{updated} policy(ies) deactivated.")

    actions = ["approve_policies", "mark_pending", "deactivate_policies"]
