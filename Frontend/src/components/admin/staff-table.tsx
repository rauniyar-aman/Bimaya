"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { STAFF_FILTERS } from "@/components/admin/filters";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { PasswordInput } from "@/components/ui/password-input";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { PlusIcon, SearchIcon } from "@/components/icons";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  api,
  errorMessage,
  fieldErrors,
  type Paginated,
  type RoleInfo,
  type StaffMember,
  type StaffRoleValue,
} from "@/lib/api";
import { formatDate } from "@/lib/date";
import { useDebouncedValue } from "@/lib/use-debounced-value";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; data: Paginated<StaffMember> };

type Pending = { member: StaffMember; action: "disable" | "enable" };

/**
 * The internal-staff console: list staff accounts, create one with a temporary
 * password, assign their coded roles, and enable / disable them. Every action
 * here is authorised (and audited) by the backend — this is the System Owner's
 * management surface for the RBAC engine.
 */
export function StaffTable() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [roles, setRoles] = useState<RoleInfo[] | null>(null);
  const [page, setPage] = useState(1);
  const [active, setActive] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  // Bumped after a create so the list refetches even when the filters are
  // already at their defaults (which would not otherwise change the effect deps).
  const [reloadKey, setReloadKey] = useState(0);

  const [creating, setCreating] = useState(false);
  // Remount the create form on each open (via key) so it always starts clean.
  const [createSeq, setCreateSeq] = useState(0);
  const [managing, setManaging] = useState<StaffMember | null>(null);

  const [pending, setPending] = useState<Pending | null>(null);
  const [working, setWorking] = useState(false);
  const [actionError, setActionError] = useState("");

  // The roles catalog backs the create / manage pickers. It is code-defined and
  // static, so load it once (any staff.view holder also holds role.view).
  useEffect(() => {
    let cancelled = false;
    api.admin
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
  }, [authFetch]);

  useEffect(() => {
    let cancelled = false;
    api.admin
      .listStaff(authFetch, {
        page,
        is_active: active === "" ? undefined : active === "true",
        search: debouncedSearch || undefined,
      })
      .then((data) => {
        if (!cancelled) setState({ phase: "ready", data });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, page, active, debouncedSearch, reloadKey]);

  function updateRow(updated: StaffMember) {
    setState((prev) =>
      prev.phase === "ready"
        ? {
            phase: "ready",
            data: {
              ...prev.data,
              results: prev.data.results.map((s) =>
                s.id === updated.id ? updated : s,
              ),
            },
          }
        : prev,
    );
  }

  async function confirm() {
    if (!pending) return;
    setWorking(true);
    setActionError("");
    try {
      const updated =
        pending.action === "disable"
          ? await api.admin.disableStaff(authFetch, pending.member.id)
          : await api.admin.enableStaff(authFetch, pending.member.id);
      updateRow(updated);
      setPending(null);
    } catch (error) {
      setActionError(errorMessage(error, "Could not update this staff account."));
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="font-display text-xl font-semibold text-ink">Staff</h2>
        <div className="flex gap-2">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
              placeholder="Search name or email"
              className="w-56 pl-9"
              aria-label="Search staff"
            />
          </div>
          <Select
            value={active}
            onChange={(e) => {
              setPage(1);
              setActive(e.target.value);
            }}
            className="w-36"
            aria-label="Filter by status"
          >
            {STAFF_FILTERS.map((o) => (
              <option key={o.label} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
          <Button
            onClick={() => {
              setCreateSeq((s) => s + 1);
              setCreating(true);
            }}
          >
            <PlusIcon className="h-4 w-4" />
            Add staff
          </Button>
        </div>
      </div>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error">
          We could not load staff accounts. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.data.results.length === 0 && (
        <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center text-sm text-muted">
          No staff accounts match your filters.
        </div>
      )}

      {state.phase === "ready" && state.data.results.length > 0 && (
        <>
          <Table>
            <THead>
              <TR>
                <TH>Staff member</TH>
                <TH>Roles</TH>
                <TH>Status</TH>
                <TH>Joined</TH>
                <TH className="text-right">Action</TH>
              </TR>
            </THead>
            <TBody>
              {state.data.results.map((s) => (
                <TR key={s.id}>
                  <TD>
                    <div className="font-medium text-ink">{s.full_name || "—"}</div>
                    <div className="text-xs text-muted">{s.email}</div>
                  </TD>
                  <TD>
                    <div className="flex max-w-xs flex-wrap gap-1">
                      {s.roles.length === 0 ? (
                        <span className="text-xs text-muted">No roles</span>
                      ) : (
                        s.roles.map((r) => (
                          <StatusPill key={r.value} status="info">
                            {r.label}
                          </StatusPill>
                        ))
                      )}
                    </div>
                  </TD>
                  <TD>
                    {s.is_active ? (
                      <StatusPill status="active">Active</StatusPill>
                    ) : (
                      <StatusPill status="failed">Disabled</StatusPill>
                    )}
                  </TD>
                  <TD className="text-muted">{formatDate(s.date_joined)}</TD>
                  <TD className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setManaging(s)}
                      >
                        Manage roles
                      </Button>
                      {s.is_active ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            setActionError("");
                            setPending({ member: s, action: "disable" });
                          }}
                        >
                          Disable
                        </Button>
                      ) : (
                        <Button
                          variant="success"
                          size="sm"
                          onClick={() => {
                            setActionError("");
                            setPending({ member: s, action: "enable" });
                          }}
                        >
                          Enable
                        </Button>
                      )}
                    </div>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>

          <Pagination page={page} count={state.data.count} onChange={setPage} />
        </>
      )}

      <CreateStaffModal
        key={createSeq}
        open={creating}
        roles={roles}
        onClose={() => setCreating(false)}
        onCreated={() => {
          setCreating(false);
          // Show the new (newest-first) row: clear filters and force a refetch.
          setActive("");
          setSearch("");
          setPage(1);
          setState({ phase: "loading" });
          setReloadKey((k) => k + 1);
        }}
      />

      <ManageRolesModal
        key={managing?.id ?? "none"}
        member={managing}
        roles={roles}
        onClose={() => setManaging(null)}
        onSaved={(updated) => {
          updateRow(updated);
          setManaging(null);
        }}
      />

      <Modal
        open={pending !== null}
        onClose={() => (working ? undefined : setPending(null))}
        title={pending?.action === "disable" ? "Disable staff" : "Enable staff"}
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
                  ? They will be signed out and cannot sign in again until
                  re-enabled.
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

/** A scrollable checkbox list of the coded roles, for the create / manage forms. */
function RolePicker({
  roles,
  selected,
  onToggle,
  disabled,
}: {
  roles: RoleInfo[];
  selected: Set<StaffRoleValue>;
  onToggle: (value: StaffRoleValue) => void;
  disabled?: boolean;
}) {
  return (
    <div className="max-h-64 space-y-1 overflow-y-auto rounded-xl border border-line bg-surface/40 p-2">
      {roles.map((role) => (
        <label
          key={role.value}
          className="flex cursor-pointer items-start gap-3 rounded-lg px-2 py-2 hover:bg-surface"
        >
          <input
            type="checkbox"
            className="mt-0.5 h-4 w-4 rounded border-line text-brand-500 focus:ring-brand-400"
            checked={selected.has(role.value)}
            onChange={() => onToggle(role.value)}
            disabled={disabled}
          />
          <span>
            <span className="block text-sm font-medium text-ink">{role.label}</span>
            <span className="block text-xs text-muted">
              {role.permission_count} permission
              {role.permission_count === 1 ? "" : "s"}
            </span>
          </span>
        </label>
      ))}
    </div>
  );
}

function CreateStaffModal({
  open,
  roles,
  onClose,
  onCreated,
}: {
  open: boolean;
  roles: RoleInfo[] | null;
  onClose: () => void;
  onCreated: () => void;
}) {
  const { authFetch } = useAuth();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [selected, setSelected] = useState<Set<StaffRoleValue>>(new Set());
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  function toggle(value: StaffRoleValue) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    if (selected.size === 0) {
      setErrors({ roles: "Select at least one role." });
      return;
    }
    setSaving(true);
    try {
      await api.admin.createStaff(authFetch, {
        email: email.trim(),
        full_name: fullName.trim(),
        password,
        roles: [...selected],
      });
      onCreated();
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(errorMessage(error, "Could not create this staff account."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add a staff member" className="max-w-xl">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <p className="text-sm text-muted">
          Creates a verified admin account with a temporary password. Share the
          password securely; they sign in with the normal email + code flow and
          change it from their profile.
        </p>
        {formError && <Alert variant="error">{formError}</Alert>}

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Email" htmlFor="staff_email" error={errors.email} required>
            <Input
              id="staff_email"
              type="email"
              inputMode="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="new.staff@bimaya.test"
              aria-invalid={Boolean(errors.email)}
            />
          </Field>

          <Field label="Full name" htmlFor="staff_name" error={errors.full_name}>
            <Input
              id="staff_name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Sita Sharma"
              aria-invalid={Boolean(errors.full_name)}
            />
          </Field>
        </div>

        <Field
          label="Temporary password"
          htmlFor="staff_password"
          error={errors.password}
          hint="At least 8 characters. Share it with them securely."
          required
        >
          <PasswordInput
            id="staff_password"
            autoComplete="off"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={Boolean(errors.password)}
          />
        </Field>

        <Field label="Roles" htmlFor="staff_roles" error={errors.roles} required>
          {roles === null ? (
            <div className="flex items-center justify-center py-6">
              <Spinner className="h-5 w-5 text-brand-500" />
            </div>
          ) : roles.length === 0 ? (
            <Alert variant="error">Could not load roles. Please close and retry.</Alert>
          ) : (
            <RolePicker roles={roles} selected={selected} onToggle={toggle} disabled={saving} />
          )}
        </Field>

        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" loading={saving} disabled={roles === null}>
            Create staff
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ManageRolesModal({
  member,
  roles,
  onClose,
  onSaved,
}: {
  member: StaffMember | null;
  roles: RoleInfo[] | null;
  onClose: () => void;
  onSaved: (updated: StaffMember) => void;
}) {
  const { authFetch } = useAuth();
  const [selected, setSelected] = useState<Set<StaffRoleValue>>(
    () => new Set(member?.roles.map((r) => r.value) ?? []),
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function toggle(value: StaffRoleValue) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  }

  async function handleSave() {
    if (!member) return;
    setError("");
    if (selected.size === 0) {
      setError("Select at least one role.");
      return;
    }
    setSaving(true);
    try {
      const updated = await api.admin.setStaffRoles(authFetch, member.id, [
        ...selected,
      ]);
      onSaved(updated);
    } catch (err) {
      setError(errorMessage(err, "Could not update this staff member's roles."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={member !== null}
      onClose={() => (saving ? undefined : onClose())}
      title={member ? `Roles — ${member.full_name || member.email}` : "Roles"}
      className="max-w-xl"
    >
      {member && (
        <div className="space-y-4">
          <p className="text-sm text-muted">
            Choose the coded roles for this staff member. Permissions follow from
            the roles — the matrix is defined in code and shown on the Roles tab.
          </p>
          {error && <Alert variant="error">{error}</Alert>}

          {roles === null ? (
            <div className="flex items-center justify-center py-8">
              <Spinner className="h-5 w-5 text-brand-500" />
            </div>
          ) : roles.length === 0 ? (
            <Alert variant="error">Could not load roles. Please close and retry.</Alert>
          ) : (
            <RolePicker roles={roles} selected={selected} onToggle={toggle} disabled={saving} />
          )}

          <div className="flex justify-end gap-2 border-t border-line pt-4">
            <Button variant="secondary" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={handleSave} loading={saving} disabled={roles === null}>
              Save roles
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
