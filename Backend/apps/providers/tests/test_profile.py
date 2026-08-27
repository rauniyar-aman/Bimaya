"""Tests for the provider profile endpoint (``/api/v1/provider/profile/``)."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.providers.models import Provider

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)


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
