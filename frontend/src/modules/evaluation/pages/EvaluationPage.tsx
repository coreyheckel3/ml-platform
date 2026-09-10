import { useQuery } from "@tanstack/react-query";
import {
  BadgeCheck,
  BarChart3,
  CheckCircle2,
  CircleDashed,
  ClipboardCheck,
  FileText,
  LineChart,
  Scale,
  ShieldCheck,
  Trophy,
} from "lucide-react";
import type { ReactNode } from "react";

import { Link } from "../../../shared/routing/router";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  ACCESS_TOKEN_KEY,
  PROJECT_CONTEXT_KEY,
} from "../../auth/session/sessionStore";
import {
  getEvaluationComparisonSummary,
  type EvaluationApprovalChecklistItem,
  type EvaluationLeaderboardEntry,
  type EvaluationMetricSlice,
  type EvaluationModelCard,
} from "../api/evaluation";

export function EvaluationPage() {
  const token = readLocalStorage(ACCESS_TOKEN_KEY);
  const projectId = readLocalStorage(PROJECT_CONTEXT_KEY);
  const canLoadEvaluation = Boolean(token && projectId);
  const comparisonQuery = useQuery({
    queryKey: ["evaluation-comparison", projectId],
    queryFn: () => getEvaluationComparisonSummary(projectId ?? "", token ?? ""),
    enabled: canLoadEvaluation,
    refetchInterval: 10_000,
    refetchIntervalInBackground: true,
  });
  const summary = comparisonQuery.data;
  const bestRun = summary?.leaderboard[0];
  const passedChecklist =
    summary?.approval_checklist.filter((item) => item.status === "passed").length ?? 0;
  const warningChecklist =
    summary?.approval_checklist.filter((item) => item.status === "warning").length ?? 0;

  return (
    <>
      <PageHeader
        eyebrow="Evaluation"
        title="Evaluation"
        description="Compare experiment candidates, metric slices, model-card evidence, and approval readiness before promoting a model."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Candidates"
          value={String(summary?.candidate_count ?? 0)}
          detail={summary?.project_name ?? projectId ?? "select a project"}
        />
        <MetricCard
          label="Best Metric"
          value={formatMetricValue(bestRun?.primary_metric_value)}
          detail={bestRun?.primary_metric_name ?? "no scored metric"}
          tone={bestRun ? "success" : "neutral"}
        />
        <MetricCard
          label="Model Cards"
          value={String(summary?.model_cards.length ?? 0)}
          detail="registry evidence records"
        />
        <MetricCard
          label="Checklist"
          value={`${passedChecklist}/${summary?.approval_checklist.length ?? 0}`}
          detail={`${warningChecklist} warnings before review`}
          tone={warningChecklist > 0 ? "warning" : passedChecklist > 0 ? "success" : "neutral"}
        />
      </div>

      <div className="mt-6">
        {!token ? (
          <StateMessage
            tone="warning"
            message="Sign in to load evaluation comparisons for an API-backed project."
          />
        ) : !projectId ? (
          <StateMessage tone="warning" message="Select a project to view evaluation evidence." />
        ) : comparisonQuery.error ? (
          <StateMessage tone="danger" message="Evaluation comparison request failed." />
        ) : comparisonQuery.isLoading ? (
          <StateMessage message="Loading evaluation comparison." />
        ) : summary && summary.leaderboard.length === 0 ? (
          <StateMessage message="No evaluated experiment runs are available yet." />
        ) : null}
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
        <DataPanel
          title="Run Leaderboard"
          action={
            <Link
              to="/experiments"
              className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 px-3 text-xs font-semibold text-steel transition hover:text-ink"
            >
              <BarChart3 className="h-4 w-4" aria-hidden="true" />
              Experiments
            </Link>
          }
        >
          {summary ? (
            <LeaderboardTable entries={summary.leaderboard} />
          ) : (
            <StateMessage message="Leaderboard rows will appear after evaluation data loads." />
          )}
        </DataPanel>

        <div className="grid gap-4">
          <DataPanel title="Approval Checklist">
            {summary ? (
              <div className="grid gap-3">
                {summary.approval_checklist.map((item) => (
                  <ChecklistItem key={item.key} item={item} />
                ))}
              </div>
            ) : (
              <StateMessage message="Approval checks are waiting for evaluation evidence." />
            )}
          </DataPanel>

          <DataPanel title="Evaluation Narrative">
            {summary ? (
              <div className="grid gap-3">
                {summary.narrative.map((sentence) => (
                  <div
                    key={sentence}
                    className="rounded border border-slate-200 bg-cloud p-3 text-sm leading-6 text-steel"
                  >
                    {sentence}
                  </div>
                ))}
              </div>
            ) : (
              <StateMessage message="Reviewer narrative will appear after comparison loads." />
            )}
          </DataPanel>
        </div>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <DataPanel title="Metric Slices">
          {summary ? (
            <MetricSlices slices={summary.metric_slices} />
          ) : (
            <StateMessage message="Metric slices are waiting for scored experiment runs." />
          )}
        </DataPanel>

        <DataPanel
          title="Model Card Evidence"
          action={
            <Link
              to="/models"
              className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 px-3 text-xs font-semibold text-steel transition hover:text-ink"
            >
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              Models
            </Link>
          }
        >
          {summary ? (
            <ModelCards cards={summary.model_cards} />
          ) : (
            <StateMessage message="Model card evidence loads after registry data is available." />
          )}
        </DataPanel>
      </div>
    </>
  );
}

