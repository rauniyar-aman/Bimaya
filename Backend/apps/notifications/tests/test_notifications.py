"""Tests for the notification endpoints, the dispatch service, the SMS adapter,
and a couple of representative transition hook points."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Notification, PushSubscription
from ..push import send_push
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


# Web Push stays off unless the flag AND a VAPID keypair are set. These fake
# values just make push_enabled() true; pywebpush is always mocked so nothing
# tries to reach a real push service.
push_on = override_settings(
    NOTIFICATIONS_PUSH_ENABLED=True,
    VAPID_PUBLIC_KEY="test-public-key",
    VAPID_PRIVATE_KEY="test-private-key",
    VAPID_ADMIN_EMAIL="ops@bimaya.test",
)


class PushServiceTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.sub = PushSubscription.objects.create(
            recipient=self.user,
            endpoint="https://push.example.com/sub-1",
            p256dh="p256dh-key",
            auth="auth-key",
        )

    def test_send_push_is_noop_when_disabled(self):
        # Default settings: flag off, no keys → nothing is delivered.
        with mock.patch("pywebpush.webpush") as webpush:
            sent = send_push(self.user, "Hi", "there", "/dashboard")
        webpush.assert_not_called()
        self.assertEqual(sent, 0)

    @push_on
    def test_send_push_delivers_and_returns_count(self):
        with mock.patch("pywebpush.webpush") as webpush:
            sent = send_push(self.user, "Hi", "there", "/dashboard")
        self.assertEqual(sent, 1)
        webpush.assert_called_once()
        kwargs = webpush.call_args.kwargs
        self.assertEqual(kwargs["subscription_info"]["endpoint"], self.sub.endpoint)
        self.assertEqual(kwargs["vapid_private_key"], "test-private-key")
        self.assertEqual(kwargs["vapid_claims"], {"sub": "mailto:ops@bimaya.test"})
        # Only display copy + deep link travel to the browser — no other data.
        import json

        payload = json.loads(kwargs["data"])
        self.assertEqual(
            payload, {"title": "Hi", "body": "there", "url": "/dashboard"}
        )

    @push_on
    def test_dead_subscription_is_pruned(self):
        from pywebpush import WebPushException

        gone = WebPushException("gone", response=mock.Mock(status_code=410))
        with mock.patch("pywebpush.webpush", side_effect=gone):
            sent = send_push(self.user, "Hi", "there", "/dashboard")
        self.assertEqual(sent, 0)
        # 410 means the browser dropped it — the row is cleaned up.
        self.assertFalse(
            PushSubscription.objects.filter(pk=self.sub.pk).exists()
        )

    @push_on
    def test_provider_error_never_raises_and_keeps_subscription(self):
        with mock.patch("pywebpush.webpush", side_effect=RuntimeError("boom")):
            sent = send_push(self.user, "Hi", "there", "/dashboard")
        self.assertEqual(sent, 0)
        # A transient provider error must not lose a healthy subscription.
        self.assertTrue(PushSubscription.objects.filter(pk=self.sub.pk).exists())

    @push_on
    def test_notify_fans_out_to_push(self):
        with mock.patch("apps.notifications.services.send_push") as push_mock:
            notify(self.user, Notification.Type.WELCOME, "Welcome", "Body", "/x")
        push_mock.assert_called_once_with(self.user, "Welcome", "Body", "/x")


@no_throttle
class PushEndpointTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user(email="other@bimaya.test")
        self.payload = {
            "endpoint": "https://push.example.com/sub-abc",
            "keys": {"p256dh": "p256dh-key", "auth": "auth-key"},
        }

    def test_subscribe_requires_auth(self):
        response = self.client.post(
            reverse("notification-push-subscribe"), self.payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_subscribe_creates_subscription(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("notification-push-subscribe"),
            self.payload,
            format="json",
            HTTP_USER_AGENT="TestBrowser/1.0",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sub = PushSubscription.objects.get(endpoint=self.payload["endpoint"])
        self.assertEqual(sub.recipient, self.user)
        self.assertEqual(sub.p256dh, "p256dh-key")
        self.assertEqual(sub.auth, "auth-key")
        self.assertEqual(sub.user_agent, "TestBrowser/1.0")

    def test_subscribe_upserts_by_endpoint(self):
        self.client.force_authenticate(self.user)
        url = reverse("notification-push-subscribe")
        self.client.post(url, self.payload, format="json")
        updated = {
            "endpoint": self.payload["endpoint"],
            "keys": {"p256dh": "new-p256dh", "auth": "new-auth"},
        }
        self.client.post(url, updated, format="json")
        subs = PushSubscription.objects.filter(endpoint=self.payload["endpoint"])
        self.assertEqual(subs.count(), 1)
        self.assertEqual(subs.first().p256dh, "new-p256dh")

    def test_subscribe_validates_keys(self):
        self.client.force_authenticate(self.user)
        bad = {"endpoint": self.payload["endpoint"], "keys": {"p256dh": "only-one"}}
        response = self.client.post(
            reverse("notification-push-subscribe"), bad, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsubscribe_removes_own_subscription(self):
        PushSubscription.objects.create(
            recipient=self.user,
            endpoint=self.payload["endpoint"],
            p256dh="k",
            auth="a",
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("notification-push-unsubscribe"),
            {"endpoint": self.payload["endpoint"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            PushSubscription.objects.filter(endpoint=self.payload["endpoint"]).exists()
        )

    def test_unsubscribe_is_scoped_to_the_caller(self):
        # A subscription belonging to someone else must be untouchable.
        endpoint = "https://push.example.com/other-sub"
        PushSubscription.objects.create(
            recipient=self.other, endpoint=endpoint, p256dh="k", auth="a"
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("notification-push-unsubscribe"),
            {"endpoint": endpoint},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PushSubscription.objects.filter(endpoint=endpoint).exists())

    def test_vapid_key_disabled_by_default(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("notification-push-vapid-key"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["enabled"])
        self.assertEqual(response.data["public_key"], "")

    @push_on
    def test_vapid_key_exposes_public_key_when_enabled(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("notification-push-vapid-key"))
        self.assertTrue(response.data["enabled"])
        self.assertEqual(response.data["public_key"], "test-public-key")

    def test_vapid_key_requires_auth(self):
        response = self.client.get(reverse("notification-push-vapid-key"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
