"""Tests for the notification endpoints, the dispatch service, the SMS adapter,
and a couple of representative transition hook points."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Notification
from ..services import notify

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)


def make_user(email="user@bimaya.test", phone="9800000000"):
    return User.objects.create_user(
        email=email,
        password="Himalaya#2026",
        role=User.Role.CUSTOMER,
        is_verified=True,
        phone=phone,
    )


@no_throttle
class NotificationEndpointTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user(email="other@bimaya.test")
        Notification.objects.create(
            recipient=self.user, type=Notification.Type.WELCOME, title="Hi"
        )
        Notification.objects.create(
            recipient=self.user, type=Notification.Type.POLICY_ISSUED, title="Active"
        )
        Notification.objects.create(
            recipient=self.other, type=Notification.Type.WELCOME, title="Not yours"
        )

    def test_list_is_scoped_to_recipient(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        titles = {row["title"] for row in response.data["results"]}
        self.assertNotIn("Not yours", titles)

    def test_unread_filter(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("notification-list"), {"unread": "true"})
        self.assertEqual(response.data["count"], 2)

    def test_unread_count(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("notification-unread-count"))
        self.assertEqual(response.data["count"], 2)

    def test_mark_one_read_is_idempotent(self):
        note = self.user.notifications.first()
        self.client.force_authenticate(self.user)
        url = reverse("notification-read", args=[note.id])

        first = self.client.post(url)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertTrue(first.data["is_read"])
        read_at = first.data["read_at"]

        second = self.client.post(url)
        self.assertEqual(second.data["read_at"], read_at)

    def test_cannot_mark_another_users_notification(self):
        note = self.other.notifications.first()
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("notification-read", args=[note.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_all_read(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("notification-read-all"))
        self.assertEqual(response.data["updated"], 2)
        self.assertEqual(self.user.notifications.unread().count(), 0)

    def test_anonymous_is_rejected(self):
        response = self.client.get(reverse("notification-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class NotificationServiceTests(APITestCase):
    def test_notify_creates_row_and_sends_email(self):
        user = make_user()
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
        ):
            notify(user, Notification.Type.WELCOME, "Welcome", "Body text")
        self.assertEqual(user.notifications.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [user.email])

    @override_settings(NOTIFICATIONS_SMS_ENABLED=False)
    def test_sms_is_noop_when_disabled(self):
        user = make_user()
        with mock.patch("apps.notifications.sms._deliver") as deliver:
            notify(user, Notification.Type.WELCOME, "Welcome", "Body")
        deliver.assert_not_called()

    @override_settings(NOTIFICATIONS_SMS_ENABLED=True)
    def test_sms_dispatches_stub_when_enabled(self):
        user = make_user()
        with mock.patch("apps.notifications.sms._deliver", return_value=True) as deliver:
            notify(user, Notification.Type.WELCOME, "Welcome", "Body")
        deliver.assert_called_once()
