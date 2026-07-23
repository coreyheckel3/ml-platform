import { useQuery } from "@tanstack/react-query";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import { listModelVersions, listRegisteredModels } from "../api/models";

export function ModelsPage() {
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadModels = Boolean(token && projectId);
  const modelsQuery = useQuery({
    queryKey: ["registered-models", projectId],
    queryFn: () => listRegisteredModels(projectId ?? "", token ?? ""),
    enabled: canLoadModels
  });
  const models = modelsQuery.data?.items ?? [];
  const selectedModel = models[0];
  const versionsQuery = useQuery({
    queryKey: ["model-versions", selectedModel?.id],
    queryFn: () => listModelVersions(selectedModel?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedModel)
  });
  const versions = versionsQuery.data?.items ?? [];
  const statusCounts = countByStatus(versions.map((version) => version.status));

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
