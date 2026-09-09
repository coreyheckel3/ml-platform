import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  FileCheck2,
  LockKeyhole,
  XCircle,
} from "lucide-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";

import {
  getPlatformAdminControls,
  type AdminEnvironment,
  type AdminPermissionGroup,
  type AdminRolePreset,
  type AdminSafeguard,
  type AdminUserAccess,
  type PlatformAdminControls,
} from "../api/adminControls";
import {
  readStoredSession,
  subscribeToSessionChanges,
} from "../../auth/session/sessionStore";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";

type BooleanSignal = {
  label: string;
  enabled: boolean;
  detail: string;
};

export function AdminControlsPage() {
  const [session, setSession] = useState(() => readStoredSession());
  const token = session?.accessToken ?? "";
  const controlsQuery = useQuery({
    queryKey: ["platform-admin-controls", token],
    queryFn: () => getPlatformAdminControls(token),
    enabled: Boolean(token),
    retry: false,
  });
  const controls = controlsQuery.data;
  const environmentSignals = useMemo(
    () => (controls ? buildEnvironmentSignals(controls.environment) : []),
    [controls],
  );

  useEffect(
    () => subscribeToSessionChanges(() => setSession(readStoredSession())),
    [],
  );

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Admin Controls"
        description="Organization-level visibility for user access, RBAC presets, runtime posture, and guarded operator workflows across the ForgeML control plane."
      />

      {!token ? (
        <DataPanel title="Authentication Required">
          <div className="flex items-start gap-3 text-sm text-steel">
            <LockKeyhole className="mt-0.5 h-4 w-4 text-amber-600" aria-hidden="true" />
            <p>Sign in to view platform admin controls.</p>
          </div>
        </DataPanel>
      ) : null}

      {token && controlsQuery.isLoading ? (
        <DataPanel title="Admin Controls">
          <div role="status" className="text-sm text-steel">
            Loading admin control plane
          </div>
        </DataPanel>
      ) : null}

      {controlsQuery.isError ? (
        <DataPanel title="Admin Controls Unavailable">
          <div className="flex items-start gap-3 text-sm text-risk">
            <XCircle className="mt-0.5 h-4 w-4" aria-hidden="true" />
            <p>Admin controls request failed.</p>
          </div>
        </DataPanel>
      ) : null}

      {controls ? (
        <>
          <AdminSummary controls={controls} />

          <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
            <OrganizationOverview controls={controls} />
            <EnvironmentVisibility
              environment={controls.environment}
              signals={environmentSignals}
            />
          </div>

          <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <UserAccess users={controls.users} />
            <RolePresetPanel rolePresets={controls.role_presets} />
          </div>

          <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <PermissionCatalog permissionGroups={controls.permission_groups} />
            <SafeAdminWorkflows
              safeguards={controls.safeguards}
              operatorCommands={controls.operator_commands}
            />
          </div>
        </>
      ) : null}
    </>
  );
}

function AdminSummary({ controls }: { controls: PlatformAdminControls }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        label="Organization Status"
        value={formatLabel(controls.organization.status)}
        detail={`${controls.organization.name} / ${controls.organization.slug}`}
        tone={controls.organization.status === "active" ? "success" : "warning"}
      />
      <MetricCard
        label="Active Users"
        value={`${controls.stats.active_users}/${controls.stats.total_users}`}
        detail={`${controls.stats.disabled_users} disabled accounts`}
        tone={controls.stats.disabled_users > 0 ? "warning" : "success"}
      />
      <MetricCard
        label="RBAC Surface"
        value={`${controls.stats.role_preset_count} roles`}
        detail={`${controls.stats.permission_count} permissions across ${controls.stats.permission_group_count} modules`}
      />
      <MetricCard
        label="Runtime Posture"
        value={formatLabel(controls.environment.environment)}
        detail={
          controls.environment.production_like
            ? "production-like safeguards expected"
            : "local or non-production runtime"
        }
        tone={controls.environment.production_like ? "warning" : "neutral"}
      />
    </div>
  );
}

function OrganizationOverview({ controls }: { controls: PlatformAdminControls }) {
  return (
    <DataPanel title="Organization Overview">
      <div className="grid gap-3 md:grid-cols-2">
        <KeyValue label="Organization ID" value={controls.organization.id} />
        <KeyValue label="Schema" value={controls.schema_version} />
        <KeyValue label="Name" value={controls.organization.name} />
        <KeyValue label="Slug" value={controls.organization.slug} />
        <KeyValue label="Status" value={formatLabel(controls.organization.status)} />
        <KeyValue
          label="Created"
          value={formatDateTime(controls.organization.created_at)}
        />
        <KeyValue label="Projects" value={String(controls.stats.project_count)} />
        <KeyValue label="Audit Events" value={String(controls.stats.audit_event_count)} />
        <KeyValue
          label="Release Reports"
          value={String(controls.stats.release_evidence_report_count)}
        />
      </div>
    </DataPanel>
  );
}

