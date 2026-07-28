import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Bell,
  Bot,
  ClipboardList,
  Eye,
  KeyRound,
  ListFilter,
  LockKeyhole,
  RefreshCw,
  Rocket,
  Search,
  ShieldCheck,
  UserRound,
  UsersRound,
} from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";

import { getCurrentUser, type CurrentUser } from "../../auth/api/auth";
import {
  ACCESS_TOKEN_KEY,
  PROJECT_CONTEXT_KEY,
  readStoredSession,
} from "../../auth/session/sessionStore";
import { listAuditLog, type AuditLogEntry, type AuditLogFilters } from "../api/auditLog";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";

type PermissionGroup = {
  scope: string;
  permissions: string[];
};

type AuditFilterDraft = {
  actorType: string;
  action: string;
  resourceType: string;
};

type AuditPreset = {
  label: string;
  filters: AuditFilterDraft;
};

const initialAuditDraft: AuditFilterDraft = {
  actorType: "",
  action: "",
  resourceType: "",
};

const auditPresets: AuditPreset[] = [
  {
    label: "All Events",
    filters: initialAuditDraft,
  },
  {
    label: "Training",
    filters: { actorType: "", action: "", resourceType: "training_run" },
  },
  {
    label: "Model Review",
    filters: { actorType: "", action: "", resourceType: "model_version" },
  },
  {
    label: "Deployment Rollout",
    filters: { actorType: "", action: "deployments.rollout", resourceType: "" },
  },
  {
    label: "Alerts",
    filters: { actorType: "", action: "", resourceType: "alert_event" },
  },
  {
    label: "Retraining",
    filters: { actorType: "", action: "", resourceType: "retraining_run" },
  },
];

const securityDefaults = [
  {
    label: "JWT access tokens",
    value: "15 minutes",
    detail: "Short-lived bearer credentials limit replay windows.",
  },
  {
    label: "RBAC",
    value: "organization and project scopes",
    detail: "Permissions map to module actions instead of page-only checks.",
  },
  {
    label: "API keys",
    value: "hashed at rest",
    detail: "Service credentials are treated as secrets, not recoverable text.",
  },
  {
    label: "Audit log",
    value: "security and model lifecycle events",
    detail: "Authentication, approvals, deployments, and policy changes are reviewable.",
  },
];

