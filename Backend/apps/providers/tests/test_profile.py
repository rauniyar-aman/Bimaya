"""Tests for the provider profile endpoint (``/api/v1/provider/profile/``)."""

from unittest import mock

import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from apps.providers.models import Provider

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)

# Logo uploads land in a throwaway media root so tests never touch real storage.
_LOGO_MEDIA_ROOT = tempfile.mkdtemp(prefix="bimaya-logo-tests-")


def _png_upload(name="logo.png", color=(26, 84, 147)):
    """A small but genuinely valid PNG, so ImageField's Pillow check passes."""
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@no_throttle
class ProviderProfileTests(APITestCase):
    def setUp(self):
        self.url = reverse("provider-profile")
        self.provider_user = User.objects.create_user(
            email="provider@bimaya.test",
            password="Himalaya#2026",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        self.customer_user = User.objects.create_user(
            email="customer@bimaya.test",
            password="Himalaya#2026",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

    def test_get_before_creation_returns_missing_code(self):
        self.client.force_authenticate(self.provider_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["code"], "provider_profile_missing")

    def test_put_creates_then_get_returns_profile(self):
        self.client.force_authenticate(self.provider_user)
        response = self.client.put(
            self.url, {"company_name": "Everest Life", "website": "https://everest.test"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["company_name"], "Everest Life")
        self.assertTrue(response.data["slug"])

        get_response = self.client.get(self.url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data["company_name"], "Everest Life")

    def test_patch_updates_existing_profile(self):
        Provider.objects.create(user=self.provider_user, company_name="Old Name")
        self.client.force_authenticate(self.provider_user)
        response = self.client.patch(self.url, {"support_phone": "+977-1-4000000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["support_phone"], "+977-1-4000000")
        self.assertEqual(response.data["company_name"], "Old Name")

    def test_provider_cannot_self_approve(self):
        self.client.force_authenticate(self.provider_user)
        self.client.put(self.url, {"company_name": "Everest Life"})
        response = self.client.patch(
            self.url, {"is_approved": True, "kyc_status": Provider.KycStatus.VERIFIED}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        provider = Provider.objects.get(user=self.provider_user)
        self.assertFalse(provider.is_approved)
        self.assertEqual(provider.kyc_status, Provider.KycStatus.PENDING)

    def test_customer_is_forbidden(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_is_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@no_throttle
@override_settings(MEDIA_ROOT=_LOGO_MEDIA_ROOT)
class ProviderLogoTests(APITestCase):
    """Uploading, replacing and removing the company logo via the profile."""

    def setUp(self):
        self.url = reverse("provider-profile")
        self.owner = User.objects.create_user(
            email="logo.owner@bimaya.test",
            password="Himalaya#2026",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        # A logo attaches to an existing profile, so create one up front.
        self.provider = Provider.objects.create(
            user=self.owner, company_name="Everest Life"
        )
        self.client.force_authenticate(self.owner)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_LOGO_MEDIA_ROOT, ignore_errors=True)

    def test_logo_can_be_uploaded(self):
        response = self.client.patch(
            self.url, {"logo": _png_upload()}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.provider.refresh_from_db()
        self.assertTrue(self.provider.logo.name.startswith("providers/logos/"))
        # The API returns an absolute media URL the browser can load directly.
        self.assertTrue(
            response.data["logo"].startswith(
                "http://testserver/media/providers/logos/"
            )
        )

    def test_logo_can_be_removed(self):
        self.client.patch(self.url, {"logo": _png_upload()}, format="multipart")
        response = self.client.patch(self.url, {"logo": None}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["logo"])
        self.provider.refresh_from_db()
        self.assertFalse(self.provider.logo)

    def test_oversized_logo_is_rejected(self):
        with mock.patch("apps.providers.serializers.LOGO_MAX_BYTES", 8):
            response = self.client.patch(
                self.url, {"logo": _png_upload()}, format="multipart"
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("logo", response.data["errors"])

    def test_non_image_upload_is_rejected(self):
        bogus = SimpleUploadedFile(
            "logo.txt", b"not an image", content_type="text/plain"
        )
        response = self.client.patch(self.url, {"logo": bogus}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("logo", response.data["errors"])