function LeaderboardTable({ entries }: { entries: EvaluationLeaderboardEntry[] }) {
  if (entries.length === 0) {
    return <StateMessage message="No comparison candidates found for this project." />;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[860px] text-left text-sm">
        <thead className="text-xs uppercase text-steel">
          <tr>
            <th className="py-2">Rank</th>
            <th>Run</th>
            <th>Metric</th>
            <th>Delta</th>
            <th>Evidence</th>
            <th>Quality</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.experiment_run_id} className="border-t border-slate-100">
              <td className="py-3">
                <span className="inline-flex h-7 min-w-7 items-center justify-center rounded bg-slate-100 px-2 text-xs font-semibold text-ink">
                  {entry.rank}
                </span>
              </td>
              <td className="pr-4">
                <div className="flex items-center gap-2">
                  {entry.rank === 1 ? (
                    <Trophy className="h-4 w-4 text-amber-600" aria-hidden="true" />
                  ) : (
                    <CircleDashed className="h-4 w-4 text-steel" aria-hidden="true" />
                  )}
                  <div>
                    <div className="font-semibold text-ink">{entry.run_name}</div>
                    <div className="text-xs text-steel">
                      {entry.experiment_name} - {entry.model_type}
                    </div>
                  </div>
                </div>
              </td>
              <td className="pr-4">
                <div className="font-semibold text-ink">
                  {formatMetricValue(entry.primary_metric_value)}
                </div>
                <div className="text-xs text-steel">{entry.primary_metric_name ?? "metric"}</div>
              </td>
              <td className="pr-4">
                <span className="text-sm font-semibold text-signal">
                  {formatSignedMetric(entry.delta_from_baseline)}
                </span>
              </td>
              <td className="pr-4">
                <StatusBadge status={entry.approval_status} />
                <div className="mt-1 max-w-[280px] text-xs leading-5 text-steel">
                  {entry.evidence_summary}
                </div>
              </td>
              <td>
                <div className="h-2 w-24 overflow-hidden rounded bg-slate-100">
                  <div
                    className="h-full rounded bg-signal"
                    style={{ width: `${Math.max(0, Math.min(100, entry.quality_score))}%` }}
                  />
                </div>
                <div className="mt-1 text-xs text-steel">{entry.quality_score}/100</div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MetricSlices({ slices }: { slices: EvaluationMetricSlice[] }) {
  if (slices.length === 0) {
    return <StateMessage message="No metric slices are available yet." />;
  }
  return (
    <div className="grid gap-3">
      {slices.map((slice) => (
        <div key={slice.metric_name} className="rounded border border-slate-200 bg-white p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-sm font-semibold text-ink">{slice.metric_name}</div>
              <div className="text-xs text-steel">
                {slice.candidate_count} candidates - {slice.higher_is_better ? "higher" : "lower"} is better
              </div>
            </div>
            <LineChart className="h-4 w-4 text-signal" aria-hidden="true" />
          </div>
          <div className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
            <MetricPill label="Best" value={formatMetricValue(slice.best_value)} />
            <MetricPill label="Baseline" value={formatMetricValue(slice.baseline_value)} />
            <MetricPill label="Delta" value={formatSignedMetric(slice.delta_from_baseline)} />
          </div>
          <div className="mt-3 text-xs text-steel">Leader: {slice.best_run_name}</div>
        </div>
      ))}
    </div>
  );
}

function ModelCards({ cards }: { cards: EvaluationModelCard[] }) {
  if (cards.length === 0) {
    return <StateMessage message="No promoted model versions are linked yet." />;
  }
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      {cards.map((card) => (
        <article key={card.model_version_id} className="rounded border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-ink">
                {card.model_name} v{card.version}
              </h2>
              <div className="mt-1 text-xs text-steel">
                {card.model_format} - {card.status}
              </div>
            </div>
            <StatusBadge status={card.approval_status} />
          </div>

          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {card.metric_summary.map((metric) => (
              <MetricPill
                key={metric.label}
                label={metric.label}
                value={formatMetricValue(metric.value)}
                tone={metric.tone}
              />
            ))}
          </div>

          <div className="mt-4 grid gap-3 text-xs text-steel">
            <EvidenceLine
              icon={<FileText className="h-4 w-4" aria-hidden="true" />}
              label="Signature"
              value={card.signature_summary.join(", ") || "not captured"}
            />
            <EvidenceLine
              icon={<BadgeCheck className="h-4 w-4" aria-hidden="true" />}
              label="Manifest"
              value={card.artifact_manifest_hash || "missing checksum"}
            />
            <EvidenceLine
              icon={<Scale className="h-4 w-4" aria-hidden="true" />}
              label="Lineage"
              value={card.lineage_summary.join(", ") || "no lineage evidence"}
            />
          </div>

          {card.risk_flags.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {card.risk_flags.map((flag) => (
                <span key={flag} className="rounded bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700">
                  {formatLabel(flag)}
                </span>
              ))}
            </div>
          ) : (
            <div className="mt-4 inline-flex items-center gap-2 rounded bg-emerald-50 px-2 py-1 text-xs font-semibold text-signal">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              Reviewer ready
            </div>
          )}
        </article>
      ))}
    </div>
  );
}

