import { useQuery } from "@tanstack/react-query";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import { listDeploymentRevisions, listDeployments } from "../api/deployments";

export function DeploymentsPage() {
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadDeployments = Boolean(token && projectId);
  const deploymentsQuery = useQuery({
    queryKey: ["deployments", projectId],
    queryFn: () => listDeployments(projectId ?? "", token ?? ""),
    enabled: canLoadDeployments
  });
  const deployments = deploymentsQuery.data?.items ?? [];
  const selectedDeployment = deployments[0];
  const revisionsQuery = useQuery({
    queryKey: ["deployment-revisions", selectedDeployment?.id],
    queryFn: () => listDeploymentRevisions(selectedDeployment?.id ?? "", token ?? ""),
    enabled: Boolean(token && selectedDeployment)
  });
  const revisions = revisionsQuery.data?.items ?? [];
  const healthyRevisions = revisions.filter((revision) => revision.status === "healthy");
  const canaries = revisions.filter((revision) => {
    return revision.traffic_percentage > 0 && revision.traffic_percentage < 100;
  });

  return (
    <>
      <PageHeader
        eyebrow="Production"
        title="Deployments"
        description="Model deployment targets, immutable revisions, canary rollout state, health checks, and rollback."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Targets" value={String(deployments.length)} detail="deployment endpoints" />
        <MetricCard label="Healthy" value={String(healthyRevisions.length)} detail="selected target" tone="success" />
        <MetricCard label="Canaries" value={String(canaries.length)} detail="traffic split active" tone="warning" />
        <MetricCard label="Traffic" value={`${activeTraffic(revisions)}%`} detail="active allocation" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <DataPanel title="Deployment Targets">
          {!canLoadDeployments ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              No project context is selected.
            </div>
          ) : deploymentsQuery.error ? (
            <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk">
              Deployment request failed.
            </div>
          ) : deployments.length === 0 ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              {deploymentsQuery.isFetching
                ? "Loading deployments."
                : "No deployments configured for this project."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Deployment</th>
                    <th>Environment</th>
                    <th>Status</th>
                    <th>Slug</th>
                  </tr>
                </thead>
                <tbody>
                  {deployments.map((deployment) => (
                    <tr key={deployment.id} className="border-t border-slate-100">
                      <td className="py-3">
                        <div className="font-medium">{deployment.name}</div>
                        <div className="text-xs text-steel">
                          {deployment.description || "No description"}
                        </div>
                      </td>
                      <td>{deployment.environment}</td>
                      <td>
                        <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                          {deployment.status}
                        </span>
                      </td>
                      <td>{deployment.slug}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel title="Rollout State">
          {!selectedDeployment ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              No deployment is available for rollout review.
            </div>
          ) : revisionsQuery.error ? (
            <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk">
              Deployment revision request failed.
            </div>
          ) : revisions.length === 0 ? (
            <div className="rounded border border-slate-200 bg-cloud p-4 text-sm text-steel">
              {revisionsQuery.isFetching
                ? "Loading deployment revisions."
                : "No revisions created for this deployment."}
            </div>
          ) : (
            <div className="space-y-4">
              {revisions.map((revision) => (
                <div key={revision.id} className="rounded border border-slate-200 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">Revision {revision.revision}</div>
                      <div className="mt-1 text-xs text-steel">{revision.serving_image}</div>
                    </div>
                    <span className="rounded bg-field px-2 py-1 text-xs font-medium">
                      {revision.status}
                    </span>
                  </div>
                  <div className="mt-3 h-3 overflow-hidden rounded bg-field">
                    <div
                      className="h-full bg-signal"
                      style={{ width: `${revision.traffic_percentage}%` }}
                    />
                  </div>
                  <div className="mt-2 flex justify-between text-xs text-steel">
                    <span>{revision.traffic_percentage}% traffic</span>
                    <span>{revision.orchestrator_deployment_id || "not submitted"}</span>
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

function activeTraffic(revisions: Array<{ traffic_percentage: number }>): number {
  return revisions.reduce((total, revision) => total + revision.traffic_percentage, 0);
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
