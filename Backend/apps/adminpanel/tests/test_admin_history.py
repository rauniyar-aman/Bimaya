"""Tests for the admin detail pages' data: the enriched detail shapes, the
merged history timelines and the self-service audit trail that feeds them.

Three things are covered here, in order:

* **Detail shape** — ``/admin/users/<pk>/`` and ``/admin/providers/<pk>/`` return
  the subject's own nested records (bounded), correctly scoped: one subject's
  page never shows another's rows.
* **History** — ``/admin/users/<pk>/history/`` and
  ``/admin/providers/<pk>/history/`` merge the subject's activity (read from the
  domain records) with the administrative actions taken on them (read from the
  audit log). The admin rows appear only for a caller who also holds
  ``audit_log.view``; without it the timeline is activity-only.
* **Instrumentation** — each self-service transition (buy, pay, claim, message,
  KYC, policy create/submit, issue) writes an :class:`AuditLogEntry` whose
  ``actor_role`` is the acting *customer*/*provider*, never ``ADMIN`` — which is
  exactly why those rows never double-list against their own domain event.

Uploads route to a throwaway ``MEDIA_ROOT``; ``tearDownModule`` removes it.
"""

import shutil
import tempfile
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.test import APITestCase

from apps.claims.models import Claim, ClaimMessage
from apps.documents.models import CustomerKyc, ProviderKyc
from apps.payments.gateways import esewa
from apps.payments.models import Payment
from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import ProviderMembership
from apps.providers.rbac import OWNER, ProviderRole
from apps.purchases.models import PolicyPurchase
from apps.staff.models import AuditLogEntry, StaffRoleAssignment
from apps.staff.rbac import StaffRole
from apps.staff.services import record_audit

from .test_adminpanel import (
    make_customer,
    make_image,
    make_kyc,
    make_policy,
    make_provider,
    make_purchase,
    no_throttle,
)

User = get_user_model()

_MEDIA_ROOT = tempfile.mkdtemp(prefix="bimaya-admin-history-tests-")


def tearDownModule():
    shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)


def make_staff(role, email=None):
    """A platform administrator holding exactly one staff role.

    The permission boundary under test here is *narrower* than the
    ``SYSTEM_OWNER`` used elsewhere: a role that grants ``customer.view`` but not
    ``audit_log.view`` must still reach the timeline — and see activity only.
    """
    value = role.value if hasattr(role, "value") else role
    user = User.objects.create_user(
        email=email or f"{value.lower()}@bimaya.test",
        password="Himalaya#2026",
        role=User.Role.ADMIN,
        is_verified=True,
    )
    StaffRoleAssignment.objects.create(user=user, role=value)
    return user


def make_claim(customer, purchase, **overrides):
    defaults = {
        "incident_date": timezone.localdate(),
        "incident_location": "Kathmandu",
        "description": "The insured vehicle was damaged in a collision.",
        "claimed_amount": Decimal("15000.00"),
    }
    defaults.update(overrides)
    return Claim.objects.create(customer=customer, purchase=purchase, **defaults)


def timestamps(results):
    """The timeline's timestamps as datetimes, in the order returned."""
    return [parse_datetime(row["timestamp"]) for row in results]


