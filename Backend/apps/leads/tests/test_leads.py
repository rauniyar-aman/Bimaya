"""Tests for the provider onboarding enquiry endpoint (``/api/v1/provider-leads/``)."""

from unittest import mock

from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import ProviderLead

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)


@no_throttle
class ProviderLeadCreateTests(APITestCase):
    def setUp(self):
        self.url = reverse("provider-lead-create")

    def _payload(self, **overrides):
        payload = {
            "company_name": "Everest Insurance",
            "contact_name": "Rajesh Thapa",
            "email": "rajesh@everest.test",
            "phone": "9800000000",
            "message": "We would like to list our health plans.",
        }
        payload.update(overrides)
        return payload

    def test_submit_lead_creates_record(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("detail", response.data)
        lead = ProviderLead.objects.get()
        self.assertEqual(lead.company_name, "Everest Insurance")
        self.assertEqual(lead.status, ProviderLead.Status.NEW)

    def test_submit_lead_notifies_admin(self):
        self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Everest Insurance", mail.outbox[0].subject)

    def test_message_and_phone_are_optional(self):
        response = self.client.post(
            self.url,
            self._payload(message="", phone=""),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_missing_company_name_is_rejected(self):
        response = self.client.post(
            self.url, self._payload(company_name=""), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_email_is_rejected(self):
        response = self.client.post(
            self.url, self._payload(email="not-an-email"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lead_endpoint_needs_no_auth(self):
        # No force_authenticate — the endpoint is public.
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_client_cannot_set_status(self):
        response = self.client.post(
            self.url,
            self._payload(status=ProviderLead.Status.ONBOARDED),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProviderLead.objects.get().status, ProviderLead.Status.NEW)

    def test_provider_lead_is_kind_provider(self):
        self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(ProviderLead.objects.get().kind, ProviderLead.Kind.PROVIDER)


@no_throttle
class ContactLeadCreateTests(APITestCase):
    def setUp(self):
        self.url = reverse("contact-lead-create")

    def _payload(self, **overrides):
        payload = {
            "contact_name": "Priya Karki",
            "email": "priya@example.test",
            "phone": "9811111111",
            "message": "How do I renew my health policy?",
        }
        payload.update(overrides)
        return payload

    def test_submit_contact_creates_record(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("detail", response.data)
        lead = ProviderLead.objects.get()
        self.assertEqual(lead.kind, ProviderLead.Kind.CONTACT)
        self.assertEqual(lead.contact_name, "Priya Karki")
        self.assertEqual(lead.company_name, "")
        self.assertEqual(lead.status, ProviderLead.Status.NEW)

    def test_contact_needs_no_company(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_contact_notifies_admin(self):
        self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("contact enquiry", mail.outbox[0].subject.lower())

    def test_contact_endpoint_needs_no_auth(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invalid_email_is_rejected(self):
        response = self.client.post(
            self.url, self._payload(email="not-an-email"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