export function SettingsPage() {
  const session = readStoredSession();
  const token = session?.accessToken ?? null;
  const [selectedProjectId, setSelectedProjectId] = useState(
    () => readLocalStorage(PROJECT_CONTEXT_KEY) ?? "",
  );
  const [auditDraft, setAuditDraft] = useState<AuditFilterDraft>(initialAuditDraft);
  const [auditFilters, setAuditFilters] = useState<AuditLogFilters>({ limit: 50 });
  const [auditProjectScoped, setAuditProjectScoped] = useState(false);
  const [selectedAuditEntryId, setSelectedAuditEntryId] = useState<string | null>(null);
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const userQuery = useQuery({
    queryKey: ["current-user", token],
    queryFn: () => getCurrentUser(token ?? ""),
    enabled: Boolean(token),
  });
  const user = userQuery.data;
  const permissionGroups = useMemo(
    () => groupPermissions(user?.permissions ?? []),
    [user?.permissions],
  );
  const authenticated = Boolean(token);
  const canReadAuditLog = hasPermission(user?.permissions ?? [], "admin:audit_log:read");
  const auditQuery = useQuery({
    queryKey: ["audit-log", token, auditFilters],
    queryFn: () => listAuditLog(token ?? "", auditFilters),
    enabled: Boolean(token && user && canReadAuditLog),
  });
  const visibleAuditEntries = useMemo(
    () => {
      const auditEntries = auditQuery.data?.items ?? [];
      return auditProjectScoped && selectedProjectId
        ? auditEntries.filter((entry) => auditEntryMatchesProject(entry, selectedProjectId))
        : auditEntries;
    },
    [auditQuery.data?.items, auditProjectScoped, selectedProjectId],
  );
  const selectedAuditEntry = useMemo(
    () => visibleAuditEntries.find((entry) => entry.id === selectedAuditEntryId) ?? null,
    [selectedAuditEntryId, visibleAuditEntries],
  );

  useEffect(() => {
    if (visibleAuditEntries.length === 0) {
      setSelectedAuditEntryId(null);
      return;
    }
    if (!visibleAuditEntries.some((entry) => entry.id === selectedAuditEntryId)) {
      setSelectedAuditEntryId(visibleAuditEntries[0].id);
    }
  }, [selectedAuditEntryId, visibleAuditEntries]);

  useEffect(() => {
    if (!selectedProjectId && auditProjectScoped) {
      setAuditProjectScoped(false);
    }
  }, [auditProjectScoped, selectedProjectId]);

  function clearProjectContext() {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(PROJECT_CONTEXT_KEY);
    }
    setSelectedProjectId("");
    setOperationMessage("Cleared active project context for this browser.");
  }

  function applyAuditFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuditFilters({
      actorType: cleanDraftValue(auditDraft.actorType),
      action: cleanDraftValue(auditDraft.action),
      resourceType: cleanDraftValue(auditDraft.resourceType),
      limit: 50,
    });
  }

  function resetAuditFilters() {
    setAuditDraft(initialAuditDraft);
    setAuditFilters({ limit: 50 });
  }

  function applyAuditPreset(preset: AuditPreset) {
    setAuditDraft(preset.filters);
    setAuditFilters({
      actorType: cleanDraftValue(preset.filters.actorType),
      action: cleanDraftValue(preset.filters.action),
      resourceType: cleanDraftValue(preset.filters.resourceType),
      limit: 50,
    });
  }

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Settings"
        description="Account context, RBAC permissions, local workspace state, and security defaults for ForgeML operators."
      />

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          label="Auth"
          value={authenticated ? "connected" : "local"}
          detail={authenticated ? "API token present" : "browser session"}
          tone={authenticated ? "success" : "warning"}
        />
        <MetricCard
          label="Permissions"
          value={String(user?.permissions.length ?? 0)}
          detail={authenticated ? "granted actions" : "requires login"}
        />
        <MetricCard
          label="Organization"
          value={user?.organization_id ?? "none"}
          detail={user ? "RBAC tenant" : "not loaded"}
        />
        <MetricCard
          label="Project Context"
          value={selectedProjectId ? "selected" : "empty"}
          detail={selectedProjectId || "choose one in Projects"}
        />
      </div>

      {operationMessage ? (
        <div className="mt-4 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-signal">
          {operationMessage}
        </div>
      ) : null}

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="grid gap-4">
          <DataPanel title="Account Context">
            {!authenticated ? (
              <StateMessage message="No API token is configured for this browser." />
            ) : userQuery.error ? (
              <StateMessage message="Account context request failed." tone="danger" />
            ) : userQuery.isFetching && !user ? (
              <StateMessage message="Loading account context." />
            ) : user ? (
              <AccountPanel user={user} selectedProjectId={selectedProjectId} />
            ) : null}
          </DataPanel>

          <DataPanel
            title="Local Workspace"
            action={
              <button
                type="button"
                onClick={clearProjectContext}
                disabled={!selectedProjectId}
                className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-steel transition hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
              >
                <KeyRound className="h-4 w-4" />
                Clear project context
              </button>
            }
          >
            <div className="grid gap-3 text-sm">
              <SignalTile
                icon={<KeyRound className="h-4 w-4" />}
                label="Token Key"
                value={ACCESS_TOKEN_KEY}
                detail={session ? `expires ${formatDateTime(session.expiresAt)}` : "not configured"}
              />
              <SignalTile
                icon={<ShieldCheck className="h-4 w-4" />}
                label="Project Key"
                value={PROJECT_CONTEXT_KEY}
                detail={selectedProjectId || "no active project context"}
              />
            </div>
          </DataPanel>
        </div>

        <div className="grid gap-4">
          <DataPanel title="Permission Groups">
            {permissionGroups.length === 0 ? (
              <StateMessage message="No permissions are loaded for the active user." />
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {permissionGroups.map((group) => (
                  <PermissionGroupCard key={group.scope} group={group} />
                ))}
              </div>
            )}
          </DataPanel>

          <DataPanel title="Security Defaults">
            <div className="grid gap-3 md:grid-cols-2">
              {securityDefaults.map((item) => (
                <SecurityDefaultRow
                  key={item.label}
                  label={item.label}
                  value={item.value}
                  detail={item.detail}
                />
              ))}
            </div>
          </DataPanel>
        </div>
      </div>

      <div className="mt-4">
        <DataPanel
          title="Audit Log"
          action={
            <button
              type="button"
              onClick={() => auditQuery.refetch()}
              disabled={!canReadAuditLog}
              className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-steel transition hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          }
        >
          {!authenticated ? (
            <StateMessage message="Sign in to inspect organization audit events." />
          ) : userQuery.isFetching && !user ? (
            <StateMessage message="Loading account permissions." />
          ) : !canReadAuditLog ? (
            <StateMessage message="Current permissions do not include audit log access." />
          ) : (
            <div className="grid gap-4">
              <AuditOperationsBar
                presets={auditPresets}
                activeFilters={auditFilters}
                selectedProjectId={selectedProjectId}
                projectScoped={auditProjectScoped}
                onPresetSelect={applyAuditPreset}
                onProjectScopedChange={setAuditProjectScoped}
              />
              <AuditFiltersForm
                draft={auditDraft}
                onDraftChange={setAuditDraft}
                onSubmit={applyAuditFilters}
                onReset={resetAuditFilters}
              />
              {auditQuery.error ? (
                <StateMessage message="Audit log request failed." tone="danger" />
              ) : auditQuery.isFetching && visibleAuditEntries.length === 0 ? (
                <StateMessage message="Loading audit events." />
              ) : visibleAuditEntries.length === 0 ? (
                <StateMessage message="No audit events matched the current filters." />
              ) : (
                <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_380px]">
                  <AuditLogTable
                    entries={visibleAuditEntries}
                    selectedEntryId={selectedAuditEntry?.id ?? null}
                    onSelectEntry={setSelectedAuditEntryId}
                  />
                  <AuditEventDetail entry={selectedAuditEntry} />
                </div>
              )}
            </div>
          )}
        </DataPanel>
      </div>
    </>
  );
}

