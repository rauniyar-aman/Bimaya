"""The Bimaya internal-staff RBAC catalog — roles and granular permissions.

This is *code*, not data: the 11 staff roles, the ~90 ``module.action``
permissions and the role→permission matrix all live here so the security policy
is reviewable in version control and cannot be edited at runtime into an unsafe
state. Only the *assignment* of a role to a person is stored in the database
(:class:`apps.staff.models.StaffRoleAssignment`).

The mapping is transcribed directly from the "Staff Roles & Granular
Permissions" specification: the permission catalog (§14), the per-role primary
permissions (§3–§13) and the role-to-permission access matrix (§15). The guiding
rule from that document is least privilege — a role is granted only the
permissions its job needs, and ``SYSTEM_OWNER`` is the sole role holding
everything.

Enforcement lives in :class:`apps.staff.permissions.HasStaffPermission`; the
platform's coarse ``User.role == ADMIN`` gate still applies on top (only staff
accounts reach these endpoints at all).
"""

from django.db import models


class StaffRole(models.TextChoices):
    """The internal job roles (spec §22). Distinct from ``User.role`` — every
    holder is a platform ``ADMIN`` user; this says *what kind* of staff."""

    SYSTEM_OWNER = "SYSTEM_OWNER", "System Owner"
    OPERATIONS_MANAGER = "OPERATIONS_MANAGER", "Operations Manager"
    CUSTOMER_SUPPORT = "CUSTOMER_SUPPORT", "Customer Support"
    KYC_COMPLIANCE_OFFICER = "KYC_COMPLIANCE_OFFICER", "KYC & Compliance Officer"
    POLICY_MODERATOR = "POLICY_MODERATOR", "Policy Moderator"
    PROVIDER_RELATIONS = "PROVIDER_RELATIONS", "Provider Relations"
    CLAIMS_OFFICER = "CLAIMS_OFFICER", "Claims Officer"
    FINANCE_OFFICER = "FINANCE_OFFICER", "Finance Officer"
    TECHNICAL_ADMIN = "TECHNICAL_ADMIN", "Technical Administrator"
    MARKETING_OFFICER = "MARKETING_OFFICER", "Marketing Officer"
    LEGAL_ADVISOR = "LEGAL_ADVISOR", "Legal / Regulatory Advisor"


