"""Tests for payment endpoints (``/api/v1/payments/``)."""

from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import Provider
from apps.purchases.models import PolicyPurchase

from ..gateways import esewa
from ..models import Payment

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)


def make_customer(email="cust@bimaya.test"):
    return User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.CUSTOMER, is_verified=True
    )


def make_provider(email="prov@bimaya.test", company="Everest Life"):
    user = User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.PROVIDER, is_verified=True
    )
    return Provider.objects.create(user=user, company_name=company, is_approved=True)


def make_purchase(customer, provider, category, **kwargs):
    policy = Policy.objects.create(
        provider=provider,
        category=category,
        name="Term Shield",
        premium=Decimal("10000.00"),
        coverage_amount=Decimal("1000000.00"),
        term_months=12,
        status=Policy.Status.APPROVED,
    )
    defaults = {
        "nominee_name": "Sita Sharma",
        "nominee_relationship": "Spouse",
        "nominee_contact": "9800000000",
    }
    defaults.update(kwargs)
    return PolicyPurchase.objects.create(customer=customer, policy=policy, **defaults)


@no_throttle
class PaymentInitiateTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider()
        self.customer = make_customer()
        self.purchase = make_purchase(self.customer, self.provider, self.category)
        self.url = reverse("payment-initiate")

    def test_initiate_esewa_creates_payment_and_returns_form_fields(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.url,
            {"policy_purchase_id": self.purchase.id, "gateway": "ESEWA"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["fields"]["total_amount"], "10000.00")
        payment = Payment.objects.get(id=response.data["payment_id"])
        self.assertEqual(payment.status, Payment.Status.INITIATED)
        self.assertEqual(payment.amount, self.purchase.policy.premium)
        self.assertIsNone(payment.gateway_transaction_id)

    def test_initiate_khalti_calls_gateway_api(self):
        self.client.force_authenticate(self.customer)
        fake_response = mock.Mock()
        fake_response.json.return_value = {
            "payment_url": "https://dev.khalti.com/pay/abc",
            "pidx": "abc123",
        }
        fake_response.raise_for_status = mock.Mock()
        with mock.patch(
            "apps.payments.gateways.khalti.requests.post", return_value=fake_response
        ) as post:
            response = self.client.post(
                self.url,
                {"policy_purchase_id": self.purchase.id, "gateway": "KHALTI"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["pidx"], "abc123")
        post.assert_called_once()

    def test_cannot_initiate_for_non_pending_purchase(self):
        self.purchase.status = PolicyPurchase.Status.ACTIVE
        self.purchase.save(update_fields=["status"])
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.url,
            {"policy_purchase_id": self.purchase.id, "gateway": "ESEWA"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_initiate_for_another_customers_purchase(self):
        other = make_customer("other@bimaya.test")
        self.client.force_authenticate(other)
        response = self.client.post(
            self.url,
            {"policy_purchase_id": self.purchase.id, "gateway": "ESEWA"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@no_throttle
class PaymentCallbackTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider()
        self.customer = make_customer()
        self.purchase = make_purchase(self.customer, self.provider, self.category)
        self.payment = Payment.objects.create(
            policy_purchase=self.purchase,
            amount=self.purchase.policy.premium,
            gateway=Payment.Gateway.ESEWA,
        )
        self.callback_url = reverse("payment-callback", args=["esewa"])

    def _payload(self):
        reference = f"BIM-{self.payment.id}"
        amount = str(self.payment.amount)
        return {
            "transaction_uuid": reference,
            "total_amount": amount,
            "product_code": "EPAYTEST",
            "status": "COMPLETE",
            "transaction_code": "0000ABC",
            "signature": esewa._sign(amount, reference, "EPAYTEST"),
        }

    def test_successful_callback_activates_purchase(self):
        with mock.patch("apps.payments.gateways.esewa.verify", return_value=True):
            response = self.client.post(self.callback_url, self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.payment.refresh_from_db()
        self.purchase.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.SUCCESS)
        self.assertEqual(self.payment.gateway_transaction_id, "0000ABC")
        self.assertIsNotNone(self.payment.paid_at)
        self.assertEqual(self.purchase.status, PolicyPurchase.Status.ACTIVE)
        self.assertTrue(self.purchase.policy_number)
        self.assertTrue(self.purchase.policy_number.startswith("BIM-"))
        self.assertIsNotNone(self.purchase.start_date)
        self.assertIsNotNone(self.purchase.end_date)

    def test_failed_callback_leaves_purchase_retryable(self):
        with mock.patch("apps.payments.gateways.esewa.verify", return_value=False):
            response = self.client.post(self.callback_url, self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.payment.refresh_from_db()
        self.purchase.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertIsNone(self.payment.gateway_transaction_id)
        self.assertEqual(self.purchase.status, PolicyPurchase.Status.PENDING_PAYMENT)
        self.assertIsNone(self.purchase.policy_number)

    def test_callback_rejects_tampered_signature(self):
        # No mocking here — exercises the real signature check in esewa.verify().
        payload = self._payload()
        payload["signature"] = "not-a-real-signature"
        response = self.client.post(self.callback_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)

    def test_callback_for_unknown_gateway_is_404(self):
        response = self.client.post(
            reverse("payment-callback", args=["unknown"]), {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_callback_for_unresolvable_payment_is_404(self):
        response = self.client.post(
            self.callback_url, {"transaction_uuid": "BIM-999999"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
