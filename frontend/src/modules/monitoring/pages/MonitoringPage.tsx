import { useQuery } from "@tanstack/react-query";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  getProjectMonitoringSummary,
  listInferenceEndpointMonitoringSummaries
} from "../api/monitoring";

export function MonitoringPage() {
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadMonitoring = Boolean(token && projectId);
  const summaryQuery = useQuery({
    queryKey: ["monitoring-summary", projectId],
    queryFn: () => getProjectMonitoringSummary(projectId ?? "", token ?? ""),
    enabled: canLoadMonitoring
  });
  const endpointsQuery = useQuery({
    queryKey: ["monitoring-inference-endpoints", projectId],
    queryFn: () => listInferenceEndpointMonitoringSummaries(projectId ?? "", token ?? ""),
    enabled: canLoadMonitoring
  });
  const summary = summaryQuery.data;
  const endpoints = endpointsQuery.data?.items ?? [];

  return (
    <>
      <PageHeader
        eyebrow="Observability"
        title="Monitoring"
        description="Latency, CPU, memory, prediction count, training time, pipeline failures, feature drift, and inference errors."
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
          tone={summary && summary.error_rate > 0.05 ? "danger" : "success"}
        />
        <MetricCard
          label="Active Alerts"
          value={String(summary?.active_alert_count ?? 0)}
          detail={`${(summary?.max_p95_latency_ms ?? 0).toFixed(1)}ms max p95`}
          tone={summary && summary.active_alert_count > 0 ? "warning" : "success"}
        />
      </div>
      <div className="mt-6">
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
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Endpoint</th>
                    <th>Predictions</th>
                    <th>Error Rate</th>
                    <th>p50</th>
                    <th>p95</th>
                    <th>Window</th>
                  </tr>
                </thead>
                <tbody>
                  {endpoints.map((endpoint) => (
                    <tr key={endpoint.endpoint_id} className="border-t border-slate-100">
                      <td className="py-3">
                        <div className="font-medium">{endpoint.endpoint_name}</div>
                        <code className="text-xs text-steel">{endpoint.route_path}</code>
                      </td>
                      <td>{endpoint.prediction_count}</td>
                      <td>{formatPercent(endpoint.error_rate)}</td>
                      <td>{endpoint.p50_latency_ms.toFixed(1)}ms</td>
                      <td>{endpoint.p95_latency_ms.toFixed(1)}ms</td>
                      <td>{endpoint.latest_window_seconds}s</td>
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

function StateMessage({
  message,
  tone = "neutral"
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

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