function EnvironmentVisibility({
  environment,
  signals,
}: {
  environment: AdminEnvironment;
  signals: BooleanSignal[];
}) {
  return (
    <DataPanel title="Environment Visibility">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <KeyValue label="Runtime" value={formatLabel(environment.environment)} compact />
          <KeyValue
            label="Production Like"
            value={environment.production_like ? "Yes" : "No"}
            compact
          />
          <KeyValue
            label="Release Provider"
            value={environment.release_evidence_provider}
            compact
          />
          <KeyValue
            label="Release Repo"
            value={environment.release_evidence_repository ?? "not configured"}
            compact
          />
          <KeyValue
            label="Release Branch"
            value={environment.release_evidence_branch ?? "not configured"}
            compact
          />
          <KeyValue
            label="Workflow"
            value={environment.release_evidence_workflow ?? "not configured"}
            compact
          />
          <KeyValue
            label="Access Token TTL"
            value={formatDuration(environment.access_token_ttl_seconds)}
            compact
          />
          <KeyValue
            label="Refresh Token TTL"
            value={formatDuration(environment.refresh_token_ttl_seconds)}
            compact
          />
        </div>
        <div className="space-y-2">
          {signals.map((signal) => (
            <BooleanSignalRow key={signal.label} signal={signal} />
          ))}
        </div>
      </div>
    </DataPanel>
  );
}

