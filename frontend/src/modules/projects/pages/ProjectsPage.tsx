import { Plus } from "lucide-react";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { PageHeader } from "../../../shared/ui/PageHeader";

const projects = [
  ["Movie Recommendation", "active", "Ranking and candidate generation", "movie-ranker-v2"],
  ["Semantic Search", "active", "Embedding-based document retrieval", "semantic-catalog-embed"],
  ["Fraud Detection", "active", "Payment risk scoring", "fraud-risk-xgb"]
];

export function ProjectsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Projects"
        description="Independent ML product areas with isolated datasets, experiments, models, deployments, and operational policy."
      />
      <DataPanel
        title="Project Inventory"
        action={
          <button className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white">
            <Plus className="h-4 w-4" />
            New
          </button>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-xs uppercase text-steel">
              <tr>
                <th className="py-2">Project</th>
                <th>Status</th>
                <th>Domain</th>
                <th>Latest Model</th>
              </tr>
            </thead>
            <tbody>
              {projects.map(([name, status, domain, model]) => (
                <tr key={name} className="border-t border-slate-100">
                  <td className="py-3 font-medium">{name}</td>
                  <td>{status}</td>
                  <td>{domain}</td>
                  <td>{model}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataPanel>
    </>
  );
}