function AuditOperationsBar({
  presets,
  activeFilters,
  selectedProjectId,
  projectScoped,
  onPresetSelect,
  onProjectScopedChange,
}: {
  presets: AuditPreset[];
  activeFilters: AuditLogFilters;
  selectedProjectId: string;
  projectScoped: boolean;
  onPresetSelect: (preset: AuditPreset) => void;
  onProjectScopedChange: (enabled: boolean) => void;
}) {
  return (
    <div className="grid gap-3 border-b border-slate-200 pb-4">
      <div className="flex flex-wrap items-center gap-2">
        {presets.map((preset) => {
          const selected = filtersMatchDraft(activeFilters, preset.filters);
          return (
            <button
              key={preset.label}
              type="button"
              aria-pressed={selected}
              onClick={() => onPresetSelect(preset)}
              className={`inline-flex h-9 items-center gap-2 rounded border px-3 text-xs font-semibold transition ${
                selected
                  ? "border-ink bg-ink text-white"
                  : "border-slate-200 bg-white text-steel hover:text-ink"
              }`}
            >
              <ListFilter className="h-4 w-4" />
              {preset.label}
            </button>
          );
        })}
      </div>
      <label className="flex max-w-xl items-center gap-3 rounded border border-slate-200 bg-cloud px-3 py-2 text-sm text-steel">
        <input
          type="checkbox"
          aria-label="Project activity"
          checked={projectScoped}
          disabled={!selectedProjectId}
          onChange={(event) => onProjectScopedChange(event.target.checked)}
          className="h-4 w-4 rounded border-slate-300 text-signal focus:ring-signal"
        />
        <span className="font-medium text-ink">Project activity</span>
        <span className="truncate text-xs">
          {selectedProjectId || "No active project context"}
        </span>
      </label>
    </div>
  );
}

function AccountPanel({
  user,
  selectedProjectId,
}: {
  user: CurrentUser;
  selectedProjectId: string;
}) {
  return (
    <div className="grid gap-3">
      <SignalTile
        icon={<UserRound className="h-4 w-4" />}
        label="Principal"
        value={user.email}
        detail={user.id}
      />
      <SignalTile
        icon={<UsersRound className="h-4 w-4" />}
        label="Organization"
        value={user.organization_id}
        detail="tenant boundary"
      />
      <SignalTile
        icon={<ShieldCheck className="h-4 w-4" />}
        label="Permission Count"
        value={String(user.permissions.length)}
        detail="module-level grants"
      />
      <SignalTile
        icon={<KeyRound className="h-4 w-4" />}
        label="Active Project"
        value={selectedProjectId || "none"}
        detail="used by workflow pages"
      />
    </div>
  );
}

