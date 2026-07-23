import { useQuery } from "@tanstack/react-query";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import { listTrainingRuns } from "../api/trainingRuns";

export function TrainingRunsPage() {
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadTrainingRuns = Boolean(token && projectId);
  const { data, error, isFetching } = useQuery({
    queryKey: ["training-runs", projectId],
    queryFn: () => listTrainingRuns(projectId ?? "", token ?? ""),
    enabled: canLoadTrainingRuns
  });
  const trainingRuns = data?.items ?? [];
  const counts = countByStatus(trainingRuns.map((run) => run.status));

  return (
    <>
      <PageHeader
        eyebrow="Workflow Plane"
        title="Training Runs"
        description="Airflow-orchestrated training jobs with retries, cancellation, evaluation, and artifact tracking."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Queued" value={String(counts.queued ?? 0)} detail="awaiting workers" />
        <MetricCard label="Running" value={String(counts.running ?? 0)} detail="active jobs" />
        <MetricCard label="Succeeded" value={String(counts.succeeded ?? 0)} detail="completed" tone="success" />
        <MetricCard label="Failed" value={String(counts.failed ?? 0)} detail="terminal errors" tone="danger" />
      </div>
      <div className="mt-6">
        <DataPanel title="Training Queue">
          {!canLoadTrainingRuns ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              No project context is selected.
            </div>
          ) : error ? (
            <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk">
              Training run request failed.
            </div>
          ) : trainingRuns.length === 0 ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              {isFetching ? "Loading training runs." : "No training runs submitted for this project."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Run</th>
                    <th>Algorithm</th>
                    <th>Objective</th>
                    <th>Status</th>
                    <th>Metric</th>
                    <th>Workflow</th>
                  </tr>
                </thead>
                <tbody>
                  {trainingRuns.map((run) => (
                    <tr key={run.id} className="border-t border-slate-100">
                      <td className="py-3">
                        <div className="font-medium">{run.id.slice(0, 8)}</div>
                        <div className="text-xs text-steel">{run.model_type}</div>
                      </td>
                      <td>{run.algorithm}</td>
                      <td>{run.objective_metric_name}</td>
                      <td>
                        <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                          {run.status}
                        </span>
                      </td>
                      <td>{firstMetric(run.metrics)}</td>
                      <td className="max-w-[240px] truncate">{run.orchestrator_run_id}</td>
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

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
