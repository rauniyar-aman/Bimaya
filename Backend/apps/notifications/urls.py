"""Notification routes, mounted at ``/api/v1/`` by :mod:`bimaya.urls`."""

from django.urls import path

from .views import (
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
    NotificationUnreadCountView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/unread-count/",
        NotificationUnreadCountView.as_view(),
        name="notification-unread-count",
    ),
    path(
        "notifications/read-all/",
        NotificationReadAllView.as_view(),
        name="notification-read-all",
    ),
    path(
        "notifications/<int:pk>/read/",
        NotificationReadView.as_view(),
        name="notification-read",
    ),
]