class Perm:
    """The granular ``module.action`` permission catalog (spec §14).

    String constants, grouped by module, so views and the matrix below refer to
    them symbolically (``Perm.KYC_APPROVE``) rather than by raw string.
    """

    # Dashboard & reports
    DASHBOARD_VIEW = "dashboard.view"
    REPORT_VIEW = "report.view"
    REPORT_EXPORT = "report.export"
    ANALYTICS_VIEW = "analytics.view"

    # Staff & access
    STAFF_VIEW = "staff.view"
    STAFF_CREATE = "staff.create"
    STAFF_EDIT = "staff.edit"
    STAFF_ACTIVATE = "staff.activate"
    STAFF_DEACTIVATE = "staff.deactivate"
    ROLE_VIEW = "role.view"
    ROLE_CREATE = "role.create"
    ROLE_EDIT = "role.edit"
    ROLE_DELETE = "role.delete"
    PERMISSION_VIEW = "permission.view"
    PERMISSION_ASSIGN = "permission.assign"

    # Customers
    CUSTOMER_VIEW = "customer.view"
    CUSTOMER_VIEW_LIMITED = "customer.view_limited"
    CUSTOMER_CREATE = "customer.create"
    CUSTOMER_UPDATE = "customer.update"
    CUSTOMER_UPDATE_LIMITED = "customer.update_limited"
    CUSTOMER_SUSPEND = "customer.suspend"
    CUSTOMER_RESTORE = "customer.restore"

    # KYC & compliance
    KYC_VIEW = "kyc.view"
    KYC_APPROVE = "kyc.approve"
    KYC_REJECT = "kyc.reject"
    KYC_REQUEST_RESUBMISSION = "kyc.request_resubmission"
    KYC_DOCUMENT_VIEW = "kyc.document_view"
    PROVIDER_KYC_REVIEW = "provider.kyc_review"
    COMPLIANCE_RECORD_VIEW = "compliance.record_view"
    COMPLIANCE_RECORD_UPDATE = "compliance.record_update"

    # Providers
    PROVIDER_VIEW = "provider.view"
    PROVIDER_CREATE = "provider.create"
    PROVIDER_EDIT = "provider.edit"
    PROVIDER_ONBOARDING = "provider.onboarding"
    PROVIDER_APPROVE = "provider.approve"
    PROVIDER_SUSPEND = "provider.suspend"
    PROVIDER_RESTORE = "provider.restore"
    PROVIDER_DOCUMENT_VIEW_LIMITED = "provider.document_view_limited"
    PROVIDER_POLICY_MANAGE = "provider.policy_manage"
    PROVIDER_PERFORMANCE_VIEW = "provider.performance_view"
    PROVIDER_COMMUNICATION = "provider.communication"

    # Policies
    POLICY_VIEW = "policy.view"
    POLICY_CREATE = "policy.create"
    POLICY_EDIT = "policy.edit"
    POLICY_APPROVE = "policy.approve"
    POLICY_REJECT = "policy.reject"
    POLICY_REQUEST_CHANGES = "policy.request_changes"
    POLICY_SUSPEND = "policy.suspend"
    POLICY_RESTORE = "policy.restore"

    # Purchases
    PURCHASE_VIEW = "purchase.view"
    PURCHASE_CREATE_ADMIN = "purchase.create_admin"
    PURCHASE_MANAGE = "purchase.manage"
    PURCHASE_SUPPORT = "purchase.support"
    PURCHASE_CANCEL = "purchase.cancel"

    # Payments & transactions
    PAYMENT_VIEW = "payment.view"
    TRANSACTION_VIEW = "transaction.view"
    TRANSACTION_RECONCILE = "transaction.reconcile"
    PAYMENT_REFUND = "payment.refund"
    REFUND_VIEW = "refund.view"
    REFUND_MANAGE = "refund.manage"

    # Commissions & settlements
    COMMISSION_VIEW = "commission.view"
    COMMISSION_MANAGE = "commission.manage"
    SETTLEMENT_VIEW = "settlement.view"
    SETTLEMENT_MANAGE = "settlement.manage"

    # Claims
    CLAIM_VIEW = "claim.view"
    CLAIM_CREATE = "claim.create"
    CLAIM_UPDATE = "claim.update"
    CLAIM_ASSIGN = "claim.assign"
    CLAIM_REQUEST_DOCUMENT = "claim.request_document"
    CLAIM_STATUS_UPDATE = "claim.status_update"
    CLAIM_ESCALATE = "claim.escalate"
    CLAIM_CLOSE = "claim.close"

    # Documents
    DOCUMENT_VIEW = "document.view"
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_DOWNLOAD = "document.download"
    DOCUMENT_DELETE_RESTRICTED = "document.delete_restricted"

    # Notifications
    NOTIFICATION_VIEW = "notification.view"
    NOTIFICATION_CREATE = "notification.create"
    NOTIFICATION_MANAGE = "notification.manage"

    # Support
    SUPPORT_TICKET_VIEW = "support_ticket.view"
    SUPPORT_TICKET_CREATE = "support_ticket.create"
    SUPPORT_TICKET_MANAGE = "support_ticket.manage"
    SUPPORT_TICKET_ASSIGN = "support_ticket.assign"
    SUPPORT_TICKET_ESCALATE = "support_ticket.escalate"

    # Marketing
    MARKETING_VIEW = "marketing.view"
    MARKETING_CREATE = "marketing.create"
    MARKETING_EDIT = "marketing.edit"
    CAMPAIGN_MANAGE = "campaign.manage"
    PROMOTION_MANAGE = "promotion.manage"
    ANALYTICS_MARKETING_VIEW = "analytics.marketing_view"

    # Technical
    SYSTEM_VIEW = "system.view"
    SYSTEM_CONFIGURE = "system.configure"
    API_MANAGE = "api.manage"
    INTEGRATION_MANAGE = "integration.manage"
    SYSTEM_LOGS_VIEW = "system_logs.view"
    DEPLOYMENT_MANAGE = "deployment.manage"
    STORAGE_MANAGE = "storage.manage"
    TECHNICAL_INCIDENT_MANAGE = "technical_incident.manage"

    # Audit
    AUDIT_LOG_VIEW = "audit_log.view"
    AUDIT_LOG_EXPORT = "audit_log.export"

    # Legal
    LEGAL_DOCUMENT_VIEW = "legal.document.view"
    LEGAL_DOCUMENT_CREATE = "legal.document.create"
    LEGAL_DOCUMENT_EDIT = "legal.document.edit"
    LEGAL_CASE_VIEW = "legal.case.view"

    @classmethod
    def all(cls):
        """Every permission string in the catalog."""
        return frozenset(
            value
            for key, value in vars(cls).items()
            if key.isupper() and isinstance(value, str)
        )


