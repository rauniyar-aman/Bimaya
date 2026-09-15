"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { api, type RoleInfo, type RolesCatalog } from "@/lib/api";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; catalog: RolesCatalog };

/** Split a `module.action` permission into its module and action halves. */
function splitPerm(perm: string): { module: string; action: string } {
  const dot = perm.indexOf(".");
  if (dot === -1) return { module: "other", action: perm };
  return { module: perm.slice(0, dot), action: perm.slice(dot + 1) };
}

/** Turn a module key like `audit_log` into a readable "Audit log" label. */
function humanise(key: string): string {
  const spaced = key.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/**
 * The read-only roles → permissions matrix. The policy is code
 * (`apps/staff/rbac.py`) and cannot be edited at runtime, so this screen only
 * displays each role and the granular permissions it grants, grouped by module.
 */
export function RolesMatrix() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    let cancelled = false;
    api.admin
      .listRoles(authFetch)
      .then((catalog) => {
        if (!cancelled) setState({ phase: "ready", catalog });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch]);

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-xl font-semibold text-ink">
          Roles &amp; permissions
        </h2>
        <p className="mt-1 text-sm text-muted">
          The role catalogue is defined in code and managed by engineering. It is
          read-only here — assign these roles to staff on the Staff tab.
        </p>
      </div>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error">
          We could not load the roles matrix. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && (
        <div className="grid gap-4 lg:grid-cols-2">
          {state.catalog.roles.map((role) => (
            <RoleCard key={role.value} role={role} />
          ))}
        </div>
      )}
    </div>
  );
}

function RoleCard({ role }: { role: RoleInfo }) {
  // Group the role's permissions by module for a scannable layout.
  const groups = useMemo(() => {
    const byModule = new Map<string, string[]>();
    for (const perm of role.permissions) {
      const { module, action } = splitPerm(perm);
      const list = byModule.get(module) ?? [];
      list.push(action);
      byModule.set(module, list);
    }
    return [...byModule.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [role.permissions]);

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-display text-base font-semibold text-ink">
          {role.label}
        </h3>
        <span className="shrink-0 text-xs font-medium text-muted">
          {role.permission_count} permission
          {role.permission_count === 1 ? "" : "s"}
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {groups.map(([module, actions]) => (
          <div key={module}>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              {humanise(module)}
            </p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {actions.map((action) => (
                <Badge key={action}>{action}</Badge>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
