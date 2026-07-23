import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle, CircleCheck, CircleX, Play, Plus, RefreshCw, X } from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";

import { listDatasets, listDatasetVersions, type Dataset } from "../../datasets/api/datasets";
import { listDeployments, type Deployment } from "../../deployments/api/deployments";
import { listExperiments, type Experiment } from "../../experiments/api/experiments";
import { listFeatureSets, type FeatureSet } from "../../feature_store/api/featureStore";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  approveRetrainingRun,
  createRetrainingPolicy,
  listRetrainingPolicies,
  listRetrainingRuns,
  rejectRetrainingRun,
  triggerRetrainingRun,
  type RetrainingPolicy,
  type RetrainingRun,
} from "../api/retraining";

export function RetrainingPage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadRetraining = Boolean(token && projectId);
  const [selectedPolicyId, setSelectedPolicyId] = useState("");
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedDeploymentId, setSelectedDeploymentId] = useState("");
  const [selectedExperimentId, setSelectedExperimentId] = useState("");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [selectedDatasetVersionId, setSelectedDatasetVersionId] = useState("");
  const [selectedFeatureSetId, setSelectedFeatureSetId] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [policyName, setPolicyName] = useState("");
  const [policyDescription, setPolicyDescription] = useState("");
  const [triggerType, setTriggerType] = useState("drift");
  const [lineageMode, setLineageMode] = useState<"dataset" | "feature_set">("dataset");
  const [minDriftScore, setMinDriftScore] = useState("0.2");
  const [minDriftedFeatures, setMinDriftedFeatures] = useState("1");
  const [alertInfoEnabled, setAlertInfoEnabled] = useState(false);
  const [alertWarningEnabled, setAlertWarningEnabled] = useState(true);
  const [alertCriticalEnabled, setAlertCriticalEnabled] = useState(true);
  const [alertMinObservedValue, setAlertMinObservedValue] = useState("");
  const [runNamePrefix, setRunNamePrefix] = useState("retrain");
  const [algorithm, setAlgorithm] = useState("xgboost");
  const [modelType, setModelType] = useState("xgboost");
  const [objectiveMetricName, setObjectiveMetricName] = useState("auc");
  const [hyperparametersText, setHyperparametersText] = useState(defaultHyperparametersText);
  const [cooldownSeconds, setCooldownSeconds] = useState("3600");
  const [maxRunsPerDay, setMaxRunsPerDay] = useState("3");
  const [approvalRequired, setApprovalRequired] = useState(true);
  const [enabled, setEnabled] = useState(true);
  const [manualReason, setManualReason] = useState("Operator requested retraining.");
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const policiesQuery = useQuery({
    queryKey: ["retraining-policies", projectId],
    queryFn: () => listRetrainingPolicies(projectId ?? "", token ?? ""),
    enabled: canLoadRetraining,
  });
  const runsQuery = useQuery({
    queryKey: ["retraining-runs", projectId],
    queryFn: () => listRetrainingRuns(projectId ?? "", token ?? ""),
    enabled: canLoadRetraining,
  });
  const deploymentsQuery = useQuery({
    queryKey: ["deployments", projectId],
    queryFn: () => listDeployments(projectId ?? "", token ?? ""),
    enabled: canLoadRetraining,
  });
  const experimentsQuery = useQuery({
    queryKey: ["experiments", projectId],
    queryFn: () => listExperiments(projectId ?? "", token ?? ""),
    enabled: canLoadRetraining,
  });
  const datasetsQuery = useQuery({
    queryKey: ["datasets", projectId],
    queryFn: () => listDatasets(projectId ?? "", token ?? ""),
    enabled: canLoadRetraining,
  });
  const featureSetsQuery = useQuery({
    queryKey: ["feature-sets", projectId],
    queryFn: () => listFeatureSets(projectId ?? "", token ?? ""),
    enabled: canLoadRetraining,
  });
  const policies = useMemo(
    () => policiesQuery.data?.items ?? [],
    [policiesQuery.data?.items],
  );
  const runs = useMemo(() => runsQuery.data?.items ?? [], [runsQuery.data?.items]);
  const deployments = useMemo(
    () => deploymentsQuery.data?.items ?? [],
    [deploymentsQuery.data?.items],
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
  const selectedPolicy =
    policies.find((policy) => policy.id === selectedPolicyId) ?? policies[0];
  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? runs[0];
  const selectedDeployment =
    deployments.find((deployment) => deployment.id === selectedDeploymentId) ??
    deployments[0];
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
    datasetVersions.find((version) => version.id === selectedDatasetVersionId) ??
    datasetVersions[0];
  const selectedFeatureSet =
    featureSets.find((featureSet) => featureSet.id === selectedFeatureSetId) ??
    featureSets[0];
  const activePolicies = policies.filter((policy) => policy.enabled && policy.status === "active");
  const pendingRuns = runs.filter((run) => run.status === "pending_approval");
  const queuedRuns = runs.filter((run) => run.status === "queued");
  const terminalRuns = runs.filter((run) => ["rejected", "skipped", "failed"].includes(run.status));
  const createPolicyMutation = useMutation({
    mutationFn: () => {
      if (!projectId || !token) {
        throw new Error("Retraining policy creation requires project context.");
      }
      if (!selectedDeployment) {
        throw new Error("Retraining policy creation requires a deployment.");
      }
      if (!selectedExperiment) {
        throw new Error("Retraining policy creation requires an experiment.");
      }
      return createRetrainingPolicy(
        projectId,
        {
          deployment_id: selectedDeployment.id,
          name: policyName.trim(),
          description: policyDescription.trim(),
          trigger_type: triggerType,
          trigger_config: buildTriggerConfig(),
          training_template: buildTrainingTemplate(),
          cooldown_seconds: parseInteger(cooldownSeconds, "Cooldown", 0, 604_800),
          max_runs_per_day: parseInteger(maxRunsPerDay, "Max runs per day", 1, 50),
          approval_required: approvalRequired,
          enabled,
        },
        token,
      );
    },
    onSuccess: (policy) => {
      setOperationError(null);
      setOperationMessage(`Created retraining policy ${policy.name}.`);
      setSelectedPolicyId(policy.id);
      closeCreateForm();
      queryClient.invalidateQueries({ queryKey: ["retraining-policies", projectId] });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Retraining policy creation failed.",
      );
    },
  });
  const triggerRunMutation = useMutation({
    mutationFn: () => {
      if (!selectedPolicy || !token) {
        throw new Error("Manual retraining requires a selected policy.");
      }
      return triggerRetrainingRun(
        selectedPolicy.id,
        { reason: manualReason.trim() },
        token,
      );
    },
    onSuccess: (evaluation) => {
      setOperationError(null);
      if (evaluation.run) {
        setSelectedRunId(evaluation.run.id);
      }
      setOperationMessage(
        evaluation.triggered
          ? `Manual retraining ${runVerb(evaluation.run?.status ?? "requested")}.`
          : `Manual retraining skipped: ${evaluation.reason}`,
      );
      invalidateRunState();
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Manual retraining trigger failed.",
      );
    },
  });
  const approveRunMutation = useMutation({
    mutationFn: (run: RetrainingRun) => {
      if (!token) {
        throw new Error("Retraining approval requires API access.");
      }
      return approveRetrainingRun(run.id, token);
    },
    onSuccess: (run) => {
      setOperationError(null);
      setSelectedRunId(run.id);
      setOperationMessage(`Approved retraining run ${run.id.slice(0, 8)}.`);
      invalidateRunState();
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(error instanceof Error ? error.message : "Retraining approval failed.");
    },
  });
  const rejectRunMutation = useMutation({
    mutationFn: (run: RetrainingRun) => {
      if (!token) {
        throw new Error("Retraining rejection requires API access.");
      }
      return rejectRetrainingRun(run.id, token);
    },
    onSuccess: (run) => {
      setOperationError(null);
      setSelectedRunId(run.id);
      setOperationMessage(`Rejected retraining run ${run.id.slice(0, 8)}.`);
      invalidateRunState();
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(error instanceof Error ? error.message : "Retraining rejection failed.");
    },
  });

  useEffect(() => {
    if (!selectedPolicyId && policies[0]) {
      setSelectedPolicyId(policies[0].id);
      return;
    }
    if (selectedPolicyId && !policies.some((policy) => policy.id === selectedPolicyId)) {
      setSelectedPolicyId(policies[0]?.id ?? "");
    }
  }, [policies, selectedPolicyId]);

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

  function invalidateRunState() {
    queryClient.invalidateQueries({ queryKey: ["retraining-runs", projectId] });
    queryClient.invalidateQueries({ queryKey: ["training-runs", projectId] });
  }

  function closeCreateForm() {
    setIsCreateOpen(false);
    setPolicyName("");
    setPolicyDescription("");
    setTriggerType("drift");
    setLineageMode("dataset");
    setMinDriftScore("0.2");
    setMinDriftedFeatures("1");
    setAlertInfoEnabled(false);
    setAlertWarningEnabled(true);
    setAlertCriticalEnabled(true);
    setAlertMinObservedValue("");
    setRunNamePrefix("retrain");
    setAlgorithm("xgboost");
    setModelType("xgboost");
    setObjectiveMetricName("auc");
    setHyperparametersText(defaultHyperparametersText);
    setCooldownSeconds("3600");
    setMaxRunsPerDay("3");
    setApprovalRequired(true);
    setEnabled(true);
  }

  function handleCreatePolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (policyName.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Retraining policy name must be at least 3 characters.");
      return;
    }
    createPolicyMutation.mutate();
  }

  function buildTriggerConfig(): Record<string, unknown> {
    if (triggerType === "drift") {
      return {
        min_drift_score: parseRatio(minDriftScore, "Minimum drift score"),
        min_drifted_features: parseInteger(
          minDriftedFeatures,
          "Minimum drifted features",
          0,
          1000,
        ),
      };
    }
    if (triggerType === "alert") {
      const severities = [
        alertInfoEnabled ? "info" : null,
        alertWarningEnabled ? "warning" : null,
        alertCriticalEnabled ? "critical" : null,
      ].filter((value): value is string => Boolean(value));
      if (severities.length === 0) {
        throw new Error("Alert-triggered retraining requires at least one severity.");
      }
      const config: Record<string, unknown> = { severities };
      const minObserved = optionalNonNegativeFloat(alertMinObservedValue, "Minimum observed value");
      if (minObserved !== null) {
        config.min_observed_value = minObserved;
      }
      return config;
    }
    return {};
  }

  function buildTrainingTemplate(): Record<string, unknown> {
    if (!selectedExperiment) {
      throw new Error("Training template requires an experiment.");
    }
    if (runNamePrefix.trim().length < 3) {
      throw new Error("Run name prefix must be at least 3 characters.");
    }
    if (algorithm.trim().length < 2) {
      throw new Error("Algorithm must be at least 2 characters.");
    }
    if (modelType.trim().length < 2) {
      throw new Error("Model type must be at least 2 characters.");
    }
    if (!objectiveMetricName.trim()) {
      throw new Error("Objective metric name is required.");
    }
    const hyperparameters = parseJsonObject(hyperparametersText, "Hyperparameters");
    const datasetVersionId =
      lineageMode === "dataset" ? selectedDatasetVersion?.id ?? null : null;
    const featureSetId = lineageMode === "feature_set" ? selectedFeatureSet?.id ?? null : null;
    if (!datasetVersionId && !featureSetId) {
      throw new Error("Training template requires a dataset version or feature set.");
    }
    return {
      experiment_id: selectedExperiment.id,
      dataset_version_id: datasetVersionId,
      feature_set_id: featureSetId,
      run_name_prefix: runNamePrefix.trim(),
      algorithm: algorithm.trim(),
      model_type: modelType.trim(),
      objective_metric_name: objectiveMetricName.trim(),
      hyperparameters,
    };
  }

  return (
    <>
      <PageHeader
        eyebrow="Automation"
        title="Retraining"
        description="Policy-driven retraining loops with drift triggers, alert triggers, approval gates, and training job handoff."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Policies" value={String(policies.length)} detail="configured loops" />
        <MetricCard
          label="Active"
          value={String(activePolicies.length)}
          detail="eligible to trigger"
          tone="success"
        />
        <MetricCard
          label="Pending"
          value={String(pendingRuns.length)}
          detail="awaiting approval"
          tone={pendingRuns.length > 0 ? "warning" : "success"}
        />
        <MetricCard
          label="Queued"
          value={String(queuedRuns.length)}
          detail={`${terminalRuns.length} terminal`}
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

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <DataPanel
          title="Retraining Policies"
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
              Policy
            </button>
          }
        >
          {isCreateOpen ? (
            <CreatePolicyForm
              policyName={policyName}
              policyDescription={policyDescription}
              triggerType={triggerType}
              deployments={deployments}
              experiments={experiments}
              datasets={datasets}
              datasetVersions={datasetVersions}
              featureSets={featureSets}
              selectedDeployment={selectedDeployment}
              selectedExperiment={selectedExperiment}
              selectedDataset={selectedDataset}
              selectedDatasetVersionId={selectedDatasetVersion?.id ?? ""}
              selectedFeatureSet={selectedFeatureSet}
              lineageMode={lineageMode}
              minDriftScore={minDriftScore}
              minDriftedFeatures={minDriftedFeatures}
              alertInfoEnabled={alertInfoEnabled}
              alertWarningEnabled={alertWarningEnabled}
              alertCriticalEnabled={alertCriticalEnabled}
              alertMinObservedValue={alertMinObservedValue}
              runNamePrefix={runNamePrefix}
              algorithm={algorithm}
              modelType={modelType}
              objectiveMetricName={objectiveMetricName}
              hyperparametersText={hyperparametersText}
              cooldownSeconds={cooldownSeconds}
              maxRunsPerDay={maxRunsPerDay}
              approvalRequired={approvalRequired}
              enabled={enabled}
              isPending={createPolicyMutation.isPending}
              dependenciesLoading={
                deploymentsQuery.isFetching ||
                experimentsQuery.isFetching ||
                datasetsQuery.isFetching ||
                datasetVersionsQuery.isFetching ||
                featureSetsQuery.isFetching
              }
              dependenciesError={
                Boolean(deploymentsQuery.error) ||
                Boolean(experimentsQuery.error) ||
                Boolean(datasetsQuery.error) ||
                Boolean(datasetVersionsQuery.error) ||
                Boolean(featureSetsQuery.error)
              }
              onSubmit={handleCreatePolicy}
              onCancel={closeCreateForm}
              onPolicyNameChange={setPolicyName}
              onPolicyDescriptionChange={setPolicyDescription}
              onTriggerTypeChange={setTriggerType}
              onDeploymentChange={setSelectedDeploymentId}
              onExperimentChange={setSelectedExperimentId}
              onDatasetChange={(datasetId) => {
                setSelectedDatasetId(datasetId);
                setSelectedDatasetVersionId("");
              }}
              onDatasetVersionChange={setSelectedDatasetVersionId}
              onFeatureSetChange={setSelectedFeatureSetId}
              onLineageModeChange={setLineageMode}
              onMinDriftScoreChange={setMinDriftScore}
              onMinDriftedFeaturesChange={setMinDriftedFeatures}
              onAlertInfoChange={setAlertInfoEnabled}
              onAlertWarningChange={setAlertWarningEnabled}
              onAlertCriticalChange={setAlertCriticalEnabled}
              onAlertMinObservedValueChange={setAlertMinObservedValue}
              onRunNamePrefixChange={setRunNamePrefix}
              onAlgorithmChange={setAlgorithm}
              onModelTypeChange={setModelType}
              onObjectiveMetricNameChange={setObjectiveMetricName}
              onHyperparametersTextChange={setHyperparametersText}
              onCooldownSecondsChange={setCooldownSeconds}
              onMaxRunsPerDayChange={setMaxRunsPerDay}
              onApprovalRequiredChange={setApprovalRequired}
              onEnabledChange={setEnabled}
            />
          ) : null}
          {!canLoadRetraining ? (
            <StateMessage message="No project context is selected." />
          ) : policiesQuery.error ? (
            <StateMessage message="Retraining policy request failed." tone="danger" />
          ) : policies.length === 0 ? (
            <StateMessage
              message={
                policiesQuery.isFetching
                  ? "Loading retraining policies."
                  : "No retraining policies configured for this project."
              }
            />
          ) : (
            <div className="space-y-3">
              {policies.map((policy) => (
                <PolicyCard
                  key={policy.id}
                  policy={policy}
                  deployment={deploymentForPolicy(deployments, policy)}
                  selected={policy.id === selectedPolicy?.id}
                  onSelect={() => setSelectedPolicyId(policy.id)}
                />
              ))}
            </div>
          )}
        </DataPanel>

        <DataPanel title="Policy Operations">
          {!selectedPolicy ? (
            <StateMessage message="No retraining policy is selected." />
          ) : (
            <div className="grid gap-4">
              <PolicyDetail
                policy={selectedPolicy}
                deployment={deploymentForPolicy(deployments, selectedPolicy)}
              />
              <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                Manual Reason
                <textarea
                  value={manualReason}
                  onChange={(event) => setManualReason(event.target.value)}
                  rows={4}
                  className="rounded border border-slate-200 bg-white px-3 py-2 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                />
              </label>
              <button
                type="button"
                onClick={() => triggerRunMutation.mutate()}
                disabled={triggerRunMutation.isPending}
                className="inline-flex h-10 w-fit items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Play className="h-4 w-4" />
                Trigger manual run
              </button>
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <DataPanel title="Retraining Runs">
          {!canLoadRetraining ? (
            <StateMessage message="No project context is selected." />
          ) : runsQuery.error ? (
            <StateMessage message="Retraining run request failed." tone="danger" />
          ) : runs.length === 0 ? (
            <StateMessage
              message={
                runsQuery.isFetching
                  ? "Loading retraining runs."
                  : "No retraining runs have been recorded."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[960px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Run</th>
                    <th>Policy</th>
                    <th>Trigger</th>
                    <th>Status</th>
                    <th>Signal</th>
                    <th>Training</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <RunRow
                      key={run.id}
                      run={run}
                      policy={policyForRun(policies, run)}
                      selected={run.id === selectedRun?.id}
                      isMutating={approveRunMutation.isPending || rejectRunMutation.isPending}
                      onSelect={() => setSelectedRunId(run.id)}
                      onApprove={() => approveRunMutation.mutate(run)}
                      onReject={() => rejectRunMutation.mutate(run)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel title="Run Detail">
          {!selectedRun ? (
            <StateMessage message="No retraining run is selected." />
          ) : (
            <RunDetail run={selectedRun} policy={policyForRun(policies, selectedRun)} />
          )}
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

type CreatePolicyFormProps = {
  policyName: string;
  policyDescription: string;
  triggerType: string;
  deployments: Deployment[];
  experiments: Experiment[];
  datasets: Dataset[];
  datasetVersions: Array<{
    id: string;
    version: number;
    status: string;
  }>;
  featureSets: FeatureSet[];
  selectedDeployment: Deployment | undefined;
  selectedExperiment: Experiment | undefined;
  selectedDataset: Dataset | undefined;
  selectedDatasetVersionId: string;
  selectedFeatureSet: FeatureSet | undefined;
  lineageMode: "dataset" | "feature_set";
  minDriftScore: string;
  minDriftedFeatures: string;
  alertInfoEnabled: boolean;
  alertWarningEnabled: boolean;
  alertCriticalEnabled: boolean;
  alertMinObservedValue: string;
  runNamePrefix: string;
  algorithm: string;
  modelType: string;
  objectiveMetricName: string;
  hyperparametersText: string;
  cooldownSeconds: string;
  maxRunsPerDay: string;
  approvalRequired: boolean;
  enabled: boolean;
  isPending: boolean;
  dependenciesLoading: boolean;
  dependenciesError: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onPolicyNameChange: (value: string) => void;
  onPolicyDescriptionChange: (value: string) => void;
  onTriggerTypeChange: (value: string) => void;
  onDeploymentChange: (value: string) => void;
  onExperimentChange: (value: string) => void;
  onDatasetChange: (value: string) => void;
  onDatasetVersionChange: (value: string) => void;
  onFeatureSetChange: (value: string) => void;
  onLineageModeChange: (value: "dataset" | "feature_set") => void;
  onMinDriftScoreChange: (value: string) => void;
  onMinDriftedFeaturesChange: (value: string) => void;
  onAlertInfoChange: (value: boolean) => void;
  onAlertWarningChange: (value: boolean) => void;
  onAlertCriticalChange: (value: boolean) => void;
  onAlertMinObservedValueChange: (value: string) => void;
  onRunNamePrefixChange: (value: string) => void;
  onAlgorithmChange: (value: string) => void;
  onModelTypeChange: (value: string) => void;
  onObjectiveMetricNameChange: (value: string) => void;
  onHyperparametersTextChange: (value: string) => void;
  onCooldownSecondsChange: (value: string) => void;
  onMaxRunsPerDayChange: (value: string) => void;
  onApprovalRequiredChange: (value: boolean) => void;
  onEnabledChange: (value: boolean) => void;
};

function CreatePolicyForm({
  policyName,
  policyDescription,
  triggerType,
  deployments,
  experiments,
  datasets,
  datasetVersions,
  featureSets,
  selectedDeployment,
  selectedExperiment,
  selectedDataset,
  selectedDatasetVersionId,
  selectedFeatureSet,
  lineageMode,
  minDriftScore,
  minDriftedFeatures,
  alertInfoEnabled,
  alertWarningEnabled,
  alertCriticalEnabled,
  alertMinObservedValue,
  runNamePrefix,
  algorithm,
  modelType,
  objectiveMetricName,
  hyperparametersText,
  cooldownSeconds,
  maxRunsPerDay,
  approvalRequired,
  enabled,
  isPending,
  dependenciesLoading,
  dependenciesError,
  onSubmit,
  onCancel,
  onPolicyNameChange,
  onPolicyDescriptionChange,
  onTriggerTypeChange,
  onDeploymentChange,
  onExperimentChange,
  onDatasetChange,
  onDatasetVersionChange,
  onFeatureSetChange,
  onLineageModeChange,
  onMinDriftScoreChange,
  onMinDriftedFeaturesChange,
  onAlertInfoChange,
  onAlertWarningChange,
  onAlertCriticalChange,
  onAlertMinObservedValueChange,
  onRunNamePrefixChange,
  onAlgorithmChange,
  onModelTypeChange,
  onObjectiveMetricNameChange,
  onHyperparametersTextChange,
  onCooldownSecondsChange,
  onMaxRunsPerDayChange,
  onApprovalRequiredChange,
  onEnabledChange,
}: CreatePolicyFormProps) {
  const lineageReady =
    lineageMode === "dataset" ? datasetVersions.length > 0 : featureSets.length > 0;
  const canSubmit =
    !isPending &&
    !dependenciesLoading &&
    !dependenciesError &&
    Boolean(selectedDeployment && selectedExperiment && lineageReady);
  return (
    <form
      aria-label="Create retraining policy"
      onSubmit={onSubmit}
      className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(170px,0.8fr)_minmax(220px,1fr)]">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Policy Name
          <input
            value={policyName}
            onChange={(event) => onPolicyNameChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Policy Description
          <input
            value={policyDescription}
            onChange={(event) => onPolicyDescriptionChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
      </div>
      <div className="mt-3 grid gap-3 lg:grid-cols-3">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Policy Deployment
          <select
            value={selectedDeployment?.id ?? ""}
            onChange={(event) => onDeploymentChange(event.target.value)}
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
          Trigger Type
          <select
            value={triggerType}
            onChange={(event) => onTriggerTypeChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          >
            <option value="drift">drift</option>
            <option value="alert">alert</option>
            <option value="manual">manual</option>
          </select>
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
      <TriggerConfigFields
        triggerType={triggerType}
        minDriftScore={minDriftScore}
        minDriftedFeatures={minDriftedFeatures}
        alertInfoEnabled={alertInfoEnabled}
        alertWarningEnabled={alertWarningEnabled}
        alertCriticalEnabled={alertCriticalEnabled}
        alertMinObservedValue={alertMinObservedValue}
        onMinDriftScoreChange={onMinDriftScoreChange}
        onMinDriftedFeaturesChange={onMinDriftedFeaturesChange}
        onAlertInfoChange={onAlertInfoChange}
        onAlertWarningChange={onAlertWarningChange}
        onAlertCriticalChange={onAlertCriticalChange}
        onAlertMinObservedValueChange={onAlertMinObservedValueChange}
      />
      <div className="mt-4 rounded border border-slate-200 bg-white p-3">
        <div className="text-xs font-semibold uppercase text-steel">Training Template</div>
        <div className="mt-3 grid gap-3 lg:grid-cols-[140px_1fr_1fr]">
          <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
            Lineage Source
            <select
              value={lineageMode}
              onChange={(event) => onLineageModeChange(event.target.value as "dataset" | "feature_set")}
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
        <div className="mt-3 grid gap-3 lg:grid-cols-4">
          <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
            Run Name Prefix
            <input
              value={runNamePrefix}
              onChange={(event) => onRunNamePrefixChange(event.target.value)}
              className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
            />
          </label>
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
              onChange={(event) => onObjectiveMetricNameChange(event.target.value)}
              className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
            />
          </label>
        </div>
        <label className="mt-3 grid gap-1 text-xs font-semibold uppercase text-steel">
          Hyperparameters
          <textarea
            value={hyperparametersText}
            onChange={(event) => onHyperparametersTextChange(event.target.value)}
            rows={5}
            className="rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
      </div>
      <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_1fr_140px_120px]">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Cooldown Seconds
          <input
            inputMode="numeric"
            value={cooldownSeconds}
            onChange={(event) => onCooldownSecondsChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Max Runs Per Day
          <input
            inputMode="numeric"
            value={maxRunsPerDay}
            onChange={(event) => onMaxRunsPerDayChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <ToggleField
          label="Approval"
          checked={approvalRequired}
          onChange={onApprovalRequiredChange}
          text={approvalRequired ? "required" : "auto queue"}
        />
        <ToggleField
          label="Enabled"
          checked={enabled}
          onChange={onEnabledChange}
          text={enabled ? "enabled" : "disabled"}
        />
      </div>
      {dependenciesError ? (
        <div className="mt-3 rounded border border-rose-200 bg-rose-50 p-3 text-sm text-risk">
          Policy dependencies failed to load.
        </div>
      ) : !lineageReady ? (
        <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Select an available dataset version or feature set before creating the policy.
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex h-9 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <CheckCircle className="h-4 w-4" />
          Create policy
        </button>
        <button
          type="button"
          aria-label="Cancel retraining policy creation"
          onClick={onCancel}
          className="inline-flex h-9 w-9 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </form>
  );
}

function TriggerConfigFields({
  triggerType,
  minDriftScore,
  minDriftedFeatures,
  alertInfoEnabled,
  alertWarningEnabled,
  alertCriticalEnabled,
  alertMinObservedValue,
  onMinDriftScoreChange,
  onMinDriftedFeaturesChange,
  onAlertInfoChange,
  onAlertWarningChange,
  onAlertCriticalChange,
  onAlertMinObservedValueChange,
}: {
  triggerType: string;
  minDriftScore: string;
  minDriftedFeatures: string;
  alertInfoEnabled: boolean;
  alertWarningEnabled: boolean;
  alertCriticalEnabled: boolean;
  alertMinObservedValue: string;
  onMinDriftScoreChange: (value: string) => void;
  onMinDriftedFeaturesChange: (value: string) => void;
  onAlertInfoChange: (value: boolean) => void;
  onAlertWarningChange: (value: boolean) => void;
  onAlertCriticalChange: (value: boolean) => void;
  onAlertMinObservedValueChange: (value: string) => void;
}) {
  if (triggerType === "drift") {
    return (
      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Minimum Drift Score
          <input
            inputMode="decimal"
            value={minDriftScore}
            onChange={(event) => onMinDriftScoreChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Minimum Drifted Features
          <input
            inputMode="numeric"
            value={minDriftedFeatures}
            onChange={(event) => onMinDriftedFeaturesChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
      </div>
    );
  }
  if (triggerType === "alert") {
    return (
      <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_1fr]">
        <div>
          <div className="text-xs font-semibold uppercase text-steel">Alert Severities</div>
          <div className="mt-2 flex flex-wrap gap-2">
            <ToggleField
              label="Info"
              checked={alertInfoEnabled}
              onChange={onAlertInfoChange}
              text="info"
            />
            <ToggleField
              label="Warning"
              checked={alertWarningEnabled}
              onChange={onAlertWarningChange}
              text="warning"
            />
            <ToggleField
              label="Critical"
              checked={alertCriticalEnabled}
              onChange={onAlertCriticalChange}
              text="critical"
            />
          </div>
        </div>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Minimum Observed Value
          <input
            inputMode="decimal"
            value={alertMinObservedValue}
            onChange={(event) => onAlertMinObservedValueChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
      </div>
    );
  }
  return (
    <div className="mt-3 rounded border border-slate-200 bg-white p-3 text-sm text-steel">
      Manual policies rely on operator-triggered runs and guardrail limits.
    </div>
  );
}

function PolicyCard({
  policy,
  deployment,
  selected,
  onSelect,
}: {
  policy: RetrainingPolicy;
  deployment: Deployment | undefined;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <div className="rounded border border-slate-200 p-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-medium">{policy.name}</div>
          <div className="mt-1 text-xs text-steel">
            {policy.description || formatTrainingTemplate(policy.training_template)}
          </div>
        </div>
        <span className={policyStatusClassName(policy)}>{policy.trigger_type}</span>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-steel sm:grid-cols-4">
        <div>{deployment?.name ?? policy.deployment_id.slice(0, 8)}</div>
        <div>{policy.approval_required ? "approval required" : "auto queue"}</div>
        <div>{formatDuration(policy.cooldown_seconds)} cooldown</div>
        <div>{policy.max_runs_per_day}/day limit</div>
      </div>
      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="text-xs text-steel">
          {policy.enabled ? "enabled" : "disabled"} / {policy.status}
        </span>
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
      </div>
    </div>
  );
}

function PolicyDetail({
  policy,
  deployment,
}: {
  policy: RetrainingPolicy;
  deployment: Deployment | undefined;
}) {
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold">{policy.name}</div>
          <div className="mt-1 text-xs text-steel">
            {deployment?.name ?? policy.deployment_id.slice(0, 8)}
          </div>
        </div>
        <span className={policyStatusClassName(policy)}>{policy.status}</span>
      </div>
      <div className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3">
        <SignalTile
          icon={<RefreshCw className="h-4 w-4" />}
          label="Trigger"
          value={policy.trigger_type}
          detail={formatTriggerConfig(policy)}
        />
        <SignalTile
          icon={<CheckCircle className="h-4 w-4" />}
          label="Approval"
          value={policy.approval_required ? "required" : "auto queue"}
          detail={`${policy.max_runs_per_day}/day limit`}
        />
        <SignalTile
          icon={<Play className="h-4 w-4" />}
          label="Training"
          value={String(policy.training_template.algorithm ?? "algorithm")}
          detail={String(policy.training_template.objective_metric_name ?? "objective")}
        />
      </div>
      <div className="rounded border border-slate-200 p-3 text-xs text-steel">
        {formatTrainingTemplate(policy.training_template)}
      </div>
    </div>
  );
}

function RunRow({
  run,
  policy,
  selected,
  isMutating,
  onSelect,
  onApprove,
  onReject,
}: {
  run: RetrainingRun;
  policy: RetrainingPolicy | undefined;
  selected: boolean;
  isMutating: boolean;
  onSelect: () => void;
  onApprove: () => void;
  onReject: () => void;
}) {
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3">
        <div className="font-medium">{formatRunName(run)}</div>
        <div className="text-xs text-steel">{run.reason}</div>
      </td>
      <td>{policy?.name ?? run.policy_id.slice(0, 8)}</td>
      <td>{run.trigger_type}</td>
      <td>
        <span className={runStatusClassName(run.status)}>{run.status}</span>
      </td>
      <td>{formatSignal(run)}</td>
      <td className="max-w-[200px] truncate">{run.training_run_id ?? "not launched"}</td>
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
          {run.status === "pending_approval" ? (
            <>
              <button
                type="button"
                aria-label={`Approve retraining run ${run.id.slice(0, 8)}`}
                onClick={onApprove}
                disabled={isMutating}
                className="inline-flex h-8 w-8 items-center justify-center rounded border border-emerald-200 bg-emerald-50 text-signal transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <CircleCheck className="h-4 w-4" />
              </button>
              <button
                type="button"
                aria-label={`Reject retraining run ${run.id.slice(0, 8)}`}
                onClick={onReject}
                disabled={isMutating}
                className="inline-flex h-8 w-8 items-center justify-center rounded border border-rose-200 bg-rose-50 text-risk transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <CircleX className="h-4 w-4" />
              </button>
            </>
          ) : null}
        </div>
      </td>
    </tr>
  );
}

function RunDetail({
  run,
  policy,
}: {
  run: RetrainingRun;
  policy: RetrainingPolicy | undefined;
}) {
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold">{formatRunName(run)}</div>
          <div className="mt-1 text-xs text-steel">{policy?.name ?? run.policy_id.slice(0, 8)}</div>
        </div>
        <span className={runStatusClassName(run.status)}>{run.status}</span>
      </div>
      <div className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3">
        <SignalTile
          icon={<RefreshCw className="h-4 w-4" />}
          label="Trigger"
          value={run.trigger_type}
          detail={formatSignal(run)}
        />
        <SignalTile
          icon={<Play className="h-4 w-4" />}
          label="Training"
          value={run.training_run_id ? run.training_run_id.slice(0, 8) : "not launched"}
          detail={String(run.training_config.algorithm ?? "algorithm")}
        />
        <SignalTile
          icon={<CheckCircle className="h-4 w-4" />}
          label="Decision"
          value={String(run.decision_metadata.reason ?? run.reason)}
          detail={run.approved_by ? "approved" : run.rejected_by ? "rejected" : "open"}
        />
      </div>
      <div className="rounded border border-slate-200 p-3 text-sm">
        <div className="font-medium">Training Config</div>
        <div className="mt-2 grid gap-2 text-xs text-steel sm:grid-cols-2">
          <div>algorithm: {String(run.training_config.algorithm ?? "unknown")}</div>
          <div>model: {String(run.training_config.model_type ?? "unknown")}</div>
          <div>objective: {String(run.training_config.objective_metric_name ?? "unknown")}</div>
          <div>run id: {run.id}</div>
        </div>
      </div>
    </div>
  );
}

function ToggleField({
  label,
  checked,
  onChange,
  text,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  text: string;
}) {
  return (
    <label className="inline-flex min-h-10 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold uppercase text-steel">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 rounded border-slate-300 text-signal focus:ring-signal"
      />
      <span>
        {label}: <span className="font-normal normal-case text-ink">{text}</span>
      </span>
    </label>
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

function deploymentForPolicy(
  deployments: Deployment[],
  policy: RetrainingPolicy,
): Deployment | undefined {
  return deployments.find((deployment) => deployment.id === policy.deployment_id);
}

function policyForRun(
  policies: RetrainingPolicy[],
  run: RetrainingRun,
): RetrainingPolicy | undefined {
  return policies.find((policy) => policy.id === run.policy_id);
}

function formatTrainingTemplate(template: Record<string, unknown>): string {
  const algorithm = String(template.algorithm ?? "algorithm");
  const objective = String(template.objective_metric_name ?? "objective");
  const source =
    typeof template.feature_set_id === "string" && template.feature_set_id
      ? "feature set"
      : "dataset version";
  return `${algorithm} optimizing ${objective} from ${source}`;
}

function formatTriggerConfig(policy: RetrainingPolicy): string {
  if (policy.trigger_type === "drift") {
    const score = policy.trigger_config.min_drift_score;
    const features = policy.trigger_config.min_drifted_features;
    return `score ${formatNumber(score)}, features ${formatNumber(features)}`;
  }
  if (policy.trigger_type === "alert") {
    const severities = policy.trigger_config.severities;
    return Array.isArray(severities) ? severities.join(", ") : "alert signals";
  }
  return "operator trigger";
}

function formatNumber(value: unknown): string {
  return typeof value === "number" ? value.toString() : "n/a";
}

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  if (seconds < 3600) {
    return `${Math.round(seconds / 60)}m`;
  }
  return `${Math.round(seconds / 3600)}h`;
}

function formatRunName(run: RetrainingRun): string {
  const runName = run.training_config.run_name;
  return typeof runName === "string" ? runName : run.id.slice(0, 8);
}

function formatSignal(run: RetrainingRun): string {
  if (run.drift_report_id) {
    const score = run.decision_metadata.drift_score;
    return typeof score === "number" ? `drift ${score.toFixed(3)}` : "drift report";
  }
  if (run.alert_event_id) {
    const severity = run.decision_metadata.alert_severity;
    return typeof severity === "string" ? severity : "alert event";
  }
  return "manual";
}

function runVerb(status: string): string {
  if (status === "pending_approval") {
    return "is waiting for approval";
  }
  if (status === "queued") {
    return "was queued";
  }
  return `status is ${status}`;
}

function policyStatusClassName(policy: RetrainingPolicy): string {
  if (!policy.enabled || policy.status !== "active") {
    return "rounded bg-rose-50 px-2 py-1 text-xs font-medium text-risk";
  }
  if (policy.trigger_type === "manual") {
    return "rounded bg-field px-2 py-1 text-xs font-medium";
  }
  return "rounded bg-emerald-50 px-2 py-1 text-xs font-medium text-signal";
}

function runStatusClassName(status: string): string {
  if (status === "queued") {
    return "rounded bg-emerald-50 px-2 py-1 text-xs font-medium text-signal";
  }
  if (status === "pending_approval") {
    return "rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700";
  }
  if (status === "failed" || status === "rejected") {
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

function parseInteger(value: string, label: string, min: number, max: number): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < min || parsed > max) {
    throw new Error(`${label} must be an integer between ${min} and ${max}.`);
  }
  return parsed;
}

function parseRatio(value: string, label: string): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0 || parsed > 1) {
    throw new Error(`${label} must be between 0 and 1.`);
  }
  return parsed;
}

function optionalNonNegativeFloat(value: string, label: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new Error(`${label} must be non-negative.`);
  }
  return parsed;
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
