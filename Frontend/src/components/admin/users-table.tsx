"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { ROLE_FILTERS } from "@/components/admin/filters";
import { ROLE_META } from "@/components/admin/status-meta";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { SearchIcon } from "@/components/icons";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  api,
  type AdminUser,
  type AdminUserDetail,
  type Paginated,
  type UserRole,
} from "@/lib/api";
import { formatDate } from "@/lib/date";
import { useDebouncedValue } from "@/lib/use-debounced-value";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; data: Paginated<AdminUser> };

/** Admin read-only users table with role filter, search and a detail modal. */
export function UsersTable() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [page, setPage] = useState(1);
  const [role, setRole] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [activeId, setActiveId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.admin
      .listUsers(authFetch, {
        page,
        role: (role || undefined) as UserRole | undefined,
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
  }, [authFetch, page, role, debouncedSearch]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="font-display text-xl font-semibold text-ink">Users</h2>
        <div className="flex gap-2">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
              placeholder="Search name, email, phone"
              className="w-60 pl-9"
              aria-label="Search users"
            />
          </div>
          <Select
            value={role}
            onChange={(e) => {
              setPage(1);
              setRole(e.target.value);
            }}
            className="w-40"
            aria-label="Filter by role"
          >
            {ROLE_FILTERS.map((o) => (
              <option key={o.label} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error">
          We could not load users. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.data.results.length === 0 && (
        <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center text-sm text-muted">
          No users match your filters.
        </div>
      )}

      {state.phase === "ready" && state.data.results.length > 0 && (
        <>
          <Table>
            <THead>
              <TR>
                <TH>User</TH>
                <TH>Phone</TH>
                <TH>Role</TH>
                <TH>Verified</TH>
                <TH>Joined</TH>
                <TH className="text-right">Action</TH>
              </TR>
            </THead>
            <TBody>
              {state.data.results.map((u) => {
                const roleMeta = ROLE_META[u.role];
                return (
                  <TR key={u.id}>
                    <TD>
                      <div className="font-medium text-ink">{u.full_name || "—"}</div>
                      <div className="text-xs text-muted">{u.email}</div>
                    </TD>
                    <TD className="text-muted">{u.phone || "—"}</TD>
                    <TD>
                      <StatusPill status={roleMeta.variant}>{roleMeta.label}</StatusPill>
                    </TD>
                    <TD>
                      {!u.is_active ? (
                        <StatusPill status="failed">Inactive</StatusPill>
                      ) : u.is_verified ? (
                        <StatusPill status="active">Verified</StatusPill>
                      ) : (
                        <StatusPill status="pending">Unverified</StatusPill>
                      )}
                    </TD>
                    <TD className="text-muted">{formatDate(u.date_joined)}</TD>
                    <TD className="text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setActiveId(u.id)}
                      >
                        View
                      </Button>
                    </TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>

          <Pagination page={page} count={state.data.count} onChange={setPage} />
        </>
      )}

      <UserDetailModal
        key={activeId ?? "none"}
        userId={activeId}
        onClose={() => setActiveId(null)}
      />
    </div>
  );
}

type DetailState =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; user: AdminUserDetail };

function UserDetailModal({
  userId,
  onClose,
}: {
  userId: number | null;
  onClose: () => void;
}) {
  const { authFetch } = useAuth();
  const [state, setState] = useState<DetailState>({ phase: "loading" });

  useEffect(() => {
    if (userId === null) return;
    let cancelled = false;
    api.admin
      .getUser(authFetch, userId)
      .then((user) => {
        if (!cancelled) setState({ phase: "ready", user });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, userId]);

  return (
    <Modal open={userId !== null} onClose={onClose} title="User details">
      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-10">
          <Spinner className="h-5 w-5 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error">We could not load this user.</Alert>
      )}

      {state.phase === "ready" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-display text-lg font-semibold text-ink">
                {state.user.full_name || "—"}
              </p>
              <p className="text-xs text-muted">{state.user.email}</p>
            </div>
            <StatusPill status={ROLE_META[state.user.role].variant}>
              {ROLE_META[state.user.role].label}
            </StatusPill>
          </div>

          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 rounded-xl border border-line bg-surface/40 p-4 text-sm">
            <Detail label="Phone">{state.user.phone || "—"}</Detail>
            <Detail label="Joined">{formatDate(state.user.date_joined)}</Detail>
            <Detail label="Purchases">{state.user.purchase_count}</Detail>
            <Detail label="Claims">{state.user.claim_count}</Detail>
            <Detail label="Verified">{state.user.is_verified ? "Yes" : "No"}</Detail>
            <Detail label="Active">{state.user.is_active ? "Yes" : "No"}</Detail>
          </dl>

          <div className="flex justify-end border-t border-line pt-4">
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 text-ink">{children}</dd>
    </div>
  );
}
