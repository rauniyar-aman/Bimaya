"""Notification endpoints (``/api/v1/notifications/``).

Every view is scoped to the signed-in user's own notifications — a user can
only ever see or touch their own.
"""

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer

NOTIFICATION_TAG = ["notifications"]


class NotificationBase:
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.for_user(self.request.user)


@extend_schema(
    tags=NOTIFICATION_TAG,
    summary="List the signed-in user's notifications",
    parameters=[
        OpenApiParameter(
            "unread",
            bool,
            description="When true, return only unread notifications.",
        )
    ],
)
class NotificationListView(NotificationBase, ListAPIView):
    def get_queryset(self):
        qs = super().get_queryset()
        unread = self.request.query_params.get("unread")
        if unread and unread.lower() in ("1", "true", "yes"):
            qs = qs.unread()
        return qs


@extend_schema(
    tags=NOTIFICATION_TAG,
    summary="Count the signed-in user's unread notifications",
    responses={200: OpenApiResponse(description='{"count": <int>}')},
)
class NotificationUnreadCountView(NotificationBase, GenericAPIView):
    def get(self, request):
        count = self.get_queryset().unread().count()
        return Response({"count": count})


@extend_schema(
    tags=NOTIFICATION_TAG,
    summary="Mark one notification read",
    request=None,
    responses=NotificationSerializer,
)
class NotificationReadView(NotificationBase, GenericAPIView):
    def post(self, request, pk):
        notification = self.get_object()
        notification.mark_read()
        return Response(self.get_serializer(notification).data)


@extend_schema(
    tags=NOTIFICATION_TAG,
    summary="Mark all of the user's notifications read",
    request=None,
    responses={200: OpenApiResponse(description='{"updated": <int>}')},
)
class NotificationReadAllView(NotificationBase, GenericAPIView):
    def post(self, request):
        updated = self.get_queryset().unread().update(
            read_at=timezone.now(), updated_at=timezone.now()
        )
        return Response({"updated": updated}, status=status.HTTP_200_OK)
