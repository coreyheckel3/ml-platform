import { useQuery } from "@tanstack/react-query";

import { apiGet, type HealthResponse } from "../../../shared/api/client";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";

const recentRuns = [
  ["fraud-risk-xgb", "completed", "0.941 AUC", "12m 44s"],
  ["semantic-catalog-embed", "running", "trial 8/20", "32m 10s"],
  ["movie-ranker-v2", "failed", "feature null check", "2m 18s"]
];

export function DashboardPage() {
  const { data } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<HealthResponse>("/health/ready")
  });

  return (
    <>
      <PageHeader
        eyebrow="Control Plane"
        title="Dashboard"
        description="Operational view across projects, model lifecycle workflows, deployments, drift signals, and platform health."
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="API Health" value={data?.status ?? "checking"} detail="FastAPI readiness" tone="success" />
        <MetricCard label="Active Projects" value="3" detail="Movie Rec, Search, Fraud" />
        <MetricCard label="Open Alerts" value="2" detail="1 latency, 1 drift" tone="warning" />
        <MetricCard label="Prediction Volume" value="1.28M" detail="last 24 hours" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
        <DataPanel title="Recent Training Runs">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead className="text-xs uppercase text-steel">
                <tr>
                  <th className="py-2">Run</th>
                  <th>Status</th>
                  <th>Signal</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map(([run, status, signal, duration]) => (
                  <tr key={run} className="border-t border-slate-100">
                    <td className="py-3 font-medium">{run}</td>
                    <td>{status}</td>
                    <td>{signal}</td>
                    <td>{duration}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DataPanel>
        <DataPanel title="Deployment Health">
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span>fraud-prod</span>
              <span className="font-medium text-signal">healthy</span>
            </div>
            <div className="flex items-center justify-between">
              <span>semantic-search-staging</span>
              <span className="font-medium text-amber-600">canary</span>
            </div>
            <div className="flex items-center justify-between">
              <span>movie-rec-prod</span>
              <span className="font-medium text-signal">healthy</span>
            </div>
          </div>
        </DataPanel>
      </div>
    </>
  );
}

