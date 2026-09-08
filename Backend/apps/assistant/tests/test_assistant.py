"""Tests for the assistant endpoints.

* ``POST /api/v1/assistant/recommend/`` — public, rule-based ranking.
* ``POST /api/v1/assistant/chat/`` — authenticated, flag-gated LLM Q&A.

The chat provider is never actually called: the flag is off by default (so we
assert the disabled path), and when we exercise the enabled path we monkeypatch
the provider function so no network call or key is needed.
"""

from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.assistant import services
from apps.assistant.exceptions import AssistantUnavailable
from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import Provider

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)


def make_customer(email="cust@bimaya.test"):
    return User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.CUSTOMER, is_verified=True
    )


def make_provider(email="prov@bimaya.test", company="Everest Life", *, approved=True):
    user = User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.PROVIDER, is_verified=True
    )
    return Provider.objects.create(user=user, company_name=company, is_approved=approved)


def make_policy(provider, category, name, **kwargs):
    defaults = {
        "premium": Decimal("10000.00"),
        "coverage_amount": Decimal("1000000.00"),
        "term_months": 12,
        "status": Policy.Status.APPROVED,
    }
    defaults.update(kwargs)
    return Policy.objects.create(
        provider=provider, category=category, name=name, **defaults
    )


@no_throttle
class RecommendTests(APITestCase):
    def setUp(self):
        self.url = reverse("assistant-recommend")
        self.provider = make_provider()
        self.health = InsuranceCategory.objects.create(name="Health")
        self.vehicle = InsuranceCategory.objects.create(name="Vehicle")
        # A spread of policies to rank.
        self.cheap_health = make_policy(
            self.provider, self.health, "Basic Health",
            premium=Decimal("5000.00"), coverage_amount=Decimal("500000.00"),
        )
        self.rich_health = make_policy(
            self.provider, self.health, "Premium Health",
            premium=Decimal("20000.00"), coverage_amount=Decimal("3000000.00"),
            is_featured=True,
        )
        self.vehicle_plan = make_policy(
            self.provider, self.vehicle, "Motor Shield",
            premium=Decimal("8000.00"), coverage_amount=Decimal("800000.00"),
        )

    def test_public_no_auth_required(self):
        res = self.client.post(self.url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Returns all public policies when no criteria given.
        self.assertEqual(len(res.data), 3)
        for row in res.data:
            self.assertIn("match_score", row)
            self.assertIn("reasons", row)

    def test_excludes_non_public_policies(self):
        # A draft and an unapproved-provider policy must never surface.
        make_policy(
            self.provider, self.health, "Draft Plan", status=Policy.Status.DRAFT
        )
        other = make_provider(email="p2@bimaya.test", company="Hidden", approved=False)
        make_policy(other, self.health, "Hidden Plan")

        res = self.client.post(self.url, {}, format="json")
        names = {r["name"] for r in res.data}
        self.assertNotIn("Draft Plan", names)
        self.assertNotIn("Hidden Plan", names)
        self.assertEqual(len(res.data), 3)

    def test_category_filter(self):
        res = self.client.post(self.url, {"category": "vehicle"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], "Motor Shield")

    def test_budget_filter_excludes_over_budget(self):
        res = self.client.post(self.url, {"budget_max": "8000"}, format="json")
        names = {r["name"] for r in res.data}
        self.assertIn("Basic Health", names)
        self.assertIn("Motor Shield", names)
        self.assertNotIn("Premium Health", names)  # 20000 > 8000

    def test_scores_present_and_ordered_desc(self):
        res = self.client.post(
            self.url,
            {"category": "health", "budget_max": "25000", "coverage_min": "400000"},
            format="json",
        )
        scores = [r["match_score"] for r in res.data]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for row in res.data:
            self.assertGreaterEqual(row["match_score"], 0)
            self.assertLessEqual(row["match_score"], 100)

    def test_limit_respected(self):
        res = self.client.post(self.url, {"limit": 2}, format="json")
        self.assertEqual(len(res.data), 2)

    def test_empty_catalog_ok(self):
        Policy.objects.all().delete()
        res = self.client.post(self.url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])


@no_throttle
class ChatDisabledTests(APITestCase):
    """By default the chat assistant is off (no key configured)."""

    def setUp(self):
        self.url = reverse("assistant-chat")
        self.customer = make_customer()

    def test_requires_authentication(self):
        res = self.client.post(self.url, {"message": "Hello"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_disabled_by_default(self):
        self.client.force_authenticate(self.customer)
        res = self.client.post(self.url, {"message": "What is term life?"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["code"], "assistant_disabled")


@no_throttle
@override_settings(AI_CHAT_ENABLED=True, GEMINI_API_KEY="test-key", AI_CHAT_PROVIDER="gemini")
class ChatEnabledTests(APITestCase):
    def setUp(self):
        self.url = reverse("assistant-chat")
        self.customer = make_customer()
        self.client.force_authenticate(self.customer)

    def test_returns_reply_from_provider(self):
        with mock.patch.object(
            services, "_gemini_reply", return_value="Term life covers a fixed period."
        ) as gemini:
            res = self.client.post(
                self.url, {"message": "What is term life?"}, format="json"
            )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["reply"], "Term life covers a fixed period.")
        gemini.assert_called_once()

    def test_history_capped_to_recent_turns(self):
        long_history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"turn {i}"}
            for i in range(20)
        ]
        with mock.patch.object(
            services, "_gemini_reply", return_value="ok"
        ) as gemini:
            res = self.client.post(
                self.url,
                {"message": "and now?", "history": long_history},
                format="json",
            )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        passed_history = gemini.call_args.args[1]
        self.assertLessEqual(len(passed_history), services._MAX_HISTORY_TURNS)

    def test_provider_error_returns_503(self):
        with mock.patch.object(
            services, "_gemini_reply", side_effect=RuntimeError("boom")
        ):
            res = self.client.post(
                self.url, {"message": "hi"}, format="json"
            )
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(res.data["code"], "assistant_unavailable")

    def test_blank_message_rejected(self):
        res = self.client.post(self.url, {"message": "   "}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class ChatEnabledFlagTests(APITestCase):
    """chat_enabled() needs both the flag and a key."""

    @override_settings(AI_CHAT_ENABLED=True, GEMINI_API_KEY="")
    def test_flag_on_but_no_key_is_disabled(self):
        self.assertFalse(services.chat_enabled())

    @override_settings(AI_CHAT_ENABLED=False, GEMINI_API_KEY="test-key")
    def test_key_present_but_flag_off_is_disabled(self):
        self.assertFalse(services.chat_enabled())

    @override_settings(AI_CHAT_ENABLED=True, GEMINI_API_KEY="test-key")
    def test_both_present_is_enabled(self):
        self.assertTrue(services.chat_enabled())
