import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  CircleDashed,
  Clock3,
  ExternalLink,
  GitPullRequestArrow,
} from "lucide-react";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import { Link } from "../../../shared/routing/router";
import { ACCESS_TOKEN_KEY, PROJECT_CONTEXT_KEY } from "../../auth/session/sessionStore";
import {
  getProjectLifecycleSummary,
  type LifecycleStageStatus,
  type ProjectLifecycleDependency,
  type ProjectLifecycleMetric,
  type ProjectLifecycleStage,
} from "../api/lifecycle";

export function LifecyclePage() {
  const token = readLocalStorage(ACCESS_TOKEN_KEY);
  const projectId = readLocalStorage(PROJECT_CONTEXT_KEY);
  const canLoadLifecycle = Boolean(token && projectId);
  const lifecycleQuery = useQuery({
    queryKey: ["project-lifecycle-summary", projectId],
    queryFn: () => getProjectLifecycleSummary(projectId ?? "", token ?? ""),
    enabled: canLoadLifecycle,
    refetchInterval: 10_000,
  });
  const summary = lifecycleQuery.data;
  const activeActions =
    summary?.recommended_actions.length ? summary.recommended_actions : fallbackActions;

  return (
    <>
      <PageHeader
        eyebrow="Project Lifecycle"
        title="Lifecycle"
        description="A project-level operating map from dataset contracts through training, registry, serving, monitoring, drift detection, and retraining."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Readiness"
          value={`${summary?.readiness_score ?? 0}%`}
          detail={
            summary
              ? `${summary.ready_stage_count} of ${summary.total_stage_count} stages ready`
              : "select a project"
          }
          tone={readinessTone(summary?.readiness_score ?? 0)}
        />
        <MetricCard
          label="Project"
          value={summary?.project_name ?? "none"}
          detail={summary?.project_slug ?? projectId ?? "no active context"}
        />
        <MetricCard
          label="Schema"
          value={summary ? "project_lifecycle.v1" : "v1"}
          detail={summary?.schema_version ?? "cross-module read model"}
          tone="success"
        />
        <MetricCard
          label="Generated"
          value={summary ? formatTime(summary.generated_at) : "--"}
          detail={summary ? summary.project_status : "waiting for API"}
        />
      </div>

      <div className="mt-6">
        {!token ? (
          <StateMessage
            tone="warning"
            message="Sign in to load lifecycle readiness for an API-backed project."
          />
        ) : !projectId ? (
          <StateMessage
            tone="warning"
            message="Select a project to view lifecycle readiness."
          />
        ) : lifecycleQuery.error ? (
          <StateMessage
            tone="danger"
            message="Lifecycle summary request failed."
          />
        ) : lifecycleQuery.isLoading ? (
          <StateMessage message="Loading lifecycle summary." />
        ) : summary ? (
          <LifecycleReadiness score={summary.readiness_score} />
        ) : null}
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <DataPanel title="Stage Readiness">
          {summary ? (
            <div className="grid gap-3">
              {summary.stages.map((stage, index) => (
                <StageRow
                  key={stage.key}
                  stage={stage}
                  isLast={index === summary.stages.length - 1}
                />
              ))}
            </div>
          ) : (
            <StateMessage message="Lifecycle stages will appear after project context is available." />
          )}
        </DataPanel>

        <div className="grid gap-4">
          <DataPanel title="Recommended Actions">
            <div className="grid gap-3">
              {activeActions.map((action) => (
                <div
                  key={action}
                  className="flex gap-3 rounded border border-slate-200 bg-cloud p-3 text-sm"
                >
                  <GitPullRequestArrow
                    className="mt-0.5 h-4 w-4 shrink-0 text-signal"
                    aria-hidden="true"
                  />
                  <span className="leading-6 text-steel">{action}</span>
                </div>
              ))}
            </div>
          </DataPanel>

          <DataPanel title="Project Signals">
            {summary ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {summary.metrics.map((metric) => (
                  <LifecycleMetric key={metric.label} metric={metric} />
                ))}
              </div>
            ) : (
              <StateMessage message="Project signals are waiting for lifecycle data." />
            )}
          </DataPanel>
        </div>
      </div>

      <div className="mt-6">
        <DataPanel title="Dependency Map">
          {summary ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Source</th>
                    <th>Flow</th>
                    <th>Target</th>
                    <th>Status</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.dependencies.map((dependency) => (
                    <DependencyRow
                      key={`${dependency.source_stage}-${dependency.target_stage}`}
                      dependency={dependency}
                      stages={summary.stages}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <StateMessage message="Dependency health is available after the summary loads." />
          )}
        </DataPanel>
      </div>
    </>
  );
}

function LifecycleReadiness({ score }: { score: number }) {
  return (
    <div className="rounded border border-slate-200 bg-white p-4 shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-ink">
            End-to-End Lifecycle Readiness
          </div>
          <p className="mt-1 text-sm leading-6 text-steel">
            The score is derived from required evidence across ten production ML
            lifecycle stages.
          </p>
        </div>
        <StatusBadge status={score >= 80 ? "ready" : score >= 50 ? "pending" : "needs_attention"} />
      </div>
      <div className="mt-4 h-3 overflow-hidden rounded bg-slate-100">
        <div
          className={[
            "h-full rounded",
            score >= 80
              ? "bg-signal"
              : score >= 50
                ? "bg-amber-500"
                : "bg-risk",
          ].join(" ")}
          style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
        />
      </div>
    </div>
  );
}