# ---------------------------------------------------------------------------
# Detail shapes
# ---------------------------------------------------------------------------


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AdminUserDetailShapeTests(APITestCase):
    """The user detail page carries the person's own records, and only theirs."""

    def setUp(self):
        self.admin = make_staff(StaffRole.SYSTEM_OWNER)
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider(approved=True)
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.other = make_customer("other@bimaya.test")
        self.kyc = make_kyc(self.customer)
        self.purchase = make_purchase(self.customer, self.policy, kyc=self.kyc)
        self.claim = make_claim(self.customer, self.purchase)
        self.client.force_authenticate(self.admin)
        self.url = reverse("admin-user-detail", args=[self.customer.id])

    def test_detail_nests_the_users_own_records(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        # The counts the page has always had are still there…
        self.assertEqual(data["purchase_count"], 1)
        self.assertEqual(data["claim_count"], 1)
        # …alongside the records themselves.
        self.assertEqual([row["id"] for row in data["kyc_records"]], [self.kyc.id])
        self.assertEqual(
            [row["id"] for row in data["recent_purchases"]], [self.purchase.id]
        )
        self.assertEqual(data["recent_purchases"][0]["policy_name"], self.policy.name)
        self.assertEqual([row["id"] for row in data["recent_claims"]], [self.claim.id])
        self.assertEqual(data["recent_claims"][0]["policy_name"], self.policy.name)
        self.assertIsNone(data["avatar"])
        self.assertIn("last_login", data)

    def test_another_users_records_never_appear(self):
        other_kyc = make_kyc(self.other)
        other_purchase = make_purchase(self.other, self.policy, kyc=other_kyc)
        response = self.client.get(self.url)
        self.assertNotIn(
            other_purchase.id, [row["id"] for row in response.data["recent_purchases"]]
        )
        self.assertNotIn(
            other_kyc.id, [row["id"] for row in response.data["kyc_records"]]
        )

    def test_nested_lists_are_bounded(self):
        for index in range(12):
            make_purchase(self.customer, self.policy, kyc=self.kyc)
        response = self.client.get(self.url)
        self.assertEqual(response.data["purchase_count"], 13)
        self.assertEqual(len(response.data["recent_purchases"]), 10)

    def test_forbidden_without_customer_view(self):
        self.client.force_authenticate(make_staff(StaffRole.FINANCE_OFFICER))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AdminProviderDetailShapeTests(APITestCase):
    """The provider detail page carries the team, KYC, policies and totals."""

    def setUp(self):
        self.admin = make_staff(StaffRole.SYSTEM_OWNER)
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider(approved=True)
        self.policy = make_policy(self.provider, self.category)
        self.draft = make_policy(
            self.provider, self.category, name="Draft Plan", status=Policy.Status.DRAFT
        )
        self.member = User.objects.create_user(
            email="member@bimaya.test",
            password="Himalaya#2026",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        self.membership = ProviderMembership.objects.create(
            provider=self.provider,
            user=self.member,
            role=ProviderRole.POLICY_MANAGER.value,
        )
        self.document = ProviderKyc.objects.create(
            provider=self.provider,
            document_type=ProviderKyc.DocumentType.REGISTRATION,
            file=make_image("registration.png"),
            uploaded_by=self.provider.user,
        )
        self.customer = make_customer()
        self.purchase = make_purchase(
            self.customer, self.policy, status=PolicyPurchase.Status.FORWARDED
        )
        self.purchase.issue("NLI-DETAIL-1")  # creates the commission payout
        self.claim = make_claim(self.customer, self.purchase)
        self.client.force_authenticate(self.admin)
        self.url = reverse("admin-provider-detail", args=[self.provider.id])

    def test_detail_nests_team_kyc_policies_and_totals(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # The owner leads the people list with the implicit OWNER role, then the
        # added members — the same shape the dedicated members endpoint returns.
        people = data["memberships"]
        self.assertEqual(people[0]["email"], self.provider.user.email)
        self.assertEqual(people[0]["role"], OWNER)
        self.assertIsNone(people[0]["membership_id"])
        self.assertEqual(people[1]["email"], self.member.email)
        self.assertEqual(people[1]["membership_id"], self.membership.id)
        self.assertEqual(people[1]["role"], ProviderRole.POLICY_MANAGER.value)

        self.assertEqual([row["id"] for row in data["kyc_documents"]], [self.document.id])
        self.assertEqual(
            {row["name"] for row in data["recent_policies"]},
            {self.policy.name, self.draft.name},
        )
        self.assertEqual(data["active_policies"], 1)  # the draft does not count
        self.assertEqual(data["purchase_count"], 1)
        self.assertEqual(data["payout_net_total"], "9000.00")  # 10000 less 10%
        self.assertEqual(data["pending_claims"], 1)

    def test_another_providers_records_never_appear(self):
        rival = make_provider("rival@bimaya.test", "Himalayan Health", approved=True)
        rival_policy = make_policy(rival, self.category, name="Rival Plan")
        response = self.client.get(self.url)
        self.assertNotIn(
            rival_policy.name, [row["name"] for row in response.data["recent_policies"]]
        )
        self.assertNotIn(
            rival.user.email, [row["email"] for row in response.data["memberships"]]
        )

    def test_list_view_stays_lean(self):
        response = self.client.get(reverse("admin-provider-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = response.data["results"][0]
        self.assertIn("company_name", row)
        self.assertNotIn("memberships", row)
        self.assertNotIn("kyc_documents", row)

    def test_forbidden_without_provider_view(self):
        self.client.force_authenticate(make_staff(StaffRole.FINANCE_OFFICER))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# History timelines
# ---------------------------------------------------------------------------


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AdminUserHistoryTests(APITestCase):
    def setUp(self):
        self.admin = make_staff(StaffRole.SYSTEM_OWNER)
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider(approved=True)
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.kyc = make_kyc(self.customer)
        self.purchase = make_purchase(
            self.customer, self.policy, kyc=self.kyc, status=PolicyPurchase.Status.PAID
        )
        self.payment = Payment.objects.create(
            policy_purchase=self.purchase,
            amount=self.policy.premium,
            gateway=Payment.Gateway.ESEWA,
            status=Payment.Status.SUCCESS,
            paid_at=timezone.now(),
        )
        self.claim = make_claim(self.customer, self.purchase)
        self.message = ClaimMessage.objects.create(
            claim=self.claim,
            author=self.customer,
            author_role=self.customer.role,
            body="Attaching the garage estimate.",
        )
        self.url = reverse("admin-user-history", args=[self.customer.id])

    def _results(self, user=None):
        self.client.force_authenticate(user or self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    def test_anonymous_is_unauthorized(self):
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_forbidden_without_customer_view(self):
        self.client.force_authenticate(make_staff(StaffRole.FINANCE_OFFICER))
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_response_is_paginated(self):
        response = self._results()
        for key in ("count", "next", "previous", "results"):
            self.assertIn(key, response.data)
        self.assertEqual(response.data["count"], len(response.data["results"]))

    def test_activity_is_assembled_from_the_domain_records(self):
        results = self._results().data["results"]
        actions = {row["action"] for row in results}
        self.assertEqual(
            {
                "account.created",
                "kyc.submitted",
                "purchase.created",
                "payment.recorded",
                "claim.submitted",
                "claim.message",
            },
            actions,
        )
        self.assertTrue(all(row["source"] == "activity" for row in results))

        purchase_event = next(r for r in results if r["action"] == "purchase.created")
        self.assertEqual(purchase_event["ref_type"], "PolicyPurchase")
        self.assertEqual(purchase_event["ref_id"], str(self.purchase.id))
        self.assertEqual(purchase_event["status"], PolicyPurchase.Status.PAID)
        self.assertEqual(purchase_event["amount"], str(self.policy.premium))
        self.assertIn(self.policy.name, purchase_event["title"])

    def test_events_are_newest_first(self):
        moments = timestamps(self._results().data["results"])
        self.assertEqual(moments, sorted(moments, reverse=True))

    def test_admin_actions_are_merged_in_for_an_audit_log_viewer(self):
        self.client.force_authenticate(self.admin)
        suspend = self.client.post(
            reverse("admin-user-suspend", args=[self.customer.id])
        )
        self.assertEqual(suspend.status_code, status.HTTP_200_OK)

        results = self._results().data["results"]
        admin_rows = [row for row in results if row["source"] == "admin"]
        self.assertEqual(len(admin_rows), 1)
        self.assertEqual(admin_rows[0]["action"], "customer.suspend")
        self.assertEqual(admin_rows[0]["title"], "Account suspended")
        self.assertEqual(admin_rows[0]["actor"], self.admin.email)
        self.assertEqual(admin_rows[0]["ref_type"], "User")
        self.assertIn("is active: True → False", admin_rows[0]["detail"])

    def test_admin_actions_are_withheld_without_audit_log_view(self):
        record_audit(
            actor=self.admin,
            action="customer.suspend",
            module="customer",
            entity_type="User",
            entity_id=self.customer.pk,
            changes={"is_active": [True, False]},
        )
        support = make_staff(StaffRole.CUSTOMER_SUPPORT)
        results = self._results(support).data["results"]
        # Customer Support may read the person, but not the audit trail.
        self.assertEqual([row for row in results if row["source"] == "admin"], [])
        self.assertTrue(any(row["action"] == "purchase.created" for row in results))

    def test_self_service_audit_rows_are_not_double_listed(self):
        # The customer's own audit row (written by the instrumentation) must not
        # reappear as an "admin" event — the domain record already represents it.
        record_audit(
            actor=self.customer,
            action="purchase.create",
            module="purchase",
            entity_type="PolicyPurchase",
            entity_id=self.purchase.pk,
            changes={"status": self.purchase.status},
        )
        results = self._results().data["results"]
        self.assertEqual([row for row in results if row["source"] == "admin"], [])
        purchase_rows = [r for r in results if r["ref_type"] == "PolicyPurchase"]
        self.assertEqual(len(purchase_rows), 1)

    def test_another_users_activity_never_appears(self):
        other = make_customer("other@bimaya.test")
        other_kyc = make_kyc(other)
        other_purchase = make_purchase(other, self.policy, kyc=other_kyc)
        results = self._results().data["results"]
        refs = {(row["ref_type"], row["ref_id"]) for row in results}
        self.assertNotIn(("PolicyPurchase", str(other_purchase.id)), refs)
        self.assertNotIn(("CustomerKyc", str(other_kyc.id)), refs)

    def test_unknown_user_is_not_found(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("admin-user-history", args=[999999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AdminProviderHistoryTests(APITestCase):
    def setUp(self):
        self.admin = make_staff(StaffRole.SYSTEM_OWNER)
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider(approved=True)
        self.policy = make_policy(self.provider, self.category)
        self.member = User.objects.create_user(
            email="member@bimaya.test",
            password="Himalaya#2026",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        ProviderMembership.objects.create(
            provider=self.provider,
            user=self.member,
            role=ProviderRole.CLAIMS_OFFICER.value,
        )
        ProviderKyc.objects.create(
            provider=self.provider,
            document_type=ProviderKyc.DocumentType.LICENSE,
            file=make_image("licence.png"),
            uploaded_by=self.provider.user,
        )
        self.customer = make_customer()
        self.purchase = make_purchase(
            self.customer, self.policy, status=PolicyPurchase.Status.FORWARDED
        )
        self.purchase.issue("NLI-HISTORY-1")
        self.claim = make_claim(self.customer, self.purchase)
        self.url = reverse("admin-provider-history", args=[self.provider.id])

    def _results(self, user=None):
        self.client.force_authenticate(user or self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    def test_anonymous_is_unauthorized(self):
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_forbidden_without_provider_view(self):
        self.client.force_authenticate(make_staff(StaffRole.FINANCE_OFFICER))
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_activity_covers_the_organisation_s_own_record_types(self):
        results = self._results().data["results"]
        actions = {row["action"] for row in results}
        self.assertEqual(
            {
                "provider.created",
                "provider_kyc.uploaded",
                "membership.added",
                "policy.created",
                "payout.recorded",
                "claim.submitted",
            },
            actions,
        )
        payout_event = next(r for r in results if r["action"] == "payout.recorded")
        self.assertEqual(payout_event["amount"], "9000.00")
        self.assertEqual(payout_event["ref_type"], "ProviderPayout")

    def test_events_are_newest_first_and_paginated(self):
        response = self._results()
        self.assertIn("results", response.data)
        moments = timestamps(response.data["results"])
        self.assertEqual(moments, sorted(moments, reverse=True))

    def test_admin_actions_are_merged_in_for_an_audit_log_viewer(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("admin-provider-commission", args=[self.provider.id]),
            {"commission_rate": "12.50"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        admin_rows = [
            row for row in self._results().data["results"] if row["source"] == "admin"
        ]
        self.assertEqual(len(admin_rows), 1)
        self.assertEqual(admin_rows[0]["action"], "commission.manage")
        self.assertEqual(admin_rows[0]["title"], "Commission rate changed")
        self.assertEqual(admin_rows[0]["actor"], self.admin.email)
        self.assertEqual(admin_rows[0]["ref_type"], "Provider")

    def test_admin_actions_are_withheld_without_audit_log_view(self):
        record_audit(
            actor=self.admin,
            action="provider.approve",
            module="provider",
            entity_type="Provider",
            entity_id=self.provider.pk,
            changes={"is_approved": [False, True]},
        )
        relations = make_staff(StaffRole.PROVIDER_RELATIONS)
        results = self._results(relations).data["results"]
        self.assertEqual([row for row in results if row["source"] == "admin"], [])
        self.assertTrue(any(row["action"] == "policy.created" for row in results))

    def test_another_providers_activity_never_appears(self):
        rival = make_provider("rival@bimaya.test", "Himalayan Health", approved=True)
        rival_policy = make_policy(rival, self.category, name="Rival Plan")
        results = self._results().data["results"]
        refs = {(row["ref_type"], row["ref_id"]) for row in results}
        self.assertNotIn(("Policy", str(rival_policy.id)), refs)
        self.assertNotIn(("Provider", str(rival.id)), refs)

    def test_unknown_provider_is_not_found(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("admin-provider-history", args=[999999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Self-service audit instrumentation
# ---------------------------------------------------------------------------


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class SelfServiceAuditTrailTests(APITestCase):
    """Every self-service transition leaves an audit row behind.

    These rows make the durable trail (and ``/admin/audit/``) complete. Their
    ``actor_role`` is the acting customer or provider — never ``ADMIN`` — which
    is what keeps them out of the per-subject timeline's *admin* section.
    """

    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider(approved=True)
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()

    def _entry(self, action):
        entry = AuditLogEntry.objects.filter(action=action).first()
        self.assertIsNotNone(entry, f"no audit row recorded for {action!r}")
        return entry

    # --- customer side ------------------------------------------------------
    def test_self_kyc_submission_is_recorded(self):
        self.client.force_authenticate(self.customer)
        response = self.client.put(
            reverse("kyc-self"),
            {
                "full_name": "Sita Sharma",
                "permanent_address": "Kathmandu",
                "document_type": CustomerKyc.DocumentType.NID,
                "document_number": "NID-777",
                "document_front": make_image("front.png"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry = self._entry("customer_kyc.submit")
        self.assertEqual(entry.actor, self.customer)
        self.assertEqual(entry.actor_role, User.Role.CUSTOMER)
        self.assertEqual(entry.entity_type, "CustomerKyc")
        self.assertEqual(entry.entity_id, str(response.data["id"]))
        self.assertEqual(entry.reason, "created")

    def test_beneficiary_kyc_submission_is_recorded(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("kyc-beneficiary"),
            {
                "full_name": "Hari Sharma",
                "permanent_address": "Pokhara",
                "document_type": CustomerKyc.DocumentType.NID,
                "document_number": "NID-888",
                "document_front": make_image("front.png"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry = self._entry("customer_kyc.submit")
        self.assertEqual(entry.changes["is_self"], False)
        self.assertEqual(entry.entity_id, str(response.data["id"]))

    def test_purchase_creation_is_recorded(self):
        kyc = make_kyc(self.customer, status=CustomerKyc.Status.VERIFIED)
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("purchase-list"),
            {
                "policy": self.policy.id,
                "kyc": kyc.id,
                "insured_is_self": True,
                "nominee_name": "Sita Sharma",
                "nominee_relationship": "Spouse",
                "nominee_contact": "9800000000",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry = self._entry("purchase.create")
        self.assertEqual(entry.actor, self.customer)
        self.assertEqual(entry.actor_role, User.Role.CUSTOMER)
        self.assertEqual(entry.entity_type, "PolicyPurchase")
        self.assertEqual(entry.entity_id, str(response.data["id"]))
        self.assertEqual(entry.changes["policy"], self.policy.name)

    def test_payment_success_is_recorded_against_the_paying_customer(self):
        purchase = make_purchase(self.customer, self.policy)
        payment = Payment.objects.create(
            policy_purchase=purchase,
            amount=self.policy.premium,
            gateway=Payment.Gateway.ESEWA,
        )
        reference = f"BIM-{payment.id}"
        amount = str(payment.amount)
        response = self.client.post(
            reverse("payment-callback", args=["esewa"]),
            {
                "transaction_uuid": reference,
                "total_amount": amount,
                "product_code": "EPAYTEST",
                "status": "COMPLETE",
                "transaction_code": "0000ABC",
                "signature": esewa._sign(amount, reference, "EPAYTEST"),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The gateway calls the endpoint anonymously, so the row is attributed to
        # the customer whose purchase was paid for.
        entry = self._entry("payment.success")
        self.assertEqual(entry.actor, self.customer)
        self.assertEqual(entry.actor_role, User.Role.CUSTOMER)
        self.assertEqual(entry.entity_type, "Payment")
        self.assertEqual(entry.entity_id, str(payment.id))

    def test_claim_submission_and_message_are_recorded(self):
        kyc = make_kyc(self.customer, status=CustomerKyc.Status.VERIFIED)
        purchase = make_purchase(
            self.customer, self.policy, kyc=kyc, status=PolicyPurchase.Status.FORWARDED
        )
        purchase.issue("NLI-AUDIT-1")
        self.client.force_authenticate(self.customer)

        filed = self.client.post(
            reverse("claim-list"),
            {
                "purchase": purchase.id,
                "incident_date": timezone.localdate().isoformat(),
                "incident_location": "Kathmandu",
                "description": "Collision on the ring road.",
                "claimed_amount": "15000.00",
                "documents": [make_image("estimate.png")],
            },
            format="multipart",
        )
        self.assertEqual(filed.status_code, status.HTTP_201_CREATED)
        entry = self._entry("claim.submit")
        self.assertEqual(entry.actor, self.customer)
        self.assertEqual(entry.entity_type, "Claim")
        self.assertEqual(entry.entity_id, str(filed.data["id"]))

        messaged = self.client.post(
            reverse("claim-message", args=[filed.data["id"]]),
            {"body": "Attaching the garage estimate."},
            format="json",
        )
        self.assertEqual(messaged.status_code, status.HTTP_200_OK)
        message_entry = self._entry("claim.message")
        self.assertEqual(message_entry.changes, {"from": "customer"})
        self.assertEqual(message_entry.actor_role, User.Role.CUSTOMER)

    # --- provider side ------------------------------------------------------
    def test_policy_create_and_submit_are_recorded(self):
        self.client.force_authenticate(self.provider.user)
        created = self.client.post(
            reverse("provider-policy-list"),
            {
                "name": "Two Wheeler Shield",
                "summary": "Cover for scooters and motorbikes.",
                "description": "Third-party and own-damage cover.",
                "category": self.category.id,
                "premium": "4500.00",
                "coverage_amount": "300000.00",
                "term_months": 12,
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        entry = self._entry("policy.create")
        self.assertEqual(entry.actor, self.provider.user)
        self.assertEqual(entry.actor_role, User.Role.PROVIDER)
        self.assertEqual(entry.entity_type, "Policy")
        self.assertEqual(entry.entity_id, str(created.data["id"]))
        self.assertEqual(entry.changes["status"], Policy.Status.DRAFT)

        submitted = self.client.post(
            reverse("provider-policy-submit", args=[created.data["id"]])
        )
        self.assertEqual(submitted.status_code, status.HTTP_200_OK)
        submit_entry = self._entry("policy.submit")
        self.assertEqual(
            submit_entry.changes["status"],
            [Policy.Status.DRAFT, Policy.Status.PENDING],
        )

    def test_issuance_is_recorded(self):
        purchase = make_purchase(
            self.customer, self.policy, status=PolicyPurchase.Status.FORWARDED
        )
        self.client.force_authenticate(self.provider.user)
        response = self.client.post(
            reverse("provider-issuance-issue", args=[purchase.id]),
            {"policy_number": "NLI-ISSUE-9"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry = self._entry("issuance.issue")
        self.assertEqual(entry.actor, self.provider.user)
        self.assertEqual(entry.actor_role, User.Role.PROVIDER)
        self.assertEqual(entry.entity_type, "PolicyPurchase")
        self.assertEqual(entry.entity_id, str(purchase.id))
        self.assertEqual(entry.changes["policy_number"], [None, "NLI-ISSUE-9"])

    def test_provider_kyc_upload_is_recorded(self):
        self.client.force_authenticate(self.provider.user)
        response = self.client.post(
            reverse("provider-kyc-list"),
            {
                "document_type": ProviderKyc.DocumentType.REGISTRATION,
                "file": make_image("registration.png"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry = self._entry("provider_kyc.upload")
        self.assertEqual(entry.actor, self.provider.user)
        self.assertEqual(entry.entity_type, "ProviderKyc")

    def test_provider_claim_message_is_recorded(self):
        purchase = make_purchase(
            self.customer, self.policy, status=PolicyPurchase.Status.FORWARDED
        )
        purchase.issue("NLI-AUDIT-2")
        claim = make_claim(self.customer, purchase)
        self.client.force_authenticate(self.provider.user)
        response = self.client.post(
            reverse("provider-claim-message", args=[claim.id]),
            {"body": "Please share the police report."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry = self._entry("claim.message")
        self.assertEqual(entry.changes, {"from": "provider"})
        self.assertEqual(entry.actor_role, User.Role.PROVIDER)

    def test_instrumentation_never_breaks_the_request(self):
        """A failing audit write must not fail the customer's purchase."""
        kyc = make_kyc(self.customer, status=CustomerKyc.Status.VERIFIED)
        self.client.force_authenticate(self.customer)
        with mock.patch(
            "apps.staff.services.AuditLogEntry.objects.create",
            side_effect=RuntimeError("audit table unavailable"),
        ):
            response = self.client.post(
                reverse("purchase-list"),
                {
                    "policy": self.policy.id,
                    "kyc": kyc.id,
                    "insured_is_self": True,
                    "nominee_name": "Sita Sharma",
                    "nominee_relationship": "Spouse",
                    "nominee_contact": "9800000000",
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PolicyPurchase.objects.filter(customer=self.customer).exists())
        self.assertFalse(AuditLogEntry.objects.exists())

    def test_no_self_service_row_is_attributed_to_an_administrator(self):
        kyc = make_kyc(self.customer, status=CustomerKyc.Status.VERIFIED)
        self.client.force_authenticate(self.customer)
        self.client.post(
            reverse("purchase-list"),
            {
                "policy": self.policy.id,
                "kyc": kyc.id,
                "insured_is_self": True,
                "nominee_name": "Sita Sharma",
                "nominee_relationship": "Spouse",
                "nominee_contact": "9800000000",
            },
            format="json",
        )
        self.assertTrue(AuditLogEntry.objects.exists())
        self.assertFalse(
            AuditLogEntry.objects.filter(actor_role=User.Role.ADMIN).exists()
        )


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class HistoryReflectsLiveSelfServiceTests(APITestCase):
    """End to end: a customer buys, and the admin's timeline shows it."""

    def setUp(self):
        self.admin = make_staff(StaffRole.SYSTEM_OWNER)
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider(approved=True)
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()

    def test_a_fresh_purchase_appears_as_activity_and_in_the_audit_log(self):
        kyc = make_kyc(self.customer, status=CustomerKyc.Status.VERIFIED)
        self.client.force_authenticate(self.customer)
        bought = self.client.post(
            reverse("purchase-list"),
            {
                "policy": self.policy.id,
                "kyc": kyc.id,
                "insured_is_self": True,
                "nominee_name": "Sita Sharma",
                "nominee_relationship": "Spouse",
                "nominee_contact": "9800000000",
            },
            format="json",
        )
        self.assertEqual(bought.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.admin)
        timeline = self.client.get(
            reverse("admin-user-history", args=[self.customer.id])
        )
        self.assertEqual(timeline.status_code, status.HTTP_200_OK)
        purchase_rows = [
            row
            for row in timeline.data["results"]
            if row["ref_type"] == "PolicyPurchase"
        ]
        # One row, from the domain record — not two (the audit row is the
        # customer's own, so it is not listed again as an admin action).
        self.assertEqual(len(purchase_rows), 1)
        self.assertEqual(purchase_rows[0]["source"], "activity")
        self.assertEqual(purchase_rows[0]["ref_id"], str(bought.data["id"]))

        audit = self.client.get(reverse("staff-audit-log"))
        self.assertEqual(audit.status_code, status.HTTP_200_OK)
        self.assertIn(
            "purchase.create", {row["action"] for row in audit.data["results"]}
        )
