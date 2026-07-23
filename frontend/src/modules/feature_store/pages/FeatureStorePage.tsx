import { useQuery } from "@tanstack/react-query";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import { listFeatureSets } from "../api/featureStore";

export function FeatureStorePage() {
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadFeatureSets = Boolean(token && projectId);
  const { data, error, isFetching } = useQuery({
    queryKey: ["feature-sets", projectId],
    queryFn: () => listFeatureSets(projectId ?? "", token ?? ""),
    enabled: canLoadFeatureSets
  });
  const featureSets = data?.items ?? [];

  return (
    <>
      <PageHeader
        eyebrow="Feature Platform"
        title="Feature Store"
        description="Feature sets, feature definitions, lineage, pipeline registration, and materialization lifecycle."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Feature Sets" value={String(featureSets.length)} detail="registered groups" />
        <MetricCard label="Materializations" value="0" detail="latest project versions" />
        <MetricCard label="Pipelines" value="0" detail="registered transforms" />
        <MetricCard label="Lineage Links" value="0" detail="dataset dependencies" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <DataPanel title="Feature Set Inventory">
          {!canLoadFeatureSets ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              No project context is selected.
            </div>
          ) : error ? (
            <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk">
              Feature store request failed.
            </div>
          ) : featureSets.length === 0 ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              {isFetching ? "Loading feature sets." : "No feature sets registered for this project."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Feature Set</th>
                    <th>Entity Key</th>
                    <th>Status</th>
                    <th>Slug</th>
                  </tr>
                </thead>
                <tbody>
                  {featureSets.map((featureSet) => (
                    <tr key={featureSet.id} className="border-t border-slate-100">
                      <td className="py-3">
                        <div className="font-medium">{featureSet.name}</div>
                        <div className="text-xs text-steel">
                          {featureSet.description || "No description"}
                        </div>
                      </td>
                      <td>{featureSet.entity_key}</td>
                      <td>
                        <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                          {featureSet.status}
                        </span>
                      </td>
                      <td>{featureSet.slug}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>
        <DataPanel title="Materialization Contract">
          <div className="space-y-3 text-sm">
            <div className="rounded border border-slate-200 p-3">
              Feature pipelines trigger through an orchestration port.
            </div>
            <div className="rounded border border-slate-200 p-3">
              Materialized versions are immutable and addressable by offline URI.
            </div>
            <div className="rounded border border-slate-200 p-3">
              Dataset lineage is recorded when pipelines declare source datasets.
            </div>
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

