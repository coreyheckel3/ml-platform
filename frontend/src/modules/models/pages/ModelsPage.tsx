import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, GitBranchPlus, Send, X } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import { listTrainingRuns, type TrainingRun } from "../../training_runs/api/trainingRuns";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  listModelVersions,
  listRegisteredModels,
  promoteTrainingRunToModelVersion,
  requestModelApproval,
  reviewModelVersion,
  type ModelVersion
} from "../api/models";

export function ModelsPage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadModels = Boolean(token && projectId);
  const [selectedModelId, setSelectedModelId] = useState("");
  const [selectedTrainingRunId, setSelectedTrainingRunId] = useState("");
  const [modelFormat, setModelFormat] = useState("mlflow");
  const [signatureText, setSignatureText] = useState("");
  const [mutationMessage, setMutationMessage] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const modelsQuery = useQuery({
    queryKey: ["registered-models", projectId],
    queryFn: () => listRegisteredModels(projectId ?? "", token ?? ""),
    enabled: canLoadModels
  });
  const models = useMemo(() => modelsQuery.data?.items ?? [], [modelsQuery.data?.items]);
  const selectedModel = models.find((model) => model.id === selectedModelId) ?? models[0];
  const activeModelId = selectedModel?.id ?? "";
  const versionsQuery = useQuery({
    queryKey: ["model-versions", activeModelId],
    queryFn: () => listModelVersions(activeModelId, token ?? ""),
    enabled: Boolean(token && activeModelId)
  });
  const trainingRunsQuery = useQuery({
    queryKey: ["training-runs", projectId],
    queryFn: () => listTrainingRuns(projectId ?? "", token ?? ""),
    enabled: canLoadModels
  });
  const versions = useMemo(
    () => versionsQuery.data?.items ?? [],
    [versionsQuery.data?.items]
  );
  const trainingRuns = useMemo(
    () => trainingRunsQuery.data?.items ?? [],
    [trainingRunsQuery.data?.items]
  );
  const promotedTrainingRunIds = useMemo(
    () => new Set(versions.map((version) => version.training_run_id)),
    [versions]
  );
  const promotableRuns = useMemo(
    () =>
      trainingRuns.filter(
        (run) => run.status === "succeeded" && !promotedTrainingRunIds.has(run.id)
      ),
    [promotedTrainingRunIds, trainingRuns]
  );
  const selectedTrainingRun =
    promotableRuns.find((run) => run.id === selectedTrainingRunId) ?? promotableRuns[0];
  const statusCounts = countByStatus(versions.map((version) => version.status));
  const promoteMutation = useMutation({
    mutationFn: () => {
      if (!selectedModel || !selectedTrainingRun || !token) {
        throw new Error("Promotion requires a model, a succeeded training run, and API access.");
      }
      return promoteTrainingRunToModelVersion(
        selectedModel.id,
        {
          training_run_id: selectedTrainingRun.id,
          model_format: modelFormat,
          signature: parseSignature(signatureText)
        },
        token
      );
    },
    onSuccess: (version) => {
      setMutationError(null);
      setMutationMessage(`Promoted v${version.version} from ${version.training_run_id.slice(0, 8)}`);
      queryClient.invalidateQueries({ queryKey: ["model-versions", activeModelId] });
    },
    onError: (error) => {
      setMutationMessage(null);
      setMutationError(error instanceof Error ? error.message : "Promotion failed.");
    }
  });
  const requestApprovalMutation = useMutation({
    mutationFn: (version: ModelVersion) =>
      requestModelApproval(
        version.id,
        { comment: `Requesting approval for ${selectedModel?.name ?? "model"} v${version.version}.` },
        token ?? ""
      ),
    onSuccess: () => {
      setMutationError(null);
      setMutationMessage("Approval requested.");
      queryClient.invalidateQueries({ queryKey: ["model-versions", activeModelId] });
    },
    onError: () => {
      setMutationMessage(null);
      setMutationError("Approval request failed.");
    }
  });
  const reviewMutation = useMutation({
    mutationFn: ({ version, status }: { version: ModelVersion; status: "approved" | "rejected" }) =>
      reviewModelVersion(
        version.id,
        { status, comment: status === "approved" ? "Approved from registry UI." : "Rejected from registry UI." },
        token ?? ""
      ),
    onSuccess: (_approval, variables) => {
      setMutationError(null);
      setMutationMessage(`Version ${variables.status}.`);
      queryClient.invalidateQueries({ queryKey: ["model-versions", activeModelId] });
    },
    onError: () => {
      setMutationMessage(null);
      setMutationError("Review failed.");
    }
  });

  useEffect(() => {
    if (!selectedModelId && models[0]) {
      setSelectedModelId(models[0].id);
      return;
    }
    if (selectedModelId && !models.some((model) => model.id === selectedModelId)) {
      setSelectedModelId(models[0]?.id ?? "");
    }
  }, [models, selectedModelId]);

  useEffect(() => {
    if (!selectedTrainingRunId && promotableRuns[0]) {
      setSelectedTrainingRunId(promotableRuns[0].id);
      return;
    }
    if (selectedTrainingRunId && !promotableRuns.some((run) => run.id === selectedTrainingRunId)) {
      setSelectedTrainingRunId(promotableRuns[0]?.id ?? "");
    }
  }, [promotableRuns, selectedTrainingRunId]);

  useEffect(() => {
    if (!selectedTrainingRun) {
      setModelFormat("mlflow");
      setSignatureText("");
      return;
    }
    setModelFormat(inferModelFormat(selectedTrainingRun));
    setSignatureText(JSON.stringify(buildDefaultSignature(selectedTrainingRun), null, 2));
  }, [selectedTrainingRun]);

  function handlePromote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    promoteMutation.mutate();
  }

  return (
    <>
      <PageHeader
        eyebrow="Registry"
        title="Models"
        description="Versioned model packages with signatures, lineage, approval workflow, and promotion readiness."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Registered" value={String(models.length)} detail="model packages" />
        <MetricCard label="Versions" value={String(versions.length)} detail="selected model" />
        <MetricCard label="Approved" value={String(statusCounts.approved ?? 0)} detail="launch ready" tone="success" />
        <MetricCard label="Pending" value={String(statusCounts.pending_approval ?? 0)} detail="review queue" />
      </div>

      <div className="mt-6">
        <DataPanel title="Promotion Workbench">
          {!canLoadModels ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              No project context is selected.
            </div>
          ) : modelsQuery.error || trainingRunsQuery.error ? (
            <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk">
              Registry promotion data request failed.
            </div>
          ) : models.length === 0 ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              {modelsQuery.isFetching ? "Loading registered models." : "No registered models are available."}
            </div>
          ) : (
            <form aria-label="Promote training run" onSubmit={handlePromote} className="grid gap-4">
              <div className="grid gap-3 xl:grid-cols-[minmax(180px,0.8fr)_minmax(220px,1fr)_minmax(160px,0.5fr)_auto]">
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
                  Training run
                  <select
                    value={selectedTrainingRun?.id ?? ""}
                    onChange={(event) => setSelectedTrainingRunId(event.target.value)}
                    disabled={promotableRuns.length === 0}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal disabled:bg-cloud"
                  >
                    {promotableRuns.length === 0 ? (
                      <option value="">No succeeded runs</option>
                    ) : (
                      promotableRuns.map((run) => (
                        <option key={run.id} value={run.id}>
                          {run.id.slice(0, 8)} - {run.algorithm} - {firstMetric(run.metrics)}
                        </option>
                      ))
                    )}
                  </select>
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Format
                  <select
                    value={modelFormat}
                    onChange={(event) => setModelFormat(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  >
                    {modelFormatOptions.map((format) => (
                      <option key={format} value={format}>
                        {format}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="flex items-end">
                  <button
                    type="submit"
                    disabled={!selectedTrainingRun || promoteMutation.isPending}
                    className="inline-flex h-10 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <GitBranchPlus className="h-4 w-4" />
                    Promote
                  </button>
                </div>
              </div>
              <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                Signature
                <textarea
                  value={signatureText}
                  onChange={(event) => setSignatureText(event.target.value)}
                  rows={6}
                  className="min-h-32 rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
                />
              </label>
              {mutationMessage ? (
                <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-signal">
                  {mutationMessage}
                </div>
              ) : null}
              {mutationError ? (
                <div className="rounded border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-risk">
                  {mutationError}
                </div>
              ) : null}
            </form>
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <DataPanel title="Model Registry">
          {!canLoadModels ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              No project context is selected.
            </div>
          ) : modelsQuery.error ? (
            <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk">
              Model registry request failed.
            </div>
          ) : models.length === 0 ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              {modelsQuery.isFetching
                ? "Loading registered models."
                : "No models registered for this project."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Model</th>
                    <th>Task</th>
                    <th>Status</th>
                    <th>Selected</th>
                    <th>Slug</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((model) => (
                    <tr key={model.id} className="border-t border-slate-100">
                      <td className="py-3">
                        <div className="font-medium">{model.name}</div>
                        <div className="text-xs text-steel">
                          {model.description || "No description"}
                        </div>
                      </td>
                      <td>{model.task_type}</td>
                      <td>
                        <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                          {model.status}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          onClick={() => setSelectedModelId(model.id)}
                          className={[
                            "inline-flex h-8 items-center rounded border px-3 text-xs font-semibold transition",
                            model.id === activeModelId
                              ? "border-ink bg-ink text-white"
                              : "border-slate-200 bg-white text-steel hover:text-ink"
                          ].join(" ")}
                        >
                          {model.id === activeModelId ? "Active" : "Select"}
                        </button>
                      </td>
                      <td>{model.slug}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel title="Version Approval Queue">
          {!selectedModel ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              No model is available for version review.
            </div>
          ) : versionsQuery.error ? (
            <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk">
              Model version request failed.
            </div>
          ) : versions.length === 0 ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              {versionsQuery.isFetching
                ? "Loading model versions."
                : "No versions registered for this model."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[780px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Version</th>
                    <th>Format</th>
                    <th>Status</th>
                    <th>Metric</th>
                    <th>Artifact</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((version) => (
                    <tr key={version.id} className="border-t border-slate-100">
                      <td className="py-3">
                        <div className="font-medium">v{version.version}</div>
                        <div className="text-xs text-steel">
                          {version.training_run_id.slice(0, 8)}
                        </div>
                      </td>
                      <td>{version.model_format}</td>
                      <td>
                        <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                          {version.status}
                        </span>
                      </td>
                      <td>{firstMetric(version.metrics)}</td>
                      <td className="max-w-[240px] truncate">{version.artifact_uri}</td>
                      <td>{versionAction(version)}</td>
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

  function versionAction(version: ModelVersion) {
    if (version.status === "candidate") {
      return (
        <button
          type="button"
          onClick={() => requestApprovalMutation.mutate(version)}
          disabled={requestApprovalMutation.isPending}
          className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-ink transition hover:border-ink disabled:opacity-60"
        >
          <Send className="h-3.5 w-3.5" />
          Request approval
        </button>
      );
    }
    if (version.status === "pending_approval") {
      return (
        <div className="flex gap-2">
          <button
            type="button"
            aria-label={`Approve v${version.version}`}
            onClick={() => reviewMutation.mutate({ version, status: "approved" })}
            disabled={reviewMutation.isPending}
            className="inline-flex h-8 w-8 items-center justify-center rounded border border-emerald-200 bg-emerald-50 text-signal transition hover:border-signal disabled:opacity-60"
          >
            <Check className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            aria-label={`Reject v${version.version}`}
            onClick={() => reviewMutation.mutate({ version, status: "rejected" })}
            disabled={reviewMutation.isPending}
            className="inline-flex h-8 w-8 items-center justify-center rounded border border-rose-200 bg-rose-50 text-risk transition hover:border-risk disabled:opacity-60"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      );
    }
    return <span className="text-xs text-steel">No action</span>;
  }
}

const modelFormatOptions = [
  "mlflow",
  "xgboost-booster",
  "lightgbm-booster",
  "torchscript",
  "safetensors",
  "pickle",
  "onnx"
];

function countByStatus(statuses: string[]): Record<string, number> {
  return statuses.reduce<Record<string, number>>((counts, status) => {
    counts[status] = (counts[status] ?? 0) + 1;
    return counts;
  }, {});
}

function firstMetric(metrics: Record<string, number>): string {
  const [entry] = Object.entries(metrics);
  if (!entry) {
    return "none";
  }
  return `${entry[0]} ${entry[1].toFixed(3)}`;
}

function inferModelFormat(run: TrainingRun): string {
  const modelType = run.model_type.toLowerCase();
  const algorithm = run.algorithm.toLowerCase();
  if (modelType.includes("xgboost") || algorithm.includes("xgboost")) {
    return "xgboost-booster";
  }
  if (modelType.includes("lightgbm") || algorithm.includes("lightgbm")) {
    return "lightgbm-booster";
  }
  if (modelType.includes("torch") || algorithm.includes("pytorch")) {
    return "torchscript";
  }
  if (algorithm.includes("sentence-transformer")) {
    return "safetensors";
  }
  if (algorithm.includes("tfidf") || algorithm.includes("sklearn")) {
    return "pickle";
  }
  return "mlflow";
}

function buildDefaultSignature(run: TrainingRun): Record<string, unknown> {
  return {
    inputs: [
      {
        name: "features",
        type: "record",
        required: true
      }
    ],
    outputs: [
      {
        name: run.objective_metric_name || "prediction",
        type: "number"
      }
    ],
    metadata: {
      training_run_id: run.id,
      model_type: run.model_type
    }
  };
}

function parseSignature(signatureText: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(signatureText) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("Model signature must be a JSON object.");
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error("Model signature must be valid JSON.");
    }
    throw error;
  }
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
