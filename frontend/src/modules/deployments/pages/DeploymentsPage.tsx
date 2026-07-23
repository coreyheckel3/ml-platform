import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Gauge,
  Plus,
  Rocket,
  RotateCcw,
  ShieldCheck,
  X,
} from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import {
  listModelVersions,
  listRegisteredModels,
  type ModelVersion,
} from "../../models/api/models";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  createDeployment,
  createDeploymentRevision,
  listDeploymentEvents,
  listDeploymentHealthChecks,
  listDeploymentRevisions,
  listDeployments,
  recordDeploymentHealth,
  rollbackDeployment,
  updateDeploymentTraffic,
  type DeploymentRevision,
} from "../api/deployments";

type HealthStatus = "healthy" | "degraded" | "unhealthy";

export function DeploymentsPage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadDeployments = Boolean(token && projectId);
  const [selectedDeploymentId, setSelectedDeploymentId] = useState("");
  const [selectedModelId, setSelectedModelId] = useState("");
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [isCreateTargetOpen, setIsCreateTargetOpen] = useState(false);
  const [targetName, setTargetName] = useState("");
  const [targetDescription, setTargetDescription] = useState("");
  const [targetEnvironment, setTargetEnvironment] = useState("production");
  const [servingImage, setServingImage] = useState(
    "ghcr.io/forgeml/serving-runtime:latest",
  );
  const [trafficPercentage, setTrafficPercentage] = useState("10");
  const [runtimeConfigText, setRuntimeConfigText] = useState(
    JSON.stringify(defaultRuntimeConfig, null, 2),
  );
  const [healthLatencyMs, setHealthLatencyMs] = useState("85");
  const [healthErrorRate, setHealthErrorRate] = useState("0.01");
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const deploymentsQuery = useQuery({
    queryKey: ["deployments", projectId],
    queryFn: () => listDeployments(projectId ?? "", token ?? ""),
    enabled: canLoadDeployments,
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
  const eventsQuery = useQuery({
    queryKey: ["deployment-events", activeDeploymentId],
    queryFn: () => listDeploymentEvents(activeDeploymentId, token ?? ""),
    enabled: Boolean(token && activeDeploymentId),
  });
  const modelsQuery = useQuery({
    queryKey: ["registered-models", projectId],
    queryFn: () => listRegisteredModels(projectId ?? "", token ?? ""),
    enabled: canLoadDeployments,
  });
  const models = useMemo(
    () => modelsQuery.data?.items ?? [],
    [modelsQuery.data?.items],
  );
  const selectedModel =
    models.find((model) => model.id === selectedModelId) ?? models[0];
  const activeModelId = selectedModel?.id ?? "";
  const versionsQuery = useQuery({
    queryKey: ["model-versions", activeModelId],
    queryFn: () => listModelVersions(activeModelId, token ?? ""),
    enabled: Boolean(token && activeModelId),
  });
  const versions = useMemo(
    () => versionsQuery.data?.items ?? [],
    [versionsQuery.data?.items],
  );
  const approvedVersions = useMemo(
    () => versions.filter((version) => version.status === "approved"),
    [versions],
  );
  const selectedVersion =
    approvedVersions.find((version) => version.id === selectedVersionId) ??
    approvedVersions[0];
  const revisions = useMemo(
    () =>
      [...(revisionsQuery.data?.items ?? [])].sort(
        (left, right) => right.revision - left.revision,
      ),
    [revisionsQuery.data?.items],
  );
  const latestRevision = revisions[0];
  const healthChecksQuery = useQuery({
    queryKey: ["deployment-health-checks", latestRevision?.id],
    queryFn: () =>
      listDeploymentHealthChecks(latestRevision?.id ?? "", token ?? ""),
    enabled: Boolean(token && latestRevision),
  });
  const healthChecks = healthChecksQuery.data?.items ?? [];
  const latestHealthCheck = healthChecks[0];
  const events = eventsQuery.data?.items ?? [];
  const healthyRevisions = revisions.filter(
    (revision) => revision.status === "healthy",
  );
  const canaries = revisions.filter((revision) => {
    return revision.traffic_percentage > 0 && revision.traffic_percentage < 100;
  });
  const createTargetMutation = useMutation({
    mutationFn: () => {
      if (!projectId || !token) {
        throw new Error("Deployment target creation requires project context.");
      }
      return createDeployment(
        projectId,
        {
          name: targetName.trim(),
          description: targetDescription.trim(),
          environment: targetEnvironment,
        },
        token,
      );
    },
    onSuccess: (deployment) => {
      setOperationError(null);
      setOperationMessage(`Created ${deployment.name}.`);
      setSelectedDeploymentId(deployment.id);
      closeCreateTargetForm();
      queryClient.invalidateQueries({ queryKey: ["deployments", projectId] });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error
          ? error.message
          : "Deployment target creation failed.",
      );
    },
  });
  const createRevisionMutation = useMutation({
    mutationFn: () => {
      if (!selectedDeployment || !selectedVersion || !token) {
        throw new Error(
          "Creating a revision requires a target and an approved model version.",
        );
      }
      return createDeploymentRevision(
        selectedDeployment.id,
        {
          model_version_id: selectedVersion.id,
          serving_image: servingImage.trim(),
          runtime_config: parseRuntimeConfig(runtimeConfigText),
          traffic_percentage: parsePercentage(trafficPercentage, "Traffic"),
        },
        token,
      );
    },
    onSuccess: (revision) => {
      setOperationError(null);
      setOperationMessage(`Created revision ${revision.revision}.`);
      queryClient.invalidateQueries({
        queryKey: ["deployment-revisions", activeDeploymentId],
      });
      queryClient.invalidateQueries({
        queryKey: ["deployment-events", activeDeploymentId],
      });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error
          ? error.message
          : "Deployment revision creation failed.",
      );
    },
  });
  const healthMutation = useMutation({
    mutationFn: ({
      revision,
      status,
    }: {
      revision: DeploymentRevision;
      status: HealthStatus;
    }) => {
      if (!token) {
        throw new Error("Recording deployment health requires API access.");
      }
      return recordDeploymentHealth(
        revision.id,
        {
          status,
          latency_ms: parseNonNegativeFloat(healthLatencyMs, "Latency"),
          error_rate: parseErrorRate(healthErrorRate),
          details: {
            source: "release-console",
            deployment_id: revision.deployment_id,
            revision: revision.revision,
          },
        },
        token,
      );
    },
    onSuccess: (_healthCheck, variables) => {
      setOperationError(null);
      setOperationMessage(
        `Revision ${variables.revision.revision} health recorded.`,
      );
      queryClient.invalidateQueries({
        queryKey: ["deployment-revisions", activeDeploymentId],
      });
      queryClient.invalidateQueries({
        queryKey: ["deployment-health-checks", variables.revision.id],
      });
      queryClient.invalidateQueries({
        queryKey: ["deployment-events", activeDeploymentId],
      });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error
          ? error.message
          : "Health check recording failed.",
      );
    },
  });
  const trafficMutation = useMutation({
    mutationFn: ({
      revision,
      nextTrafficPercentage,
    }: {
      revision: DeploymentRevision;
      nextTrafficPercentage: number;
    }) => {
      if (!token) {
        throw new Error("Traffic changes require API access.");
      }
      return updateDeploymentTraffic(
        revision.id,
        { traffic_percentage: nextTrafficPercentage },
        token,
      );
    },
    onSuccess: (revision) => {
      setOperationError(null);
      setOperationMessage(
        `Revision ${revision.revision} traffic is ${revision.traffic_percentage}%.`,
      );
      queryClient.invalidateQueries({
        queryKey: ["deployment-revisions", activeDeploymentId],
      });
      queryClient.invalidateQueries({
        queryKey: ["deployment-events", activeDeploymentId],
      });
    },
    onError: () => {
      setOperationMessage(null);
      setOperationError("Traffic update failed.");
    },
  });
  const rollbackMutation = useMutation({
    mutationFn: (revision: DeploymentRevision) => {
      if (!selectedDeployment || !token) {
        throw new Error("Rollback requires a selected deployment target.");
      }
      return rollbackDeployment(
        selectedDeployment.id,
        { target_revision_id: revision.id },
        token,
      );
    },
    onSuccess: (revision) => {
      setOperationError(null);
      setOperationMessage(`Rolled back to revision ${revision.revision}.`);
      queryClient.invalidateQueries({
        queryKey: ["deployment-revisions", activeDeploymentId],
      });
      queryClient.invalidateQueries({
        queryKey: ["deployment-events", activeDeploymentId],
      });
    },
    onError: () => {
      setOperationMessage(null);
      setOperationError("Rollback failed.");
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
    if (!selectedModelId && models[0]) {
      setSelectedModelId(models[0].id);
      return;
    }
    if (
      selectedModelId &&
      !models.some((model) => model.id === selectedModelId)
    ) {
      setSelectedModelId(models[0]?.id ?? "");
    }
  }, [models, selectedModelId]);

  useEffect(() => {
    if (!selectedVersionId && approvedVersions[0]) {
      setSelectedVersionId(approvedVersions[0].id);
      return;
    }
    if (
      selectedVersionId &&
      !approvedVersions.some((version) => version.id === selectedVersionId)
    ) {
      setSelectedVersionId(approvedVersions[0]?.id ?? "");
    }
  }, [approvedVersions, selectedVersionId]);

  function closeCreateTargetForm() {
    setIsCreateTargetOpen(false);
    setTargetName("");
    setTargetDescription("");
    setTargetEnvironment("production");
  }

  function handleCreateTarget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (targetName.trim().length < 3) {
      setOperationMessage(null);
      setOperationError(
        "Deployment target name must be at least 3 characters.",
      );
      return;
    }
    createTargetMutation.mutate();
  }

  function handleCreateRevision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createRevisionMutation.mutate();
  }

  return (
    <>
      <PageHeader
        eyebrow="Production"
        title="Deployments"
        description="Model deployment targets, immutable revisions, canary rollout state, health checks, and rollback."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          label="Targets"
          value={String(deployments.length)}
          detail="deployment endpoints"
        />
        <MetricCard
          label="Healthy"
          value={String(healthyRevisions.length)}
          detail="selected target"
          tone="success"
        />
        <MetricCard
          label="Canaries"
          value={String(canaries.length)}
          detail="traffic split active"
          tone="warning"
        />
        <MetricCard
          label="Latest Health"
          value={latestHealthCheck?.status ?? "unknown"}
          detail={
            latestRevision
              ? `revision ${latestRevision.revision}`
              : "no revisions"
          }
          tone={latestHealthCheck?.status === "healthy" ? "success" : "neutral"}
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
        <DataPanel title="Release Console">
          {!canLoadDeployments ? (
            <EmptyState message="No project context is selected." />
          ) : deploymentsQuery.error ||
            modelsQuery.error ||
            versionsQuery.error ? (
            <ErrorState message="Deployment release data request failed." />
          ) : !selectedDeployment ? (
            <EmptyState message="Create a deployment target before releasing a model version." />
          ) : models.length === 0 ? (
            <EmptyState
              message={
                modelsQuery.isFetching
                  ? "Loading registered models."
                  : "No registered models are available."
              }
            />
          ) : approvedVersions.length === 0 ? (
            <EmptyState
              message={
                versionsQuery.isFetching
                  ? "Loading approved model versions."
                  : "No approved versions are available for the selected model."
              }
            />
          ) : (
            <form
              aria-label="Create deployment revision"
              onSubmit={handleCreateRevision}
              className="grid gap-4"
            >
              <div className="grid gap-3 xl:grid-cols-[minmax(180px,0.9fr)_minmax(180px,0.9fr)_minmax(180px,0.8fr)_120px]">
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Target
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
                  Model
                  <select
                    value={activeModelId}
                    onChange={(event) => setSelectedModelId(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  >
                    {models.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Approved version
                  <select
                    value={selectedVersion?.id ?? ""}
                    onChange={(event) =>
                      setSelectedVersionId(event.target.value)
                    }
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  >
                    {approvedVersions.map((version) => (
                      <option key={version.id} value={version.id}>
                        v{version.version} - {firstMetric(version)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Traffic
                  <input
                    value={trafficPercentage}
                    onChange={(event) =>
                      setTrafficPercentage(event.target.value)
                    }
                    inputMode="numeric"
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
              </div>
              <div className="grid gap-3 xl:grid-cols-[minmax(260px,0.8fr)_minmax(320px,1.2fr)_auto]">
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Serving image
                  <input
                    value={servingImage}
                    onChange={(event) => setServingImage(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Runtime config
                  <textarea
                    value={runtimeConfigText}
                    onChange={(event) =>
                      setRuntimeConfigText(event.target.value)
                    }
                    rows={4}
                    className="min-h-24 rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <div className="flex items-end">
                  <button
                    type="submit"
                    disabled={createRevisionMutation.isPending}
                    className="inline-flex h-10 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Rocket className="h-4 w-4" />
                    Create revision
                  </button>
                </div>
              </div>
            </form>
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <DataPanel
          title="Deployment Targets"
          action={
            <button
              type="button"
              onClick={() => {
                setIsCreateTargetOpen(true);
                setOperationError(null);
              }}
              className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              <Plus className="h-4 w-4" />
              Target
            </button>
          }
        >
          {isCreateTargetOpen ? (
            <form
              aria-label="Create deployment target"
              onSubmit={handleCreateTarget}
              className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
            >
              <div className="grid gap-3 lg:grid-cols-[minmax(160px,0.7fr)_minmax(220px,1fr)_150px_auto]">
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Name
                  <input
                    value={targetName}
                    onChange={(event) => setTargetName(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Description
                  <input
                    value={targetDescription}
                    onChange={(event) =>
                      setTargetDescription(event.target.value)
                    }
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Environment
                  <select
                    value={targetEnvironment}
                    onChange={(event) =>
                      setTargetEnvironment(event.target.value)
                    }
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  >
                    {deploymentEnvironments.map((environment) => (
                      <option key={environment} value={environment}>
                        {environment}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="flex items-end gap-2">
                  <button
                    type="submit"
                    disabled={createTargetMutation.isPending}
                    className="inline-flex h-10 items-center gap-2 rounded bg-signal px-3 text-sm font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    <ShieldCheck className="h-4 w-4" />
                    Create
                  </button>
                  <button
                    type="button"
                    aria-label="Cancel deployment target creation"
                    onClick={closeCreateTargetForm}
                    className="inline-flex h-10 w-10 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </form>
          ) : null}
          {!canLoadDeployments ? (
            <EmptyState message="No project context is selected." />
          ) : deploymentsQuery.error ? (
            <ErrorState message="Deployment request failed." />
          ) : deployments.length === 0 ? (
            <EmptyState
              message={
                deploymentsQuery.isFetching
                  ? "Loading deployments."
                  : "No deployments configured for this project."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Deployment</th>
                    <th>Environment</th>
                    <th>Status</th>
                    <th>Selected</th>
                    <th>Slug</th>
                  </tr>
                </thead>
                <tbody>
                  {deployments.map((deployment) => (
                    <tr
                      key={deployment.id}
                      className="border-t border-slate-100"
                    >
                      <td className="py-3">
                        <div className="font-medium">{deployment.name}</div>
                        <div className="text-xs text-steel">
                          {deployment.description || "No description"}
                        </div>
                      </td>
                      <td>{deployment.environment}</td>
                      <td>
                        <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                          {deployment.status}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          onClick={() => setSelectedDeploymentId(deployment.id)}
                          className={[
                            "inline-flex h-8 items-center rounded border px-3 text-xs font-semibold transition",
                            deployment.id === activeDeploymentId
                              ? "border-ink bg-ink text-white"
                              : "border-slate-200 bg-white text-steel hover:text-ink",
                          ].join(" ")}
                        >
                          {deployment.id === activeDeploymentId
                            ? "Active"
                            : "Select"}
                        </button>
                      </td>
                      <td>{deployment.slug}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel title="Rollout State">
          {!selectedDeployment ? (
            <EmptyState message="No deployment is available for rollout review." />
          ) : revisionsQuery.error ? (
            <ErrorState message="Deployment revision request failed." />
          ) : revisions.length === 0 ? (
            <EmptyState
              message={
                revisionsQuery.isFetching
                  ? "Loading deployment revisions."
                  : "No revisions created for this deployment."
              }
            />
          ) : (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-[160px_160px]">
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Probe latency
                  <input
                    value={healthLatencyMs}
                    onChange={(event) => setHealthLatencyMs(event.target.value)}
                    inputMode="decimal"
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Error rate
                  <input
                    value={healthErrorRate}
                    onChange={(event) => setHealthErrorRate(event.target.value)}
                    inputMode="decimal"
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
              </div>
              {revisions.map((revision) => (
                <div
                  key={revision.id}
                  className="rounded border border-slate-200 p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">
                        Revision {revision.revision}
                      </div>
                      <div className="mt-1 text-xs text-steel">
                        {revision.serving_image}
                      </div>
                    </div>
                    <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                      {revision.status}
                    </span>
                  </div>
                  <div className="mt-3 h-3 overflow-hidden rounded bg-field">
                    <div
                      className="h-full bg-signal"
                      style={{ width: `${revision.traffic_percentage}%` }}
                    />
                  </div>
                  <div className="mt-2 flex justify-between text-xs text-steel">
                    <span>{revision.traffic_percentage}% traffic</span>
                    <span>
                      {revision.orchestrator_deployment_id || "not submitted"}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {healthStatusOptions.map((status) => (
                      <button
                        key={status}
                        type="button"
                        aria-label={`Mark revision ${revision.revision} ${status}`}
                        onClick={() =>
                          healthMutation.mutate({ revision, status })
                        }
                        disabled={healthMutation.isPending}
                        className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-ink transition hover:border-signal disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <Activity className="h-3.5 w-3.5" />
                        {status}
                      </button>
                    ))}
                    <button
                      type="button"
                      aria-label={`Promote revision ${revision.revision} to full traffic`}
                      onClick={() =>
                        trafficMutation.mutate({
                          revision,
                          nextTrafficPercentage: 100,
                        })
                      }
                      disabled={
                        trafficMutation.isPending ||
                        revision.traffic_percentage === 100
                      }
                      className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-ink transition hover:border-ink disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <Gauge className="h-3.5 w-3.5" />
                      100%
                    </button>
                    <button
                      type="button"
                      aria-label={`Drain revision ${revision.revision} traffic`}
                      onClick={() =>
                        trafficMutation.mutate({
                          revision,
                          nextTrafficPercentage: 0,
                        })
                      }
                      disabled={
                        trafficMutation.isPending ||
                        revision.traffic_percentage === 0
                      }
                      className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-ink transition hover:border-ink disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <Gauge className="h-3.5 w-3.5" />
                      0%
                    </button>
                    <button
                      type="button"
                      aria-label={`Rollback to revision ${revision.revision}`}
                      onClick={() => rollbackMutation.mutate(revision)}
                      disabled={
                        rollbackMutation.isPending ||
                        revision.status !== "healthy"
                      }
                      className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-ink transition hover:border-risk disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                      Rollback
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6">
        <DataPanel title="Deployment Events">
          {!selectedDeployment ? (
            <EmptyState message="No deployment is selected." />
          ) : eventsQuery.error ? (
            <ErrorState message="Deployment event request failed." />
          ) : events.length === 0 ? (
            <EmptyState
              message={
                eventsQuery.isFetching
                  ? "Loading deployment events."
                  : "No deployment events have been recorded."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Event</th>
                    <th>Message</th>
                    <th>Revision</th>
                    <th>Metadata</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <tr key={event.id} className="border-t border-slate-100">
                      <td className="py-3">
                        <StatusBadge value={event.event_type} />
                      </td>
                      <td>{event.message}</td>
                      <td className="text-xs text-steel">
                        {event.deployment_revision_id?.slice(0, 8) ?? "target"}
                      </td>
                      <td className="max-w-[280px] truncate font-mono text-xs text-steel">
                        {JSON.stringify(event.metadata)}
                      </td>
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

const deploymentEnvironments = ["development", "staging", "production"];
const healthStatusOptions: HealthStatus[] = [
  "healthy",
  "degraded",
  "unhealthy",
];
const defaultRuntimeConfig = {
  resources: {
    cpu: "500m",
    memory: "1Gi",
  },
  autoscaling: {
    min_replicas: 1,
    max_replicas: 3,
  },
  observability: {
    metrics_enabled: true,
    logs_enabled: true,
  },
};

function firstMetric(version: ModelVersion): string {
  const [entry] = Object.entries(version.metrics);
  if (!entry) {
    return "no metric";
  }
  return `${entry[0]} ${entry[1].toFixed(3)}`;
}

function parseRuntimeConfig(
  runtimeConfigText: string,
): Record<string, unknown> {
  try {
    const parsed = JSON.parse(runtimeConfigText) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("Runtime config must be a JSON object.");
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error("Runtime config must be valid JSON.");
    }
    throw error;
  }
}

function parsePercentage(value: string, label: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0 || parsed > 100) {
    throw new Error(`${label} must be an integer between 0 and 100.`);
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

function parseErrorRate(value: string): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0 || parsed > 1) {
    throw new Error("Error rate must be between 0 and 1.");
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
