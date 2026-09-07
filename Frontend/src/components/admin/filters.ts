/**
 * Dropdown filter option lists for the admin tables. Each list starts with an
 * "all" option whose value is the empty string, matching the `Select` state
 * convention used across the admin components.
 */

export const PROVIDER_FILTERS = [
  { value: "", label: "All providers" },
  { value: "false", label: "Awaiting approval" },
  { value: "true", label: "Approved" },
];

export const KYC_FILTERS = [
  { value: "", label: "All KYC" },
  { value: "PENDING", label: "Pending" },
  { value: "VERIFIED", label: "Verified" },
  { value: "REJECTED", label: "Rejected" },
];

export const PURCHASE_FILTERS = [
  { value: "", label: "All purchases" },
  { value: "PENDING_PAYMENT", label: "Pending payment" },
  { value: "PAID", label: "Paid — awaiting review" },
  { value: "FORWARDED", label: "With provider" },
  { value: "ACTIVE", label: "Active" },
  { value: "EXPIRED", label: "Expired" },
  { value: "CANCELLED", label: "Cancelled" },
];

export const ROLE_FILTERS = [
  { value: "", label: "All roles" },
  { value: "CUSTOMER", label: "Customers" },
  { value: "PROVIDER", label: "Providers" },
  { value: "ADMIN", label: "Admins" },
];

export const POLICY_FILTERS = [
  { value: "", label: "All statuses" },
  { value: "DRAFT", label: "Draft" },
  { value: "PENDING", label: "Pending review" },
  { value: "APPROVED", label: "Approved" },
  { value: "INACTIVE", label: "Inactive" },
];