function StageRow({
  stage,
  isLast,
}: {
  stage: ProjectLifecycleStage;
  isLast: boolean;
}) {
  const Icon = statusIcon(stage.status);
  return (
    <div className="grid gap-3 rounded border border-slate-200 bg-white p-3 sm:grid-cols-[2rem_1fr_auto]">
      <div className="flex sm:block">
        <div
          className={[
            "flex h-8 w-8 items-center justify-center rounded border",
            statusClass(stage.status),
          ].join(" ")}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
        {!isLast ? (
          <div className="ml-4 hidden h-full border-l border-slate-200 sm:block" />
        ) : null}
      </div>
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold text-ink">{stage.title}</h2>
          <StatusBadge status={stage.status} />
        </div>
        <p className="mt-1 text-sm leading-6 text-steel">{stage.description}</p>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-steel">
          <span className="rounded bg-slate-100 px-2 py-1">
            {stage.primary_signal}
          </span>
          <span className="rounded bg-slate-100 px-2 py-1">
            updated {formatTime(stage.last_updated_at)}
          </span>
        </div>
      </div>
      <Link
        to={stage.route_path}
        className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 px-3 text-xs font-semibold text-steel transition hover:text-ink"
      >
        <ExternalLink className="h-4 w-4" aria-hidden="true" />
        Open
      </Link>
    </div>
  );
}

function LifecycleMetric({ metric }: { metric: ProjectLifecycleMetric }) {
  return (
    <div className="rounded border border-slate-200 bg-cloud p-3">
      <div className="text-xs font-semibold uppercase text-steel">
        {metric.label}
      </div>
      <div className={["mt-2 text-xl font-semibold", metricToneClass(metric.tone)].join(" ")}>
        {metric.value}
      </div>
      <div className="mt-1 text-sm text-steel">{metric.detail}</div>
    </div>
  );
}

function DependencyRow({
  dependency,
  stages,
}: {
  dependency: ProjectLifecycleDependency;
  stages: ProjectLifecycleStage[];
}) {
  const source = stages.find((stage) => stage.key === dependency.source_stage);
  const target = stages.find((stage) => stage.key === dependency.target_stage);
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3 font-medium text-ink">{source?.title ?? dependency.source_stage}</td>
      <td>
        <ArrowRight className="h-4 w-4 text-steel" aria-hidden="true" />
      </td>
      <td className="font-medium text-ink">{target?.title ?? dependency.target_stage}</td>
      <td>
        <span
          className={[
            "inline-flex rounded border px-2 py-1 text-xs font-semibold",
            dependency.status === "connected"
              ? "border-emerald-200 bg-emerald-50 text-signal"
              : "border-rose-200 bg-rose-50 text-risk",
          ].join(" ")}
        >
          {labelize(dependency.status)}
        </span>
      </td>
      <td className="max-w-[360px] text-steel">{dependency.detail}</td>
    </tr>
  );
}

function StatusBadge({ status }: { status: LifecycleStageStatus }) {
  return (
    <span
      className={[
        "inline-flex rounded border px-2 py-1 text-xs font-semibold",
        statusClass(status),
      ].join(" ")}
    >
      {labelize(status)}
    </span>
  );
}

function StateMessage({
  message,
  tone = "neutral",
}: {
  message: string;
  tone?: "neutral" | "warning" | "danger";
}) {
  const toneClass = {
    neutral: "border-slate-200 bg-white text-steel",
    warning: "border-amber-200 bg-amber-50 text-amber-700",
    danger: "border-rose-200 bg-rose-50 text-risk",
  }[tone];
  return <div className={`rounded border px-3 py-2 text-sm ${toneClass}`}>{message}</div>;
}

function statusIcon(status: LifecycleStageStatus) {
  if (status === "ready") {
    return CheckCircle2;
  }
  if (status === "needs_attention") {
    return AlertTriangle;
  }
  if (status === "pending") {
    return Clock3;
  }
  return CircleDashed;
}

function statusClass(status: LifecycleStageStatus): string {
  if (status === "ready") {
    return "border-emerald-200 bg-emerald-50 text-signal";
  }
  if (status === "needs_attention") {
    return "border-rose-200 bg-rose-50 text-risk";
  }
  if (status === "pending") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-slate-200 bg-slate-50 text-steel";
}

function metricToneClass(tone: ProjectLifecycleMetric["tone"]): string {
  const classes = {
    neutral: "text-ink",
    success: "text-signal",
    warning: "text-amber-600",
    danger: "text-risk",
  };
  return classes[tone];
}

function readinessTone(score: number): "neutral" | "success" | "warning" | "danger" {
  if (score >= 80) {
    return "success";
  }
  if (score >= 50) {
    return "warning";
  }
  if (score > 0) {
    return "danger";
  }
  return "neutral";
}

function formatTime(value: string | null | undefined): string {
  if (!value) {
    return "--";
  }
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return "--";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(timestamp));
}

function labelize(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}

const fallbackActions = [
  "Select an API-backed project to inspect lifecycle readiness.",
  "Use Projects to choose context before reviewing cross-module evidence.",
];
