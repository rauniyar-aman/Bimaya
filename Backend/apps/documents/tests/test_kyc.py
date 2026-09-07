"""Tests for the customer KYC endpoints (``/api/v1/kyc/``)."""

import io
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import CustomerKyc

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)


def make_customer(email="cust@bimaya.test"):
    return User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.CUSTOMER, is_verified=True
    )


def make_image(name="doc.png"):
    """A tiny in-memory PNG, so ``ImageField`` validation passes."""
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def nid_payload(**overrides):
    payload = {
        "full_name": "Sita Sharma",
        "email": "sita@bimaya.test",
        "phone": "9800000000",
        "marital_status": CustomerKyc.MaritalStatus.MARRIED,
        "permanent_address": "Kathmandu",
        "document_type": CustomerKyc.DocumentType.NID,
        "document_number": "NID-123",
        "document_front": make_image("front.png"),
    }
    payload.update(overrides)
    return payload


@no_throttle
class SelfKycUpsertTests(APITestCase):
    def setUp(self):
        self.customer = make_customer()
        self.url = reverse("kyc-self")

    def test_get_before_setup_is_404(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["code"], "self_kyc_missing")

    def test_create_self_kyc_is_pending(self):
        self.client.force_authenticate(self.customer)
        response = self.client.put(self.url, nid_payload(), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], CustomerKyc.Status.PENDING)
        self.assertTrue(response.data["is_self"])
        kyc = CustomerKyc.objects.get(customer=self.customer, is_self=True)
        self.assertEqual(kyc.full_name, "Sita Sharma")

    def test_editing_verified_self_kyc_resets_to_pending(self):
        kyc = CustomerKyc.objects.create(
            customer=self.customer,
            is_self=True,
            full_name="Sita Sharma",
            permanent_address="Kathmandu",
            document_type=CustomerKyc.DocumentType.NID,
            document_number="NID-123",
            document_front=make_image(),
            status=CustomerKyc.Status.VERIFIED,
            review_note="",
        )
        self.client.force_authenticate(self.customer)
        response = self.client.patch(
            self.url, {"full_name": "Sita R. Sharma"}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        kyc.refresh_from_db()
        self.assertEqual(kyc.status, CustomerKyc.Status.PENDING)
        self.assertEqual(kyc.full_name, "Sita R. Sharma")

    def test_second_put_updates_rather_than_duplicates(self):
        self.client.force_authenticate(self.customer)
        self.client.put(self.url, nid_payload(), format="multipart")
        self.client.put(
            self.url, nid_payload(full_name="Someone Else"), format="multipart"
        )
        self.assertEqual(
            CustomerKyc.objects.filter(customer=self.customer, is_self=True).count(), 1
        )


@no_throttle
class KycDocumentValidationTests(APITestCase):
    def setUp(self):
        self.customer = make_customer()
        self.url = reverse("kyc-self")
        self.client.force_authenticate(self.customer)

    def test_front_image_required(self):
        payload = nid_payload()
        payload.pop("document_front")
        response = self.client.put(self.url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("document_front", response.data["errors"])

    def test_citizenship_requires_back(self):
        payload = nid_payload(document_type=CustomerKyc.DocumentType.CITIZENSHIP)
        response = self.client.put(self.url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("document_back", response.data["errors"])

    def test_citizenship_with_back_succeeds(self):
        payload = nid_payload(
            document_type=CustomerKyc.DocumentType.CITIZENSHIP,
            document_back=make_image("back.png"),
        )
        response = self.client.put(self.url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_nid_back_optional(self):
        response = self.client.put(self.url, nid_payload(), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_passport_single_image(self):
        payload = nid_payload(document_type=CustomerKyc.DocumentType.PASSPORT)
        response = self.client.put(self.url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


@no_throttle
class BeneficiaryKycTests(APITestCase):
    def setUp(self):
        self.customer = make_customer()
        self.url = reverse("kyc-beneficiary")

    def test_create_beneficiary_kyc(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.url, nid_payload(), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["is_self"])
        self.assertEqual(response.data["status"], CustomerKyc.Status.PENDING)

    def test_beneficiary_does_not_collide_with_self_constraint(self):
        # A customer may hold many beneficiary KYCs — the unique constraint only
        # guards the single self KYC.
        self.client.force_authenticate(self.customer)
        self.client.post(self.url, nid_payload(), format="multipart")
        response = self.client.post(self.url, nid_payload(), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            CustomerKyc.objects.filter(customer=self.customer, is_self=False).count(), 2
        )

    def test_anonymous_cannot_create(self):
        response = self.client.post(self.url, nid_payload(), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