function ChecklistItem({ item }: { item: EvaluationApprovalChecklistItem }) {
  const Icon = item.status === "passed" ? CheckCircle2 : item.status === "warning" ? ClipboardCheck : CircleDashed;
  return (
    <div className="rounded border border-slate-200 bg-white p-3">
      <div className="flex items-start gap-3">
        <div className={["flex h-8 w-8 items-center justify-center rounded border", checklistClass(item.status)].join(" ")}>
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-sm font-semibold text-ink">{item.label}</div>
            <StatusBadge status={item.status} />
          </div>
          <p className="mt-1 text-sm leading-6 text-steel">{item.detail}</p>
          <div className="mt-2 text-xs text-steel">{item.evidence}</div>
        </div>
      </div>
    </div>
  );
}

function EvidenceLine({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-signal">{icon}</span>
      <span className="font-semibold text-ink">{label}</span>
      <span className="truncate">{value}</span>
    </div>
  );
}

function MetricPill({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "success" | "warning" | "danger";
}) {
  const toneClass = {
    neutral: "text-ink",
    success: "text-signal",
    warning: "text-amber-600",
    danger: "text-risk",
  }[tone];
  return (
    <div className="rounded bg-slate-100 px-3 py-2">
      <div className="text-xs font-semibold uppercase text-steel">{label}</div>
      <div className={["mt-1 text-sm font-semibold", toneClass].join(" ")}>{value}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const tone =
    normalized === "approved" || normalized === "passed" || normalized === "succeeded"
      ? "bg-emerald-50 text-signal"
      : normalized === "warning" || normalized === "requested" || normalized === "pending_approval"
        ? "bg-amber-50 text-amber-700"
        : normalized === "missing" || normalized === "rejected" || normalized === "failed"
          ? "bg-rose-50 text-risk"
          : "bg-slate-100 text-steel";
  return (
    <span className={["rounded px-2 py-1 text-xs font-semibold", tone].join(" ")}>
      {formatLabel(status)}
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
    neutral: "border-slate-200 bg-cloud text-steel",
    warning: "border-amber-200 bg-amber-50 text-amber-700",
    danger: "border-rose-200 bg-rose-50 text-risk",
  }[tone];
  return <div className={["rounded border p-4 text-sm", toneClass].join(" ")}>{message}</div>;
}

function checklistClass(status: EvaluationApprovalChecklistItem["status"]): string {
  if (status === "passed") {
    return "border-emerald-200 bg-emerald-50 text-signal";
  }
  if (status === "warning") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-slate-200 bg-slate-100 text-steel";
}

function formatMetricValue(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "--";
  }
  if (Math.abs(value) >= 100) {
    return value.toFixed(1);
  }
  if (Math.abs(value) >= 1) {
    return value.toFixed(3);
  }
  return value.toFixed(4);
}

function formatSignedMetric(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "--";
  }
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${formatMetricValue(value)}`;
}

function formatLabel(value: string): string {
  return value
    .split(/[_:.-]/g)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function readLocalStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}
