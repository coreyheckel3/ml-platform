import { CheckCircle2 } from "lucide-react";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import { exampleProjects } from "../data/exampleProjects";

const lifecycleStageCount = new Set(
  exampleProjects.flatMap((project) => project.lifecycleStages)
).size;
const modelTypes = new Set(exampleProjects.map((project) => project.modelType)).size;
const approvedModels = exampleProjects.length;

export function ExampleProjectsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Reference Workloads"
        title="Example Projects"
        description="Portfolio-grade reference projects that exercise ForgeML ingestion, feature engineering, experiments, registry governance, deployment, monitoring, drift detection, and retraining."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Projects" value={String(exampleProjects.length)} detail="reference workloads" />
        <MetricCard label="Model Families" value={String(modelTypes)} detail="ranking, retrieval, risk" />
        <MetricCard
          label="Approved Models"
          value={String(approvedModels)}
          detail="seeded through registry gates"
          tone="success"
        />
        <MetricCard
          label="Lifecycle Areas"
          value={String(lifecycleStageCount)}
          detail="covered by manifests"
        />
      </div>

      <div className="mt-6 grid gap-4">
        <DataPanel title="Project Catalog">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1040px] text-left text-sm">
              <thead className="text-xs uppercase text-steel">
                <tr>
                  <th className="py-2">Project</th>
                  <th>Dataset</th>
                  <th>Feature Set</th>
                  <th>Model</th>
                  <th>Objective</th>
                  <th>Endpoint</th>
                  <th>Guardrail</th>
                </tr>
              </thead>
              <tbody>
                {exampleProjects.map((project) => (
                  <tr key={project.slug} className="border-t border-slate-100 align-top">
                    <td className="py-3">
                      <div className="font-medium text-ink">{project.name}</div>
                      <div className="mt-1 text-xs text-steel">{project.ownerPersona}</div>
                    </td>
                    <td className="max-w-[220px] pr-4">
                      <div className="font-medium">{project.datasetName}</div>
                      <div className="mt-1 text-xs leading-5 text-steel">{project.datasetShape}</div>
                    </td>
                    <td className="max-w-[180px] pr-4">{project.featureSetName}</td>
                    <td className="max-w-[180px] pr-4">
                      <div>{project.modelName}</div>
                      <div className="mt-1 text-xs text-steel">{project.modelType}</div>
                    </td>
                    <td>{project.objectiveMetric}</td>
                    <td className="font-mono text-xs">{project.endpointPath}</td>
                    <td className="max-w-[180px] pr-4">
                      <div>{project.alertSignal}</div>
                      <div className="mt-1 text-xs text-steel">{project.retrainingPolicy}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DataPanel>

        <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <DataPanel title="Offline Quality Signals">
            <div className="grid gap-4 md:grid-cols-3">
              {exampleProjects.map((project) => (
                <div key={project.slug} className="border-l-2 border-signal pl-3">
                  <div className="text-sm font-medium text-ink">{project.name}</div>
                  <div className="mt-3 space-y-2">
                    {project.metrics.map((metric) => (
                      <div key={metric.label} className="flex items-center justify-between gap-4 text-sm">
                        <span className="text-steel">{metric.label}</span>
                        <span className="font-semibold text-ink">{metric.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </DataPanel>

          <DataPanel title="Lifecycle Coverage">
            <div className="grid gap-3 md:grid-cols-3">
              {exampleProjects.map((project) => (
                <div key={project.slug} className="space-y-2">
                  <div className="text-sm font-medium text-ink">{project.name}</div>
                  {project.lifecycleStages.map((stage) => (
                    <div key={stage} className="flex items-center gap-2 text-sm text-steel">
                      <CheckCircle2 className="h-4 w-4 text-signal" aria-hidden="true" />
                      <span>{stage}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </DataPanel>
        </div>
      </div>
    </>
  );
}
