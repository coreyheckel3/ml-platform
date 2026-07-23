import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, CheckCircle, Gauge, Plus, Radar, RefreshCw, X } from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";

import {
  listInferenceEndpointMonitoringSummaries,
  type InferenceEndpointMonitoringSummary,
} from "../../monitoring/api/monitoring";
import {
  evaluateRetrainingPolicy,
  listRetrainingPolicies,
  type RetrainingPolicy,
} from "../../retraining/api/retraining";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  createDriftProfile,
  listDriftFeatureResults,
  listDriftProfiles,
  listProjectDriftReports,
  runDriftReport,
  type DriftFeatureResult,
  type DriftProfile,
  type DriftReport,
} from "../api/drift";

export function DriftDetectionPage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadDrift = Boolean(token && projectId);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [selectedEndpointId, setSelectedEndpointId] = useState("");
  const [selectedReportId, setSelectedReportId] = useState("");
  const [selectedPolicyId, setSelectedPolicyId] = useState("");
  const [isCreateProfileOpen, setIsCreateProfileOpen] = useState(false);
  const [profileName, setProfileName] = useState("");
  const [profileDescription, setProfileDescription] = useState("");
  const [modelVersionId, setModelVersionId] = useState("");
  const [datasetVersionId, setDatasetVersionId] = useState("");
  const [baselineProfileText, setBaselineProfileText] = useState(defaultBaselineProfileText);
  const [windowSeconds, setWindowSeconds] = useState("3600");
  const [driftThreshold, setDriftThreshold] = useState("0.2");
  const [sampleLimit, setSampleLimit] = useState("200");
  const [reportUri, setReportUri] = useState("");
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const profilesQuery = useQuery({
    queryKey: ["drift-profiles", projectId],
    queryFn: () => listDriftProfiles(projectId ?? "", token ?? ""),
    enabled: canLoadDrift,
  });
  const reportsQuery = useQuery({
    queryKey: ["drift-reports", projectId],
    queryFn: () => listProjectDriftReports(projectId ?? "", token ?? ""),
    enabled: canLoadDrift,
  });
  const endpointsQuery = useQuery({
    queryKey: ["monitoring-inference-endpoints", projectId],
    queryFn: () => listInferenceEndpointMonitoringSummaries(projectId ?? "", token ?? ""),
    enabled: canLoadDrift,
  });
  const policiesQuery = useQuery({
    queryKey: ["retraining-policies", projectId],
    queryFn: () => listRetrainingPolicies(projectId ?? "", token ?? ""),
    enabled: canLoadDrift,
  });
  const profiles = useMemo(
    () => profilesQuery.data?.items ?? [],
    [profilesQuery.data?.items],
  );
  const reports = useMemo(
    () => reportsQuery.data?.items ?? [],
    [reportsQuery.data?.items],
  );
  const endpoints = useMemo(
    () => endpointsQuery.data?.items ?? [],
    [endpointsQuery.data?.items],
  );
  const policies = useMemo(
    () => policiesQuery.data?.items ?? [],
    [policiesQuery.data?.items],
  );
  const selectedProfile =
    profiles.find((profile) => profile.id === selectedProfileId) ?? profiles[0];
  const selectedEndpoint =
    endpoints.find((endpoint) => endpoint.endpoint_id === selectedEndpointId) ??
    endpointForLatestReport(endpoints, reports[0]) ??
    endpoints[0];
  const selectedReport =
    reports.find((report) => report.id === selectedReportId) ?? reports[0];
  const eligiblePolicies = useMemo(
    () =>
      policies.filter(
        (policy) =>
          policy.trigger_type === "drift" &&
          policy.enabled &&
          policy.status === "active" &&
          (!selectedReport || policy.deployment_id === selectedReport.deployment_id),
      ),
    [policies, selectedReport],
  );
  const selectedPolicy =
    eligiblePolicies.find((policy) => policy.id === selectedPolicyId) ??
    eligiblePolicies[0];
  const featuresQuery = useQuery({
    queryKey: ["drift-feature-results", selectedReport?.id],
    queryFn: () => listDriftFeatureResults(selectedReport?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedReport),
  });
  const featureResults = useMemo(
    () => featuresQuery.data?.items ?? [],
    [featuresQuery.data?.items],
  );
  const maxScore = Math.max(0, ...reports.map((report) => report.drift_score));
  const openDriftReports = reports.filter((report) => report.drift_score > report.drift_threshold);
  const driftedFeatures = reports.reduce(
    (total, report) => total + report.drifted_feature_count,
    0,
  );
  const highestRiskFeature = featureResults.reduce<DriftFeatureResult | null>(
    (current, feature) => {
      if (!current) {
        return feature;
      }
      return feature.drift_score > current.drift_score ? feature : current;
    },
    null,
  );
  const createProfileMutation = useMutation({
    mutationFn: () => {
      if (!projectId || !token) {
        throw new Error("Drift profile creation requires project context.");
      }
      return createDriftProfile(
        projectId,
        {
          name: profileName.trim(),
          description: profileDescription.trim(),
          model_version_id: optionalString(modelVersionId),
          dataset_version_id: optionalString(datasetVersionId),
          baseline_profile: parseBaselineProfile(baselineProfileText),
        },
        token,
      );
    },
    onSuccess: (profile) => {
      setOperationError(null);
      setOperationMessage(`Created drift profile ${profile.name}.`);
      setSelectedProfileId(profile.id);
      closeProfileForm();
      queryClient.invalidateQueries({ queryKey: ["drift-profiles", projectId] });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Drift profile creation failed.",
      );
    },
  });
  const runReportMutation = useMutation({
    mutationFn: () => {
      if (!selectedProfile || !selectedEndpoint || !token) {
        throw new Error("Drift report execution requires a profile and endpoint.");
      }
      return runDriftReport(
        selectedProfile.id,
        {
          endpoint_id: selectedEndpoint.endpoint_id,
          window_seconds: parsePositiveInteger(windowSeconds, "Report window", 86_400),
          drift_threshold: parseRatio(driftThreshold, "Drift threshold"),
          sample_limit: parsePositiveInteger(sampleLimit, "Sample limit", 10_000),
          report_uri: reportUri.trim(),
        },
        token,
      );
    },
    onSuccess: (report) => {
      setOperationError(null);
      setOperationMessage(`Completed drift report for ${reportEndpointName(report)}.`);
      setSelectedReportId(report.id);
      queryClient.invalidateQueries({ queryKey: ["drift-reports", projectId] });
      queryClient.invalidateQueries({ queryKey: ["drift-feature-results", report.id] });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Drift report execution failed.",
      );
    },
  });
  const evaluateRetrainingMutation = useMutation({
    mutationFn: () => {
      if (!selectedPolicy || !selectedReport || !token) {
        throw new Error("Retraining evaluation requires a drift policy and report.");
      }
      return evaluateRetrainingPolicy(
        selectedPolicy.id,
        {
          drift_report_id: selectedReport.id,
          alert_event_id: null,
          reason: `Drift report ${selectedReport.id.slice(0, 8)} scored ${selectedReport.drift_score.toFixed(
            3,
          )} against ${selectedReport.drift_threshold.toFixed(3)}.`,
        },
        token,
      );
    },
    onSuccess: (evaluation) => {
      setOperationError(null);
      if (evaluation.triggered && evaluation.run) {
        setOperationMessage(
          `Retraining ${retrainingRunVerb(evaluation.run.status)} for drift report ${selectedReport?.id.slice(
            0,
            8,
          )}.`,
        );
      } else {
        setOperationMessage(`Retraining policy skipped: ${evaluation.reason}`);
      }
      queryClient.invalidateQueries({ queryKey: ["retraining-runs", projectId] });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Retraining policy evaluation failed.",
      );
    },
  });

  useEffect(() => {
    if (!selectedProfileId && profiles[0]) {
      setSelectedProfileId(profiles[0].id);
      return;
    }
    if (selectedProfileId && !profiles.some((profile) => profile.id === selectedProfileId)) {
      setSelectedProfileId(profiles[0]?.id ?? "");
    }
  }, [profiles, selectedProfileId]);

  useEffect(() => {
    if (!selectedEndpointId && selectedEndpoint) {
      setSelectedEndpointId(selectedEndpoint.endpoint_id);
      return;
    }
    if (
      selectedEndpointId &&
      !endpoints.some((endpoint) => endpoint.endpoint_id === selectedEndpointId)
    ) {
      setSelectedEndpointId(selectedEndpoint?.endpoint_id ?? "");
    }
  }, [endpoints, selectedEndpoint, selectedEndpointId]);

  useEffect(() => {
    if (!selectedReportId && reports[0]) {
      setSelectedReportId(reports[0].id);
      return;
    }
    if (selectedReportId && !reports.some((report) => report.id === selectedReportId)) {
      setSelectedReportId(reports[0]?.id ?? "");
    }
  }, [reports, selectedReportId]);

  useEffect(() => {
    if (!selectedPolicyId && selectedPolicy) {
      setSelectedPolicyId(selectedPolicy.id);
      return;
    }
    if (selectedPolicyId && !eligiblePolicies.some((policy) => policy.id === selectedPolicyId)) {
      setSelectedPolicyId(selectedPolicy?.id ?? "");
    }
  }, [eligiblePolicies, selectedPolicy, selectedPolicyId]);

  function closeProfileForm() {
    setIsCreateProfileOpen(false);
    setProfileName("");
    setProfileDescription("");
    setModelVersionId("");
    setDatasetVersionId("");
    setBaselineProfileText(defaultBaselineProfileText);
  }

  function handleCreateProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (profileName.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Drift profile name must be at least 3 characters.");
      return;
    }
    createProfileMutation.mutate();
  }

  function handleRunReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    runReportMutation.mutate();
  }

  return (
    <>
      <PageHeader
        eyebrow="ML Quality"
        title="Drift Detection"
        description="Reference profiles, production-window comparisons, feature drift scores, and retraining triggers."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Profiles" value={String(profiles.length)} detail="active baselines" />
        <MetricCard label="Reports" value={String(reports.length)} detail="evaluated windows" />
        <MetricCard
          label="Max Score"
          value={maxScore.toFixed(3)}
          detail={`${openDriftReports.length} over threshold`}
          tone={maxScore > 0.2 ? "warning" : "success"}
        />
        <MetricCard
          label="Drifted Features"
          value={String(driftedFeatures)}
          detail={highestRiskFeature ? highestRiskFeature.feature_name : "no feature signals"}
          tone={driftedFeatures > 0 ? "warning" : "success"}
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
          title="Reference Profiles"
          action={
            <button
              type="button"
              onClick={() => {
                setIsCreateProfileOpen(true);
                setOperationError(null);
              }}
              className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              <Plus className="h-4 w-4" />
              Profile
            </button>
          }
        >
          {isCreateProfileOpen ? (
            <form
              aria-label="Create drift profile"
              onSubmit={handleCreateProfile}
              className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
            >
              <div className="grid gap-3 lg:grid-cols-[minmax(170px,0.8fr)_minmax(220px,1fr)]">
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Profile Name
                  <input
                    value={profileName}
                    onChange={(event) => setProfileName(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Profile Description
                  <input
                    value={profileDescription}
                    onChange={(event) => setProfileDescription(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
              </div>
              <div className="mt-3 grid gap-3 lg:grid-cols-2">
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Model Version ID
                  <input
                    value={modelVersionId}
                    onChange={(event) => setModelVersionId(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Dataset Version ID
                  <input
                    value={datasetVersionId}
                    onChange={(event) => setDatasetVersionId(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
              </div>
              <label className="mt-3 grid gap-1 text-xs font-semibold uppercase text-steel">
                Baseline Profile
                <textarea
                  value={baselineProfileText}
                  onChange={(event) => setBaselineProfileText(event.target.value)}
                  rows={8}
                  className="rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
                />
              </label>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <button
                  type="submit"
                  disabled={createProfileMutation.isPending}
                  className="inline-flex h-9 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <CheckCircle className="h-4 w-4" />
                  Create profile
                </button>
                <button
                  type="button"
                  aria-label="Cancel drift profile creation"
                  onClick={closeProfileForm}
                  className="inline-flex h-9 w-9 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </form>
          ) : null}
          {!canLoadDrift ? (
            <StateMessage message="No project context is selected." />
          ) : profilesQuery.error ? (
            <StateMessage message="Drift profile request failed." tone="danger" />
          ) : profiles.length === 0 ? (
            <StateMessage
              message={
                profilesQuery.isFetching
                  ? "Loading drift profiles."
                  : "No drift profiles configured for this project."
              }
            />
          ) : (
            <div className="space-y-3">
              {profiles.map((profile) => (
                <ProfileRow
                  key={profile.id}
                  profile={profile}
                  selected={profile.id === selectedProfile?.id}
                  onSelect={() => setSelectedProfileId(profile.id)}
                />
              ))}
            </div>
          )}
        </DataPanel>

        <DataPanel title="Run Drift Report">
          {!canLoadDrift ? (
            <StateMessage message="No project context is selected." />
          ) : profiles.length === 0 ? (
            <StateMessage message="Create a drift profile before running drift analysis." />
          ) : endpointsQuery.error ? (
            <StateMessage message="Inference endpoint request failed." tone="danger" />
          ) : endpoints.length === 0 ? (
            <StateMessage
              message={
                endpointsQuery.isFetching
                  ? "Loading inference endpoints."
                  : "No inference endpoints are available for drift analysis."
              }
            />
          ) : (
            <form onSubmit={handleRunReport} className="grid gap-4">
              <div className="grid gap-3 lg:grid-cols-2">
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Reference Profile
                  <select
                    value={selectedProfile?.id ?? ""}
                    onChange={(event) => setSelectedProfileId(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  >
                    {profiles.map((profile) => (
                      <option key={profile.id} value={profile.id}>
                        {profile.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Endpoint
                  <select
                    value={selectedEndpoint?.endpoint_id ?? ""}
                    onChange={(event) => setSelectedEndpointId(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  >
                    {endpoints.map((endpoint) => (
                      <option key={endpoint.endpoint_id} value={endpoint.endpoint_id}>
                        {endpoint.endpoint_name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr]">
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Drift Threshold
                  <input
                    inputMode="decimal"
                    value={driftThreshold}
                    onChange={(event) => setDriftThreshold(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Report Window
                  <input
                    inputMode="numeric"
                    value={windowSeconds}
                    onChange={(event) => setWindowSeconds(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
                <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                  Sample Limit
                  <input
                    inputMode="numeric"
                    value={sampleLimit}
                    onChange={(event) => setSampleLimit(event.target.value)}
                    className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                  />
                </label>
              </div>
              <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                Report URI
                <input
                  value={reportUri}
                  onChange={(event) => setReportUri(event.target.value)}
                  className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                />
              </label>
              {selectedEndpoint ? <EndpointSummary endpoint={selectedEndpoint} /> : null}
              <button
                type="submit"
                disabled={runReportMutation.isPending || !selectedProfile || !selectedEndpoint}
                className="inline-flex h-10 w-fit items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <RefreshCw className="h-4 w-4" />
                Run drift report
              </button>
            </form>
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <DataPanel title="Drift Reports">
          {!canLoadDrift ? (
            <StateMessage message="No project context is selected." />
          ) : reportsQuery.error ? (
            <StateMessage message="Drift report request failed." tone="danger" />
          ) : reports.length === 0 ? (
            <StateMessage
              message={
                reportsQuery.isFetching
                  ? "Loading drift reports."
                  : "No drift reports have been generated."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Report</th>
                    <th>Status</th>
                    <th>Score</th>
                    <th>Features</th>
                    <th>Window</th>
                    <th>Selected</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((report) => (
                    <ReportRow
                      key={report.id}
                      report={report}
                      selected={report.id === selectedReport?.id}
                      onSelect={() => setSelectedReportId(report.id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel title="Report Detail">
          {!selectedReport ? (
            <StateMessage message="No drift report is selected." />
          ) : (
            <div className="grid gap-4">
              <ReportDetail report={selectedReport} />
              <RetrainingHandoff
                policies={eligiblePolicies}
                selectedPolicy={selectedPolicy}
                selectedPolicyId={selectedPolicyId}
                onPolicyChange={setSelectedPolicyId}
                onEvaluate={() => evaluateRetrainingMutation.mutate()}
                disabled={evaluateRetrainingMutation.isPending}
                policiesError={Boolean(policiesQuery.error)}
              />
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6">
        <DataPanel title="Feature Drift Analysis">
          {!selectedReport ? (
            <StateMessage message="No drift report is available for feature analysis." />
          ) : featuresQuery.error ? (
            <StateMessage message="Drift feature request failed." tone="danger" />
          ) : featureResults.length === 0 ? (
            <StateMessage
              message={
                featuresQuery.isFetching
                  ? "Loading feature drift results."
                  : "No feature drift results are available."
              }
            />
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {featureResults.slice(0, 9).map((feature) => (
                <FeatureCard key={feature.id} feature={feature} />
              ))}
            </div>
          )}
        </DataPanel>
      </div>
    </>
  );
}

const defaultBaselineProfileText = `{
  "numeric_signal": {
    "type": "numeric",
    "mean": 125.4,
    "std": 38.2,
    "threshold": 0.18
  },
  "category_segment": {
    "type": "categorical",
    "distribution": {
      "control": 0.42,
      "variant_a": 0.18,
      "variant_b": 0.4
    },
    "threshold": 0.2
  }
}`;

function ProfileRow({
  profile,
  selected,
  onSelect,
}: {
  profile: DriftProfile;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <div className="rounded border border-slate-200 p-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-medium">{profile.name}</div>
          <div className="mt-1 text-xs text-steel">
            {profile.description || `${featureCount(profile.baseline_profile)} features`}
          </div>
        </div>
        <span className="rounded bg-field px-2 py-1 text-xs font-medium">{profile.status}</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-steel">
        <div>{featureCount(profile.baseline_profile)} baseline features</div>
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

function EndpointSummary({ endpoint }: { endpoint: InferenceEndpointMonitoringSummary }) {
  return (
    <div className="grid gap-3 rounded border border-slate-200 p-3 text-sm md:grid-cols-3">
      <SignalTile
        icon={<Activity className="h-4 w-4" />}
        label="Endpoint"
        value={endpoint.endpoint_name}
        detail={endpoint.route_path}
      />
      <SignalTile
        icon={<Gauge className="h-4 w-4" />}
        label="p95"
        value={`${endpoint.p95_latency_ms.toFixed(1)}ms`}
        detail={`${formatPercent(endpoint.error_rate)} error rate`}
      />
      <SignalTile
        icon={<Radar className="h-4 w-4" />}
        label="Traffic"
        value={String(endpoint.prediction_count)}
        detail={`${endpoint.latest_window_seconds}s window`}
      />
    </div>
  );
}

function ReportRow({
  report,
  selected,
  onSelect,
}: {
  report: DriftReport;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3">
        <div className="font-medium">{reportEndpointName(report)}</div>
        <code className="text-xs text-steel">{reportRoutePath(report)}</code>
      </td>
      <td>
        <span className={statusClassName(report.status)}>{report.status}</span>
      </td>
      <td>
        <span className={report.drift_score > report.drift_threshold ? "text-amber-700" : ""}>
          {report.drift_score.toFixed(3)}
        </span>
      </td>
      <td>
        {report.drifted_feature_count}/{report.evaluated_feature_count} drifted
      </td>
      <td>{formatDuration(report.window_seconds)}</td>
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

function ReportDetail({ report }: { report: DriftReport }) {
  const ratio = ratioFromSummary(report.summary);
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold">{reportEndpointName(report)}</div>
          <code className="mt-1 block text-xs text-steel">{reportRoutePath(report)}</code>
        </div>
        <DriftBadge report={report} />
      </div>
      <div className="grid gap-3 text-sm sm:grid-cols-3">
        <SignalTile
          icon={<Radar className="h-4 w-4" />}
          label="Score"
          value={report.drift_score.toFixed(3)}
          detail={`threshold ${report.drift_threshold.toFixed(3)}`}
        />
        <SignalTile
          icon={<Gauge className="h-4 w-4" />}
          label="Features"
          value={`${report.drifted_feature_count}/${report.evaluated_feature_count}`}
          detail={`${formatPercent(ratio)} drift ratio`}
        />
        <SignalTile
          icon={<Activity className="h-4 w-4" />}
          label="Samples"
          value={String(report.summary.sample_count ?? "0")}
          detail={formatDuration(report.window_seconds)}
        />
      </div>
      <BudgetBar
        label="Drift threshold"
        value={report.drift_score}
        budget={report.drift_threshold}
        formatter={(value) => value.toFixed(3)}
      />
    </div>
  );
}

function RetrainingHandoff({
  policies,
  selectedPolicy,
  selectedPolicyId,
  onPolicyChange,
  onEvaluate,
  disabled,
  policiesError,
}: {
  policies: RetrainingPolicy[];
  selectedPolicy: RetrainingPolicy | undefined;
  selectedPolicyId: string;
  onPolicyChange: (policyId: string) => void;
  onEvaluate: () => void;
  disabled: boolean;
  policiesError: boolean;
}) {
  if (policiesError) {
    return <StateMessage message="Retraining policy request failed." tone="danger" />;
  }
  if (policies.length === 0) {
    return (
      <StateMessage message="No active drift retraining policy matches this deployment." />
    );
  }
  return (
    <div className="rounded border border-slate-200 p-3">
      <div className="flex flex-wrap items-end gap-3">
        <label className="grid min-w-[240px] flex-1 gap-1 text-xs font-semibold uppercase text-steel">
          Retraining Policy
          <select
            value={selectedPolicy?.id ?? selectedPolicyId}
            onChange={(event) => onPolicyChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          >
            {policies.map((policy) => (
              <option key={policy.id} value={policy.id}>
                {policy.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={onEvaluate}
          disabled={disabled || !selectedPolicy}
          className="inline-flex h-10 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className="h-4 w-4" />
          Evaluate retraining
        </button>
      </div>
      {selectedPolicy ? (
        <div className="mt-3 grid gap-2 text-xs text-steel sm:grid-cols-3">
          <div>{selectedPolicy.approval_required ? "approval required" : "auto queue"}</div>
          <div>{formatDuration(selectedPolicy.cooldown_seconds)} cooldown</div>
          <div>{selectedPolicy.max_runs_per_day}/day limit</div>
        </div>
      ) : null}
    </div>
  );
}

function FeatureCard({ feature }: { feature: DriftFeatureResult }) {
  return (
    <div className="rounded border border-slate-200 p-3 text-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-medium">{feature.feature_name}</div>
          <div className="mt-1 text-xs text-steel">{feature.feature_type}</div>
        </div>
        <span className={feature.drift_detected ? "text-amber-600" : "text-signal"}>
          {feature.drift_score.toFixed(3)}
        </span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded bg-field">
        <div
          className={feature.drift_detected ? "h-full bg-amber-500" : "h-full bg-signal"}
          style={{ width: barWidth(feature.drift_score, feature.threshold) }}
        />
      </div>
      <div className="mt-3 text-xs text-steel">
        threshold {feature.threshold.toFixed(3)}
        {formatFeatureStats(feature.statistics)}
      </div>
    </div>
  );
}

function DriftBadge({ report }: { report: DriftReport }) {
  if (report.status === "failed") {
    return <span className="rounded bg-rose-50 px-2 py-1 text-xs font-semibold text-risk">failed</span>;
  }
  if (report.drift_score > report.drift_threshold || report.drifted_feature_count > 0) {
    return (
      <span className="rounded bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700">
        drift detected
      </span>
    );
  }
  return (
    <span className="rounded bg-emerald-50 px-2 py-1 text-xs font-semibold text-signal">
      stable
    </span>
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
  detail?: string;
}) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase text-steel">
        {icon}
        {label}
      </div>
      <div className="mt-2 truncate text-sm font-medium">{value}</div>
      {detail ? <div className="mt-1 truncate text-xs text-steel">{detail}</div> : null}
    </div>
  );
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
  const scale = budget <= 0 ? 1 : budget;
  const exceeded = value > budget;
  const width = `${Math.min(value / scale, 1) * 100}%`;
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-xs text-steel">
        <span className="font-semibold uppercase">{label}</span>
        <span>
          {formatter(value)} / {formatter(budget)}
        </span>
      </div>
      <div className="mt-2 h-3 overflow-hidden rounded bg-field">
        <div className={exceeded ? "h-full bg-risk" : "h-full bg-signal"} style={{ width }} />
      </div>
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

function endpointForLatestReport(
  endpoints: InferenceEndpointMonitoringSummary[],
  report: DriftReport | undefined,
): InferenceEndpointMonitoringSummary | undefined {
  if (!report) {
    return undefined;
  }
  return endpoints.find((endpoint) => endpoint.endpoint_id === report.endpoint_id);
}

function parseBaselineProfile(value: string): Record<string, unknown> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new Error("Baseline profile must be valid JSON.");
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Baseline profile must be a JSON object.");
  }
  if (Object.keys(parsed).length === 0) {
    throw new Error("Baseline profile must include at least one feature.");
  }
  return parsed as Record<string, unknown>;
}

function parsePositiveInteger(value: string, label: string, max: number): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0 || parsed > max) {
    throw new Error(`${label} must be an integer between 1 and ${max}.`);
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

function optionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function featureCount(profile: Record<string, unknown>): number {
  return Object.keys(profile).length;
}

function reportEndpointName(report: DriftReport): string {
  return String(report.summary.endpoint_name ?? "Inference endpoint");
}

function reportRoutePath(report: DriftReport): string {
  return String(report.summary.route_path ?? report.endpoint_id);
}

function ratioFromSummary(summary: Record<string, unknown>): number {
  const value = summary.drifted_feature_ratio;
  return typeof value === "number" ? value : 0;
}

function formatFeatureStats(statistics: Record<string, unknown>): string {
  const sampleCount = statistics.sample_count;
  if (typeof sampleCount === "number") {
    return `, ${sampleCount} samples`;
  }
  return "";
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
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

function barWidth(value: number, threshold: number): string {
  const scale = threshold <= 0 ? 1 : threshold;
  return `${Math.min((value / scale) * 100, 100)}%`;
}

function retrainingRunVerb(status: string): string {
  if (status === "pending_approval") {
    return "approval requested";
  }
  if (status === "queued") {
    return "run queued";
  }
  return `run ${status}`;
}

function statusClassName(status: string): string {
  if (status === "completed") {
    return "rounded bg-emerald-50 px-2 py-1 text-xs font-medium text-signal";
  }
  if (status === "failed") {
    return "rounded bg-rose-50 px-2 py-1 text-xs font-medium text-risk";
  }
  return "rounded bg-field px-2 py-1 text-xs font-medium";
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