# Every permission — the System Owner holds all of them (spec §3, "staff.* |
# role.* | ... | system.*").
ALL_PERMS = Perm.all()


# Role → permission sets. Transcribed from the per-role "Primary permissions"
# lists (§3–§13) and cross-checked against the access matrix (§15). Least
# privilege: each role gets only what its section grants.
ROLE_PERMISSIONS = {
    StaffRole.SYSTEM_OWNER.value: ALL_PERMS,
    # §4 Operations Manager — runs day-to-day operations across support, KYC,
    # policy review, claims and providers; no staff/role admin or tech config.
    StaffRole.OPERATIONS_MANAGER.value: frozenset(
        {
            Perm.DASHBOARD_VIEW,
            Perm.REPORT_VIEW,
            Perm.REPORT_EXPORT,
            Perm.ANALYTICS_VIEW,
            Perm.CUSTOMER_VIEW,
            Perm.CUSTOMER_UPDATE,
            Perm.CUSTOMER_SUSPEND,
            Perm.CUSTOMER_RESTORE,
            Perm.PURCHASE_VIEW,
            Perm.PURCHASE_MANAGE,
            Perm.PURCHASE_CANCEL,
            Perm.KYC_VIEW,
            Perm.KYC_APPROVE,
            Perm.KYC_REJECT,
            Perm.KYC_REQUEST_RESUBMISSION,
            Perm.CLAIM_VIEW,
            Perm.CLAIM_UPDATE,
            Perm.CLAIM_ASSIGN,
            Perm.CLAIM_STATUS_UPDATE,
            Perm.CLAIM_ESCALATE,
            Perm.CLAIM_CLOSE,
            Perm.PROVIDER_VIEW,
            Perm.PROVIDER_EDIT,
            Perm.PROVIDER_APPROVE,
            Perm.PROVIDER_SUSPEND,
            Perm.PROVIDER_RESTORE,
            Perm.POLICY_VIEW,
            Perm.PAYMENT_VIEW,
            Perm.TRANSACTION_VIEW,
            Perm.COMMISSION_VIEW,
            Perm.NOTIFICATION_VIEW,
            Perm.NOTIFICATION_CREATE,
            Perm.NOTIFICATION_MANAGE,
            Perm.SUPPORT_TICKET_VIEW,
            Perm.SUPPORT_TICKET_MANAGE,
            Perm.SUPPORT_TICKET_ASSIGN,
            Perm.SUPPORT_TICKET_ESCALATE,
            Perm.AUDIT_LOG_VIEW,
        }
    ),
    # §5 Customer Support — inquiries, tickets, limited customer edits; minimal
    # KYC; no finance/staff/role/system admin.
    StaffRole.CUSTOMER_SUPPORT.value: frozenset(
        {
            Perm.DASHBOARD_VIEW,
            Perm.CUSTOMER_VIEW,
            Perm.CUSTOMER_UPDATE_LIMITED,
            Perm.PURCHASE_VIEW,
            Perm.PURCHASE_SUPPORT,
            Perm.POLICY_VIEW,
            Perm.CLAIM_VIEW,
            Perm.NOTIFICATION_CREATE,
            Perm.SUPPORT_TICKET_VIEW,
            Perm.SUPPORT_TICKET_CREATE,
            Perm.SUPPORT_TICKET_MANAGE,
        }
    ),
    # §6 KYC & Compliance — reviews customer KYC and provider compliance docs;
    # no payment/refund/settlement admin. KYC access is audited.
    StaffRole.KYC_COMPLIANCE_OFFICER.value: frozenset(
        {
            Perm.DASHBOARD_VIEW,
            Perm.CUSTOMER_VIEW_LIMITED,
            Perm.KYC_VIEW,
            Perm.KYC_APPROVE,
            Perm.KYC_REJECT,
            Perm.KYC_REQUEST_RESUBMISSION,
            Perm.KYC_DOCUMENT_VIEW,
            Perm.PROVIDER_VIEW,
            Perm.PROVIDER_KYC_REVIEW,
            Perm.COMPLIANCE_RECORD_VIEW,
            Perm.COMPLIANCE_RECORD_UPDATE,
            Perm.AUDIT_LOG_VIEW,
        }
    ),
    # §7 Policy Moderator — reviews policy listings; no customer financial
    # access, no unrestricted KYC.
    StaffRole.POLICY_MODERATOR.value: frozenset(
        {
            Perm.DASHBOARD_VIEW,
            Perm.POLICY_VIEW,
            Perm.POLICY_CREATE,
            Perm.POLICY_EDIT,
            Perm.POLICY_APPROVE,
            Perm.POLICY_REJECT,
            Perm.POLICY_REQUEST_CHANGES,
            Perm.POLICY_SUSPEND,
            Perm.POLICY_RESTORE,
            Perm.PROVIDER_VIEW,
        }
    ),
    # §8 Provider Relations / Business Development — onboards and manages
    # providers; commission changes are restricted (not granted here).
    StaffRole.PROVIDER_RELATIONS.value: frozenset(
        {
            Perm.DASHBOARD_VIEW,
            Perm.PROVIDER_VIEW,
            Perm.PROVIDER_CREATE,
            Perm.PROVIDER_EDIT,
            Perm.PROVIDER_ONBOARDING,
            Perm.PROVIDER_DOCUMENT_VIEW_LIMITED,
            Perm.PROVIDER_POLICY_MANAGE,
            Perm.PROVIDER_PERFORMANCE_VIEW,
            Perm.PROVIDER_COMMUNICATION,
            Perm.POLICY_VIEW,
        }
    ),
    # §9 Claims Officer — intake, tracking and coordination of claims; no
    # unrestricted financial or KYC admin.
    StaffRole.CLAIMS_OFFICER.value: frozenset(
        {
            Perm.DASHBOARD_VIEW,
            Perm.CLAIM_VIEW,
            Perm.CLAIM_CREATE,
            Perm.CLAIM_UPDATE,
            Perm.CLAIM_ASSIGN,
            Perm.CLAIM_REQUEST_DOCUMENT,
            Perm.CLAIM_STATUS_UPDATE,
            Perm.CLAIM_ESCALATE,
            Perm.CLAIM_CLOSE,
            Perm.CUSTOMER_VIEW_LIMITED,
            Perm.PROVIDER_VIEW,
            Perm.POLICY_VIEW,
        }
    ),
    # §10 Finance Officer — reconciles payments, commissions and settlements; no
    # KYC-document access, no staff/role admin.
    StaffRole.FINANCE_OFFICER.value: frozenset(
        {
            Perm.DASHBOARD_VIEW,
            Perm.PAYMENT_VIEW,
            Perm.TRANSACTION_VIEW,
            Perm.TRANSACTION_RECONCILE,
            Perm.REFUND_VIEW,
            Perm.REFUND_MANAGE,
            Perm.PAYMENT_REFUND,
            Perm.COMMISSION_VIEW,
            Perm.COMMISSION_MANAGE,
            Perm.SETTLEMENT_VIEW,
            Perm.SETTLEMENT_MANAGE,
            Perm.REPORT_VIEW,
        }
    ),
    # §11 Technical Administrator — application/infra/integrations; no KYC
    # approval, commission admin or claim approval.
    StaffRole.TECHNICAL_ADMIN.value: frozenset(
        {
            Perm.SYSTEM_VIEW,
            Perm.SYSTEM_CONFIGURE,
            Perm.API_MANAGE,
            Perm.INTEGRATION_MANAGE,
            Perm.SYSTEM_LOGS_VIEW,
            Perm.DEPLOYMENT_MANAGE,
            Perm.STORAGE_MANAGE,
            Perm.TECHNICAL_INCIDENT_MANAGE,
            Perm.AUDIT_LOG_VIEW,
        }
    ),
    # §12 Marketing & Growth — campaigns, promotions, marketing analytics;
    # customer analytics limited/aggregated; no KYC/claim/payment/staff admin.
    StaffRole.MARKETING_OFFICER.value: frozenset(
        {
            Perm.DASHBOARD_VIEW,
            Perm.MARKETING_VIEW,
            Perm.MARKETING_CREATE,
            Perm.MARKETING_EDIT,
            Perm.CAMPAIGN_MANAGE,
            Perm.PROMOTION_MANAGE,
            Perm.ANALYTICS_MARKETING_VIEW,
            Perm.POLICY_VIEW,
            Perm.PROVIDER_VIEW,
        }
    ),
    # §13 Legal / Regulatory Advisor — highly restricted, read-oriented.
    StaffRole.LEGAL_ADVISOR.value: frozenset(
        {
            Perm.LEGAL_DOCUMENT_VIEW,
            Perm.LEGAL_DOCUMENT_CREATE,
            Perm.LEGAL_DOCUMENT_EDIT,
            Perm.LEGAL_CASE_VIEW,
            Perm.COMPLIANCE_RECORD_VIEW,
        }
    ),
}


def permissions_for(role_values):
    """The union of permissions granted by the given staff-role values."""
    granted = set()
    for role in role_values:
        granted |= ROLE_PERMISSIONS.get(role, frozenset())
    return granted