function AuditFiltersForm({
  draft,
  onDraftChange,
  onSubmit,
  onReset,
}: {
  draft: AuditFilterDraft;
  onDraftChange: (draft: AuditFilterDraft) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
}) {
  return (
    <form
      aria-label="Filter audit log"
      onSubmit={onSubmit}
      className="grid gap-3 border-b border-slate-200 pb-4 lg:grid-cols-[1fr_1fr_1fr_auto]"
    >
      <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
        Actor
        <input
          value={draft.actorType}
          onChange={(event) =>
            onDraftChange({ ...draft, actorType: event.target.value })
          }
          className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
        />
      </label>
      <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
        Action
        <input
          value={draft.action}
          onChange={(event) => onDraftChange({ ...draft, action: event.target.value })}
          className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
        />
      </label>
      <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
        Resource
        <input
          value={draft.resourceType}
          onChange={(event) =>
            onDraftChange({ ...draft, resourceType: event.target.value })
          }
          className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
        />
      </label>
      <div className="flex items-end gap-2">
        <button
          type="submit"
          className="inline-flex h-10 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          <Search className="h-4 w-4" />
          Apply
        </button>
        <button
          type="button"
          onClick={onReset}
          className="inline-flex h-10 items-center rounded border border-slate-200 bg-white px-3 text-sm font-semibold text-steel transition hover:text-ink"
        >
          Reset
        </button>
      </div>
    </form>
  );
}

