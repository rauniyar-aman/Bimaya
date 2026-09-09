from django.contrib import admin

from .models import Notification, PushSubscription


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "type", "title", "read_at", "created_at")
    list_filter = ("type",)
    search_fields = ("recipient__email", "title", "body")
    autocomplete_fields = ("recipient",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("recipient", "endpoint", "user_agent", "created_at")
    search_fields = ("recipient__email", "endpoint", "user_agent")
    autocomplete_fields = ("recipient",)
    readonly_fields = ("created_at", "updated_at")
