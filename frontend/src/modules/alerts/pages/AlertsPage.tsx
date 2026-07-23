import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, CircleCheck, CircleX, Plus, X } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  acknowledgeAlertEvent,
  createAlertRule,
  listAlertEvents,
  listAlertRules,
  resolveAlertEvent,
  type AlertEvent,
  type AlertRule,
} from "../api/alerts";

export function AlertsPage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadAlerts = Boolean(token && projectId);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [ruleName, setRuleName] = useState("");
  const [ruleDescription, setRuleDescription] = useState("");
  const [severity, setSeverity] = useState("warning");
  const [metric, setMetric] = useState("inference_error_rate");
  const [operator, setOperator] = useState("gt");
  const [threshold, setThreshold] = useState("0.05");
  const [windowSeconds, setWindowSeconds] = useState("300");
  const [enabled, setEnabled] = useState(true);
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const rulesQuery = useQuery({
    queryKey: ["alert-rules", projectId],
    queryFn: () => listAlertRules(projectId ?? "", token ?? ""),
    enabled: canLoadAlerts,
  });
  const eventsQuery = useQuery({
    queryKey: ["alert-events", projectId],
    queryFn: () => listAlertEvents(projectId ?? "", token ?? ""),
    enabled: canLoadAlerts,
  });
  const rules = useMemo(
    () => rulesQuery.data?.items ?? [],
    [rulesQuery.data?.items],
  );
  const events = useMemo(
    () => eventsQuery.data?.items ?? [],
    [eventsQuery.data?.items],
  );
  const openEvents = events.filter((event) => event.status === "open");
  const acknowledgedEvents = events.filter(
    (event) => event.status === "acknowledged",
  );
  const criticalEvents = events.filter(
    (event) => event.severity === "critical" && event.status !== "resolved",
  );
  const createRuleMutation = useMutation({
    mutationFn: () => {
      if (!projectId || !token) {
        throw new Error("Alert rule creation requires project context.");
      }
      return createAlertRule(
        projectId,
        {
          name: ruleName.trim(),
          description: ruleDescription.trim(),
          severity,
          metric,
          operator,
          threshold: parseNonNegativeFloat(threshold, "Threshold"),
          window_seconds: parsePositiveInteger(windowSeconds, "Window"),
          enabled,
        },
        token,
      );
    },
    onSuccess: (rule) => {
      setOperationError(null);
      setOperationMessage(`Created alert rule ${rule.name}.`);
      closeCreateForm();
      queryClient.invalidateQueries({ queryKey: ["alert-rules", projectId] });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Alert rule creation failed.",
      );
    },
  });
  const acknowledgeMutation = useMutation({
    mutationFn: (event: AlertEvent) => {
      if (!token) {
        throw new Error("Alert acknowledgement requires API access.");
      }
      return acknowledgeAlertEvent(event.id, token);
    },
    onSuccess: (event) => {
      setOperationError(null);
      setOperationMessage(`Acknowledged alert ${event.id.slice(0, 8)}.`);
      invalidateAlertState();
    },
    onError: () => {
      setOperationMessage(null);
      setOperationError("Alert acknowledgement failed.");
    },
  });
  const resolveMutation = useMutation({
    mutationFn: (event: AlertEvent) => {
      if (!token) {
        throw new Error("Alert resolution requires API access.");
      }
      return resolveAlertEvent(event.id, token);
    },
    onSuccess: (event) => {
      setOperationError(null);
      setOperationMessage(`Resolved alert ${event.id.slice(0, 8)}.`);
      invalidateAlertState();
    },
    onError: () => {
      setOperationMessage(null);
      setOperationError("Alert resolution failed.");
    },
  });

  function invalidateAlertState() {
    queryClient.invalidateQueries({ queryKey: ["alert-events", projectId] });
    queryClient.invalidateQueries({
      queryKey: ["monitoring-summary", projectId],
    });
  }

  function closeCreateForm() {
    setIsCreateOpen(false);
    setRuleName("");
    setRuleDescription("");
    setSeverity("warning");
    setMetric("inference_error_rate");
    setOperator("gt");
    setThreshold("0.05");
    setWindowSeconds("300");
    setEnabled(true);
  }

  function handleCreateRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (ruleName.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Alert rule name must be at least 3 characters.");
      return;
    }
    createRuleMutation.mutate();
  }

  return (
    <>
      <PageHeader
        eyebrow="Operations"
        title="Alerts"
        description="Alert rules, alert events, severity, acknowledgement, resolution, and runbook routing."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          label="Rules"
          value={String(rules.length)}
          detail="configured policies"
        />
        <MetricCard
          label="Enabled"
          value={String(rules.filter((rule) => rule.enabled).length)}
          detail="actively evaluated"
          tone="success"
        />
        <MetricCard
          label="Open"
          value={String(openEvents.length)}
          detail={`${acknowledgedEvents.length} acknowledged`}
          tone={openEvents.length > 0 ? "warning" : "success"}
        />
        <MetricCard
          label="Critical"
          value={String(criticalEvents.length)}
          detail="unresolved severity"
          tone={criticalEvents.length > 0 ? "danger" : "success"}
        />
      </div>
      {operationMessage ? (
        <div className="mt-4 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-signal">
          {operationMessage}
        </div>
      ) : null}
      {operationError ? (
        <div className="mt-4 rounded border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-risk">
          {operationError}
        </div>
      ) : null}

      <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <DataPanel title="Alert Events">
          {!canLoadAlerts ? (
            <StateMessage message="No project context is selected." />
          ) : eventsQuery.error ? (
            <StateMessage message="Alert event request failed." tone="danger" />
          ) : events.length === 0 ? (
            <StateMessage
              message={
                eventsQuery.isFetching
                  ? "Loading alert events."
                  : "No alert events have been recorded."
              }
            />
          ) : (
            <div className="space-y-3">
              {events.slice(0, 8).map((event) => (
                <AlertEventCard
                  key={event.id}
                  event={event}
                  onAcknowledge={() => acknowledgeMutation.mutate(event)}
                  onResolve={() => resolveMutation.mutate(event)}
                  isMutating={
                    acknowledgeMutation.isPending || resolveMutation.isPending
                  }
                />
              ))}
            </div>
          )}
        </DataPanel>

        <DataPanel
          title="Alert Rules"
          action={
            <button
              type="button"
              onClick={() => {
                setIsCreateOpen(true);
                setOperationError(null);
              }}
              className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              <Plus className="h-4 w-4" />
              Rule
            </button>
          }
        >
          {isCreateOpen ? (
            <form
              aria-label="Create alert rule"
              onSubmit={handleCreateRule}
              className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
            >
              <div className="grid gap-3 lg:grid-cols-[minmax(160px,0.8fr)_minmax(200px,1fr)]">
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Name
                  <input
                    value={ruleName}
                    onChange={(event) => setRuleName(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Description
                  <input
                    value={ruleDescription}
                    onChange={(event) => setRuleDescription(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
              </div>
              <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(160px,1fr)_120px_110px_120px_120px]">
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Metric
                  <select
                    value={metric}
                    onChange={(event) => setMetric(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  >
                    {alertMetrics.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Operator
                  <select
                    value={operator}
                    onChange={(event) => setOperator(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  >
                    {alertOperators.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Threshold
                  <input
                    value={threshold}
                    onChange={(event) => setThreshold(event.target.value)}
                    inputMode="decimal"
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Window
                  <input
                    value={windowSeconds}
                    onChange={(event) => setWindowSeconds(event.target.value)}
                    inputMode="numeric"
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Severity
                  <select
                    value={severity}
                    onChange={(event) => setSeverity(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  >
                    {alertSeverities.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="mt-3 flex flex-wrap items-end gap-2">
                <label className="inline-flex h-10 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(event) => setEnabled(event.target.checked)}
                    className="h-4 w-4 accent-emerald-600"
                  />
                  Enabled
                </label>
                <button
                  type="submit"
                  disabled={createRuleMutation.isPending}
                  className="inline-flex h-10 items-center gap-2 rounded bg-signal px-3 text-sm font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <Check className="h-4 w-4" />
                  Create rule
                </button>
                <button
                  type="button"
                  aria-label="Cancel alert rule creation"
                  onClick={closeCreateForm}
                  className="inline-flex h-10 w-10 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </form>
          ) : null}
          {!canLoadAlerts ? (
            <StateMessage message="No project context is selected." />
          ) : rulesQuery.error ? (
            <StateMessage message="Alert rule request failed." tone="danger" />
          ) : rules.length === 0 ? (
            <StateMessage
              message={
                rulesQuery.isFetching
                  ? "Loading alert rules."
                  : "No alert rules configured."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Rule</th>
                    <th>Metric</th>
                    <th>Condition</th>
                    <th>Severity</th>
                    <th>Window</th>
                    <th>State</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.id} className="border-t border-slate-100">
                      <td className="py-3">
                        <div className="font-medium">{rule.name}</div>
                        <div className="text-xs text-steel">
                          {rule.description || rule.slug}
                        </div>
                      </td>
                      <td>{formatMetric(rule.metric)}</td>
                      <td>
                        {rule.operator} {formatThreshold(rule)}
                      </td>
                      <td>{rule.severity}</td>
                      <td>{rule.window_seconds}s</td>
                      <td>{rule.enabled ? "enabled" : "disabled"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>
      </div>
    </>
  );
}

function AlertEventCard({
  event,
  onAcknowledge,
  onResolve,
  isMutating,
}: {
  event: AlertEvent;
  onAcknowledge: () => void;
  onResolve: () => void;
  isMutating: boolean;
}) {
  return (
    <div className={eventClassName(event.severity)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-medium">{event.message}</div>
          <div className="mt-1 text-xs">
            observed {event.observed_value.toFixed(4)} / threshold{" "}
            {event.threshold.toFixed(4)}
          </div>
          <div className="mt-1 text-xs">
            endpoint {event.endpoint_id?.slice(0, 8) ?? "project"} / rule{" "}
            {event.alert_rule_id.slice(0, 8)}
          </div>
        </div>
        <span className="rounded bg-white px-2 py-1 text-xs font-medium">
          {event.status}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {event.status === "open" ? (
          <button
            type="button"
            aria-label={`Acknowledge alert ${event.id.slice(0, 8)}`}
            onClick={onAcknowledge}
            disabled={isMutating}
            className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-ink transition hover:border-ink disabled:cursor-not-allowed disabled:opacity-60"
          >
            <CircleCheck className="h-3.5 w-3.5" />
            Acknowledge
          </button>
        ) : null}
        {event.status !== "resolved" ? (
          <button
            type="button"
            aria-label={`Resolve alert ${event.id.slice(0, 8)}`}
            onClick={onResolve}
            disabled={isMutating}
            className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-ink transition hover:border-risk disabled:cursor-not-allowed disabled:opacity-60"
          >
            <CircleX className="h-3.5 w-3.5" />
            Resolve
          </button>
        ) : (
          <span className="text-xs text-steel">No action</span>
        )}
      </div>
    </div>
  );
}

const alertMetrics = [
  { value: "inference_error_rate", label: "error rate" },
  { value: "inference_p95_latency_ms", label: "p95 latency" },
  { value: "inference_prediction_count", label: "prediction count" },
];

const alertOperators = [
  { value: "gt", label: ">" },
  { value: "gte", label: ">=" },
  { value: "lt", label: "<" },
  { value: "lte", label: "<=" },
];

const alertSeverities = ["info", "warning", "critical"];

function parsePositiveInteger(value: string, label: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${label} must be a positive integer.`);
  }
  return parsed;
}

function parseNonNegativeFloat(value: string, label: string): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new Error(`${label} must be a non-negative number.`);
  }
  return parsed;
}

function formatThreshold(rule: AlertRule): string {
  if (rule.metric === "inference_error_rate") {
    return `${(rule.threshold * 100).toFixed(1)}%`;
  }
  if (rule.metric === "inference_p95_latency_ms") {
    return `${rule.threshold.toFixed(1)}ms`;
  }
  return String(rule.threshold);
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

function eventClassName(severity: string): string {
  if (severity === "critical") {
    return "rounded border border-rose-200 bg-rose-50 p-3 text-sm text-risk";
  }
  if (severity === "info") {
    return "rounded border border-slate-200 bg-cloud p-3 text-sm text-steel";
  }
  return "rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800";
}

function formatMetric(metric: string): string {
  return metric.replaceAll("_", " ");
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
