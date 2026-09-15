"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { SearchIcon } from "@/components/icons";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { api, type AuditEntry, type Paginated } from "@/lib/api";
import { formatDate, formatRelativeTime } from "@/lib/date";
import { useDebouncedValue } from "@/lib/use-debounced-value";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; data: Paginated<AuditEntry> };

type Options = { actions: string[]; modules: string[] };

/** Merge freshly-seen filter values into the accumulated, sorted option lists. */
function mergeOptions(prev: Options, rows: AuditEntry[]): Options {
  const actions = new Set(prev.actions);
  const modules = new Set(prev.modules);
  for (const row of rows) {
    if (row.action) actions.add(row.action);
    if (row.module) modules.add(row.module);
  }
  return {
    actions: [...actions].sort(),
    modules: [...modules].sort(),
  };
}

/** Render a `changes` map compactly: `field: old → new` per entry. */
function summariseChanges(changes: Record<string, unknown>): string {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(changes)) {
    if (Array.isArray(value) && value.length === 2) {
      parts.push(`${key}: ${formatValue(value[0])} → ${formatValue(value[1])}`);
    } else {
      parts.push(`${key}: ${formatValue(value)}`);
    }
  }
  return parts.join("; ");
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "∅";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "∅";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/**
 * The append-only staff audit trail. Read-only: every state-changing admin
 * action is recorded server-side; this screen lets holders of `audit_log.view`
 * browse, filter, and search it. Filter options grow as more pages are loaded.
 */
export function AuditLog() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [options, setOptions] = useState<Options>({ actions: [], modules: [] });
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [module, setModule] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);

  useEffect(() => {
    let cancelled = false;
    api.admin
      .listAudit(authFetch, {
        page,
        action: action || undefined,
        module: module || undefined,
        search: debouncedSearch || undefined,
      })
      .then((data) => {
        if (cancelled) return;
        setState({ phase: "ready", data });
        setOptions((prev) => mergeOptions(prev, data.results));
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, page, action, module, debouncedSearch]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-display text-xl font-semibold text-ink">Audit log</h2>
          <p className="mt-1 text-sm text-muted">
            An append-only record of every administrative action.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
              placeholder="Search action, entity, actor"
              className="w-56 pl-9"
              aria-label="Search audit log"
            />
          </div>
          <Select
            value={module}
            onChange={(e) => {
              setPage(1);
              setModule(e.target.value);
            }}
            className="w-40"
            aria-label="Filter by module"
          >
            <option value="">All modules</option>
            {options.modules.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </Select>
          <Select
            value={action}
            onChange={(e) => {
              setPage(1);
              setAction(e.target.value);
            }}
            className="w-48"
            aria-label="Filter by action"
          >
            <option value="">All actions</option>
            {options.actions.map((a) => (
              <option key={a} value={a}>
                {a}
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
          We could not load the audit log. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.data.results.length === 0 && (
        <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center text-sm text-muted">
          No audit entries match your filters.
        </div>
      )}

      {state.phase === "ready" && state.data.results.length > 0 && (
        <>
          <Table>
            <THead>
              <TR>
                <TH>When</TH>
                <TH>Actor</TH>
                <TH>Action</TH>
                <TH>Entity</TH>
                <TH>Details</TH>
              </TR>
            </THead>
            <TBody>
              {state.data.results.map((entry) => (
                <TR key={entry.id}>
                  <TD className="whitespace-nowrap text-muted" title={formatDate(entry.created_at)}>
                    {formatRelativeTime(entry.created_at)}
                  </TD>
                  <TD>
                    <div className="font-medium text-ink">
                      {entry.actor_email || "System"}
                    </div>
                    {entry.actor_role && (
                      <div className="text-xs text-muted">{entry.actor_role}</div>
                    )}
                  </TD>
                  <TD>
                    <code className="rounded bg-surface px-1.5 py-0.5 text-xs text-ink">
                      {entry.action}
                    </code>
                  </TD>
                  <TD className="text-muted">
                    {entry.entity_type
                      ? `${entry.entity_type}${entry.entity_id ? ` #${entry.entity_id}` : ""}`
                      : "—"}
                  </TD>
                  <TD className="max-w-sm">
                    <span className="block truncate text-xs text-muted" title={summariseChanges(entry.changes)}>
                      {summariseChanges(entry.changes) || "—"}
                    </span>
                    {entry.reason && (
                      <span className="mt-0.5 block text-xs italic text-muted">
                        {entry.reason}
                      </span>
                    )}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>

          <Pagination page={page} count={state.data.count} onChange={setPage} />
        </>
      )}
    </div>
  );
}
