import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  BarChart3,
  CheckCircle,
  ClipboardCheck,
  Package,
  Play,
  Plus,
  X,
} from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";

import {
  listDatasets,
  listDatasetVersions,
  type Dataset,
} from "../../datasets/api/datasets";
import { listFeatureSets, type FeatureSet } from "../../feature_store/api/featureStore";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  completeExperimentRun,
  createExperiment,
  listExperimentArtifacts,
  listExperimentRuns,
  listExperiments,
  logExperimentArtifact,
  logExperimentMetrics,
  startExperimentRun,
  type Experiment,
  type ExperimentArtifact,
  type ExperimentRun,
} from "../api/experiments";

type LineageMode = "dataset" | "feature_set";
type TerminalStatus = "succeeded" | "failed" | "canceled";

export function ExperimentsPage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadExperiments = Boolean(token && projectId);
  const [selectedExperimentId, setSelectedExperimentId] = useState("");
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [selectedDatasetVersionId, setSelectedDatasetVersionId] = useState("");
  const [selectedFeatureSetId, setSelectedFeatureSetId] = useState("");
  const [isCreateExperimentOpen, setIsCreateExperimentOpen] = useState(false);
  const [isStartRunOpen, setIsStartRunOpen] = useState(false);
  const [experimentName, setExperimentName] = useState("fraud-risk-baseline");
  const [experimentDescription, setExperimentDescription] = useState(
    "Offline comparison group for fraud risk models.",
  );
  const [lineageMode, setLineageMode] = useState<LineageMode>("dataset");
  const [runName, setRunName] = useState("fraud-xgb-baseline");
  const [modelType, setModelType] = useState("xgboost");
  const [artifactUri, setArtifactUri] = useState(
    "s3://forgeml/experiments/fraud-xgb-baseline",
  );
  const [parametersText, setParametersText] = useState(defaultParametersText);
  const [metricsText, setMetricsText] = useState(defaultMetricsText);
  const [evaluationReportText, setEvaluationReportText] = useState(
    defaultEvaluationReportText,
  );
  const [artifactName, setArtifactName] = useState("model-card");
  const [artifactType, setArtifactType] = useState("evaluation_report");
  const [artifactLogUri, setArtifactLogUri] = useState(
    "s3://forgeml/experiments/fraud-xgb-baseline/model-card.json",
  );
  const [artifactMetadataText, setArtifactMetadataText] = useState(
    defaultArtifactMetadataText,
  );
  const [completionStatus, setCompletionStatus] =
    useState<TerminalStatus>("succeeded");
  const [completionErrorMessage, setCompletionErrorMessage] = useState("");
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);

  const experimentsQuery = useQuery({
    queryKey: ["experiments", projectId],
    queryFn: () => listExperiments(projectId ?? "", token ?? ""),
    enabled: canLoadExperiments,
  });
  const experiments = useMemo(
    () => experimentsQuery.data?.items ?? [],
    [experimentsQuery.data?.items],
  );
  const selectedExperiment =
    experiments.find((experiment) => experiment.id === selectedExperimentId) ??
    experiments[0];
  const activeExperimentId = selectedExperiment?.id ?? "";
  const runsQuery = useQuery({
    queryKey: ["experiment-runs", activeExperimentId],
    queryFn: () => listExperimentRuns(activeExperimentId, token ?? ""),
    enabled: Boolean(token && activeExperimentId),
  });
  const runs = useMemo(() => runsQuery.data?.items ?? [], [runsQuery.data?.items]);
  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? runs[0];
  const activeRunId = selectedRun?.id ?? "";
  const artifactsQuery = useQuery({
    queryKey: ["experiment-artifacts", activeRunId],
    queryFn: () => listExperimentArtifacts(activeRunId, token ?? ""),
    enabled: Boolean(token && activeRunId),
  });
  const artifacts = useMemo(
    () => artifactsQuery.data?.items ?? [],
    [artifactsQuery.data?.items],
  );
  const datasetsQuery = useQuery({
    queryKey: ["datasets", projectId],
    queryFn: () => listDatasets(projectId ?? "", token ?? ""),
    enabled: canLoadExperiments,
  });
  const datasets = useMemo(
    () => datasetsQuery.data?.items ?? [],
    [datasetsQuery.data?.items],
  );
  const selectedDataset =
    datasets.find((dataset) => dataset.id === selectedDatasetId) ?? datasets[0];
  const datasetVersionsQuery = useQuery({
    queryKey: ["dataset-versions", selectedDataset?.id],
    queryFn: () => listDatasetVersions(selectedDataset?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedDataset),
  });
  const datasetVersions = useMemo(
    () => datasetVersionsQuery.data?.items ?? [],
    [datasetVersionsQuery.data?.items],
  );
  const selectedDatasetVersion =
    datasetVersions.find((version) => version.id === selectedDatasetVersionId) ??
    datasetVersions[0];
  const featureSetsQuery = useQuery({
    queryKey: ["feature-sets", projectId],
    queryFn: () => listFeatureSets(projectId ?? "", token ?? ""),
    enabled: canLoadExperiments,
  });
  const featureSets = useMemo(
    () => featureSetsQuery.data?.items ?? [],
    [featureSetsQuery.data?.items],
  );
  const selectedFeatureSet =
    featureSets.find((featureSet) => featureSet.id === selectedFeatureSetId) ??
    featureSets[0];
  const terminalRuns = runs.filter((run) => isTerminalStatus(run.status));
  const bestMetric = findBestMetric(runs);
  const counts = countByStatus(runs.map((run) => run.status));

  const createExperimentMutation = useMutation({
    mutationFn: () => {
      if (!projectId || !token) {
        throw new Error("Experiment creation requires project context.");
      }
      return createExperiment(
        projectId,
        {
          name: experimentName.trim(),
          description: experimentDescription.trim(),
        },
        token,
      );
    },
    onSuccess: (experiment) => {
      queryClient.setQueryData<{ items: Experiment[]; next_cursor: string | null }>(
        ["experiments", projectId],
        (current) => ({
          items: [
            experiment,
            ...(current?.items.filter((item) => item.id !== experiment.id) ?? []),
          ],
          next_cursor: current?.next_cursor ?? null,
        }),
      );
      setOperationError(null);
      setOperationMessage(`Created experiment ${experiment.name}.`);
      setSelectedExperimentId(experiment.id);
      setSelectedRunId("");
      closeCreateExperimentForm();
      queryClient.invalidateQueries({ queryKey: ["experiments", projectId] });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Experiment creation failed.",
      );
    },
  });
  const startRunMutation = useMutation({
    mutationFn: () => {
      if (!selectedExperiment || !token) {
        throw new Error("Experiment run creation requires a selected experiment.");
      }
      return startExperimentRun(
        selectedExperiment.id,
        {
          run_name: runName.trim(),
          model_type: modelType.trim(),
          artifact_uri: artifactUri.trim(),
          dataset_version_id:
            lineageMode === "dataset" ? selectedDatasetVersion?.id ?? null : null,
          feature_set_id:
            lineageMode === "feature_set" ? selectedFeatureSet?.id ?? null : null,
          parameters: parseJsonObject(parametersText, "Parameters"),
        },
        token,
      );
    },
    onSuccess: (run) => {
      queryClient.setQueryData<{ items: ExperimentRun[]; next_cursor: string | null }>(
        ["experiment-runs", run.experiment_id],
        (current) => ({
          items: [run, ...(current?.items.filter((item) => item.id !== run.id) ?? [])],
          next_cursor: current?.next_cursor ?? null,
        }),
      );
      setOperationError(null);
      setOperationMessage(`Started experiment run ${run.id.slice(0, 8)}.`);
      setSelectedRunId(run.id);
      closeStartRunForm();
      invalidateExperimentState(run.experiment_id, run.id);
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Experiment run creation failed.",
      );
    },
  });
  const logMetricsMutation = useMutation({
    mutationFn: () => {
      if (!selectedRun || !token) {
        throw new Error("Metric logging requires a selected experiment run.");
      }
      return logExperimentMetrics(
        selectedRun.id,
        {
          metrics: parseMetricObject(metricsText, "Experiment metrics", true),
          evaluation_report: parseJsonObject(
            evaluationReportText,
            "Evaluation report",
          ),
        },
        token,
      );
    },
    onSuccess: (run) => {
      queryClient.setQueryData<{ items: ExperimentRun[]; next_cursor: string | null }>(
        ["experiment-runs", run.experiment_id],
        (current) => ({
          items: (current?.items ?? []).map((item) => (item.id === run.id ? run : item)),
          next_cursor: current?.next_cursor ?? null,
        }),
      );
      setOperationError(null);
      setOperationMessage(`Logged metrics for ${run.run_name}.`);
      setSelectedRunId(run.id);
      invalidateExperimentState(run.experiment_id, run.id);
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Experiment metric logging failed.",
      );
    },
  });
  const logArtifactMutation = useMutation({
    mutationFn: () => {
      if (!selectedRun || !token) {
        throw new Error("Artifact logging requires a selected experiment run.");
      }
      return logExperimentArtifact(
        selectedRun.id,
        {
          name: artifactName.trim(),
          artifact_type: artifactType.trim(),
          uri: artifactLogUri.trim(),
          metadata: parseJsonObject(artifactMetadataText, "Artifact metadata"),
        },
        token,
      );
    },
    onSuccess: (artifact) => {
      queryClient.setQueryData<{ items: ExperimentArtifact[]; next_cursor: string | null }>(
        ["experiment-artifacts", artifact.experiment_run_id],
        (current) => ({
          items: [
            artifact,
            ...(current?.items.filter((item) => item.id !== artifact.id) ?? []),
          ],
          next_cursor: current?.next_cursor ?? null,
        }),
      );
      setOperationError(null);
      setOperationMessage(`Logged artifact ${artifact.name}.`);
      queryClient.invalidateQueries({
        queryKey: ["experiment-artifacts", artifact.experiment_run_id],
      });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Experiment artifact logging failed.",
      );
    },
  });
  const completeRunMutation = useMutation({
    mutationFn: () => {
      if (!selectedRun || !token) {
        throw new Error("Run completion requires a selected experiment run.");
      }
      return completeExperimentRun(
        selectedRun.id,
        {
          status: completionStatus,
          metrics: parseMetricObject(metricsText, "Completion metrics", false),
          evaluation_report: parseJsonObject(
            evaluationReportText,
            "Evaluation report",
          ),
          error_message: optionalString(completionErrorMessage),
        },
        token,
      );
    },
    onSuccess: (run) => {
      queryClient.setQueryData<{ items: ExperimentRun[]; next_cursor: string | null }>(
        ["experiment-runs", run.experiment_id],
        (current) => ({
          items: (current?.items ?? []).map((item) => (item.id === run.id ? run : item)),
          next_cursor: current?.next_cursor ?? null,
        }),
      );
      setOperationError(null);
      setOperationMessage(`Completed ${run.run_name} as ${run.status}.`);
      setSelectedRunId(run.id);
      invalidateExperimentState(run.experiment_id, run.id);
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Experiment run completion failed.",
      );
    },
  });

  useEffect(() => {
    if (!selectedExperimentId && experiments[0]) {
      setSelectedExperimentId(experiments[0].id);
      return;
    }
    if (
      selectedExperimentId &&
      !experiments.some((experiment) => experiment.id === selectedExperimentId)
    ) {
      setSelectedExperimentId(experiments[0]?.id ?? "");
    }
  }, [experiments, selectedExperimentId]);

  useEffect(() => {
    if (!selectedRunId && runs[0]) {
      setSelectedRunId(runs[0].id);
      return;
    }
    if (selectedRunId && !runs.some((run) => run.id === selectedRunId)) {
      setSelectedRunId(runs[0]?.id ?? "");
    }
  }, [runs, selectedRunId]);

  useEffect(() => {
    if (!selectedDatasetId && datasets[0]) {
      setSelectedDatasetId(datasets[0].id);
      return;
    }
    if (selectedDatasetId && !datasets.some((dataset) => dataset.id === selectedDatasetId)) {
      setSelectedDatasetId(datasets[0]?.id ?? "");
    }
  }, [datasets, selectedDatasetId]);

  useEffect(() => {
    if (!selectedDatasetVersionId && datasetVersions[0]) {
      setSelectedDatasetVersionId(datasetVersions[0].id);
      return;
    }
    if (
      selectedDatasetVersionId &&
      !datasetVersions.some((version) => version.id === selectedDatasetVersionId)
    ) {
      setSelectedDatasetVersionId(datasetVersions[0]?.id ?? "");
    }
  }, [datasetVersions, selectedDatasetVersionId]);

  useEffect(() => {
    if (!selectedFeatureSetId && featureSets[0]) {
      setSelectedFeatureSetId(featureSets[0].id);
      return;
    }
    if (
      selectedFeatureSetId &&
      !featureSets.some((featureSet) => featureSet.id === selectedFeatureSetId)
    ) {
      setSelectedFeatureSetId(featureSets[0]?.id ?? "");
    }
  }, [featureSets, selectedFeatureSetId]);

  function invalidateExperimentState(experimentId: string, runId: string) {
    queryClient.invalidateQueries({ queryKey: ["experiment-runs", experimentId] });
    queryClient.invalidateQueries({ queryKey: ["experiment-artifacts", runId] });
    queryClient.invalidateQueries({ queryKey: ["experiments", projectId] });
  }

  function closeCreateExperimentForm() {
    setIsCreateExperimentOpen(false);
    setExperimentName("fraud-risk-baseline");
    setExperimentDescription("Offline comparison group for fraud risk models.");
  }

  function closeStartRunForm() {
    setIsStartRunOpen(false);
    setLineageMode("dataset");
    setRunName("fraud-xgb-baseline");
    setModelType("xgboost");
    setArtifactUri("s3://forgeml/experiments/fraud-xgb-baseline");
    setParametersText(defaultParametersText);
  }

  function handleCreateExperiment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (experimentName.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Experiment name must be at least 3 characters.");
      return;
    }
    createExperimentMutation.mutate();
  }

  function handleStartRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (runName.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Run name must be at least 3 characters.");
      return;
    }
    if (modelType.trim().length < 2) {
      setOperationMessage(null);
      setOperationError("Model type must be at least 2 characters.");
      return;
    }
    if (artifactUri.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Artifact URI is required.");
      return;
    }
    if (lineageMode === "dataset" && !selectedDatasetVersion) {
      setOperationMessage(null);
      setOperationError("Experiment runs require a dataset version.");
      return;
    }
    if (lineageMode === "feature_set" && !selectedFeatureSet) {
      setOperationMessage(null);
      setOperationError("Experiment runs require a feature set.");
      return;
    }
    startRunMutation.mutate();
  }

  function handleLogMetrics(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    logMetricsMutation.mutate();
  }

  function handleLogArtifact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!artifactName.trim() || artifactType.trim().length < 2 || artifactLogUri.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Artifact name, type, and URI are required.");
      return;
    }
    logArtifactMutation.mutate();
  }

  function handleCompleteRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    completeRunMutation.mutate();
  }

  return (
    <>
      <PageHeader
        eyebrow="Experiment Tracking"
        title="Experiments"
        description="Run comparison, parameters, metrics, artifacts, evaluation reports, and MLflow-backed lineage."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Experiments" value={String(experiments.length)} detail="tracked groups" />
        <MetricCard label="Runs" value={String(runs.length)} detail="selected experiment" />
        <MetricCard
          label="Terminal"
          value={String(terminalRuns.length)}
          detail={`${counts.running ?? 0} running`}
        />
        <MetricCard
          label="Best Metric"
          value={bestMetric.value}
          detail={bestMetric.label}
          tone="success"
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

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <DataPanel
          title="Experiment Registry"
          action={
            <button
              type="button"
              onClick={() => {
                setIsCreateExperimentOpen(true);
                setOperationError(null);
              }}
              className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              <Plus className="h-4 w-4" />
              Experiment
            </button>
          }
        >
          {isCreateExperimentOpen ? (
            <CreateExperimentForm
              name={experimentName}
              description={experimentDescription}
              isPending={createExperimentMutation.isPending}
              onSubmit={handleCreateExperiment}
              onCancel={closeCreateExperimentForm}
              onNameChange={setExperimentName}
              onDescriptionChange={setExperimentDescription}
            />
          ) : null}
          {!canLoadExperiments ? (
            <StateMessage message="No project context is selected." />
          ) : experimentsQuery.error ? (
            <StateMessage message="Experiment registry request failed." tone="danger" />
          ) : experiments.length === 0 ? (
            <StateMessage
              message={
                experimentsQuery.isFetching
                  ? "Loading experiments."
                  : "No experiments registered for this project."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Experiment</th>
                    <th>Status</th>
                    <th>Slug</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {experiments.map((experiment) => (
                    <ExperimentRow
                      key={experiment.id}
                      experiment={experiment}
                      selected={experiment.id === selectedExperiment?.id}
                      onSelect={() => {
                        setSelectedExperimentId(experiment.id);
                        setSelectedRunId("");
                      }}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel
          title="Run Comparison"
          action={
            <button
              type="button"
              onClick={() => {
                setIsStartRunOpen(true);
                setOperationError(null);
              }}
              className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              <Plus className="h-4 w-4" />
              Run
            </button>
          }
        >
          {isStartRunOpen ? (
            <StartRunForm
              selectedExperiment={selectedExperiment}
              datasets={datasets}
              datasetVersions={datasetVersions}
              featureSets={featureSets}
              selectedDataset={selectedDataset}
              selectedDatasetVersionId={selectedDatasetVersion?.id ?? ""}
              selectedFeatureSet={selectedFeatureSet}
              lineageMode={lineageMode}
              runName={runName}
              modelType={modelType}
              artifactUri={artifactUri}
              parametersText={parametersText}
              isPending={startRunMutation.isPending}
              dependenciesLoading={
                experimentsQuery.isFetching ||
                datasetsQuery.isFetching ||
                datasetVersionsQuery.isFetching ||
                featureSetsQuery.isFetching
              }
              dependenciesError={
                Boolean(experimentsQuery.error) ||
                Boolean(datasetsQuery.error) ||
                Boolean(datasetVersionsQuery.error) ||
                Boolean(featureSetsQuery.error)
              }
              onSubmit={handleStartRun}
              onCancel={closeStartRunForm}
              onDatasetChange={(datasetId) => {
                setSelectedDatasetId(datasetId);
                setSelectedDatasetVersionId("");
              }}
              onDatasetVersionChange={setSelectedDatasetVersionId}
              onFeatureSetChange={setSelectedFeatureSetId}
              onLineageModeChange={setLineageMode}
              onRunNameChange={setRunName}
              onModelTypeChange={setModelType}
              onArtifactUriChange={setArtifactUri}
              onParametersTextChange={setParametersText}
            />
          ) : null}
          {!selectedExperiment ? (
            <StateMessage message="No experiment is available for comparison." />
          ) : runsQuery.error ? (
            <StateMessage message="Experiment run request failed." tone="danger" />
          ) : runs.length === 0 ? (
            <StateMessage
              message={
                runsQuery.isFetching ? "Loading runs." : "No runs recorded for this experiment."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[920px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Run</th>
                    <th>Model</th>
                    <th>Status</th>
                    <th>Metric</th>
                    <th>Lineage</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <RunRow
                      key={run.id}
                      run={run}
                      selected={run.id === selectedRun?.id}
                      onSelect={() => setSelectedRunId(run.id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <DataPanel title="Run Detail">
          {!selectedRun ? (
            <StateMessage message="No experiment run is selected." />
          ) : (
            <RunDetail run={selectedRun} />
          )}
        </DataPanel>

        <DataPanel title="Run Operations">
          {!selectedRun ? (
            <StateMessage message="Select an experiment run before recording tracking data." />
          ) : (
            <div className="grid gap-5">
              <form aria-label="Log experiment metrics" onSubmit={handleLogMetrics} className="grid gap-3">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <BarChart3 className="h-4 w-4 text-signal" />
                  Metrics
                </div>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Metrics
                  <textarea
                    value={metricsText}
                    onChange={(event) => setMetricsText(event.target.value)}
                    rows={5}
                    className="rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Evaluation Report
                  <textarea
                    value={evaluationReportText}
                    onChange={(event) => setEvaluationReportText(event.target.value)}
                    rows={5}
                    className="rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <button
                  type="submit"
                  disabled={logMetricsMutation.isPending}
                  className="inline-flex h-9 w-fit items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <ClipboardCheck className="h-4 w-4" />
                  Log metrics
                </button>
              </form>

              <form
                aria-label="Log experiment artifact"
                onSubmit={handleLogArtifact}
                className="grid gap-3 border-t border-slate-200 pt-5"
              >
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <Package className="h-4 w-4 text-signal" />
                  Artifacts
                </div>
                <div className="grid gap-3 lg:grid-cols-2">
                  <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                    Artifact Name
                    <input
                      value={artifactName}
                      onChange={(event) => setArtifactName(event.target.value)}
                      className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                    />
                  </label>
                  <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                    Artifact Type
                    <input
                      value={artifactType}
                      onChange={(event) => setArtifactType(event.target.value)}
                      className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                    />
                  </label>
                </div>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Artifact URI
                  <input
                    value={artifactLogUri}
                    onChange={(event) => setArtifactLogUri(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Metadata
                  <textarea
                    value={artifactMetadataText}
                    onChange={(event) => setArtifactMetadataText(event.target.value)}
                    rows={4}
                    className="rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <button
                  type="submit"
                  disabled={logArtifactMutation.isPending}
                  className="inline-flex h-9 w-fit items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Package className="h-4 w-4" />
                  Log artifact
                </button>
              </form>

              <form
                aria-label="Complete experiment run"
                onSubmit={handleCompleteRun}
                className="grid gap-3 border-t border-slate-200 pt-5"
              >
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <CheckCircle className="h-4 w-4 text-signal" />
                  Completion
                </div>
                {isTerminalStatus(selectedRun.status) ? (
                  <StateMessage message="Selected run already has a terminal status." />
                ) : (
                  <>
                    <div className="grid gap-3 lg:grid-cols-2">
                      <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                        Result Status
                        <select
                          value={completionStatus}
                          onChange={(event) =>
                            setCompletionStatus(event.target.value as TerminalStatus)
                          }
                          className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                        >
                          <option value="succeeded">succeeded</option>
                          <option value="failed">failed</option>
                          <option value="canceled">canceled</option>
                        </select>
                      </label>
                      <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                        Error Message
                        <input
                          value={completionErrorMessage}
                          onChange={(event) => setCompletionErrorMessage(event.target.value)}
                          className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                        />
                      </label>
                    </div>
                    <button
                      type="submit"
                      disabled={completeRunMutation.isPending}
                      className="inline-flex h-9 w-fit items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <CheckCircle className="h-4 w-4" />
                      Complete run
                    </button>
                  </>
                )}
              </form>
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6">
        <DataPanel title="Run Artifacts">
          {!selectedRun ? (
            <StateMessage message="No experiment run is selected." />
          ) : artifactsQuery.error ? (
            <StateMessage message="Experiment artifact request failed." tone="danger" />
          ) : artifacts.length === 0 ? (
            <StateMessage
              message={
                artifactsQuery.isFetching
                  ? "Loading run artifacts."
                  : "No artifacts are recorded for this run."
              }
            />
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {artifacts.map((artifact) => (
                <ArtifactCard key={artifact.id} artifact={artifact} />
              ))}
            </div>
          )}
        </DataPanel>
      </div>
    </>
  );
}

const defaultParametersText = `{
  "max_depth": 6,
  "learning_rate": 0.08,
  "n_estimators": 250
}`;

const defaultMetricsText = `{
  "auc": 0.94,
  "log_loss": 0.18
}`;

const defaultEvaluationReportText = `{
  "validation": {
    "slice_count": 4,
    "passed": true
  }
}`;

const defaultArtifactMetadataText = `{
  "stage": "offline-evaluation",
  "format": "json"
}`;

type CreateExperimentFormProps = {
  name: string;
  description: string;
  isPending: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
};

function CreateExperimentForm({
  name,
  description,
  isPending,
  onSubmit,
  onCancel,
  onNameChange,
  onDescriptionChange,
}: CreateExperimentFormProps) {
  return (
    <form
      aria-label="Create experiment"
      onSubmit={onSubmit}
      className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(180px,1fr)_minmax(220px,1.3fr)]">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Experiment Name
          <input
            value={name}
            onChange={(event) => onNameChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Description
          <input
            value={description}
            onChange={(event) => onDescriptionChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={isPending}
          className="inline-flex h-9 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Plus className="h-4 w-4" />
          Create experiment
        </button>
        <button
          type="button"
          aria-label="Cancel experiment creation"
          onClick={onCancel}
          className="inline-flex h-9 w-9 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </form>
  );
}

type StartRunFormProps = {
  selectedExperiment: Experiment | undefined;
  datasets: Dataset[];
  datasetVersions: Array<{
    id: string;
    version: number;
    status: string;
  }>;
  featureSets: FeatureSet[];
  selectedDataset: Dataset | undefined;
  selectedDatasetVersionId: string;
  selectedFeatureSet: FeatureSet | undefined;
  lineageMode: LineageMode;
  runName: string;
  modelType: string;
  artifactUri: string;
  parametersText: string;
  isPending: boolean;
  dependenciesLoading: boolean;
  dependenciesError: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onDatasetChange: (value: string) => void;
  onDatasetVersionChange: (value: string) => void;
  onFeatureSetChange: (value: string) => void;
  onLineageModeChange: (value: LineageMode) => void;
  onRunNameChange: (value: string) => void;
  onModelTypeChange: (value: string) => void;
  onArtifactUriChange: (value: string) => void;
  onParametersTextChange: (value: string) => void;
};

function StartRunForm({
  selectedExperiment,
  datasets,
  datasetVersions,
  featureSets,
  selectedDataset,
  selectedDatasetVersionId,
  selectedFeatureSet,
  lineageMode,
  runName,
  modelType,
  artifactUri,
  parametersText,
  isPending,
  dependenciesLoading,
  dependenciesError,
  onSubmit,
  onCancel,
  onDatasetChange,
  onDatasetVersionChange,
  onFeatureSetChange,
  onLineageModeChange,
  onRunNameChange,
  onModelTypeChange,
  onArtifactUriChange,
  onParametersTextChange,
}: StartRunFormProps) {
  const lineageReady =
    lineageMode === "dataset" ? datasetVersions.length > 0 : featureSets.length > 0;
  const canSubmit =
    !isPending &&
    !dependenciesLoading &&
    !dependenciesError &&
    Boolean(selectedExperiment && lineageReady);
  return (
    <form
      aria-label="Start experiment run"
      onSubmit={onSubmit}
      className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(180px,1fr)_minmax(140px,0.7fr)]">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Run Name
          <input
            value={runName}
            onChange={(event) => onRunNameChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Model Type
          <input
            value={modelType}
            onChange={(event) => onModelTypeChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
      </div>
      <div className="mt-3 grid gap-3 lg:grid-cols-[140px_1fr_1fr]">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Lineage Source
          <select
            value={lineageMode}
            onChange={(event) => onLineageModeChange(event.target.value as LineageMode)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          >
            <option value="dataset">dataset</option>
            <option value="feature_set">feature set</option>
          </select>
        </label>
        {lineageMode === "dataset" ? (
          <>
            <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
              Dataset
              <select
                value={selectedDataset?.id ?? ""}
                onChange={(event) => onDatasetChange(event.target.value)}
                className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
              >
                {datasets.map((dataset) => (
                  <option key={dataset.id} value={dataset.id}>
                    {dataset.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
              Dataset Version
              <select
                value={selectedDatasetVersionId}
                onChange={(event) => onDatasetVersionChange(event.target.value)}
                className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
              >
                {datasetVersions.map((version) => (
                  <option key={version.id} value={version.id}>
                    v{version.version} - {version.status}
                  </option>
                ))}
              </select>
            </label>
          </>
        ) : (
          <label className="grid gap-1 text-xs font-semibold uppercase text-steel lg:col-span-2">
            Feature Set
            <select
              value={selectedFeatureSet?.id ?? ""}
              onChange={(event) => onFeatureSetChange(event.target.value)}
              className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
            >
              {featureSets.map((featureSet) => (
                <option key={featureSet.id} value={featureSet.id}>
                  {featureSet.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <label className="mt-3 grid gap-1 text-xs font-semibold uppercase text-steel">
        Artifact URI
        <input
          value={artifactUri}
          onChange={(event) => onArtifactUriChange(event.target.value)}
          className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
        />
      </label>
      <label className="mt-3 grid gap-1 text-xs font-semibold uppercase text-steel">
        Parameters
        <textarea
          value={parametersText}
          onChange={(event) => onParametersTextChange(event.target.value)}
          rows={6}
          className="rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
        />
      </label>
      {dependenciesError ? (
        <div className="mt-3 rounded border border-rose-200 bg-rose-50 p-3 text-sm text-risk">
          Experiment run dependencies failed to load.
        </div>
      ) : !lineageReady ? (
        <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Select an available dataset version or feature set before starting a run.
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex h-9 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Play className="h-4 w-4" />
          Start run
        </button>
        <button
          type="button"
          aria-label="Cancel experiment run creation"
          onClick={onCancel}
          className="inline-flex h-9 w-9 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </form>
  );
}

function ExperimentRow({
  experiment,
  selected,
  onSelect,
}: {
  experiment: Experiment;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3">
        <div className="font-medium">{experiment.name}</div>
        <div className="text-xs text-steel">
          {experiment.description || "No description"}
        </div>
      </td>
      <td>
        <span className="rounded bg-field px-2 py-1 text-xs font-medium">
          {experiment.status}
        </span>
      </td>
      <td>{experiment.slug}</td>
      <td>
        <button
          type="button"
          onClick={onSelect}
          className={[
            "inline-flex h-8 items-center rounded border px-3 text-xs font-semibold transition",
            selected
              ? "border-ink bg-ink text-white"
              : "border-slate-200 bg-white text-steel hover:text-ink",
          ].join(" ")}
        >
          {selected ? "Active" : "Select"}
        </button>
      </td>
    </tr>
  );
}

function RunRow({
  run,
  selected,
  onSelect,
}: {
  run: ExperimentRun;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3">
        <div className="font-medium">{run.run_name}</div>
        <div className="text-xs text-steel">{run.id.slice(0, 8)}</div>
      </td>
      <td>{run.model_type}</td>
      <td>
        <span className={statusClassName(run.status)}>{run.status}</span>
      </td>
      <td>{firstMetric(run.metrics)}</td>
      <td>{run.dataset_version_id ? "dataset" : "feature set"}</td>
      <td>
        <button
          type="button"
          onClick={onSelect}
          className={[
            "inline-flex h-8 items-center rounded border px-3 text-xs font-semibold transition",
            selected
              ? "border-ink bg-ink text-white"
              : "border-slate-200 bg-white text-steel hover:text-ink",
          ].join(" ")}
        >
          {selected ? "Active" : "Select"}
        </button>
      </td>
    </tr>
  );
}

function RunDetail({ run }: { run: ExperimentRun }) {
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold">{run.run_name}</div>
          <div className="mt-1 text-xs text-steel">{run.artifact_uri}</div>
        </div>
        <span className={statusClassName(run.status)}>{run.status}</span>
      </div>
      <div className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3">
        <SignalTile
          icon={<Activity className="h-4 w-4" />}
          label="Run"
          value={run.id.slice(0, 8)}
          detail={run.experiment_id.slice(0, 8)}
        />
        <SignalTile
          icon={<BarChart3 className="h-4 w-4" />}
          label="Metric"
          value={firstMetric(run.metrics)}
          detail={`${Object.keys(run.metrics).length} tracked`}
        />
        <SignalTile
          icon={<ClipboardCheck className="h-4 w-4" />}
          label="Lineage"
          value={run.dataset_version_id ? "dataset" : "feature set"}
          detail={(run.dataset_version_id ?? run.feature_set_id ?? "none").slice(0, 8)}
        />
      </div>
      <div className="rounded border border-slate-200 p-3 text-sm">
        <div className="font-medium">Parameters</div>
        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-xs text-steel">
          {formatObject(run.parameters)}
        </pre>
      </div>
      <div className="rounded border border-slate-200 p-3 text-sm">
        <div className="font-medium">Evaluation Report</div>
        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-xs text-steel">
          {formatObject(run.evaluation_report)}
        </pre>
      </div>
      {run.error_message ? (
        <div className="rounded border border-rose-200 bg-rose-50 p-3 text-sm text-risk">
          {run.error_message}
        </div>
      ) : null}
    </div>
  );
}

function ArtifactCard({ artifact }: { artifact: ExperimentArtifact }) {
  return (
    <article className="rounded border border-slate-200 p-3 text-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-semibold">{artifact.name}</div>
          <div className="mt-1 truncate text-xs text-steel">{artifact.uri}</div>
        </div>
        <span className="rounded bg-field px-2 py-1 text-xs font-medium">
          {artifact.artifact_type}
        </span>
      </div>
      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap font-mono text-xs text-steel">
        {formatObject(artifact.metadata)}
      </pre>
    </article>
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
    <div className="min-w-0">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase text-steel">
        {icon}
        {label}
      </div>
      <div className="mt-2 truncate text-sm font-medium">{value}</div>
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

function findBestMetric(runs: Array<{ metrics: Record<string, number> }>): {
  label: string;
  value: string;
} {
  let best: { label: string; value: number } | null = null;
  for (const run of runs) {
    for (const [label, value] of Object.entries(run.metrics)) {
      if (best === null || value > best.value) {
        best = { label, value };
      }
    }
  }
  return best
    ? { label: best.label, value: best.value.toFixed(3) }
    : { label: "no metrics", value: "0" };
}

function firstMetric(metrics: Record<string, number>): string {
  const [entry] = Object.entries(metrics);
  if (!entry) {
    return "none";
  }
  return `${entry[0]} ${entry[1].toFixed(3)}`;
}

function countByStatus(statuses: string[]): Record<string, number> {
  return statuses.reduce<Record<string, number>>((counts, status) => {
    counts[status] = (counts[status] ?? 0) + 1;
    return counts;
  }, {});
}

function isTerminalStatus(status: string): boolean {
  return status === "succeeded" || status === "failed" || status === "canceled";
}

function statusClassName(status: string): string {
  if (status === "succeeded") {
    return "rounded bg-emerald-50 px-2 py-1 text-xs font-medium text-signal";
  }
  if (status === "running" || status === "requested" || status === "queued") {
    return "rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700";
  }
  if (status === "failed" || status === "canceled") {
    return "rounded bg-rose-50 px-2 py-1 text-xs font-medium text-risk";
  }
  return "rounded bg-field px-2 py-1 text-xs font-medium";
}

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new Error(`${label} must be valid JSON.`);
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON object.`);
  }
  return parsed as Record<string, unknown>;
}

function parseMetricObject(
  value: string,
  label: string,
  requireMetric: boolean,
): Record<string, number> {
  const parsed = parseJsonObject(value, label);
  const metrics: Record<string, number> = {};
  for (const [key, rawValue] of Object.entries(parsed)) {
    if (typeof rawValue !== "number" || !Number.isFinite(rawValue)) {
      throw new Error(`${label} must contain finite numbers.`);
    }
    metrics[key] = rawValue;
  }
  if (requireMetric && Object.keys(metrics).length === 0) {
    throw new Error(`${label} must contain at least one metric.`);
  }
  return metrics;
}

function optionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function formatObject(value: Record<string, unknown>): string {
  if (Object.keys(value).length === 0) {
    return "{}";
  }
  return JSON.stringify(value, null, 2);
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
