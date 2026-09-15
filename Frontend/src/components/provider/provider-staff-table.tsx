"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { useProviderPortal } from "@/components/provider/provider-portal";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { PasswordInput } from "@/components/ui/password-input";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { PlusIcon } from "@/components/icons";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  api,
  errorMessage,
  fieldErrors,
  type AssignableProviderRole,
  type ProviderRoleInfo,
  type ProviderTeamMember,
} from "@/lib/api";
import { formatDate } from "@/lib/date";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; members: ProviderTeamMember[] };

type Pending = { member: ProviderTeamMember; action: "disable" | "enable" };

/**
 * The provider portal's own team console: list the people in the signed-in
 * user's organisation, add a member with a scoped role, change roles, and
 * enable / disable them. Gated by the caller's org permissions — `staff.view`
 * to see it, `staff.manage` to act — but the backend authorises (and audits)
 * every request itself. The owner is a synthetic, non-editable row.
 */
export function ProviderStaffTable() {
  const { authFetch, user } = useAuth();
  const { permissions } = useProviderPortal();
  const canManage = permissions.includes("staff.manage");

  const [state, setState] = useState<State>({ phase: "loading" });
  const [roles, setRoles] = useState<ProviderRoleInfo[] | null>(null);

  const [creating, setCreating] = useState(false);
  // Remount the create form on each open so it always starts clean.
  const [createSeq, setCreateSeq] = useState(0);

  // Per-row role change.
  const [busyId, setBusyId] = useState<number | null>(null);
  const [rowError, setRowError] = useState("");

  // Enable / disable confirmation.
  const [pending, setPending] = useState<Pending | null>(null);
  const [working, setWorking] = useState(false);
  const [actionError, setActionError] = useState("");

  const canView = permissions.includes("staff.view");

  // The assignable-roles catalog backs the create / change-role pickers. It is
  // code-defined and static, so load it once (any staff.view holder can read it).
  useEffect(() => {
    if (!canView) return;
    let cancelled = false;
    api.provider
      .listRoles(authFetch)
      .then((catalog) => {
        if (!cancelled) setRoles(catalog.roles);
      })
      .catch(() => {
        if (!cancelled) setRoles([]);
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, canView]);

  useEffect(() => {
    if (!canView) return;
    let cancelled = false;
    api.provider
      .listMembers(authFetch)
      .then((members) => {
        if (!cancelled) setState({ phase: "ready", members });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, canView]);

  function upsertMember(updated: ProviderTeamMember) {
    setState((prev) =>
      prev.phase === "ready"
        ? {
            phase: "ready",
            members: prev.members.some((m) => m.user_id === updated.user_id)
              ? prev.members.map((m) =>
                  m.user_id === updated.user_id ? updated : m,
                )
              : [...prev.members, updated],
          }
        : prev,
    );
  }

  async function changeRole(
    member: ProviderTeamMember,
    next: AssignableProviderRole,
  ) {
    if (member.membership_id === null || member.role.value === next) return;
    setBusyId(member.user_id);
    setRowError("");
    try {
      const updated = await api.provider.setMemberRole(
        authFetch,
        member.membership_id,
        next,
      );
      upsertMember(updated);
    } catch (error) {
      setRowError(errorMessage(error, "Could not change this member's role."));
    } finally {
      setBusyId(null);
    }
  }

  async function confirm() {
    if (!pending || pending.member.membership_id === null) return;
    setWorking(true);
    setActionError("");
    try {
      const updated =
        pending.action === "disable"
          ? await api.provider.disableMember(authFetch, pending.member.membership_id)
          : await api.provider.enableMember(authFetch, pending.member.membership_id);
      upsertMember(updated);
      setPending(null);
    } catch (error) {
      setActionError(errorMessage(error, "Could not update this team member."));
    } finally {
      setWorking(false);
    }
  }

  if (!canView) {
    return (
      <Alert variant="error">
        You do not have access to team management for this organisation.
      </Alert>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold text-ink sm:text-2xl">
            Team
          </h1>
          <p className="mt-1 text-sm text-muted">
            People in your organisation and what each can do. Roles decide which
            parts of the provider area a member can use.
          </p>
        </div>
        {canManage && (
          <Button
            className="shrink-0"
            onClick={() => {
              setCreateSeq((s) => s + 1);
              setCreating(true);
            }}
          >
            <PlusIcon className="h-4 w-4" />
            Add member
          </Button>
        )}
      </div>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error">
          We could not load your team. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && (
        <>
          {rowError && <Alert variant="error">{rowError}</Alert>}

          <Table>
            <THead>
              <TR>
                <TH>Member</TH>
                <TH>Role</TH>
                <TH>Status</TH>
                <TH className="text-right">Action</TH>
              </TR>
            </THead>
            <TBody>
              {state.members.map((member) => {
                const isOwner = member.membership_id === null;
                const isSelf = member.user_id === user?.id;
                const busy = busyId === member.user_id;
                return (
                  <TR key={member.user_id}>
                    <TD>
                      <div className="font-medium text-ink">
                        {member.full_name || "—"}
                        {isSelf && (
                          <span className="ml-2 text-xs font-normal text-muted">
                            (you)
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-muted">{member.email}</div>
                      <div className="text-xs text-muted">
                        Joined {formatDate(member.date_joined)}
                      </div>
                    </TD>
                    <TD>
                      {isOwner || !canManage || roles === null ? (
                        <StatusPill status={isOwner ? "active" : "info"}>
                          {member.role.label}
                        </StatusPill>
                      ) : (
                        <Select
                          value={member.role.value}
                          onChange={(e) =>
                            changeRole(
                              member,
                              e.target.value as AssignableProviderRole,
                            )
                          }
                          disabled={busy}
                          className="w-52"
                          aria-label={`Role for ${member.email}`}
                        >
                          {roles.map((role) => (
                            <option key={role.value} value={role.value}>
                              {role.label}
                            </option>
                          ))}
                        </Select>
                      )}
                    </TD>
                    <TD>
                      {isOwner ? (
                        <span className="text-xs text-muted">
                          Signs in as the organisation
                        </span>
                      ) : member.is_active ? (
                        <StatusPill status="active">Active</StatusPill>
                      ) : (
                        <StatusPill status="failed">Disabled</StatusPill>
                      )}
                    </TD>
                    <TD className="text-right">
                      {isOwner || !canManage || isSelf ? (
                        <span className="text-xs text-muted">—</span>
                      ) : member.is_active ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={busy}
                          onClick={() => {
                            setActionError("");
                            setPending({ member, action: "disable" });
                          }}
                        >
                          Disable
                        </Button>
                      ) : (
                        <Button
                          variant="success"
                          size="sm"
                          disabled={busy}
                          onClick={() => {
                            setActionError("");
                            setPending({ member, action: "enable" });
                          }}
                        >
                          Enable
                        </Button>
                      )}
                    </TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>
        </>
      )}

      <AddMemberModal
        key={createSeq}
        open={creating}
        roles={roles}
        onClose={() => setCreating(false)}
        onCreated={(member) => {
          upsertMember(member);
          setCreating(false);
        }}
      />

      <Modal
        open={pending !== null}
        onClose={() => (working ? undefined : setPending(null))}
        title={pending?.action === "disable" ? "Disable member" : "Enable member"}
      >
        {pending && (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              {pending.action === "disable" ? (
                <>
                  Disable{" "}
                  <strong className="text-ink">
                    {pending.member.full_name || pending.member.email}
                  </strong>
                  ? They will be signed out and cannot sign in again until you
                  re-enable them.
                </>
              ) : (
                <>
                  Enable{" "}
                  <strong className="text-ink">
                    {pending.member.full_name || pending.member.email}
                  </strong>
                  ? They will be able to sign in again.
                </>
              )}
            </p>
            {actionError && <Alert variant="error">{actionError}</Alert>}
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => setPending(null)}
                disabled={working}
              >
                Cancel
              </Button>
              <Button
                variant={pending.action === "disable" ? "primary" : "success"}
                onClick={confirm}
                loading={working}
              >
                {pending.action === "disable" ? "Disable" : "Enable"}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

function AddMemberModal({
  open,
  roles,
  onClose,
  onCreated,
}: {
  open: boolean;
  roles: ProviderRoleInfo[] | null;
  onClose: () => void;
  onCreated: (member: ProviderTeamMember) => void;
}) {
  const { authFetch } = useAuth();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<AssignableProviderRole | "">("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const selectedRole = roles?.find((r) => r.value === role) ?? null;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    if (!role) {
      setErrors({ role: "Choose a role for this member." });
      return;
    }
    setSaving(true);
    try {
      const member = await api.provider.createMember(authFetch, {
        email: email.trim(),
        full_name: fullName.trim(),
        password,
        role,
      });
      onCreated(member);
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(errorMessage(error, "Could not add this team member."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add a team member" className="max-w-xl">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <p className="text-sm text-muted">
          Creates a verified account for your organisation with a temporary
          password. Share it securely; they sign in with the normal email + code
          flow and change it from their profile.
        </p>
        {formError && <Alert variant="error">{formError}</Alert>}

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Email" htmlFor="member_email" error={errors.email} required>
            <Input
              id="member_email"
              type="email"
              inputMode="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="teammate@example.com.np"
              aria-invalid={Boolean(errors.email)}
            />
          </Field>

          <Field label="Full name" htmlFor="member_name" error={errors.full_name}>
            <Input
              id="member_name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Sita Sharma"
              aria-invalid={Boolean(errors.full_name)}
            />
          </Field>
        </div>

        <Field
          label="Temporary password"
          htmlFor="member_password"
          error={errors.password}
          hint="At least 8 characters. Share it with them securely."
          required
        >
          <PasswordInput
            id="member_password"
            autoComplete="off"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={Boolean(errors.password)}
          />
        </Field>

        <Field label="Role" htmlFor="member_role" error={errors.role} required>
          {roles === null ? (
            <div className="flex items-center justify-center py-6">
              <Spinner className="h-5 w-5 text-brand-500" />
            </div>
          ) : roles.length === 0 ? (
            <Alert variant="error">Could not load roles. Please close and retry.</Alert>
          ) : (
            <>
              <Select
                id="member_role"
                value={role}
                onChange={(e) => setRole(e.target.value as AssignableProviderRole)}
                aria-invalid={Boolean(errors.role)}
              >
                <option value="" disabled>
                  Choose a role…
                </option>
                {roles.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
              {selectedRole && (
                <p className="mt-1.5 text-xs text-muted">
                  Grants {selectedRole.permission_count} permission
                  {selectedRole.permission_count === 1 ? "" : "s"} across the
                  provider area.
                </p>
              )}
            </>
          )}
        </Field>

        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" loading={saving} disabled={roles === null}>
            Add member
          </Button>
        </div>
      </form>
    </Modal>
  );
}