function UserAccess({ users }: { users: AdminUserAccess[] }) {
  return (
    <DataPanel title="User Access">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
          <thead className="text-xs uppercase text-steel">
            <tr>
              <th scope="col" className="py-2 pr-4 font-semibold">
                User
              </th>
              <th scope="col" className="py-2 pr-4 font-semibold">
                Status
              </th>
              <th scope="col" className="py-2 pr-4 font-semibold">
                Roles
              </th>
              <th scope="col" className="py-2 pr-4 font-semibold">
                Permissions
              </th>
              <th scope="col" className="py-2 font-semibold">
                Last Login
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {users.map((user) => (
              <tr key={user.id}>
                <td className="py-3 pr-4 align-top">
                  <div className="font-medium text-ink">{user.display_name}</div>
                  <div className="mt-1 text-xs text-steel">{user.email}</div>
                </td>
                <td className="py-3 pr-4 align-top">
                  <StatusBadge status={user.status} />
                </td>
                <td className="py-3 pr-4 align-top">
                  <BadgeList
                    values={user.role_codes.length > 0 ? user.role_codes : ["custom"]}
                  />
                </td>
                <td className="py-3 pr-4 align-top text-steel">
                  {user.permission_count}
                </td>
                <td className="py-3 align-top text-steel">
                  {formatDateTime(user.last_login_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DataPanel>
  );
}

function RolePresetPanel({ rolePresets }: { rolePresets: AdminRolePreset[] }) {
  return (
    <DataPanel title="RBAC Matrix">
      <div className="space-y-3">
        {rolePresets.map((role) => (
          <div key={role.code} className="rounded border border-slate-200 p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-medium text-ink">{role.name}</div>
                <div className="mt-1 text-xs text-steel">{role.code}</div>
              </div>
              <span className="rounded border border-slate-200 bg-cloud px-2 py-1 text-xs font-semibold text-steel">
                {role.assigned_user_count} assigned
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-steel">{role.description}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="rounded border border-slate-200 bg-white px-2 py-1 font-medium text-steel">
                {role.permission_count} permissions
              </span>
              <span
                className={[
                  "rounded border px-2 py-1 font-medium",
                  role.granted_to_current_principal
                    ? "border-emerald-200 bg-emerald-50 text-signal"
                    : "border-amber-200 bg-amber-50 text-amber-700",
                ].join(" ")}
              >
                {role.granted_to_current_principal
                  ? "granted to current principal"
                  : "not granted to current principal"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </DataPanel>
  );
}

function PermissionCatalog({
  permissionGroups,
}: {
  permissionGroups: AdminPermissionGroup[];
}) {
  return (
    <DataPanel title="Permission Catalog">
      <div className="grid gap-3 md:grid-cols-2">
        {permissionGroups.map((group) => (
          <div key={group.module} className="rounded border border-slate-200 p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="font-medium text-ink">{formatModule(group.module)}</div>
              <span className="text-xs font-semibold text-steel">
                {group.granted_count}/{group.permission_count} granted
              </span>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {group.permissions.slice(0, 5).map((permission) => (
                <span
                  key={permission.code}
                  className={[
                    "rounded border px-2 py-1 text-xs font-medium",
                    permission.granted_to_current_principal
                      ? "border-emerald-200 bg-emerald-50 text-signal"
                      : "border-slate-200 bg-white text-steel",
                  ].join(" ")}
                >
                  {permission.code}
                </span>
              ))}
              {group.permissions.length > 5 ? (
                <span className="rounded border border-slate-200 bg-cloud px-2 py-1 text-xs font-medium text-steel">
                  +{group.permissions.length - 5} more
                </span>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </DataPanel>
  );
}

function SafeAdminWorkflows({
  safeguards,
  operatorCommands,
}: {
  safeguards: AdminSafeguard[];
  operatorCommands: string[];
}) {
  return (
    <DataPanel title="Safe Admin Workflows">
      <div className="space-y-4">
        <div className="space-y-3">
          {safeguards.map((safeguard) => (
            <SafeguardRow key={safeguard.label} safeguard={safeguard} />
          ))}
        </div>
        <div>
          <div className="mb-2 text-xs font-semibold uppercase text-steel">
            Operator Commands
          </div>
          <div className="space-y-2">
            {operatorCommands.map((command) => (
              <code
                key={command}
                className="block overflow-x-auto rounded border border-slate-200 bg-cloud px-3 py-2 text-xs text-ink"
              >
                {command}
              </code>
            ))}
          </div>
        </div>
      </div>
    </DataPanel>
  );
}

function BooleanSignalRow({ signal }: { signal: BooleanSignal }) {
  const Icon = signal.enabled ? CheckCircle2 : XCircle;
  return (
    <div className="flex items-start gap-3 rounded border border-slate-200 p-3">
      <Icon
        className={[
          "mt-0.5 h-4 w-4",
          signal.enabled ? "text-signal" : "text-amber-600",
        ].join(" ")}
        aria-hidden="true"
      />
      <div>
        <div className="text-sm font-medium text-ink">{signal.label}</div>
        <div className="mt-1 text-xs leading-5 text-steel">{signal.detail}</div>
      </div>
    </div>
  );
}

function SafeguardRow({ safeguard }: { safeguard: AdminSafeguard }) {
  return (
    <div className="rounded border border-slate-200 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-ink">{safeguard.label}</div>
          <p className="mt-1 text-xs leading-5 text-steel">{safeguard.detail}</p>
        </div>
        <StatusBadge status={safeguard.status} />
      </div>
      <div className="mt-3 flex items-center gap-2 text-xs text-steel">
        <FileCheck2 className="h-3.5 w-3.5" aria-hidden="true" />
        <span>{safeguard.evidence}</span>
      </div>
    </div>
  );
}

function KeyValue({
  label,
  value,
  compact = false,
}: {
  label: string;
  value: ReactNode;
  compact?: boolean;
}) {
  return (
    <div className={compact ? "" : "rounded border border-slate-200 p-3"}>
      <div className="text-xs font-semibold uppercase text-steel">{label}</div>
      <div className="mt-1 break-words text-sm font-medium text-ink">{value}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const tone =
    normalized === "active" ||
    normalized === "enforced" ||
    normalized === "visible" ||
    normalized === "contracted"
      ? "border-emerald-200 bg-emerald-50 text-signal"
      : normalized === "read-only"
        ? "border-sky-200 bg-sky-50 text-sky-700"
        : "border-amber-200 bg-amber-50 text-amber-700";
  return (
    <span className={`inline-flex rounded border px-2 py-1 text-xs font-semibold ${tone}`}>
      {formatLabel(status)}
    </span>
  );
}

function BadgeList({ values }: { values: string[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {values.map((value) => (
        <span
          key={value}
          className="rounded border border-slate-200 bg-cloud px-2 py-1 text-xs font-medium text-steel"
        >
          {value}
        </span>
      ))}
    </div>
  );
}

function buildEnvironmentSignals(environment: AdminEnvironment): BooleanSignal[] {
  return [
    {
      label: "Rate Limiting",
      enabled: environment.rate_limit_enabled,
      detail: "API gateway policy reports runtime throttle enforcement.",
    },
    {
      label: "Request Logging",
      enabled: environment.request_logging_enabled,
      detail: "HTTP requests emit trace-aware audit and observability events.",
    },
    {
      label: "Structured Logging",
      enabled: environment.structured_logging_enabled,
      detail: "Runtime logs include machine-parseable fields for incident review.",
    },
    {
      label: "Readiness Checks",
      enabled: environment.readiness_checks_enabled,
      detail: "Health probes include dependency checks for production rollouts.",
    },
    {
      label: "Object Storage",
      enabled: environment.object_storage_configured,
      detail: "Model and dataset artifacts have a configured object storage endpoint.",
    },
    {
      label: "Redis",
      enabled: environment.redis_configured,
      detail: "Cache and job coordination settings are visible to operators.",
    },
    {
      label: "MLflow Tracking",
      enabled: environment.mlflow_tracking_configured,
      detail: "Experiment tracking adapter has a configured tracking URI.",
    },
    {
      label: "Airflow Orchestration",
      enabled: environment.airflow_orchestration_enabled,
      detail: "Training orchestration can trigger the configured DAG boundary.",
    },
    {
      label: "External Training Profiles",
      enabled: environment.external_training_profiles_enabled,
      detail: "Allowlisted external ML packages can run through ForgeML profiles.",
    },
  ];
}

function formatLabel(value: string): string {
  return value
    .split(/[_-]/g)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatModule(value: string): string {
  return formatLabel(value.replace("model_registry", "registry"));
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "never";
  }
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return value;
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(timestamp));
}

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  if (seconds < 3_600) {
    return `${Math.round(seconds / 60)}m`;
  }
  if (seconds < 86_400) {
    return `${Math.round(seconds / 3_600)}h`;
  }
  return `${Math.round(seconds / 86_400)}d`;
}
