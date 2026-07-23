import { useQuery } from "@tanstack/react-query";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import { listExperimentRuns, listExperiments } from "../api/experiments";

export function ExperimentsPage() {
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadExperiments = Boolean(token && projectId);
  const experimentsQuery = useQuery({
    queryKey: ["experiments", projectId],
    queryFn: () => listExperiments(projectId ?? "", token ?? ""),
    enabled: canLoadExperiments
  });
  const experiments = experimentsQuery.data?.items ?? [];
  const selectedExperiment = experiments[0];
  const runsQuery = useQuery({
    queryKey: ["experiment-runs", selectedExperiment?.id],
    queryFn: () => listExperimentRuns(selectedExperiment?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedExperiment)
  });
  const runs = runsQuery.data?.items ?? [];
  const terminalRuns = runs.filter((run) =>
    ["succeeded", "failed", "canceled"].includes(run.status)
  );
  const bestMetric = findBestMetric(runs);

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
        <MetricCard label="Terminal" value={String(terminalRuns.length)} detail="completed states" />
        <MetricCard label="Best Metric" value={bestMetric.value} detail={bestMetric.label} tone="success" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <DataPanel title="Experiment Registry">
          {!canLoadExperiments ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              No project context is selected.
            </div>
          ) : experimentsQuery.error ? (
            <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk">
              Experiment registry request failed.
            </div>
          ) : experiments.length === 0 ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              {experimentsQuery.isFetching
                ? "Loading experiments."
                : "No experiments registered for this project."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Experiment</th>
                    <th>Status</th>
                    <th>Slug</th>
                  </tr>
                </thead>
                <tbody>
                  {experiments.map((experiment) => (
                    <tr key={experiment.id} className="border-t border-slate-100">
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
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel title="Run Comparison">
          {!selectedExperiment ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              No experiment is available for comparison.
            </div>
          ) : runsQuery.error ? (
            <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk">
              Experiment run request failed.
            </div>
          ) : runs.length === 0 ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              {runsQuery.isFetching ? "Loading runs." : "No runs recorded for this experiment."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Run</th>
                    <th>Model</th>
                    <th>Status</th>
                    <th>Top Metric</th>
                    <th>Artifact</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => {
                    const topMetric = firstMetric(run.metrics);
                    return (
                      <tr key={run.id} className="border-t border-slate-100">
                        <td className="py-3">
                          <div className="font-medium">{run.run_name}</div>
                          <div className="text-xs text-steel">
                            {Object.keys(run.parameters).length} parameters
                          </div>
                        </td>
                        <td>{run.model_type}</td>
                        <td>
                          <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                            {run.status}
                          </span>
                        </td>
                        <td>{topMetric}</td>
                        <td className="max-w-[220px] truncate">{run.artifact_uri}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>
      </div>
    </>
  );
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

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
