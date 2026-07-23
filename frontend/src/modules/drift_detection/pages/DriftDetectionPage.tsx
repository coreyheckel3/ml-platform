import { useQuery } from "@tanstack/react-query";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  listDriftFeatureResults,
  listDriftProfiles,
  listProjectDriftReports
} from "../api/drift";

export function DriftDetectionPage() {
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadDrift = Boolean(token && projectId);
  const profilesQuery = useQuery({
    queryKey: ["drift-profiles", projectId],
    queryFn: () => listDriftProfiles(projectId ?? "", token ?? ""),
    enabled: canLoadDrift
  });
  const reportsQuery = useQuery({
    queryKey: ["drift-reports", projectId],
    queryFn: () => listProjectDriftReports(projectId ?? "", token ?? ""),
    enabled: canLoadDrift
  });
  const profiles = profilesQuery.data?.items ?? [];
  const reports = reportsQuery.data?.items ?? [];
  const latestReport = reports[0];
  const featuresQuery = useQuery({
    queryKey: ["drift-feature-results", latestReport?.id],
    queryFn: () => listDriftFeatureResults(latestReport?.id ?? "", token ?? ""),
    enabled: Boolean(token && latestReport)
  });
  const featureResults = featuresQuery.data?.items ?? [];
  const maxScore = Math.max(0, ...reports.map((report) => report.drift_score));
  const driftedFeatures = reports.reduce(
    (total, report) => total + report.drifted_feature_count,
    0
  );

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
          detail="latest project reports"
          tone={maxScore > 0.2 ? "warning" : "success"}
        />
        <MetricCard
          label="Drifted Features"
          value={String(driftedFeatures)}
          detail="across reports"
          tone={driftedFeatures > 0 ? "warning" : "success"}
        />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <DataPanel title="Reference Profiles">
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
                <div key={profile.id} className="rounded border border-slate-200 p-3 text-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{profile.name}</div>
                      <div className="mt-1 text-xs text-steel">
                        {profile.description || `${featureCount(profile.baseline_profile)} features`}
                      </div>
                    </div>
                    <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                      {profile.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DataPanel>

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
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Report</th>
                    <th>Status</th>
                    <th>Score</th>
                    <th>Features</th>
                    <th>Window</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((report) => (
                    <tr key={report.id} className="border-t border-slate-100">
                      <td className="py-3">
                        <div className="font-medium">
                          {String(report.summary.endpoint_name ?? "Inference endpoint")}
                        </div>
                        <div className="text-xs text-steel">
                          {String(report.summary.route_path ?? report.endpoint_id)}
                        </div>
                      </td>
                      <td>{report.status}</td>
                      <td>{report.drift_score.toFixed(3)}</td>
                      <td>
                        {report.drifted_feature_count}/{report.evaluated_feature_count} drifted
                      </td>
                      <td>{report.window_seconds}s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6">
        <DataPanel title="Top Feature Drift">
          {!latestReport ? (
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
            <div className="grid gap-3 md:grid-cols-3">
              {featureResults.slice(0, 6).map((feature) => (
                <div key={feature.id} className="rounded border border-slate-200 p-3 text-sm">
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
                      style={{ width: `${Math.min(feature.drift_score * 100, 100)}%` }}
                    />
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

function featureCount(profile: Record<string, unknown>): number {
  return Object.keys(profile).length;
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
