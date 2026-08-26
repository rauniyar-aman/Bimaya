"""End-to-end tests for the authentication flows.

Throttling is switched off for the functional tests (it would otherwise trip on
the repeated calls) and exercised separately in :class:`ThrottlingTests`.
"""

from datetime import timedelta
from unittest import mock

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import OTP

User = get_user_model()

# DRF binds ``throttle_classes`` onto the view classes at import time, so
# ``override_settings(REST_FRAMEWORK=...)`` cannot switch rate limiting off.
# Neutralising the rate check itself keeps the production settings authoritative
# while letting the functional tests make as many calls as they need.
no_throttling = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)

PASSWORD = "Sagarmatha#2026"


def register_payload(**overrides):
    payload = {
        "email": "sita@example.com",
        "full_name": "Sita Sharma",
        "phone": "9800000000",
        "role": User.Role.CUSTOMER,
        "password": PASSWORD,
        "confirm_password": PASSWORD,
    }
    payload.update(overrides)
    return payload


@no_throttling
class RegistrationTests(APITestCase):
    url = reverse("register")

    def test_registration_creates_unverified_user_and_issues_code(self):
        response = self.client.post(self.url, register_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="sita@example.com")
        self.assertFalse(user.is_verified)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertTrue(user.check_password(PASSWORD))

        otp = OTP.objects.get(user=user, purpose=OTP.Purpose.REGISTER)
        self.assertFalse(otp.is_used)
        self.assertEqual(len(otp.code), django_settings.OTP_LENGTH)
        # Dev convenience: the code comes back in the response while DEBUG is on.
        self.assertEqual(response.data["dev_otp"], otp.code)

    def test_email_is_normalised_and_must_be_unique(self):
        self.client.post(self.url, register_payload(), format="json")
        response = self.client.post(
            self.url, register_payload(email="SITA@example.com"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data["errors"])
        self.assertEqual(User.objects.count(), 1)

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            self.url, register_payload(confirm_password="somethingElse#1"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data["errors"])
        self.assertFalse(User.objects.exists())

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            self.url,
            register_payload(password="12345678", confirm_password="12345678"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.exists())

    def test_admin_role_cannot_be_self_assigned(self):
        response = self.client.post(
            self.url, register_payload(role=User.Role.ADMIN), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.data["errors"])

    def test_provider_role_is_allowed(self):
        response = self.client.post(
            self.url,
            register_payload(email="provider@example.com", role=User.Role.PROVIDER),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            User.objects.get(email="provider@example.com").role, User.Role.PROVIDER
        )


@no_throttling
class VerificationTests(APITestCase):
    def setUp(self):
        self.url = reverse("verify-otp")
        self.user = User.objects.create_user(email="ram@example.com", password=PASSWORD)
        self.otp = OTP.objects.create(
            user=self.user,
            code="123456",
            purpose=OTP.Purpose.REGISTER,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

    def test_correct_code_verifies_and_signs_in(self):
        response = self.client.post(
            self.url, {"email": self.user.email, "code": "123456"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.otp.refresh_from_db()
        self.assertTrue(self.user.is_verified)
        self.assertTrue(self.otp.is_used)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], self.user.email)

    def test_wrong_code_records_an_attempt(self):
        response = self.client.post(
            self.url, {"email": self.user.email, "code": "000000"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.otp.refresh_from_db()
        self.assertEqual(self.otp.attempts, 1)
        self.assertFalse(self.otp.is_used)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)

    def test_code_locks_after_too_many_attempts(self):
        for _ in range(django_settings.OTP_MAX_ATTEMPTS):
            self.client.post(
                self.url, {"email": self.user.email, "code": "000000"}, format="json"
            )

        # Even the correct code is refused once the code is locked out.
        response = self.client.post(
            self.url, {"email": self.user.email, "code": "123456"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Too many incorrect attempts", str(response.data["errors"]))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)

    def test_expired_code_is_refused(self):
        self.otp.expires_at = timezone.now() - timedelta(seconds=1)
        self.otp.save(update_fields=["expires_at"])

        response = self.client.post(
            self.url, {"email": self.user.email, "code": "123456"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", str(response.data["errors"]).lower())

    def test_unknown_email_is_refused(self):
        response = self.client.post(
            self.url, {"email": "nobody@example.com", "code": "123456"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_replaces_the_pending_code(self):
        response = self.client.post(
            reverse("resend-otp"), {"email": self.user.email}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.otp.refresh_from_db()
        self.assertTrue(self.otp.is_used, "the previous code should be invalidated")
        self.assertEqual(
            OTP.objects.filter(
                user=self.user, purpose=OTP.Purpose.REGISTER, is_used=False
            ).count(),
            1,
        )

    def test_resend_does_not_reveal_unknown_emails(self):
        response = self.client.post(
            reverse("resend-otp"), {"email": "nobody@example.com"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("dev_otp", response.data)


@no_throttling
class LoginTests(APITestCase):
    def setUp(self):
        self.url = reverse("login")
        self.user = User.objects.create_user(
            email="ram@example.com", password=PASSWORD, is_verified=True
        )

    def test_verified_user_receives_a_token_pair(self):
        response = self.client.post(
            self.url, {"email": self.user.email, "password": PASSWORD}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], self.user.email)

    def test_access_token_carries_role_claims(self):
        response = self.client.post(
            self.url, {"email": self.user.email, "password": PASSWORD}, format="json"
        )

        token = AccessToken(response.data["access"])
        self.assertEqual(token["role"], User.Role.CUSTOMER)
        self.assertEqual(token["email"], self.user.email)
        self.assertTrue(token["is_verified"])

    def test_unverified_user_is_told_to_verify(self):
        self.user.is_verified = False
        self.user.save(update_fields=["is_verified"])

        response = self.client.post(
            self.url, {"email": self.user.email, "password": PASSWORD}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "account_unverified")

    def test_wrong_password_is_rejected(self):
        response = self.client.post(
            self.url, {"email": self.user.email, "password": "wrong-password"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_deactivated_account_cannot_sign_in(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            self.url, {"email": self.user.email, "password": PASSWORD}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@no_throttling
class SessionLifecycleTests(APITestCase):
    """Refresh rotation and sign-out."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="ram@example.com", password=PASSWORD, is_verified=True
        )
        tokens = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": PASSWORD},
            format="json",
        ).data
        self.access = tokens["access"]
        self.refresh = tokens["refresh"]

    def test_refresh_rotates_and_retires_the_old_token(self):
        first = self.client.post(
            reverse("token-refresh"), {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertIn("access", first.data)
        self.assertIn("refresh", first.data)

        replayed = self.client.post(
            reverse("token-refresh"), {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(replayed.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_the_refresh_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.post(
            reverse("logout"), {"refresh": self.refresh}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        self.client.credentials()
        replayed = self.client.post(
            reverse("token-refresh"), {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(replayed.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_requires_authentication(self):
        response = self.client.post(
            reverse("logout"), {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_garbage_refresh_token_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.post(
            reverse("logout"), {"refresh": "not-a-token"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@no_throttling
class ProfileTests(APITestCase):
    def setUp(self):
        self.url = reverse("me")
        self.user = User.objects.create_user(
            email="ram@example.com",
            password=PASSWORD,
            full_name="Ram Thapa",
            is_verified=True,
        )
        self.client.force_authenticate(self.user)

    def test_anonymous_access_is_refused(self):
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_returns_the_signed_in_user(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["role"], User.Role.CUSTOMER)
        self.assertNotIn("password", response.data)

    def test_profile_fields_can_be_updated(self):
        response = self.client.patch(
            self.url, {"full_name": "Ram B. Thapa", "phone": "9811111111"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Ram B. Thapa")
        self.assertEqual(self.user.phone, "9811111111")

    def test_email_and_role_are_not_editable(self):
        response = self.client.patch(
            self.url,
            {"email": "hacker@example.com", "role": User.Role.ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ram@example.com")
        self.assertEqual(self.user.role, User.Role.CUSTOMER)


@no_throttling
class ChangePasswordTests(APITestCase):
    def setUp(self):
        self.url = reverse("change-password")
        self.user = User.objects.create_user(
            email="ram@example.com", password=PASSWORD, is_verified=True
        )
        self.client.force_authenticate(self.user)

    def test_password_can_be_changed(self):
        new_password = "Machhapuchhre#2026"
        response = self.client.post(
            self.url,
            {
                "current_password": PASSWORD,
                "new_password": new_password,
                "confirm_password": new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_wrong_current_password_is_refused(self):
        response = self.client.post(
            self.url,
            {
                "current_password": "not-my-password",
                "new_password": "Machhapuchhre#2026",
                "confirm_password": "Machhapuchhre#2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("current_password", response.data["errors"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))


@no_throttling
class PasswordResetTests(APITestCase):
    def setUp(self):
        self.request_url = reverse("password-reset")
        self.confirm_url = reverse("password-reset-confirm")
        self.new_password = "Machhapuchhre#2026"
        self.user = User.objects.create_user(
            email="ram@example.com", password=PASSWORD, is_verified=True
        )

    def _request_code(self):
        response = self.client.post(
            self.request_url, {"email": self.user.email}, format="json"
        )
        return OTP.objects.filter(
            user=self.user, purpose=OTP.Purpose.RESET, is_used=False
        ).latest("created_at"), response

    def test_request_issues_a_reset_code(self):
        otp, response = self._request_code()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["dev_otp"], otp.code)

    def test_request_for_unknown_email_does_not_leak(self):
        response = self.client.post(
            self.request_url, {"email": "nobody@example.com"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("dev_otp", response.data)
        self.assertFalse(OTP.objects.exists())

    def test_confirm_sets_the_new_password(self):
        otp, _ = self._request_code()

        response = self.client.post(
            self.confirm_url,
            {
                "email": self.user.email,
                "code": otp.code,
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))

        signed_in = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": self.new_password},
            format="json",
        )
        self.assertEqual(signed_in.status_code, status.HTTP_200_OK)

    def test_confirm_retires_existing_sessions(self):
        old_refresh = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": PASSWORD},
            format="json",
        ).data["refresh"]
        otp, _ = self._request_code()

        self.client.post(
            self.confirm_url,
            {
                "email": self.user.email,
                "code": otp.code,
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
            format="json",
        )

        replayed = self.client.post(
            reverse("token-refresh"), {"refresh": old_refresh}, format="json"
        )
        self.assertEqual(replayed.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_confirm_with_a_wrong_code_is_refused(self):
        self._request_code()

        response = self.client.post(
            self.confirm_url,
            {
                "email": self.user.email,
                "code": "000000",
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_registration_code_cannot_be_used_to_reset(self):
        registration_otp = OTP.objects.create(
            user=self.user,
            code="123456",
            purpose=OTP.Purpose.REGISTER,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        response = self.client.post(
            self.confirm_url,
            {
                "email": self.user.email,
                "code": registration_otp.code,
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))


@no_throttling
class ErrorEnvelopeTests(APITestCase):
    """Every error response should carry ``detail`` and ``code``."""

    def test_validation_errors_include_field_details(self):
        response = self.client.post(reverse("login"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertIn("email", response.data["errors"])
        self.assertIn("password", response.data["errors"])

    def test_authentication_errors_are_wrapped(self):
        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["code"], "not_authenticated")


class ThrottlingTests(APITestCase):
    """Rate limiting is active (this class does not disable it)."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_repeated_login_attempts_are_throttled(self):
        url = reverse("login")
        payload = {"email": "ram@example.com", "password": "wrong-password"}

        statuses = [
            self.client.post(url, payload, format="json").status_code for _ in range(11)
        ]

        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, statuses)
        self.assertEqual(statuses[-1], status.HTTP_429_TOO_MANY_REQUESTS)
