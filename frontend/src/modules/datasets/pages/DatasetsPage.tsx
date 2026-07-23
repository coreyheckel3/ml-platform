import { useQuery } from "@tanstack/react-query";

import { listDatasets } from "../api/datasets";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";

export function DatasetsPage() {
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadDatasets = Boolean(token && projectId);
  const { data, error, isFetching } = useQuery({
    queryKey: ["datasets", projectId],
    queryFn: () => listDatasets(projectId ?? "", token ?? ""),
    enabled: canLoadDatasets
  });
  const datasets = data?.items ?? [];

  return (
    <>
      <PageHeader
        eyebrow="Data"
        title="Datasets"
        description="Immutable dataset versions, schema validation, profiling, lineage, and upload lifecycle."
      />
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Registered" value={String(datasets.length)} detail="logical datasets" />
        <MetricCard label="Validated" value="0" detail="dataset versions" tone="success" />
        <MetricCard label="Failed Checks" value="0" detail="last 7 days" />
      </div>
      <div className="mt-6">
        <DataPanel title="Dataset Registry">
          {!canLoadDatasets ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              No project context is selected.
            </div>
          ) : error ? (
            <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk">
              Dataset registry request failed.
            </div>
          ) : datasets.length === 0 ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              {isFetching ? "Loading datasets." : "No datasets registered for this project."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Dataset</th>
                    <th>Source</th>
                    <th>Status</th>
                    <th>Slug</th>
                  </tr>
                </thead>
                <tbody>
                  {datasets.map((dataset) => (
                    <tr key={dataset.id} className="border-t border-slate-100">
                      <td className="py-3">
                        <div className="font-medium">{dataset.name}</div>
                        <div className="text-xs text-steel">{dataset.description || "No description"}</div>
                      </td>
                      <td>{dataset.source_type}</td>
                      <td>
                        <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                          {dataset.status}
                        </span>
                      </td>
                      <td>{dataset.slug}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
            <div className="rounded border border-slate-200 p-3">Immutable versions</div>
            <div className="rounded border border-slate-200 p-3">Schema validation</div>
            <div className="rounded border border-slate-200 p-3">Object storage uploads</div>
          </div>
        </DataPanel>
      </div>
    </>
  );
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
