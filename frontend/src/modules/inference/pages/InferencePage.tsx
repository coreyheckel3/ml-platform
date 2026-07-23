import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, Play, RadioTower, Send } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import {
  listDeploymentRevisions,
  listDeployments,
} from "../../deployments/api/deployments";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  createInferenceEndpoint,
  listInferenceEndpoints,
  listInferenceMetricSnapshots,
  listInferenceRequests,
  predictEndpoint,
  recordInferenceMetricSnapshot,
} from "../api/inference";

export function InferencePage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadEndpoints = Boolean(token && projectId);
  const [selectedEndpointId, setSelectedEndpointId] = useState("");
  const [selectedDeploymentId, setSelectedDeploymentId] = useState("");
  const [selectedRevisionId, setSelectedRevisionId] = useState("");
  const [endpointName, setEndpointName] = useState("");
  const [endpointDescription, setEndpointDescription] = useState("");
  const [routePath, setRoutePath] = useState("");
  const [probeRequestId, setProbeRequestId] = useState("control-plane-probe");
  const [probePayloadText, setProbePayloadText] = useState(
    JSON.stringify(defaultProbePayload, null, 2),
  );
  const [windowSeconds, setWindowSeconds] = useState("300");
  const [predictionCount, setPredictionCount] = useState("1200");
  const [errorCount, setErrorCount] = useState("3");
  const [p50LatencyMs, setP50LatencyMs] = useState("42");
  const [p95LatencyMs, setP95LatencyMs] = useState("138");
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const endpointsQuery = useQuery({
    queryKey: ["inference-endpoints", projectId],
    queryFn: () => listInferenceEndpoints(projectId ?? "", token ?? ""),
    enabled: canLoadEndpoints,
  });
  const deploymentsQuery = useQuery({
    queryKey: ["deployments", projectId],
    queryFn: () => listDeployments(projectId ?? "", token ?? ""),
    enabled: canLoadEndpoints,
  });
  const deployments = useMemo(
    () => deploymentsQuery.data?.items ?? [],
    [deploymentsQuery.data?.items],
  );
  const selectedDeployment =
    deployments.find((deployment) => deployment.id === selectedDeploymentId) ??
    deployments[0];
  const activeDeploymentId = selectedDeployment?.id ?? "";
  const revisionsQuery = useQuery({
    queryKey: ["deployment-revisions", activeDeploymentId],
    queryFn: () => listDeploymentRevisions(activeDeploymentId, token ?? ""),
    enabled: Boolean(token && activeDeploymentId),
  });
  const revisions = useMemo(
    () =>
      [...(revisionsQuery.data?.items ?? [])].sort(
        (left, right) => right.revision - left.revision,
      ),
    [revisionsQuery.data?.items],
  );
  const servableRevisions = useMemo(() => {
    if (selectedDeployment?.status !== "active") {
      return [];
    }
    return revisions.filter((revision) => {
      return (
        (revision.status === "healthy" || revision.status === "degraded") &&
        revision.traffic_percentage > 0
      );
    });
  }, [revisions, selectedDeployment?.status]);
  const selectedRevision =
    servableRevisions.find((revision) => revision.id === selectedRevisionId) ??
    servableRevisions[0];
  const endpoints = useMemo(
    () => endpointsQuery.data?.items ?? [],
    [endpointsQuery.data?.items],
  );
  const selectedEndpoint =
    endpoints.find((endpoint) => endpoint.id === selectedEndpointId) ??
    endpoints[0];
  const requestsQuery = useQuery({
    queryKey: ["inference-requests", selectedEndpoint?.id],
    queryFn: () =>
      listInferenceRequests(selectedEndpoint?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedEndpoint),
  });
  const snapshotsQuery = useQuery({
    queryKey: ["inference-metric-snapshots", selectedEndpoint?.id],
    queryFn: () =>
      listInferenceMetricSnapshots(selectedEndpoint?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedEndpoint),
  });
  const requestLogs = requestsQuery.data?.items ?? [];
  const snapshots = snapshotsQuery.data?.items ?? [];
  const latestSnapshot = snapshots[0];
  const errors = requestLogs.filter(
    (requestLog) => requestLog.status !== "succeeded",
  ).length;
  const createEndpointMutation = useMutation({
    mutationFn: () => {
      if (!projectId || !token || !selectedDeployment || !selectedRevision) {
        throw new Error(
          "Endpoint creation requires a deployment and servable revision.",
        );
      }
      return createInferenceEndpoint(
        projectId,
        {
          deployment_id: selectedDeployment.id,
          deployment_revision_id: selectedRevision.id,
          name: endpointName.trim(),
          description: endpointDescription.trim(),
          route_path: routePath.trim() || null,
        },
        token,
      );
    },
    onSuccess: (endpoint) => {
      setOperationError(null);
      setOperationMessage(`Created endpoint ${endpoint.name}.`);
      setSelectedEndpointId(endpoint.id);
      setEndpointName("");
      setEndpointDescription("");
      setRoutePath("");
      queryClient.invalidateQueries({
        queryKey: ["inference-endpoints", projectId],
      });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error
          ? error.message
          : "Inference endpoint creation failed.",
      );
    },
  });
  const probeMutation = useMutation({
    mutationFn: () => {
      if (!selectedEndpoint || !token) {
        throw new Error("Missing endpoint context.");
      }
      return predictEndpoint(selectedEndpoint.id, token, {
        request_id: probeRequestId.trim() || undefined,
        payload: parseJsonObject(probePayloadText, "Probe payload"),
      });
    },
    onSuccess: (prediction) => {
      setOperationError(null);
      setOperationMessage(
        `Probe ${prediction.request_id} ${prediction.status} in ${prediction.latency_ms.toFixed(1)}ms.`,
      );
      queryClient.invalidateQueries({
        queryKey: ["inference-requests", selectedEndpoint?.id],
      });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Probe failed.",
      );
    },
  });
  const snapshotMutation = useMutation({
    mutationFn: () => {
      if (!selectedEndpoint || !token) {
        throw new Error("Metric snapshots require a selected endpoint.");
      }
      return recordInferenceMetricSnapshot(
        selectedEndpoint.id,
        {
          window_seconds: parsePositiveInteger(windowSeconds, "Window"),
          prediction_count: parseNonNegativeInteger(
            predictionCount,
            "Prediction count",
          ),
          error_count: parseNonNegativeInteger(errorCount, "Error count"),
          p50_latency_ms: parseNonNegativeFloat(p50LatencyMs, "p50 latency"),
          p95_latency_ms: parseNonNegativeFloat(p95LatencyMs, "p95 latency"),
        },
        token,
      );
    },
    onSuccess: (snapshot) => {
      setOperationError(null);
      setOperationMessage(
        `Recorded ${snapshot.window_seconds}s snapshot for ${snapshot.prediction_count} predictions.`,
      );
      queryClient.invalidateQueries({
        queryKey: ["inference-metric-snapshots", selectedEndpoint?.id],
      });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error
          ? error.message
          : "Metric snapshot recording failed.",
      );
    },
  });

  useEffect(() => {
    if (!selectedDeploymentId && deployments[0]) {
      setSelectedDeploymentId(deployments[0].id);
      return;
    }
    if (
      selectedDeploymentId &&
      !deployments.some((deployment) => deployment.id === selectedDeploymentId)
    ) {
      setSelectedDeploymentId(deployments[0]?.id ?? "");
    }
  }, [deployments, selectedDeploymentId]);

  useEffect(() => {
    if (!selectedRevisionId && servableRevisions[0]) {
      setSelectedRevisionId(servableRevisions[0].id);
      return;
    }
    if (
      selectedRevisionId &&
      !servableRevisions.some((revision) => revision.id === selectedRevisionId)
    ) {
      setSelectedRevisionId(servableRevisions[0]?.id ?? "");
    }
  }, [selectedRevisionId, servableRevisions]);

  useEffect(() => {
    if (!selectedEndpointId && endpoints[0]) {
      setSelectedEndpointId(endpoints[0].id);
      return;
    }
    if (
      selectedEndpointId &&
      !endpoints.some((endpoint) => endpoint.id === selectedEndpointId)
    ) {
      setSelectedEndpointId(endpoints[0]?.id ?? "");
    }
  }, [endpoints, selectedEndpointId]);

  function handleCreateEndpoint(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (endpointName.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Endpoint name must be at least 3 characters.");
      return;
    }
    createEndpointMutation.mutate();
  }

  function handleProbe(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    probeMutation.mutate();
  }

  function handleRecordSnapshot(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    snapshotMutation.mutate();
  }

  return (
    <>
      <PageHeader
        eyebrow="Serving"
        title="Inference"
        description="Prediction endpoints, request traces, latency snapshots, and serving revision attribution."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          label="Endpoints"
          value={String(endpoints.length)}
          detail="project routes"
        />
        <MetricCard
          label="Predictions"
          value={String(latestSnapshot?.prediction_count ?? requestLogs.length)}
          detail={
            latestSnapshot
              ? `${latestSnapshot.window_seconds}s window`
              : "recent logs"
          }
        />
        <MetricCard
          label="Errors"
          value={String(latestSnapshot?.error_count ?? errors)}
          detail="selected route"
          tone={latestSnapshot?.error_count || errors ? "warning" : "success"}
        />
        <MetricCard
          label="p95 Latency"
          value={
            latestSnapshot
              ? `${latestSnapshot.p95_latency_ms.toFixed(1)}ms`
              : "0ms"
          }
          detail="latest snapshot"
          tone={
            latestSnapshot && latestSnapshot.p95_latency_ms > 500
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

      <div className="mt-6">
        <DataPanel title="Endpoint Launchpad">
          {!canLoadEndpoints ? (
            <EmptyState message="No project context is selected." />
          ) : deploymentsQuery.error || revisionsQuery.error ? (
            <ErrorState message="Deployment serving candidate request failed." />
          ) : deployments.length === 0 ? (
            <EmptyState
              message={
                deploymentsQuery.isFetching
                  ? "Loading deployments."
                  : "No deployment targets are available."
              }
            />
          ) : servableRevisions.length === 0 ? (
            <div className="grid gap-4">
              <label className="grid max-w-sm gap-1 text-xs font-semibold uppercase text-steel">
                Deployment
                <select
                  value={activeDeploymentId}
                  onChange={(event) =>
                    setSelectedDeploymentId(event.target.value)
                  }
                  className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                >
                  {deployments.map((deployment) => (
                    <option key={deployment.id} value={deployment.id}>
                      {deployment.name}
                    </option>
                  ))}
                </select>
              </label>
              <EmptyState
                message={
                  revisionsQuery.isFetching
                    ? "Loading deployment revisions."
                    : "No healthy or degraded revisions with active traffic are available."
                }
              />
            </div>
          ) : (
            <form
              aria-label="Create inference endpoint"
              onSubmit={handleCreateEndpoint}
              className="grid gap-4"
            >
              <div className="grid gap-3 xl:grid-cols-[minmax(180px,0.8fr)_minmax(180px,0.8fr)_minmax(180px,0.8fr)_minmax(160px,0.7fr)]">
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Deployment
                  <select
                    value={activeDeploymentId}
                    onChange={(event) =>
                      setSelectedDeploymentId(event.target.value)
                    }
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  >
                    {deployments.map((deployment) => (
                      <option key={deployment.id} value={deployment.id}>
                        {deployment.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Revision
                  <select
                    value={selectedRevision?.id ?? ""}
                    onChange={(event) =>
                      setSelectedRevisionId(event.target.value)
                    }
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  >
                    {servableRevisions.map((revision) => (
                      <option key={revision.id} value={revision.id}>
                        r{revision.revision} - {revision.status} -{" "}
                        {revision.traffic_percentage}%
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Name
                  <input
                    value={endpointName}
                    onChange={(event) => setEndpointName(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Route
                  <input
                    value={routePath}
                    onChange={(event) => setRoutePath(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
              </div>
              <div className="grid gap-3 xl:grid-cols-[minmax(260px,1fr)_auto]">
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Description
                  <input
                    value={endpointDescription}
                    onChange={(event) =>
                      setEndpointDescription(event.target.value)
                    }
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <div className="flex items-end">
                  <button
                    type="submit"
                    disabled={createEndpointMutation.isPending}
                    className="inline-flex h-10 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <RadioTower className="h-4 w-4" />
                    Create endpoint
                  </button>
                </div>
              </div>
            </form>
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
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
              <table className="w-full min-w-[820px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Endpoint</th>
                    <th>Route</th>
                    <th>Status</th>
                    <th>Revision</th>
                    <th>Selected</th>
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
                        <StatusBadge value={endpoint.status} />
                      </td>
                      <td className="text-xs text-steel">
                        {endpoint.deployment_revision_id.slice(0, 8)}
                      </td>
                      <td>
                        <button
                          type="button"
                          onClick={() => setSelectedEndpointId(endpoint.id)}
                          className={[
                            "inline-flex h-8 items-center rounded border px-3 text-xs font-semibold transition",
                            endpoint.id === selectedEndpoint?.id
                              ? "border-ink bg-ink text-white"
                              : "border-slate-200 bg-white text-steel hover:text-ink",
                          ].join(" ")}
                        >
                          {endpoint.id === selectedEndpoint?.id
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

        <DataPanel title="Probe Console">
          {!selectedEndpoint ? (
            <EmptyState message="No endpoint is available for probing." />
          ) : (
            <form
              aria-label="Probe inference endpoint"
              onSubmit={handleProbe}
              className="grid gap-3"
            >
              <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                Request id
                <input
                  value={probeRequestId}
                  onChange={(event) => setProbeRequestId(event.target.value)}
                  className="h-10 rounded border border-slate-200 bg-white px-3 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
                />
              </label>
              <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                Payload
                <textarea
                  value={probePayloadText}
                  onChange={(event) => setProbePayloadText(event.target.value)}
                  rows={8}
                  className="min-h-44 rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
                />
              </label>
              <div>
                <button
                  type="submit"
                  disabled={probeMutation.isPending}
                  className="inline-flex h-10 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Play className="h-4 w-4" />
                  Probe endpoint
                </button>
              </div>
            </form>
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <DataPanel title="Request Trace">
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
                <div
                  key={requestLog.id}
                  className="rounded border border-slate-200 p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{requestLog.request_id}</div>
                      <div className="mt-1 text-xs text-steel">
                        {requestLog.latency_ms.toFixed(2)}ms latency
                      </div>
                    </div>
                    <StatusBadge value={requestLog.status} />
                  </div>
                  <pre className="mt-3 max-h-28 overflow-auto rounded bg-cloud p-3 text-xs text-steel">
                    {JSON.stringify(requestLog.output_payload, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </DataPanel>

        <DataPanel title="Metric Snapshots">
          {!selectedEndpoint ? (
            <EmptyState message="No endpoint is available for metrics." />
          ) : snapshotsQuery.error ? (
            <ErrorState message="Inference metric snapshot request failed." />
          ) : (
            <div className="grid gap-4">
              <form
                aria-label="Record inference metric snapshot"
                onSubmit={handleRecordSnapshot}
                className="grid gap-3"
              >
                <div className="grid gap-3 md:grid-cols-3">
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
                    Predictions
                    <input
                      value={predictionCount}
                      onChange={(event) =>
                        setPredictionCount(event.target.value)
                      }
                      inputMode="numeric"
                      className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                    />
                  </label>
                  <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                    Errors
                    <input
                      value={errorCount}
                      onChange={(event) => setErrorCount(event.target.value)}
                      inputMode="numeric"
                      className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                    />
                  </label>
                </div>
                <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                  <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                    p50 latency
                    <input
                      value={p50LatencyMs}
                      onChange={(event) => setP50LatencyMs(event.target.value)}
                      inputMode="decimal"
                      className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                    />
                  </label>
                  <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                    p95 latency
                    <input
                      value={p95LatencyMs}
                      onChange={(event) => setP95LatencyMs(event.target.value)}
                      inputMode="decimal"
                      className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                    />
                  </label>
                  <div className="flex items-end">
                    <button
                      type="submit"
                      disabled={snapshotMutation.isPending}
                      className="inline-flex h-10 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-sm font-semibold text-ink transition hover:border-ink disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <Send className="h-4 w-4" />
                      Record snapshot
                    </button>
                  </div>
                </div>
              </form>
              {snapshots.length === 0 ? (
                <EmptyState
                  message={
                    snapshotsQuery.isFetching
                      ? "Loading metric snapshots."
                      : "No metric snapshots have been recorded."
                  }
                />
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {snapshots.slice(0, 4).map((snapshot) => (
                    <div
                      key={snapshot.id}
                      className="rounded border border-slate-200 p-3 text-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="font-medium">
                          {snapshot.window_seconds}s window
                        </div>
                        <BarChart3 className="h-4 w-4 text-steel" />
                      </div>
                      <div className="mt-2 text-steel">
                        {snapshot.prediction_count} predictions,{" "}
                        {snapshot.error_count} errors
                      </div>
                      <div className="mt-2 text-xs text-steel">
                        p50 {snapshot.p50_latency_ms.toFixed(1)}ms / p95{" "}
                        {snapshot.p95_latency_ms.toFixed(1)}ms
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </DataPanel>
      </div>
    </>
  );
}

const defaultProbePayload = {
  customer_tenure_days: 418,
  request_source: "control-plane-probe",
  amount: 128.45,
};

function parseJsonObject(
  value: string,
  label: string,
): Record<string, unknown> {
  try {
    const parsed = JSON.parse(value) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error(`${label} must be a JSON object.`);
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error(`${label} must be valid JSON.`);
    }
    throw error;
  }
}

function parsePositiveInteger(value: string, label: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${label} must be a positive integer.`);
  }
  return parsed;
}

function parseNonNegativeInteger(value: string, label: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0) {
    throw new Error(`${label} must be a non-negative integer.`);
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

function StatusBadge({ value }: { value: string }) {
  return (
    <span className="rounded bg-field px-2 py-1 text-xs font-medium">
      {value}
    </span>
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
