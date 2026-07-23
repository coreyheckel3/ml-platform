import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play } from "lucide-react";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  listInferenceEndpoints,
  listInferenceMetricSnapshots,
  listInferenceRequests,
  predictEndpoint
} from "../api/inference";

export function InferencePage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadEndpoints = Boolean(token && projectId);
  const endpointsQuery = useQuery({
    queryKey: ["inference-endpoints", projectId],
    queryFn: () => listInferenceEndpoints(projectId ?? "", token ?? ""),
    enabled: canLoadEndpoints
  });
  const endpoints = endpointsQuery.data?.items ?? [];
  const selectedEndpoint = endpoints[0];
  const requestsQuery = useQuery({
    queryKey: ["inference-requests", selectedEndpoint?.id],
    queryFn: () => listInferenceRequests(selectedEndpoint?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedEndpoint)
  });
  const snapshotsQuery = useQuery({
    queryKey: ["inference-metric-snapshots", selectedEndpoint?.id],
    queryFn: () => listInferenceMetricSnapshots(selectedEndpoint?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedEndpoint)
  });
  const requestLogs = requestsQuery.data?.items ?? [];
  const snapshots = snapshotsQuery.data?.items ?? [];
  const latestSnapshot = snapshots[0];
  const errors = requestLogs.filter((requestLog) => requestLog.status !== "succeeded").length;
  const probeMutation = useMutation({
    mutationFn: () => {
      if (!selectedEndpoint || !token) {
        throw new Error("Missing endpoint context.");
      }
      return predictEndpoint(selectedEndpoint.id, token, {
        customer_tenure_days: 418,
        request_source: "control-plane-probe",
        amount: 128.45
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["inference-requests", selectedEndpoint?.id]
      });
    }
  });

  return (
    <>
      <PageHeader
        eyebrow="Serving"
        title="Inference"
        description="Prediction endpoints, request traces, latency snapshots, and serving revision attribution."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Endpoints" value={String(endpoints.length)} detail="project routes" />
        <MetricCard
          label="Predictions"
          value={String(latestSnapshot?.prediction_count ?? requestLogs.length)}
          detail={latestSnapshot ? `${latestSnapshot.window_seconds}s window` : "recent logs"}
        />
        <MetricCard label="Errors" value={String(latestSnapshot?.error_count ?? errors)} detail="selected route" />
        <MetricCard
          label="p95 Latency"
          value={latestSnapshot ? `${latestSnapshot.p95_latency_ms.toFixed(1)}ms` : "0ms"}
          detail="latest snapshot"
          tone={latestSnapshot && latestSnapshot.p95_latency_ms > 500 ? "warning" : "success"}
        />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <DataPanel title="Endpoints">
          {!canLoadEndpoints ? (
            <EmptyState message="No project context is selected." />
          ) : endpointsQuery.error ? (
            <ErrorState message="Inference endpoint request failed." />
          ) : endpoints.length === 0 ? (
            <EmptyState
              message={
                endpointsQuery.isFetching
                  ? "Loading inference endpoints."
                  : "No inference endpoints configured for this project."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Endpoint</th>
                    <th>Route</th>
                    <th>Status</th>
                    <th>Revision</th>
                  </tr>
                </thead>
                <tbody>
                  {endpoints.map((endpoint) => (
                    <tr key={endpoint.id} className="border-t border-slate-100">
                      <td className="py-3">
                        <div className="font-medium">{endpoint.name}</div>
                        <div className="text-xs text-steel">
                          {endpoint.description || "No description"}
                        </div>
                      </td>
                      <td>
                        <code className="rounded bg-field px-2 py-1 text-xs">
                          {endpoint.route_path}
                        </code>
                      </td>
                      <td>
                        <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                          {endpoint.status}
                        </span>
                      </td>
                      <td className="text-xs text-steel">
                        {endpoint.deployment_revision_id.slice(0, 8)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel
          title="Request Trace"
          action={
            selectedEndpoint ? (
              <button
                type="button"
                onClick={() => probeMutation.mutate()}
                disabled={probeMutation.isPending}
                className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 px-3 text-xs font-medium text-ink transition hover:bg-field disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Play className="h-3.5 w-3.5" aria-hidden="true" />
                Probe
              </button>
            ) : null
          }
        >
          {!selectedEndpoint ? (
            <EmptyState message="No endpoint is available for request review." />
          ) : requestsQuery.error ? (
            <ErrorState message="Inference request log request failed." />
          ) : requestLogs.length === 0 ? (
            <EmptyState
              message={
                requestsQuery.isFetching
                  ? "Loading inference requests."
                  : "No inference requests have been recorded."
              }
            />
          ) : (
            <div className="space-y-3">
              {requestLogs.slice(0, 5).map((requestLog) => (
                <div key={requestLog.id} className="rounded border border-slate-200 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{requestLog.request_id}</div>
                      <div className="mt-1 text-xs text-steel">
                        {requestLog.latency_ms.toFixed(2)}ms latency
                      </div>
                    </div>
                    <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                      {requestLog.status}
                    </span>
                  </div>
                  <pre className="mt-3 max-h-28 overflow-auto rounded bg-cloud p-3 text-xs text-steel">
                    {JSON.stringify(requestLog.output_payload, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6">
        <DataPanel title="Metric Snapshots">
          {snapshotsQuery.error ? (
            <ErrorState message="Inference metric snapshot request failed." />
          ) : snapshots.length === 0 ? (
            <EmptyState
              message={
                snapshotsQuery.isFetching
                  ? "Loading metric snapshots."
                  : "No metric snapshots have been recorded."
              }
            />
          ) : (
            <div className="grid gap-3 md:grid-cols-3">
              {snapshots.slice(0, 3).map((snapshot) => (
                <div key={snapshot.id} className="rounded border border-slate-200 p-3 text-sm">
                  <div className="font-medium">{snapshot.window_seconds}s window</div>
                  <div className="mt-2 text-steel">
                    {snapshot.prediction_count} predictions, {snapshot.error_count} errors
                  </div>
                  <div className="mt-2 text-xs text-steel">
                    p50 {snapshot.p50_latency_ms.toFixed(1)}ms / p95{" "}
                    {snapshot.p95_latency_ms.toFixed(1)}ms
                  </div>
                </div>
              ))}
            </div>
          )}
        </DataPanel>
      </div>
    </>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
      {message}
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk">
      {message}
    </div>
  );
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
