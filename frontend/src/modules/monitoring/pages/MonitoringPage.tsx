import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, BellRing, Gauge, Radar, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  evaluateAlertRule,
  listAlertEvents,
  listAlertRules,
  type AlertEvent,
  type AlertRule,
} from "../../alerts/api/alerts";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  getProjectMonitoringSummary,
  listInferenceEndpointMonitoringSummaries,
  type InferenceEndpointMonitoringSummary,
} from "../api/monitoring";

export function MonitoringPage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadMonitoring = Boolean(token && projectId);
  const [selectedEndpointId, setSelectedEndpointId] = useState("");
  const [selectedRuleId, setSelectedRuleId] = useState("");
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const summaryQuery = useQuery({
    queryKey: ["monitoring-summary", projectId],
    queryFn: () => getProjectMonitoringSummary(projectId ?? "", token ?? ""),
    enabled: canLoadMonitoring,
  });
  const endpointsQuery = useQuery({
    queryKey: ["monitoring-inference-endpoints", projectId],
    queryFn: () =>
      listInferenceEndpointMonitoringSummaries(projectId ?? "", token ?? ""),
    enabled: canLoadMonitoring,
  });
  const rulesQuery = useQuery({
    queryKey: ["alert-rules", projectId],
    queryFn: () => listAlertRules(projectId ?? "", token ?? ""),
    enabled: canLoadMonitoring,
  });
  const eventsQuery = useQuery({
    queryKey: ["alert-events", projectId],
    queryFn: () => listAlertEvents(projectId ?? "", token ?? ""),
    enabled: canLoadMonitoring,
  });
  const summary = summaryQuery.data;
  const endpoints = useMemo(
    () => endpointsQuery.data?.items ?? [],
    [endpointsQuery.data?.items],
  );
  const rules = useMemo(
    () => rulesQuery.data?.items ?? [],
    [rulesQuery.data?.items],
  );
  const events = eventsQuery.data?.items ?? [];
  const selectedEndpoint =
    endpoints.find((endpoint) => endpoint.endpoint_id === selectedEndpointId) ??
    endpoints[0];
  const selectedRule =
    rules.find((rule) => rule.id === selectedRuleId) ??
    bestRuleForEndpoint(rules, selectedEndpoint);
  const openEvents = events.filter((event) => event.status === "open");
  const selectedEndpointEvents = selectedEndpoint
    ? events.filter(
        (event) => event.endpoint_id === selectedEndpoint.endpoint_id,
      )
    : [];
  const selectedEndpointOpenEvents = selectedEndpointEvents.filter(
    (event) => event.status === "open",
  );
  const worstEndpoint =
    endpoints.reduce<InferenceEndpointMonitoringSummary | null>(
      (current, endpoint) => {
        if (!current) {
          return endpoint;
        }
        return riskScore(endpoint) > riskScore(current) ? endpoint : current;
      },
      null,
    );
  const evaluateMutation = useMutation({
    mutationFn: () => {
      if (!selectedEndpoint || !selectedRule || !token) {
        throw new Error(
          "Alert evaluation requires an endpoint and enabled rule.",
        );
      }
      return evaluateAlertRule(
        selectedRule.id,
        selectedEndpoint.endpoint_id,
        token,
      );
    },
    onSuccess: (evaluation) => {
      setOperationError(null);
      setOperationMessage(
        evaluation.triggered
          ? `Triggered ${selectedRule?.name ?? "rule"} at ${formatObservedValue(
              selectedRule,
              evaluation.observed_value,
            )}.`
          : `${selectedRule?.name ?? "Rule"} is clear at ${formatObservedValue(
              selectedRule,
              evaluation.observed_value,
            )}.`,
      );
      queryClient.invalidateQueries({ queryKey: ["alert-events", projectId] });
      queryClient.invalidateQueries({
        queryKey: ["monitoring-summary", projectId],
      });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error
          ? error.message
          : "Alert rule evaluation failed.",
      );
    },
  });

  useEffect(() => {
    if (!selectedEndpointId && endpoints[0]) {
      setSelectedEndpointId(endpoints[0].endpoint_id);
      return;
    }
    if (
      selectedEndpointId &&
      !endpoints.some((endpoint) => endpoint.endpoint_id === selectedEndpointId)
    ) {
      setSelectedEndpointId(endpoints[0]?.endpoint_id ?? "");
    }
  }, [endpoints, selectedEndpointId]);

  useEffect(() => {
    if (!selectedRuleId && selectedRule) {
      setSelectedRuleId(selectedRule.id);
      return;
    }
    if (selectedRuleId && !rules.some((rule) => rule.id === selectedRuleId)) {
      setSelectedRuleId(selectedRule?.id ?? "");
    }
  }, [rules, selectedRule, selectedRuleId]);

  return (
    <>
      <PageHeader
        eyebrow="Observability"
        title="Monitoring"
        description="Latency, prediction volume, inference errors, alert pressure, and endpoint-level production health."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          label="Endpoints"
          value={String(summary?.inference_endpoint_count ?? 0)}
          detail="inference routes"
        />
        <MetricCard
          label="Predictions"
          value={String(summary?.prediction_count ?? 0)}
          detail="latest snapshots"
        />
        <MetricCard
          label="Error Rate"
          value={formatPercent(summary?.error_rate ?? 0)}
          detail={`${summary?.error_count ?? 0} errors`}
          tone={
            summary && summary.error_rate > errorRateBudget
              ? "danger"
              : "success"
          }
        />
        <MetricCard
          label="Active Alerts"
          value={String(summary?.active_alert_count ?? openEvents.length)}
          detail={`${(summary?.max_p95_latency_ms ?? 0).toFixed(1)}ms max p95`}
          tone={
            summary && summary.active_alert_count > 0
              ? "warning"
              : openEvents.length > 0
                ? "warning"
                : "success"
          }
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

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <DataPanel title="Inference Endpoint Health">
          {!canLoadMonitoring ? (
            <StateMessage message="No project context is selected." />
          ) : summaryQuery.error || endpointsQuery.error ? (
            <StateMessage message="Monitoring request failed." tone="danger" />
          ) : endpoints.length === 0 ? (
            <StateMessage
              message={
                endpointsQuery.isFetching
                  ? "Loading monitoring data."
                  : "No inference endpoints are available for monitoring."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Endpoint</th>
                    <th>Predictions</th>
                    <th>Error Rate</th>
                    <th>p50</th>
                    <th>p95</th>
                    <th>Risk</th>
                    <th>Selected</th>
                  </tr>
                </thead>
                <tbody>
                  {endpoints.map((endpoint) => (
                    <tr
                      key={endpoint.endpoint_id}
                      className="border-t border-slate-100"
                    >
                      <td className="py-3">
                        <div className="font-medium">
                          {endpoint.endpoint_name}
                        </div>
                        <code className="text-xs text-steel">
                          {endpoint.route_path}
                        </code>
                      </td>
                      <td>{endpoint.prediction_count}</td>
                      <td>{formatPercent(endpoint.error_rate)}</td>
                      <td>{endpoint.p50_latency_ms.toFixed(1)}ms</td>
                      <td>{endpoint.p95_latency_ms.toFixed(1)}ms</td>
                      <td>
                        <RiskBadge endpoint={endpoint} />
                      </td>
                      <td>
                        <button
                          type="button"
                          onClick={() =>
                            setSelectedEndpointId(endpoint.endpoint_id)
                          }
                          className={[
                            "inline-flex h-8 items-center rounded border px-3 text-xs font-semibold transition",
                            endpoint.endpoint_id ===
                            selectedEndpoint?.endpoint_id
                              ? "border-ink bg-ink text-white"
                              : "border-slate-200 bg-white text-steel hover:text-ink",
                          ].join(" ")}
                        >
                          {endpoint.endpoint_id ===
                          selectedEndpoint?.endpoint_id
                            ? "Active"
                            : "Select"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel title="Endpoint Drilldown">
          {!selectedEndpoint ? (
            <StateMessage message="No endpoint is selected." />
          ) : (
            <div className="grid gap-4">
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold">
                      {selectedEndpoint.endpoint_name}
                    </div>
                    <code className="mt-1 block text-xs text-steel">
                      {selectedEndpoint.route_path}
                    </code>
                  </div>
                  <RiskBadge endpoint={selectedEndpoint} />
                </div>
                <div className="mt-3 grid gap-2 text-xs text-steel">
                  <div>status: {selectedEndpoint.status}</div>
                  <div>
                    revision:{" "}
                    {selectedEndpoint.deployment_revision_id.slice(0, 8)}
                  </div>
                  <div>window: {selectedEndpoint.latest_window_seconds}s</div>
                </div>
              </div>
              <BudgetBar
                label="Error budget"
                value={selectedEndpoint.error_rate}
                budget={errorRateBudget}
                formatter={formatPercent}
              />
              <BudgetBar
                label="p95 latency"
                value={selectedEndpoint.p95_latency_ms}
                budget={latencyBudgetMs}
                formatter={(value) => `${value.toFixed(1)}ms`}
              />
              <div className="grid grid-cols-3 gap-3 text-sm">
                <SignalTile
                  icon={<Activity className="h-4 w-4" />}
                  label="Requests"
                  value={String(selectedEndpoint.request_count)}
                />
                <SignalTile
                  icon={<Gauge className="h-4 w-4" />}
                  label="p50"
                  value={`${selectedEndpoint.p50_latency_ms.toFixed(1)}ms`}
                />
                <SignalTile
                  icon={<BellRing className="h-4 w-4" />}
                  label="Open"
                  value={String(selectedEndpointOpenEvents.length)}
                />
              </div>
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <DataPanel title="Alert Evaluation">
          {!selectedEndpoint ? (
            <StateMessage message="Select an endpoint before evaluating alert rules." />
          ) : rulesQuery.error ? (
            <StateMessage message="Alert rule request failed." tone="danger" />
          ) : rules.length === 0 ? (
            <StateMessage
              message={
                rulesQuery.isFetching
                  ? "Loading alert rules."
                  : "No alert rules are configured for this project."
              }
            />
          ) : (
            <div className="grid gap-4">
              <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                Rule
                <select
                  value={selectedRule?.id ?? ""}
                  onChange={(event) => setSelectedRuleId(event.target.value)}
                  className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                >
                  {rules.map((rule) => (
                    <option key={rule.id} value={rule.id}>
                      {rule.name} - {formatMetric(rule.metric)}
                    </option>
                  ))}
                </select>
              </label>
              {selectedRule ? <RuleSummary rule={selectedRule} /> : null}
              <button
                type="button"
                onClick={() => evaluateMutation.mutate()}
                disabled={evaluateMutation.isPending || !selectedRule}
                className="inline-flex h-10 w-fit items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <RefreshCw className="h-4 w-4" />
                Evaluate rule
              </button>
            </div>
          )}
        </DataPanel>

        <DataPanel title="Alert Context">
          {eventsQuery.error ? (
            <StateMessage message="Alert event request failed." tone="danger" />
          ) : !selectedEndpoint ? (
            <StateMessage message="No endpoint is selected." />
          ) : selectedEndpointEvents.length === 0 ? (
            <StateMessage
              message={
                eventsQuery.isFetching
                  ? "Loading alert context."
                  : "No alert events are linked to this endpoint."
              }
            />
          ) : (
            <div className="space-y-3">
              {selectedEndpointEvents.slice(0, 5).map((event) => (
                <AlertEventRow key={event.id} event={event} />
              ))}
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6">
        <DataPanel title="Operational Focus">
          {!worstEndpoint ? (
            <StateMessage message="No endpoint signals are available." />
          ) : (
            <div className="grid gap-4 md:grid-cols-[220px_1fr_1fr]">
              <SignalTile
                icon={<Radar className="h-4 w-4" />}
                label="Highest risk"
                value={worstEndpoint.endpoint_name}
              />
              <BudgetBar
                label="Highest-risk error rate"
                value={worstEndpoint.error_rate}
                budget={errorRateBudget}
                formatter={formatPercent}
              />
              <BudgetBar
                label="Highest-risk p95"
                value={worstEndpoint.p95_latency_ms}
                budget={latencyBudgetMs}
                formatter={(value) => `${value.toFixed(1)}ms`}
              />
            </div>
          )}
        </DataPanel>
      </div>
    </>
  );
}

const errorRateBudget = 0.05;
const latencyBudgetMs = 500;

function RiskBadge({
  endpoint,
}: {
  endpoint: InferenceEndpointMonitoringSummary;
}) {
  const score = riskScore(endpoint);
  const label = score >= 2 ? "critical" : score >= 1 ? "watch" : "normal";
  const className =
    label === "critical"
      ? "rounded bg-rose-50 px-2 py-1 text-xs font-semibold text-risk"
      : label === "watch"
        ? "rounded bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700"
        : "rounded bg-emerald-50 px-2 py-1 text-xs font-semibold text-signal";
  return <span className={className}>{label}</span>;
}

function riskScore(endpoint: InferenceEndpointMonitoringSummary): number {
  let score = 0;
  if (endpoint.error_rate > errorRateBudget) {
    score += 1;
  }
  if (endpoint.p95_latency_ms > latencyBudgetMs) {
    score += 1;
  }
  return score;
}

function BudgetBar({
  label,
  value,
  budget,
  formatter,
}: {
  label: string;
  value: number;
  budget: number;
  formatter: (value: number) => string;
}) {
  const ratio = budget === 0 ? 0 : value / budget;
  const width = `${Math.min(ratio, 1) * 100}%`;
  const exceeded = value > budget;
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-xs text-steel">
        <span className="font-semibold uppercase">{label}</span>
        <span>
          {formatter(value)} / {formatter(budget)}
        </span>
      </div>
      <div className="mt-2 h-3 overflow-hidden rounded bg-field">
        <div
          className={exceeded ? "h-full bg-risk" : "h-full bg-signal"}
          style={{ width }}
        />
      </div>
    </div>
  );
}

function SignalTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded border border-slate-200 p-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase text-steel">
        {icon}
        {label}
      </div>
      <div className="mt-2 truncate text-sm font-medium">{value}</div>
    </div>
  );
}

function RuleSummary({ rule }: { rule: AlertRule }) {
  return (
    <div className="rounded border border-slate-200 p-3 text-sm">
      <div className="font-medium">{rule.name}</div>
      <div className="mt-2 text-steel">
        {formatMetric(rule.metric)} {rule.operator} {formatRuleThreshold(rule)}
      </div>
      <div className="mt-2 text-xs text-steel">
        {rule.severity} severity, {rule.window_seconds}s window,{" "}
        {rule.enabled ? "enabled" : "disabled"}
      </div>
    </div>
  );
}

function AlertEventRow({ event }: { event: AlertEvent }) {
  const className =
    event.severity === "critical"
      ? "rounded border border-rose-200 bg-rose-50 p-3 text-sm text-risk"
      : "rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800";
  return (
    <div className={className}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-medium">{event.message}</div>
          <div className="mt-1 text-xs">
            observed {event.observed_value.toFixed(4)} / threshold{" "}
            {event.threshold.toFixed(4)}
          </div>
        </div>
        <span className="rounded bg-white px-2 py-1 text-xs font-medium">
          {event.status}
        </span>
      </div>
    </div>
  );
}

function bestRuleForEndpoint(
  rules: AlertRule[],
  endpoint: InferenceEndpointMonitoringSummary | undefined,
): AlertRule | undefined {
  if (!endpoint) {
    return rules[0];
  }
  const p95Rule = rules.find(
    (rule) => rule.metric === "inference_p95_latency_ms",
  );
  const errorRule = rules.find(
    (rule) => rule.metric === "inference_error_rate",
  );
  if (endpoint.p95_latency_ms > latencyBudgetMs && p95Rule) {
    return p95Rule;
  }
  if (endpoint.error_rate > errorRateBudget && errorRule) {
    return errorRule;
  }
  return errorRule ?? p95Rule ?? rules[0];
}

function formatRuleThreshold(rule: AlertRule): string {
  if (rule.metric === "inference_error_rate") {
    return formatPercent(rule.threshold);
  }
  if (rule.metric === "inference_p95_latency_ms") {
    return `${rule.threshold.toFixed(1)}ms`;
  }
  return String(rule.threshold);
}

function formatObservedValue(
  rule: AlertRule | undefined,
  value: number,
): string {
  if (rule?.metric === "inference_error_rate") {
    return formatPercent(value);
  }
  if (rule?.metric === "inference_p95_latency_ms") {
    return `${value.toFixed(1)}ms`;
  }
  return String(value);
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

function formatMetric(metric: string): string {
  return metric.replaceAll("_", " ");
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
