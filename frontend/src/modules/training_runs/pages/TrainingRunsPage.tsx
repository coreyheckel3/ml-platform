import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  CheckCircle,
  CircleStop,
  ClipboardCheck,
  Clock,
  Gauge,
  PackageCheck,
  Play,
  Plus,
  RefreshCw,
  SquareTerminal,
  X,
} from "lucide-react";
import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  listDatasets,
  listDatasetVersions,
  type Dataset,
} from "../../datasets/api/datasets";
import {
  listExperiments,
  type Experiment,
} from "../../experiments/api/experiments";
import {
  listFeatureSets,
  type FeatureSet,
} from "../../feature_store/api/featureStore";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  cancelTrainingRun,
  getTrainingRunOrchestrationStatus,
  getTrainingRun,
  listTrainingRunnerProfiles,
  listTrainingRunEvents,
  listTrainingRunLogs,
  listTrainingRuns,
  recordTrainingResult,
  startTrainingRun,
  type TrainingOrchestrationStatus,
  type TrainingRunnerProfile,
  type TrainingRun,
  type TrainingRunEvent,
  type TrainingRunLog,
} from "../api/trainingRuns";

export function TrainingRunsPage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadTrainingRuns = Boolean(token && projectId);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedExperimentId, setSelectedExperimentId] = useState("");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [selectedDatasetVersionId, setSelectedDatasetVersionId] = useState("");
  const [selectedFeatureSetId, setSelectedFeatureSetId] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [lineageMode, setLineageMode] = useState<"dataset" | "feature_set">(
    "dataset",
  );
  const [runName, setRunName] = useState("manual-training-run");
  const [algorithm, setAlgorithm] = useState("xgboost");
  const [modelType, setModelType] = useState("xgboost");
  const [objectiveMetricName, setObjectiveMetricName] = useState("auc");
  const [hyperparametersText, setHyperparametersText] = useState(
    defaultHyperparametersText,
  );
  const [resultStatus, setResultStatus] = useState<
    "succeeded" | "failed" | "canceled"
  >("succeeded");
  const [metricsText, setMetricsText] = useState(defaultMetricsText);
  const [evaluationReportText, setEvaluationReportText] = useState(
    defaultEvaluationReportText,
  );
  const [resultErrorMessage, setResultErrorMessage] = useState("");
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const runsQuery = useQuery({
    queryKey: ["training-runs", projectId],
    queryFn: () => listTrainingRuns(projectId ?? "", token ?? ""),
    enabled: canLoadTrainingRuns,
    refetchInterval: (query) => {
      const runs = query.state.data?.items ?? [];
      return runs.some((run) => isLiveTrainingRun(run.status)) ? 5000 : false;
    },
    refetchIntervalInBackground: true,
  });
  const experimentsQuery = useQuery({
    queryKey: ["experiments", projectId],
    queryFn: () => listExperiments(projectId ?? "", token ?? ""),
    enabled: canLoadTrainingRuns,
  });
  const datasetsQuery = useQuery({
    queryKey: ["datasets", projectId],
    queryFn: () => listDatasets(projectId ?? "", token ?? ""),
    enabled: canLoadTrainingRuns,
  });
  const featureSetsQuery = useQuery({
    queryKey: ["feature-sets", projectId],
    queryFn: () => listFeatureSets(projectId ?? "", token ?? ""),
    enabled: canLoadTrainingRuns,
  });
  const runnerProfilesQuery = useQuery({
    queryKey: ["training-runner-profiles", token],
    queryFn: () => listTrainingRunnerProfiles(token ?? ""),
    enabled: Boolean(token),
  });
  const trainingRuns = useMemo(
    () => runsQuery.data?.items ?? [],
    [runsQuery.data?.items],
  );
  const runnerProfiles = useMemo(
    () => runnerProfilesQuery.data?.items ?? [],
    [runnerProfilesQuery.data?.items],
  );
  const experiments = useMemo(
    () => experimentsQuery.data?.items ?? [],
    [experimentsQuery.data?.items],
  );
  const datasets = useMemo(
    () => datasetsQuery.data?.items ?? [],
    [datasetsQuery.data?.items],
  );
  const featureSets = useMemo(
    () => featureSetsQuery.data?.items ?? [],
    [featureSetsQuery.data?.items],
  );
  const selectedRun =
    trainingRuns.find((run) => run.id === selectedRunId) ?? trainingRuns[0];
  const selectedRunIsLive = Boolean(
    selectedRun && isLiveTrainingRun(selectedRun.status),
  );
  const selectedExperiment =
    experiments.find((experiment) => experiment.id === selectedExperimentId) ??
    experiments[0];
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
    datasetVersions.find(
      (version) => version.id === selectedDatasetVersionId,
    ) ?? datasetVersions[0];
  const selectedFeatureSet =
    featureSets.find((featureSet) => featureSet.id === selectedFeatureSetId) ??
    featureSets[0];
  const selectedRunQuery = useQuery({
    queryKey: ["training-run", selectedRun?.id],
    queryFn: () => getTrainingRun(selectedRun?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedRun),
    refetchInterval: (query) => {
      const run = query.state.data ?? selectedRun;
      return run && isLiveTrainingRun(run.status) ? 3000 : false;
    },
    refetchIntervalInBackground: true,
  });
  const eventsQuery = useQuery({
    queryKey: ["training-run-events", selectedRun?.id],
    queryFn: () => listTrainingRunEvents(selectedRun?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedRun),
    refetchInterval: selectedRunIsLive ? 3000 : false,
    refetchIntervalInBackground: true,
  });
  const logsQuery = useQuery({
    queryKey: ["training-run-logs", selectedRun?.id],
    queryFn: () => listTrainingRunLogs(selectedRun?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedRun),
    refetchInterval: selectedRunIsLive ? 3000 : false,
    refetchIntervalInBackground: true,
  });
  const orchestrationStatusQuery = useQuery({
    queryKey: ["training-run-orchestration-status", selectedRun?.id],
    queryFn: () =>
      getTrainingRunOrchestrationStatus(selectedRun?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedRun),
    refetchInterval: selectedRunIsLive ? 3000 : false,
    refetchIntervalInBackground: true,
  });
  const selectedRunDetail = selectedRunQuery.data ?? selectedRun;
  const selectedRunDetailIsLive = Boolean(
    selectedRunDetail && isLiveTrainingRun(selectedRunDetail.status),
  );
  const orchestrationStatus = orchestrationStatusQuery.data;
  const events = useMemo(
    () => eventsQuery.data?.items ?? [],
    [eventsQuery.data?.items],
  );
  const logs = useMemo(
    () => logsQuery.data?.items ?? [],
    [logsQuery.data?.items],
  );
  const counts = countByStatus(trainingRuns.map((run) => run.status));
  const failedCount = (counts.failed ?? 0) + (counts.dead_lettered ?? 0);
  const terminalCount =
    (counts.succeeded ?? 0) + failedCount + (counts.canceled ?? 0);
  const startRunMutation = useMutation({
    mutationFn: () => {
      if (!projectId || !token) {
        throw new Error("Training run creation requires project context.");
      }
      if (!selectedExperiment) {
        throw new Error("Training run creation requires an experiment.");
      }
      return startTrainingRun(
        projectId,
        {
          experiment_id: selectedExperiment.id,
          run_name: runName.trim(),
          dataset_version_id:
            lineageMode === "dataset"
              ? (selectedDatasetVersion?.id ?? null)
              : null,
          feature_set_id:
            lineageMode === "feature_set"
              ? (selectedFeatureSet?.id ?? null)
              : null,
          algorithm: algorithm.trim(),
          model_type: modelType.trim(),
          objective_metric_name: objectiveMetricName.trim(),
          hyperparameters: parseJsonObject(
            hyperparametersText,
            "Hyperparameters",
          ),
        },
        token,
      );
    },
    onSuccess: (run) => {
      setOperationError(null);
      setOperationMessage(`Started training run ${run.id.slice(0, 8)}.`);
      setSelectedRunId(run.id);
      closeCreateForm();
      invalidateTrainingState(run.id);
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error
          ? error.message
          : "Training run creation failed.",
      );
    },
  });
  const cancelRunMutation = useMutation({
    mutationFn: (run: TrainingRun) => {
      if (!token) {
        throw new Error("Training run cancellation requires API access.");
      }
      return cancelTrainingRun(run.id, token);
    },
    onSuccess: (run) => {
      setOperationError(null);
      setOperationMessage(`Canceled training run ${run.id.slice(0, 8)}.`);
      setSelectedRunId(run.id);
      invalidateTrainingState(run.id);
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error
          ? error.message
          : "Training run cancellation failed.",
      );
    },
  });
  const recordResultMutation = useMutation({
    mutationFn: () => {
      if (!selectedRunDetail || !token) {
        throw new Error("Recording a result requires a selected training run.");
      }
      return recordTrainingResult(
        selectedRunDetail.id,
        {
          status: resultStatus,
          metrics: parseMetricObject(metricsText),
          evaluation_report: parseJsonObject(
            evaluationReportText,
            "Evaluation report",
          ),
          error_message: optionalString(resultErrorMessage),
        },
        token,
      );
    },
    onSuccess: (run) => {
      setOperationError(null);
      setOperationMessage(
        `Recorded ${run.status} result for ${run.id.slice(0, 8)}.`,
      );
      setSelectedRunId(run.id);
      invalidateTrainingState(run.id);
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error
          ? error.message
          : "Training result recording failed.",
      );
    },
  });

  useEffect(() => {
    if (!selectedRunId && trainingRuns[0]) {
      setSelectedRunId(trainingRuns[0].id);
      return;
    }
    if (
      selectedRunId &&
      !trainingRuns.some((run) => run.id === selectedRunId)
    ) {
      setSelectedRunId(trainingRuns[0]?.id ?? "");
    }
  }, [trainingRuns, selectedRunId]);

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
    if (!selectedDatasetId && datasets[0]) {
      setSelectedDatasetId(datasets[0].id);
      return;
    }
    if (
      selectedDatasetId &&
      !datasets.some((dataset) => dataset.id === selectedDatasetId)
    ) {
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
      !datasetVersions.some(
        (version) => version.id === selectedDatasetVersionId,
      )
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

  useEffect(() => {
    if (!selectedRunDetailIsLive) {
      return;
    }
    const intervalId = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(intervalId);
  }, [selectedRunDetailIsLive, selectedRunDetail?.id]);

  function invalidateTrainingState(runId: string) {
    queryClient.invalidateQueries({ queryKey: ["training-runs", projectId] });
    queryClient.invalidateQueries({ queryKey: ["training-run", runId] });
    queryClient.invalidateQueries({ queryKey: ["training-run-events", runId] });
    queryClient.invalidateQueries({ queryKey: ["training-run-logs", runId] });
    queryClient.invalidateQueries({
      queryKey: ["training-run-orchestration-status", runId],
    });
    queryClient.invalidateQueries({ queryKey: ["experiments", projectId] });
  }

  function refreshSelectedRunState() {
    if (!selectedRunDetail) {
      return;
    }
    setOperationError(null);
    setOperationMessage(`Refreshed training run ${selectedRunDetail.id.slice(0, 8)}.`);
    invalidateTrainingState(selectedRunDetail.id);
  }

  function closeCreateForm() {
    setIsCreateOpen(false);
    setLineageMode("dataset");
    setRunName("manual-training-run");
    setAlgorithm("xgboost");
    setModelType("xgboost");
    setObjectiveMetricName("auc");
    setHyperparametersText(defaultHyperparametersText);
  }

  function applyRunnerProfile(profile: TrainingRunnerProfile) {
    setIsCreateOpen(true);
    setLineageMode("dataset");
    setRunName(`${profile.slug}-live-run`);
    setAlgorithm(profile.default_algorithm);
    setModelType(profile.default_model_type);
    setObjectiveMetricName(profile.objective_metric_name);
    setHyperparametersText(
      JSON.stringify(profile.default_hyperparameters, null, 2),
    );
    setOperationMessage(
      profile.availability.available
        ? `Loaded ${profile.display_name} profile.`
        : null,
    );
    setOperationError(
      profile.availability.available
        ? null
        : `External profile is missing ${profile.availability.missing.join(", ")}.`,
    );
  }

  function handleStartRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (runName.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Training run name must be at least 3 characters.");
      return;
    }
    if (algorithm.trim().length < 2 || modelType.trim().length < 2) {
      setOperationMessage(null);
      setOperationError(
        "Algorithm and model type must be at least 2 characters.",
      );
      return;
    }
    if (!objectiveMetricName.trim()) {
      setOperationMessage(null);
      setOperationError("Objective metric name is required.");
      return;
    }
    if (lineageMode === "dataset" && !selectedDatasetVersion) {
      setOperationMessage(null);
      setOperationError("Training requires a dataset version.");
      return;
    }
    if (lineageMode === "feature_set" && !selectedFeatureSet) {
      setOperationMessage(null);
      setOperationError("Training requires a feature set.");
      return;
    }
    startRunMutation.mutate();
  }

  function handleRecordResult(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    recordResultMutation.mutate();
  }

  return (
    <>
      <PageHeader
        eyebrow="Workflow Plane"
        title="Training Runs"
        description="Airflow-orchestrated training jobs with retries, cancellation, evaluation, and artifact tracking."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          label="Queued"
          value={String(counts.queued ?? 0)}
          detail="awaiting workers"
        />
        <MetricCard
          label="Running"
          value={String(counts.running ?? 0)}
          detail="active jobs"
        />
        <MetricCard
          label="Succeeded"
          value={String(counts.succeeded ?? 0)}
          detail={`${terminalCount} terminal`}
          tone="success"
        />
        <MetricCard
          label="Failed"
          value={String(failedCount)}
          detail={`${counts.canceled ?? 0} canceled`}
          tone={failedCount > 0 ? "danger" : "neutral"}
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
        <DataPanel title="External Package Profiles">
          {!token ? (
            <StateMessage message="Sign in to inspect external package runners." />
          ) : runnerProfilesQuery.error ? (
            <StateMessage
              message="External package profile request failed."
              tone="danger"
            />
          ) : runnerProfiles.length === 0 ? (
            <StateMessage
              message={
                runnerProfilesQuery.isFetching
                  ? "Loading external package profiles."
                  : "No external package profiles are configured."
              }
            />
          ) : (
            <div className="grid gap-3 xl:grid-cols-2">
              {runnerProfiles.map((profile) => (
                <ExternalTrainingProfileCard
                  key={profile.slug}
                  profile={profile}
                  onUseProfile={() => applyRunnerProfile(profile)}
                />
              ))}
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <DataPanel
          title="Training Queue"
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
              Run
            </button>
          }
        >
          {isCreateOpen ? (
            <StartRunForm
              experiments={experiments}
              datasets={datasets}
              datasetVersions={datasetVersions}
              featureSets={featureSets}
              selectedExperiment={selectedExperiment}
              selectedDataset={selectedDataset}
              selectedDatasetVersionId={selectedDatasetVersion?.id ?? ""}
              selectedFeatureSet={selectedFeatureSet}
              lineageMode={lineageMode}
              runName={runName}
              algorithm={algorithm}
              modelType={modelType}
              objectiveMetricName={objectiveMetricName}
              hyperparametersText={hyperparametersText}
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
              onCancel={closeCreateForm}
              onExperimentChange={setSelectedExperimentId}
              onDatasetChange={(datasetId) => {
                setSelectedDatasetId(datasetId);
                setSelectedDatasetVersionId("");
              }}
              onDatasetVersionChange={setSelectedDatasetVersionId}
              onFeatureSetChange={setSelectedFeatureSetId}
              onLineageModeChange={setLineageMode}
              onRunNameChange={setRunName}
              onAlgorithmChange={setAlgorithm}
              onModelTypeChange={setModelType}
              onObjectiveMetricNameChange={setObjectiveMetricName}
              onHyperparametersTextChange={setHyperparametersText}
            />
          ) : null}
          {!canLoadTrainingRuns ? (
            <StateMessage message="No project context is selected." />
          ) : runsQuery.error ? (
            <StateMessage
              message="Training run request failed."
              tone="danger"
            />
          ) : trainingRuns.length === 0 ? (
            <StateMessage
              message={
                runsQuery.isFetching
                  ? "Loading training runs."
                  : "No training runs submitted for this project."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[980px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Run</th>
                    <th>Algorithm</th>
                    <th>Objective</th>
                    <th>Status</th>
                    <th>Metric</th>
                    <th>Workflow</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {trainingRuns.map((run) => (
                    <TrainingRunRow
                      key={run.id}
                      run={run}
                      selected={run.id === selectedRun?.id}
                      isCanceling={cancelRunMutation.isPending}
                      onSelect={() => setSelectedRunId(run.id)}
                      onCancel={() => cancelRunMutation.mutate(run)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel
          title="Run Detail"
          action={
            <button
              type="button"
              aria-label="Refresh training run progress"
              onClick={refreshSelectedRunState}
              disabled={!selectedRunDetail || selectedRunQuery.isFetching}
              className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-steel transition hover:text-ink disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw
                className={[
                  "h-4 w-4",
                  selectedRunQuery.isFetching ? "animate-spin" : "",
                ].join(" ")}
              />
              Refresh
            </button>
          }
        >
          {!selectedRunDetail ? (
            <StateMessage message="No training run is selected." />
          ) : selectedRunQuery.error ? (
            <StateMessage
              message="Training run detail request failed."
              tone="danger"
            />
          ) : (
            <RunDetail
              run={selectedRunDetail}
              orchestrationStatus={orchestrationStatus}
              orchestrationStatusLoading={orchestrationStatusQuery.isFetching}
              orchestrationStatusFailed={Boolean(orchestrationStatusQuery.error)}
              logs={logs}
              events={events}
              nowMs={nowMs}
            />
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <DataPanel title="Record Result">
          {!selectedRunDetail ? (
            <StateMessage message="Select a training run before recording results." />
          ) : isTerminalStatus(selectedRunDetail.status) ? (
            <StateMessage message="Selected training run already has a terminal status." />
          ) : (
            <form onSubmit={handleRecordResult} className="grid gap-4">
              <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                Result Status
                <select
                  value={resultStatus}
                  onChange={(event) =>
                    setResultStatus(
                      event.target.value as "succeeded" | "failed" | "canceled",
                    )
                  }
                  className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                >
                  <option value="succeeded">succeeded</option>
                  <option value="failed">failed</option>
                  <option value="canceled">canceled</option>
                </select>
              </label>
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
                  onChange={(event) =>
                    setEvaluationReportText(event.target.value)
                  }
                  rows={5}
                  className="rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
                />
              </label>
              <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                Error Message
                <input
                  value={resultErrorMessage}
                  onChange={(event) =>
                    setResultErrorMessage(event.target.value)
                  }
                  className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                />
              </label>
              <button
                type="submit"
                disabled={recordResultMutation.isPending}
                className="inline-flex h-10 w-fit items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <ClipboardCheck className="h-4 w-4" />
                Record result
              </button>
            </form>
          )}
        </DataPanel>

        <DataPanel title="Run Events">
          {!selectedRunDetail ? (
            <StateMessage message="No training run is selected." />
          ) : eventsQuery.error ? (
            <StateMessage
              message="Training run event request failed."
              tone="danger"
            />
          ) : events.length === 0 ? (
            <StateMessage
              message={
                eventsQuery.isFetching
                  ? "Loading training run events."
                  : "No events are recorded for this run."
              }
            />
          ) : (
            <div className="space-y-3">
              {events.map((event) => (
                <EventRow key={event.id} event={event} />
              ))}
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6">
        <DataPanel
          title="Execution Logs"
          action={
            <span className="rounded bg-field px-2 py-1 text-xs font-medium text-steel">
              {selectedRunDetailIsLive ? "Live" : "Snapshot"}
            </span>
          }
        >
          <section aria-label="Execution logs">
            {!selectedRunDetail ? (
              <StateMessage message="No training run is selected." />
            ) : logsQuery.error ? (
              <StateMessage
                message="Training run log request failed."
                tone="danger"
              />
            ) : logs.length === 0 ? (
              <StateMessage
                message={
                  logsQuery.isFetching
                    ? "Loading training run logs."
                    : "No execution logs are recorded for this run."
                }
              />
            ) : (
              <div className="max-h-[420px] space-y-2 overflow-auto rounded border border-slate-200 bg-slate-950 p-3">
                {logs.map((log) => (
                  <LogRow key={log.id} log={log} />
                ))}
              </div>
            )}
          </section>
        </DataPanel>
      </div>
    </>
  );
}

const defaultHyperparametersText = `{
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

type StartRunFormProps = {
  experiments: Experiment[];
  datasets: Dataset[];
  datasetVersions: Array<{
    id: string;
    version: number;
    status: string;
  }>;
  featureSets: FeatureSet[];
  selectedExperiment: Experiment | undefined;
  selectedDataset: Dataset | undefined;
  selectedDatasetVersionId: string;
  selectedFeatureSet: FeatureSet | undefined;
  lineageMode: "dataset" | "feature_set";
  runName: string;
  algorithm: string;
  modelType: string;
  objectiveMetricName: string;
  hyperparametersText: string;
  isPending: boolean;
  dependenciesLoading: boolean;
  dependenciesError: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onExperimentChange: (value: string) => void;
  onDatasetChange: (value: string) => void;
  onDatasetVersionChange: (value: string) => void;
  onFeatureSetChange: (value: string) => void;
  onLineageModeChange: (value: "dataset" | "feature_set") => void;
  onRunNameChange: (value: string) => void;
  onAlgorithmChange: (value: string) => void;
  onModelTypeChange: (value: string) => void;
  onObjectiveMetricNameChange: (value: string) => void;
  onHyperparametersTextChange: (value: string) => void;
};

function ExternalTrainingProfileCard({
  profile,
  onUseProfile,
}: {
  profile: TrainingRunnerProfile;
  onUseProfile: () => void;
}) {
  return (
    <div className="rounded border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <PackageCheck className="h-4 w-4 text-signal" aria-hidden="true" />
            {profile.display_name}
          </div>
          <p className="mt-2 text-sm leading-6 text-steel">{profile.description}</p>
        </div>
        <span
          className={[
            "inline-flex h-7 shrink-0 items-center rounded border px-2 text-xs font-semibold",
            profile.availability.available
              ? "border-emerald-200 bg-emerald-50 text-signal"
              : "border-amber-200 bg-amber-50 text-amber-700",
          ].join(" ")}
        >
          {profile.availability.available ? "available" : "missing assets"}
        </span>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-steel md:grid-cols-2">
        <div className="truncate">package: {profile.package_name}</div>
        <div className="truncate">runner: {profile.runner_kind}</div>
        <div className="truncate">algorithm: {profile.default_algorithm}</div>
        <div className="truncate">objective: {profile.objective_metric_name}</div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {profile.supported_algorithms.map((algorithm) => (
          <span
            key={algorithm}
            className="inline-flex h-7 items-center rounded border border-slate-200 bg-field px-2 text-xs font-medium text-steel"
          >
            {algorithm}
          </span>
        ))}
      </div>
      <div className="mt-3 rounded border border-slate-200 bg-cloud p-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase text-steel">
          <SquareTerminal className="h-4 w-4" aria-hidden="true" />
          Command Preview
        </div>
        <code className="mt-2 block max-h-20 overflow-auto whitespace-pre-wrap break-words rounded bg-ink px-3 py-2 text-xs text-white">
          {profile.command_preview.join(" ")}
        </code>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-steel">
        <div className="truncate">repo: {profile.availability.repo_root}</div>
        <div className="truncate">data: {profile.availability.data_dir}</div>
      </div>
      <button
        type="button"
        onClick={onUseProfile}
        aria-label={`Use profile ${profile.display_name}`}
        className="mt-4 inline-flex h-9 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700"
      >
        <Play className="h-4 w-4" aria-hidden="true" />
        Use profile
      </button>
    </div>
  );
}

function StartRunForm({
  experiments,
  datasets,
  datasetVersions,
  featureSets,
  selectedExperiment,
  selectedDataset,
  selectedDatasetVersionId,
  selectedFeatureSet,
  lineageMode,
  runName,
  algorithm,
  modelType,
  objectiveMetricName,
  hyperparametersText,
  isPending,
  dependenciesLoading,
  dependenciesError,
  onSubmit,
  onCancel,
  onExperimentChange,
  onDatasetChange,
  onDatasetVersionChange,
  onFeatureSetChange,
  onLineageModeChange,
  onRunNameChange,
  onAlgorithmChange,
  onModelTypeChange,
  onObjectiveMetricNameChange,
  onHyperparametersTextChange,
}: StartRunFormProps) {
  const lineageReady =
    lineageMode === "dataset"
      ? datasetVersions.length > 0
      : featureSets.length > 0;
  const canSubmit =
    !isPending &&
    !dependenciesLoading &&
    !dependenciesError &&
    Boolean(selectedExperiment && lineageReady);
  return (
    <form
      aria-label="Start training run"
      onSubmit={onSubmit}
      className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(180px,1fr)_minmax(180px,1fr)]">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Run Name
          <input
            value={runName}
            onChange={(event) => onRunNameChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Experiment
          <select
            value={selectedExperiment?.id ?? ""}
            onChange={(event) => onExperimentChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          >
            {experiments.map((experiment) => (
              <option key={experiment.id} value={experiment.id}>
                {experiment.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="mt-3 grid gap-3 lg:grid-cols-[140px_1fr_1fr]">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Lineage Source
          <select
            value={lineageMode}
            onChange={(event) =>
              onLineageModeChange(
                event.target.value as "dataset" | "feature_set",
              )
            }
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
      <div className="mt-3 grid gap-3 lg:grid-cols-3">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Algorithm
          <input
            value={algorithm}
            onChange={(event) => onAlgorithmChange(event.target.value)}
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
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Objective Metric
          <input
            value={objectiveMetricName}
            onChange={(event) =>
              onObjectiveMetricNameChange(event.target.value)
            }
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
      </div>
      <label className="mt-3 grid gap-1 text-xs font-semibold uppercase text-steel">
        Hyperparameters
        <textarea
          value={hyperparametersText}
          onChange={(event) => onHyperparametersTextChange(event.target.value)}
          rows={6}
          className="rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
        />
      </label>
      {dependenciesError ? (
        <div className="mt-3 rounded border border-rose-200 bg-rose-50 p-3 text-sm text-risk">
          Training run dependencies failed to load.
        </div>
      ) : !lineageReady ? (
        <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Select an available dataset version or feature set before starting a
          run.
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
          aria-label="Cancel training run creation"
          onClick={onCancel}
          className="inline-flex h-9 w-9 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </form>
  );
}

function TrainingRunRow({
  run,
  selected,
  isCanceling,
  onSelect,
  onCancel,
}: {
  run: TrainingRun;
  selected: boolean;
  isCanceling: boolean;
  onSelect: () => void;
  onCancel: () => void;
}) {
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3">
        <div className="font-medium">{run.id.slice(0, 8)}</div>
        <div className="text-xs text-steel">{run.model_type}</div>
      </td>
      <td>{run.algorithm}</td>
      <td>{run.objective_metric_name}</td>
      <td>
        <span className={statusClassName(run.status)}>{run.status}</span>
      </td>
      <td>{firstMetric(run.metrics)}</td>
      <td className="max-w-[220px] truncate">{run.orchestrator_run_id}</td>
      <td>
        <div className="flex items-center gap-2">
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
          {canCancelStatus(run.status) ? (
            <button
              type="button"
              aria-label={`Cancel training run ${run.id.slice(0, 8)}`}
              onClick={onCancel}
              disabled={isCanceling}
              className="inline-flex h-8 w-8 items-center justify-center rounded border border-rose-200 bg-rose-50 text-risk transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <CircleStop className="h-4 w-4" />
            </button>
          ) : null}
        </div>
      </td>
    </tr>
  );
}

function RunDetail({
  run,
  orchestrationStatus,
  orchestrationStatusLoading,
  orchestrationStatusFailed,
  logs,
  events,
  nowMs,
}: {
  run: TrainingRun;
  orchestrationStatus: TrainingOrchestrationStatus | undefined;
  orchestrationStatusLoading: boolean;
  orchestrationStatusFailed: boolean;
  logs: TrainingRunLog[];
  events: TrainingRunEvent[];
  nowMs: number;
}) {
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold">{run.id.slice(0, 8)}</div>
          <div className="mt-1 text-xs text-steel">{run.artifact_uri}</div>
        </div>
        <span className={statusClassName(run.status)}>{run.status}</span>
      </div>
      <TrainingProgress run={run} logs={logs} events={events} nowMs={nowMs} />
      <div className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3">
        <SignalTile
          icon={<Activity className="h-4 w-4" />}
          label="Workflow"
          value={run.orchestrator_run_id || "not submitted"}
          detail={run.experiment_run_id.slice(0, 8)}
        />
        <SignalTile
          icon={<CheckCircle className="h-4 w-4" />}
          label="Objective"
          value={run.objective_metric_name}
          detail={firstMetric(run.metrics)}
        />
        <SignalTile
          icon={<ClipboardCheck className="h-4 w-4" />}
          label="Lineage"
          value={run.dataset_version_id ? "dataset" : "feature set"}
          detail={(
            run.dataset_version_id ??
            run.feature_set_id ??
            "none"
          ).slice(0, 8)}
        />
      </div>
      <div className="rounded border border-slate-200 p-3 text-sm">
        <div className="font-medium">Run Configuration</div>
        <div className="mt-2 grid gap-2 text-xs text-steel sm:grid-cols-2">
          <div>algorithm: {run.algorithm}</div>
          <div>model: {run.model_type}</div>
          <div>experiment: {run.experiment_id.slice(0, 8)}</div>
          <div>requested by: {run.requested_by.slice(0, 8)}</div>
        </div>
      </div>
      <div className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3">
        <SignalTile
          icon={<Play className="h-4 w-4" />}
          label="Attempts"
          value={`${run.attempt_count}/${run.max_attempts}`}
          detail={run.worker_id ?? "no active worker"}
        />
        <SignalTile
          icon={<Activity className="h-4 w-4" />}
          label="Lease"
          value={formatTimestamp(run.lease_expires_at)}
          detail={`heartbeat ${formatTimestamp(run.last_heartbeat_at)}`}
        />
        <SignalTile
          icon={<ClipboardCheck className="h-4 w-4" />}
          label="Retry"
          value={formatTimestamp(run.next_retry_at)}
          detail={lifecycleDetail(run)}
        />
      </div>
      <div className="rounded border border-slate-200 p-3 text-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="font-medium">Orchestration Status</div>
            <div className="mt-1 text-xs text-steel">
              {orchestrationStatusLoading
                ? "Polling orchestrator state"
                : `observed ${formatTimestamp(
                    orchestrationStatus?.observed_at ?? null,
                  )}`}
            </div>
          </div>
          <span
            className={statusClassName(
              orchestrationStatus?.mapped_training_status ??
                orchestrationStatus?.external_status ??
                run.status,
            )}
          >
            {orchestrationStatusFailed
              ? "unavailable"
              : (orchestrationStatus?.external_status ?? run.status)}
          </span>
        </div>
        <div className="mt-3 grid gap-2 text-xs text-steel sm:grid-cols-2">
          <div>adapter: {orchestrationStatus?.orchestrator ?? "local"}</div>
          <div>
            mapped status:{" "}
            {orchestrationStatus?.mapped_training_status ?? run.status}
          </div>
          <div>
            terminal:{" "}
            {orchestrationStatus
              ? orchestrationStatus.is_terminal
                ? "yes"
                : "no"
              : isTerminalStatus(run.status)
                ? "yes"
                : "no"}
          </div>
          <div className="truncate">
            external link: {orchestrationStatus?.external_url ?? "none"}
          </div>
        </div>
      </div>
      {run.error_message ? (
        <div className="rounded border border-rose-200 bg-rose-50 p-3 text-sm text-risk">
          {run.error_message}
        </div>
      ) : null}
    </div>
  );
}

function TrainingProgress({
  run,
  logs,
  events,
  nowMs,
}: {
  run: TrainingRun;
  logs: TrainingRunLog[];
  events: TrainingRunEvent[];
  nowMs: number;
}) {
  const progress = trainingProgress(run.status);
  const latestLog = latestTrainingLog(logs);
  return (
    <section
      aria-label="Training run progress"
      className="rounded border border-slate-200 p-3"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Gauge className="h-4 w-4 text-signal" />
            Live Progress
          </div>
          <div className="mt-1 text-xs text-steel">
            {progress.phase} / {progress.percent}%
          </div>
        </div>
        <span className={statusClassName(run.status)}>{run.status}</span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded bg-slate-100">
        <div
          role="progressbar"
          aria-label="Training run lifecycle progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress.percent}
          className="h-full rounded bg-signal transition-all"
          style={{ width: `${progress.percent}%` }}
        />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SignalTile
          icon={<Clock className="h-4 w-4" />}
          label="Elapsed"
          value={formatDurationBetween(run.queued_at, run.completed_at, nowMs)}
          detail={isLiveTrainingRun(run.status) ? "live timer" : "total time"}
        />
        <SignalTile
          icon={<Activity className="h-4 w-4" />}
          label="Queue Wait"
          value={formatDurationBetween(
            run.queued_at,
            run.started_at ?? run.completed_at,
            nowMs,
          )}
          detail={run.worker_id ?? "worker pending"}
        />
        <SignalTile
          icon={<Play className="h-4 w-4" />}
          label="Runtime"
          value={formatDurationBetween(run.started_at, run.completed_at, nowMs)}
          detail={`${run.attempt_count}/${run.max_attempts} attempts`}
        />
        <SignalTile
          icon={<SquareTerminal className="h-4 w-4" />}
          label="Logs"
          value={`${logs.length} lines`}
          detail={latestLog ? latestLog.message : `${events.length} events`}
        />
      </div>
    </section>
  );
}

function EventRow({ event }: { event: TrainingRunEvent }) {
  return (
    <div className="rounded border border-slate-200 p-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-medium">{event.message}</div>
          <div className="mt-1 text-xs text-steel">
            {formatEventMetadata(event.metadata)}
          </div>
        </div>
        <span className="rounded bg-field px-2 py-1 text-xs font-medium">
          {event.event_type}
        </span>
      </div>
    </div>
  );
}

function LogRow({ log }: { log: TrainingRunLog }) {
  return (
    <div className="grid gap-2 rounded border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 md:grid-cols-[64px_86px_minmax(120px,180px)_1fr]">
      <div className="font-mono text-slate-400">#{log.sequence}</div>
      <div className={logLevelClassName(log.level)}>{log.level}</div>
      <div className="truncate font-mono text-slate-400">{log.logger}</div>
      <div className="min-w-0">
        <div className="break-words font-mono">{log.message}</div>
        <div className="mt-1 truncate font-mono text-slate-500">
          {formatLogMetadata(log.metadata)}
        </div>
      </div>
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

function isTerminalStatus(status: string): boolean {
  return (
    status === "succeeded" ||
    status === "failed" ||
    status === "canceled" ||
    status === "dead_lettered"
  );
}

function canCancelStatus(status: string): boolean {
  return status === "requested" || status === "queued" || status === "running";
}

function isLiveTrainingRun(status: string): boolean {
  return status === "requested" || status === "queued" || status === "running";
}

function trainingProgress(status: string): { phase: string; percent: number } {
  if (status === "requested") {
    return { phase: "requested", percent: 10 };
  }
  if (status === "queued") {
    return { phase: "queued", percent: 25 };
  }
  if (status === "running") {
    return { phase: "running", percent: 65 };
  }
  if (status === "succeeded") {
    return { phase: "complete", percent: 100 };
  }
  if (status === "failed" || status === "dead_lettered") {
    return { phase: "failed", percent: 100 };
  }
  if (status === "canceled") {
    return { phase: "canceled", percent: 100 };
  }
  return { phase: status, percent: 0 };
}

function statusClassName(status: string): string {
  if (status === "succeeded") {
    return "rounded bg-emerald-50 px-2 py-1 text-xs font-medium text-signal";
  }
  if (status === "queued" || status === "running" || status === "requested") {
    return "rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700";
  }
  if (status === "failed" || status === "canceled" || status === "dead_lettered") {
    return "rounded bg-rose-50 px-2 py-1 text-xs font-medium text-risk";
  }
  return "rounded bg-field px-2 py-1 text-xs font-medium";
}

function lifecycleDetail(run: TrainingRun): string {
  if (run.completed_at) {
    return `completed ${formatTimestamp(run.completed_at)}`;
  }
  if (run.started_at) {
    return `started ${formatTimestamp(run.started_at)}`;
  }
  return `queued ${formatTimestamp(run.queued_at)}`;
}

function latestTrainingLog(logs: TrainingRunLog[]): TrainingRunLog | null {
  return logs.length > 0 ? logs[logs.length - 1] : null;
}

function formatDurationBetween(
  start: string | null,
  end: string | null,
  nowMs: number,
): string {
  const startMs = timestampMs(start);
  if (startMs === null) {
    return "none";
  }
  const endMs = timestampMs(end) ?? nowMs;
  return formatDurationMs(Math.max(endMs - startMs, 0));
}

function timestampMs(value: string | null): number | null {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatDurationMs(value: number): string {
  const totalSeconds = Math.floor(value / 1000);
  if (totalSeconds < 60) {
    return `${totalSeconds}s`;
  }
  const totalMinutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (totalMinutes < 60) {
    return `${totalMinutes}m ${seconds.toString().padStart(2, "0")}s`;
  }
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours < 24) {
    return `${hours}h ${minutes.toString().padStart(2, "0")}m`;
  }
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;
  return `${days}d ${remainingHours.toString().padStart(2, "0")}h`;
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "none";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function logLevelClassName(level: string): string {
  if (level === "error") {
    return "w-fit rounded bg-rose-950 px-2 py-0.5 font-medium text-rose-200";
  }
  if (level === "warning") {
    return "w-fit rounded bg-amber-950 px-2 py-0.5 font-medium text-amber-200";
  }
  return "w-fit rounded bg-emerald-950 px-2 py-0.5 font-medium text-emerald-200";
}

function parseJsonObject(
  value: string,
  label: string,
): Record<string, unknown> {
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

function parseMetricObject(value: string): Record<string, number> {
  const parsed = parseJsonObject(value, "Metrics");
  const metrics: Record<string, number> = {};
  for (const [key, rawValue] of Object.entries(parsed)) {
    if (typeof rawValue !== "number" || !Number.isFinite(rawValue)) {
      throw new Error("Training metrics must be finite numbers.");
    }
    metrics[key] = rawValue;
  }
  return metrics;
}

function optionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function formatEventMetadata(metadata: Record<string, unknown>): string {
  const workflowId = metadata.orchestrator_run_id;
  if (typeof workflowId === "string") {
    return workflowId;
  }
  const workerId = metadata.worker_id;
  if (typeof workerId === "string") {
    return workerId;
  }
  return "event metadata recorded";
}

function formatLogMetadata(metadata: Record<string, unknown>): string {
  const entries = Object.entries(metadata).filter(
    ([, value]) => value !== null,
  );
  if (entries.length === 0) {
    return "no metadata";
  }
  return entries
    .slice(0, 3)
    .map(([key, value]) => `${key}=${formatMetadataValue(value)}`)
    .join(" ");
}

function formatMetadataValue(value: unknown): string {
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `${value.length} items`;
  }
  if (value && typeof value === "object") {
    return "object";
  }
  return "none";
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
