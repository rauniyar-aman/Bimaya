"""End-to-end enforcement: admin endpoints require the right granular role.

Complements ``apps.adminpanel.tests`` (which drives every endpoint as a fully
empowered System Owner). Here we assert the *boundary*: an administrator holding
a narrow staff role reaches only the endpoints their role covers, and a
sensitive action writes an immutable audit entry.
"""

import io
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import CustomerKyc
from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import Provider
from apps.staff.models import AuditLogEntry, StaffRoleAssignment
from apps.staff.rbac import StaffRole

User = get_user_model()

_MEDIA_ROOT = tempfile.mkdtemp(prefix="bimaya-staff-tests-")


def tearDownModule():
    shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)


def make_admin(email, *roles):
    user = User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.ADMIN, is_verified=True
    )
    for role in roles:
        StaffRoleAssignment.objects.create(user=user, role=role)
    return user


def make_image(name="doc.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class StaffEnforcementTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        prov_user = User.objects.create_user(
            email="prov@bimaya.test",
            password="Himalaya#2026",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        self.provider = Provider.objects.create(
            user=prov_user, company_name="Everest Life", is_approved=False
        )

    # --- role scoping -------------------------------------------------------

    def test_finance_officer_cannot_approve_a_provider(self):
        finance = make_admin("finance@bimaya.test", StaffRole.FINANCE_OFFICER.value)
        self.client.force_authenticate(finance)
        response = self.client.post(
            reverse("admin-provider-approve", args=[self.provider.id])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.provider.refresh_from_db()
        self.assertFalse(self.provider.is_approved)

    def test_operations_manager_can_approve_a_provider(self):
        ops = make_admin("ops@bimaya.test", StaffRole.OPERATIONS_MANAGER.value)
        self.client.force_authenticate(ops)
        response = self.client.post(
            reverse("admin-provider-approve", args=[self.provider.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.provider.refresh_from_db()
        self.assertTrue(self.provider.is_approved)

    def test_policy_moderator_cannot_set_commission(self):
        moderator = make_admin("mod@bimaya.test", StaffRole.POLICY_MODERATOR.value)
        self.client.force_authenticate(moderator)
        response = self.client.post(
            reverse("admin-provider-commission", args=[self.provider.id]),
            {"commission_rate": "12.50"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_finance_officer_can_set_commission(self):
        finance = make_admin("finance@bimaya.test", StaffRole.FINANCE_OFFICER.value)
        self.client.force_authenticate(finance)
        response = self.client.post(
            reverse("admin-provider-commission", args=[self.provider.id]),
            {"commission_rate": "12.50"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_marketing_officer_cannot_list_kyc(self):
        marketing = make_admin("mkt@bimaya.test", StaffRole.MARKETING_OFFICER.value)
        self.client.force_authenticate(marketing)
        response = self.client.get(reverse("admin-kyc-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_kyc_officer_can_list_kyc(self):
        officer = make_admin("kyc@bimaya.test", StaffRole.KYC_COMPLIANCE_OFFICER.value)
        self.client.force_authenticate(officer)
        response = self.client.get(reverse("admin-kyc-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_kyc_officer_without_document_permission_is_covered_by_role(self):
        # The KYC officer role *does* include document view; a support agent
        # (which does not even list KYC) must not reach the document endpoint.
        support = make_admin("support@bimaya.test", StaffRole.CUSTOMER_SUPPORT.value)
        customer = User.objects.create_user(
            email="cust@bimaya.test", password="Himalaya#2026", is_verified=True
        )
        kyc = CustomerKyc.objects.create(
            customer=customer,
            is_self=True,
            full_name="Sita Sharma",
            permanent_address="Kathmandu",
            document_type=CustomerKyc.DocumentType.NID,
            document_number="NID-1",
            document_front=make_image("front.png"),
        )
        self.client.force_authenticate(support)
        response = self.client.get(
            reverse("admin-kyc-document-front", args=[kyc.id])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- audit trail --------------------------------------------------------

    def test_provider_approval_writes_one_audit_entry(self):
        ops = make_admin("ops@bimaya.test", StaffRole.OPERATIONS_MANAGER.value)
        self.client.force_authenticate(ops)
        self.client.post(reverse("admin-provider-approve", args=[self.provider.id]))
        entries = AuditLogEntry.objects.filter(
            action="provider.approve", entity_id=str(self.provider.id)
        )
        self.assertEqual(entries.count(), 1)
        entry = entries.first()
        self.assertEqual(entry.actor, ops)
        self.assertEqual(entry.actor_role, User.Role.ADMIN)
        self.assertEqual(entry.entity_type, "Provider")

    def test_commission_change_is_audited(self):
        finance = make_admin("finance@bimaya.test", StaffRole.FINANCE_OFFICER.value)
        self.client.force_authenticate(finance)
        self.client.post(
            reverse("admin-provider-commission", args=[self.provider.id]),
            {"commission_rate": "9.00"},
            format="json",
        )
        self.assertTrue(
            AuditLogEntry.objects.filter(
                action="commission.manage",
                entity_type="Provider",
                entity_id=str(self.provider.id),
            ).exists()
        )
