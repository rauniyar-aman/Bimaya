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

from .models import Notification, PushSubscription
from .push import push_enabled
from .serializers import (
    NotificationSerializer,
    PushSubscribeSerializer,
    PushUnsubscribeSerializer,
)

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


# --- Web Push -----------------------------------------------------------------
# Browser push subscriptions are owned by the signed-in user; every view here is
# scoped to ``request.user`` so one account can never touch another's devices.


@extend_schema(
    tags=NOTIFICATION_TAG,
    summary="Whether Web Push is available, and the VAPID public key to use",
    responses={
        200: OpenApiResponse(description='{"enabled": <bool>, "public_key": <str>}')
    },
)
class PushVapidKeyView(GenericAPIView):
    """Tells the frontend if push is switched on and, if so, the public key to
    subscribe with. Off by default → ``enabled: false`` and no key, so the
    toggle can show a graceful "not available" state."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.conf import settings

        enabled = push_enabled()
        return Response(
            {
                "enabled": enabled,
                "public_key": settings.VAPID_PUBLIC_KEY if enabled else "",
            }
        )


@extend_schema(
    tags=NOTIFICATION_TAG,
    summary="Register (or refresh) a browser push subscription",
    request=PushSubscribeSerializer,
    responses={200: OpenApiResponse(description='{"subscribed": true}')},
)
class PushSubscribeView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PushSubscribeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Upsert by endpoint: a browser reuses one endpoint per device, and it
        # may re-subscribe (e.g. after a key rotation) — so keep a single row and
        # re-home it to the current user with fresh keys.
        PushSubscription.objects.update_or_create(
            endpoint=data["endpoint"],
            defaults={
                "recipient": request.user,
                "p256dh": data["keys"]["p256dh"],
                "auth": data["keys"]["auth"],
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300],
            },
        )
        return Response({"subscribed": True}, status=status.HTTP_200_OK)


@extend_schema(
    tags=NOTIFICATION_TAG,
    summary="Remove a browser push subscription",
    request=PushUnsubscribeSerializer,
    responses={200: OpenApiResponse(description='{"unsubscribed": true}')},
)
class PushUnsubscribeView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PushUnsubscribeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Scope the delete to the caller's own subscriptions.
        PushSubscription.objects.filter(
            recipient=request.user, endpoint=serializer.validated_data["endpoint"]
        ).delete()
        return Response({"unsubscribed": True}, status=status.HTTP_200_OK)
