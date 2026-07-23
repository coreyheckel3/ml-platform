import { useQuery } from "@tanstack/react-query";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import { listRetrainingPolicies, listRetrainingRuns, RetrainingRun } from "../api/retraining";

export function RetrainingPage() {
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadRetraining = Boolean(token && projectId);
  const policiesQuery = useQuery({
    queryKey: ["retraining-policies", projectId],
    queryFn: () => listRetrainingPolicies(projectId ?? "", token ?? ""),
    enabled: canLoadRetraining
  });
  const runsQuery = useQuery({
    queryKey: ["retraining-runs", projectId],
    queryFn: () => listRetrainingRuns(projectId ?? "", token ?? ""),
    enabled: canLoadRetraining
  });
  const policies = policiesQuery.data?.items ?? [];
  const runs = runsQuery.data?.items ?? [];
  const activePolicies = policies.filter((policy) => policy.enabled && policy.status === "active");
  const pendingRuns = runs.filter((run) => run.status === "pending_approval");
  const queuedRuns = runs.filter((run) => run.status === "queued");

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
        <MetricCard label="Queued" value={String(queuedRuns.length)} detail="training handoffs" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <DataPanel title="Retraining Policies">
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
                <div key={policy.id} className="rounded border border-slate-200 p-3 text-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{policy.name}</div>
                      <div className="mt-1 text-xs text-steel">
                        {policy.description || formatTrainingTemplate(policy.training_template)}
                      </div>
                    </div>
                    <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                      {policy.trigger_type}
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 text-xs text-steel sm:grid-cols-3">
                    <div>{policy.approval_required ? "approval required" : "auto queue"}</div>
                    <div>{formatCooldown(policy.cooldown_seconds)} cooldown</div>
                    <div>{policy.max_runs_per_day}/day limit</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DataPanel>

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
              <table className="w-full min-w-[820px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Run</th>
                    <th>Trigger</th>
                    <th>Status</th>
                    <th>Signal</th>
                    <th>Training</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id} className="border-t border-slate-100">
                      <td className="py-3">
                        <div className="font-medium">{formatRunName(run)}</div>
                        <div className="text-xs text-steel">{run.reason}</div>
                      </td>
                      <td>{run.trigger_type}</td>
                      <td>
                        <span className={statusClassName(run.status)}>{run.status}</span>
                      </td>
                      <td>{formatSignal(run)}</td>
                      <td className="max-w-[220px] truncate">
                        {run.training_run_id ?? "not launched"}
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

function formatTrainingTemplate(template: Record<string, unknown>): string {
  const algorithm = String(template.algorithm ?? "algorithm");
  const objective = String(template.objective_metric_name ?? "objective");
  return `${algorithm} optimizing ${objective}`;
}

function formatCooldown(seconds: number): string {
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

function statusClassName(status: string): string {
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

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