function AuditLogTable({
  entries,
  selectedEntryId,
  onSelectEntry,
}: {
  entries: AuditLogEntry[];
  selectedEntryId: string | null;
  onSelectEntry: (entryId: string) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[960px] text-left text-sm">
        <thead className="text-xs uppercase text-steel">
          <tr>
            <th className="py-2">Time</th>
            <th>Action</th>
            <th>Resource</th>
            <th>Actor</th>
            <th>Metadata</th>
            <th>Inspect</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr
              key={entry.id}
              className={`border-t border-slate-100 ${
                selectedEntryId === entry.id ? "bg-emerald-50" : ""
              }`}
            >
              <td className="py-3 text-xs text-steel">{formatDateTime(entry.created_at)}</td>
              <td>
                <div className="flex items-center gap-2 font-medium">
                  <ClipboardList className="h-4 w-4 text-signal" />
                  {entry.action}
                </div>
                <div className="mt-1 text-xs text-steel">{entry.id}</div>
              </td>
              <td>
                <div className="font-medium">{entry.resource_type}</div>
                <div className="mt-1 text-xs text-steel">{entry.resource_id}</div>
              </td>
              <td>
                <div className="font-medium">{entry.actor_type}</div>
                <div className="mt-1 text-xs text-steel">{entry.actor_id}</div>
              </td>
              <td className="max-w-[360px] truncate text-xs text-steel">
                {formatMetadata(entry.metadata)}
              </td>
              <td>
                <button
                  type="button"
                  aria-label={`Inspect ${entry.action}`}
                  onClick={() => onSelectEntry(entry.id)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
                >
                  <Eye className="h-4 w-4" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AuditEventDetail({ entry }: { entry: AuditLogEntry | null }) {
  if (!entry) {
    return <StateMessage message="Select an audit event to inspect metadata." />;
  }

  return (
    <aside className="rounded border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase text-steel">Audit Event Detail</div>
          <div className="mt-2 break-words text-sm font-semibold text-ink">{entry.action}</div>
        </div>
        <AuditActionIcon action={entry.action} />
      </div>
      <dl className="mt-4 grid gap-3 text-sm">
        <DetailRow label="Time" value={formatDateTime(entry.created_at)} />
        <DetailRow label="Actor" value={`${entry.actor_type}:${entry.actor_id}`} />
        <DetailRow label="Organization" value={entry.organization_id ?? "none"} />
        <DetailRow label="Resource" value={`${entry.resource_type}:${entry.resource_id}`} />
      </dl>
      <div className="mt-4 border-t border-slate-200 pt-4">
        <div className="text-xs font-semibold uppercase text-steel">Metadata</div>
        <div className="mt-3 grid gap-2">
          {Object.entries(entry.metadata).length === 0 ? (
            <div className="rounded bg-field px-3 py-2 text-xs text-steel">none</div>
          ) : (
            Object.entries(entry.metadata).map(([key, value]) => (
              <div
                key={key}
                className="grid gap-1 rounded bg-field px-3 py-2 text-xs md:grid-cols-[120px_minmax(0,1fr)]"
              >
                <div className="font-semibold text-steel">{key}</div>
                <div className="break-words font-medium text-ink">
                  {formatMetadataValue(value)}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 rounded bg-field px-3 py-2">
      <dt className="text-xs font-semibold uppercase text-steel">{label}</dt>
      <dd className="break-words text-sm font-medium text-ink">{value}</dd>
    </div>
  );
}

function AuditActionIcon({ action }: { action: string }) {
  const className = "h-5 w-5 text-signal";
  if (action.startsWith("alert_events.")) {
    return <Bell className={className} />;
  }
  if (action.startsWith("deployments.")) {
    return <Rocket className={className} />;
  }
  if (action.startsWith("retraining_runs.")) {
    return <Bot className={className} />;
  }
  if (action.startsWith("training_runs.")) {
    return <Activity className={className} />;
  }
  return <ClipboardList className={className} />;
}

function PermissionGroupCard({ group }: { group: PermissionGroup }) {
  return (
    <div className="rounded border border-slate-200 p-3">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <LockKeyhole className="h-4 w-4 text-signal" />
        {group.scope}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {group.permissions.map((permission) => (
          <span
            key={permission}
            className="rounded bg-field px-2 py-1 text-xs font-medium text-steel"
          >
            {permission}
          </span>
        ))}
      </div>
    </div>
  );
}

function SecurityDefaultRow({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded border border-slate-200 p-3">
      <div className="text-xs font-semibold uppercase text-steel">{label}</div>
      <div className="mt-2 text-sm font-medium text-ink">{value}</div>
      <div className="mt-1 text-xs leading-5 text-steel">{detail}</div>
    </div>
  );
}

function SignalTile({
  icon,
  label,
  value,
  detail,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="min-w-0 rounded border border-slate-200 p-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase text-steel">
        {icon}
        {label}
      </div>
      <div className="mt-2 truncate text-sm font-medium text-ink">{value}</div>
      <div className="mt-1 truncate text-xs text-steel">{detail}</div>
    </div>
  );
}

function StateMessage({
  message,
  tone = "neutral",
}: {
  message: string;
  tone?: "neutral" | "danger";
}) {
  const className =
    tone === "danger"
      ? "rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk"
      : "rounded border border-slate-200 bg-cloud p-4 text-sm text-steel";
  return <div className={className}>{message}</div>;
}

function groupPermissions(permissions: string[]): PermissionGroup[] {
  const groups = permissions.reduce<Record<string, string[]>>((accumulator, permission) => {
    const [scope] = permission.split(":");
    const key = scope || "platform";
    accumulator[key] = [...(accumulator[key] ?? []), permission];
    return accumulator;
  }, {});

  return Object.entries(groups)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([scope, groupedPermissions]) => ({
      scope,
      permissions: [...groupedPermissions].sort(),
    }));
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}

function formatDateTime(value: string): string {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return "invalid expiry";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(timestamp));
}

function hasPermission(permissions: string[], permission: string): boolean {
  return permissions.includes("*") || permissions.includes(permission);
}

function cleanDraftValue(value: string): string | undefined {
  const cleaned = value.trim();
  return cleaned || undefined;
}

function filtersMatchDraft(filters: AuditLogFilters, draft: AuditFilterDraft): boolean {
  return (
    (filters.actorType ?? "") === draft.actorType &&
    (filters.action ?? "") === draft.action &&
    (filters.resourceType ?? "") === draft.resourceType
  );
}

function auditEntryMatchesProject(entry: AuditLogEntry, projectId: string): boolean {
  const metadataProjectId = entry.metadata.project_id;
  return (
    String(metadataProjectId ?? "") === projectId ||
    (entry.resource_type === "project" && entry.resource_id === projectId)
  );
}

function formatMetadata(metadata: Record<string, unknown>): string {
  const entries = Object.entries(metadata);
  if (entries.length === 0) {
    return "none";
  }
  return entries
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(", ");
}

function formatMetadataValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "none";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}
