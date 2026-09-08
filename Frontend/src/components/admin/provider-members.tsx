"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  api,
  errorMessage,
  fieldErrors,
  type AdminProvider,
  type ProviderMember,
  type ProviderRole,
} from "@/lib/api";
import { formatDate } from "@/lib/date";

const ROLE_META: Record<
  ProviderRole,
  { variant: "active" | "info" | "pending"; label: string }
> = {
  OWNER: { variant: "active", label: "Owner" },
  STAFF: { variant: "info", label: "Staff" },
  VIEWER: { variant: "pending", label: "Viewer" },
};

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; members: ProviderMember[] };

/**
 * Admin dialog to manage a provider organisation's team: the read-only owner
 * plus staff/viewers who can be added, re-roled, or removed. Opened from a row
 * in {@link ProviderApprovals} so no dedicated route is needed.
 */
export function ProviderMembersModal({
  provider,
  open,
  onClose,
}: {
  provider: AdminProvider;
  open: boolean;
  onClose: () => void;
}) {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });

  // Add-member form.
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"STAFF" | "VIEWER">("STAFF");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [adding, setAdding] = useState(false);

  // Per-row action tracking (change role / remove).
  const [busyId, setBusyId] = useState<number | null>(null);
  const [rowError, setRowError] = useState("");
  const [removing, setRemoving] = useState<ProviderMember | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    api.admin
      .listProviderMembers(authFetch, provider.id)
      .then((members) => {
        if (!cancelled) setState({ phase: "ready", members });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, provider.id, open]);

  function upsertMember(updated: ProviderMember) {
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

  function dropMember(membershipId: number) {
    setState((prev) =>
      prev.phase === "ready"
        ? {
            phase: "ready",
            members: prev.members.filter((m) => m.membership_id !== membershipId),
          }
        : prev,
    );
  }

  async function handleAdd(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    setAdding(true);
    try {
      const member = await api.admin.addProviderMember(authFetch, provider.id, {
        email: email.trim(),
        full_name: fullName.trim(),
        password,
        role,
      });
      upsertMember(member);
      setEmail("");
      setFullName("");
      setPassword("");
      setRole("STAFF");
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(errorMessage(error, "Could not add this team member."));
    } finally {
      setAdding(false);
    }
  }

  async function changeRole(member: ProviderMember, next: "STAFF" | "VIEWER") {
    if (member.membership_id === null || member.role === next) return;
    setBusyId(member.user_id);
    setRowError("");
    try {
      const updated = await api.admin.updateProviderMemberRole(
        authFetch,
        provider.id,
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

  async function confirmRemove() {
    if (!removing || removing.membership_id === null) return;
    const membershipId = removing.membership_id;
    setBusyId(removing.user_id);
    setRowError("");
    try {
      await api.admin.removeProviderMember(authFetch, provider.id, membershipId);
      dropMember(membershipId);
      setRemoving(null);
    } catch (error) {
      setRowError(errorMessage(error, "Could not remove this member."));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <Modal
        open={open}
        onClose={onClose}
        title={`Team — ${provider.company_name}`}
        className="max-w-2xl"
      >
        <div className="space-y-5">
          <p className="text-sm text-muted">
            The owner signs in as the organisation and cannot be changed here.
            Staff can manage policies, issuance, and claims; viewers have
            read-only access.
          </p>

          {state.phase === "loading" && (
            <div className="flex items-center justify-center py-10">
              <Spinner className="h-6 w-6 text-brand-500" />
            </div>
          )}

          {state.phase === "error" && (
            <Alert variant="error">
              We could not load this team. Please close and try again.
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
                    <TH className="text-right">Action</TH>
                  </TR>
                </THead>
                <TBody>
                  {state.members.map((member) => {
                    const meta = ROLE_META[member.role];
                    const isOwner = member.membership_id === null;
                    const busy = busyId === member.user_id;
                    return (
                      <TR key={member.user_id}>
                        <TD>
                          <div className="font-medium text-ink">
                            {member.full_name || "—"}
                            {!member.is_active && (
                              <span className="ml-2 text-xs font-normal text-muted">
                                (deactivated)
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-muted">{member.email}</div>
                          <div className="text-xs text-muted">
                            Joined {formatDate(member.date_joined)}
                          </div>
                        </TD>
                        <TD>
                          {isOwner ? (
                            <StatusPill status={meta.variant}>
                              {meta.label}
                            </StatusPill>
                          ) : (
                            <Select
                              value={member.role}
                              onChange={(e) =>
                                changeRole(
                                  member,
                                  e.target.value as "STAFF" | "VIEWER",
                                )
                              }
                              disabled={busy}
                              className="w-32"
                              aria-label={`Role for ${member.email}`}
                            >
                              <option value="STAFF">Staff</option>
                              <option value="VIEWER">Viewer</option>
                            </Select>
                          )}
                        </TD>
                        <TD className="text-right">
                          {isOwner ? (
                            <span className="text-xs text-muted">—</span>
                          ) : (
                            <Button
                              variant="secondary"
                              size="sm"
                              disabled={busy}
                              onClick={() => {
                                setRowError("");
                                setRemoving(member);
                              }}
                            >
                              Remove
                            </Button>
                          )}
                        </TD>
                      </TR>
                    );
                  })}
                </TBody>
              </Table>

              <form
                onSubmit={handleAdd}
                className="space-y-4 rounded-2xl border border-line bg-surface/50 p-4"
                noValidate
              >
                <h3 className="font-display text-sm font-semibold text-ink">
                  Add a team member
                </h3>
                {formError && <Alert variant="error">{formError}</Alert>}

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field
                    label="Email"
                    htmlFor="member_email"
                    error={errors.email}
                    required
                  >
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

                  <Field
                    label="Full name"
                    htmlFor="member_name"
                    error={errors.full_name}
                  >
                    <Input
                      id="member_name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Sita Sharma"
                      aria-invalid={Boolean(errors.full_name)}
                    />
                  </Field>

                  <Field
                    label="Temporary password"
                    htmlFor="member_password"
                    error={errors.password}
                    hint="At least 8 characters. Share it with them securely."
                    required
                  >
                    <Input
                      id="member_password"
                      type="text"
                      autoComplete="off"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      aria-invalid={Boolean(errors.password)}
                    />
                  </Field>

                  <Field label="Role" htmlFor="member_role" error={errors.role}>
                    <Select
                      id="member_role"
                      value={role}
                      onChange={(e) =>
                        setRole(e.target.value as "STAFF" | "VIEWER")
                      }
                    >
                      <option value="STAFF">Staff — can manage</option>
                      <option value="VIEWER">Viewer — read-only</option>
                    </Select>
                  </Field>
                </div>

                <Button type="submit" loading={adding}>
                  Add member
                </Button>
              </form>
            </>
          )}
        </div>
      </Modal>

      <Modal
        open={removing !== null}
        onClose={() => (busyId !== null ? undefined : setRemoving(null))}
        title="Remove team member"
      >
        {removing && (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Remove{" "}
              <strong className="text-ink">
                {removing.full_name || removing.email}
              </strong>{" "}
              from {provider.company_name}? Their access is revoked and their
              account is deactivated. This does not delete records they created.
            </p>
            {rowError && <Alert variant="error">{rowError}</Alert>}
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => setRemoving(null)}
                disabled={busyId !== null}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={confirmRemove}
                loading={busyId !== null}
              >
                Remove
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
