from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "type", "title", "read_at", "created_at")
    list_filter = ("type",)
    search_fields = ("recipient__email", "title", "body")
    autocomplete_fields = ("recipient",)
    readonly_fields = ("created_at", "updated_at")
