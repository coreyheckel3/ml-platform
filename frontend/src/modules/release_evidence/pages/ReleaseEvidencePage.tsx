import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BadgeCheck,
  Box,
  ClipboardCheck,
  ExternalLink,
  FileJson2,
  History,
  Image,
  PackageCheck,
  RefreshCw,
  SearchCheck,
  SquareTerminal,
} from "lucide-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";

import { readStoredSession, subscribeToSessionChanges } from "../../auth/session/sessionStore";
import {
  getReleaseEvidenceReport,
  listReleaseEvidenceReports,
  retrieveReleaseEvidenceReport,
  type ReleaseEvidenceReport,
} from "../api/releaseEvidence";
import {
  qualityGates,
  liveReleaseEvidenceRetrieval,
  releaseArtifacts,
  releaseEvidenceSummary,
  reviewerCommands,
  screenshotEvidence,
  type EvidenceGate,
} from "../data/releaseEvidence";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";

const ownerClass: Record<EvidenceGate["owner"], string> = {
  Backend: "border-sky-200 bg-sky-50 text-sky-700",
  Frontend: "border-indigo-200 bg-indigo-50 text-indigo-700",
  Operations: "border-emerald-200 bg-emerald-50 text-signal",
  Platform: "border-slate-200 bg-slate-50 text-ink",
  Security: "border-rose-200 bg-rose-50 text-risk",
};

export function ReleaseEvidencePage() {
  const [session, setSession] = useState(() => readStoredSession());
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const token = session?.accessToken ?? "";
  const queryClient = useQueryClient();
  const reportsQuery = useQuery({
    queryKey: ["release-evidence-reports", token],
    queryFn: () => listReleaseEvidenceReports(token, { limit: 10 }),
    enabled: Boolean(token),
    retry: false,
  });
  const reports = useMemo(
    () => reportsQuery.data?.items ?? [],
    [reportsQuery.data?.items],
  );
  const selectedReportFromList =
    reports.find((report) => report.id === selectedReportId) ?? reports[0] ?? null;
  const detailQuery = useQuery({
    queryKey: ["release-evidence-report", token, selectedReportId],
    queryFn: () => getReleaseEvidenceReport(token, selectedReportId ?? ""),
    enabled: Boolean(token && selectedReportId),
    retry: false,
  });
  const selectedReport = detailQuery.data ?? selectedReportFromList;
  const retrieveMutation = useMutation({
    mutationFn: () => retrieveReleaseEvidenceReport(token),
    onSuccess: (report) => {
      setSelectedReportId(report.id);
      queryClient.setQueryData(["release-evidence-report", token, report.id], report);
      queryClient.setQueryData(
        ["release-evidence-reports", token],
        (current: { items: ReleaseEvidenceReport[]; next_cursor: string | null } | undefined) => ({
          items: [report, ...(current?.items ?? []).filter((item) => item.id !== report.id)],
          next_cursor: current?.next_cursor ?? null,
        }),
      );
      void queryClient.invalidateQueries({
        queryKey: ["release-evidence-reports", token],
      });
    },
  });

  useEffect(
    () => subscribeToSessionChanges(() => setSession(readStoredSession())),
    [],
  );

  useEffect(() => {
    if (reports.length === 0) {
      setSelectedReportId(null);
      return;
    }
    if (!selectedReportId || !reports.some((report) => report.id === selectedReportId)) {
      setSelectedReportId(reports[0].id);
    }
  }, [reports, selectedReportId]);

  return (
    <>
      <PageHeader
        eyebrow="Release Governance"
        title="Release Evidence"
        description="Reviewer and operator workspace for release manifests, quality gates, demo screenshots, and CI provenance."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Required Artifacts"
          value={String(releaseEvidenceSummary.artifactCount)}
          detail="contracts, runbooks, docs, and deployment assets"
        />
        <MetricCard
          label="Quality Gates"
          value={String(releaseEvidenceSummary.qualityGateCount)}
          detail="validated before release evidence is published"
          tone="success"
        />
        <MetricCard
          label="Image Targets"
          value={String(releaseEvidenceSummary.imageTargetCount)}
          detail="backend, frontend, worker, migrations, and release smoke"
        />
        <MetricCard
          label="CI Artifact"
          value="published"
          detail={releaseEvidenceSummary.ciArtifactName}
          tone="success"
        />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <DataPanel
          title="Release Manifest"
          action={
            <span className="inline-flex h-8 items-center gap-2 rounded border border-emerald-200 bg-emerald-50 px-3 text-xs font-semibold text-signal">
              <PackageCheck className="h-4 w-4" aria-hidden="true" />
              CI published
            </span>
          }
        >
          <div className="grid gap-4">
            <div className="rounded border border-slate-200 bg-cloud p-3">
              <div className="flex items-center gap-2 break-all text-sm font-semibold text-ink">
                <FileJson2 className="h-4 w-4 shrink-0 text-signal" aria-hidden="true" />
                {releaseEvidenceSummary.manifestPath}
              </div>
              <p className="mt-2 text-sm leading-6 text-steel">
                The manifest records artifact checksums, Docker image targets, Git
                metadata, required quality gates, and the GitHub Actions run URL used
                as release provenance.
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Artifact</th>
                    <th>Kind</th>
                    <th>Path</th>
                    <th>Reviewer Signal</th>
                  </tr>
                </thead>
                <tbody>
                  {releaseArtifacts.map((artifact) => (
                    <tr key={artifact.path} className="border-t border-slate-100">
                      <td className="py-3 font-medium text-ink">{artifact.name}</td>
                      <td>{artifact.kind}</td>
                      <td>
                        <code className="rounded bg-slate-100 px-2 py-1 text-xs text-ink">
                          {artifact.path}
                        </code>
                      </td>
                      <td className="max-w-[280px] text-steel">{artifact.signal}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </DataPanel>

        <DataPanel
          title="Live Evidence Retrieval"
          action={
            <span className="inline-flex h-8 items-center gap-2 rounded border border-emerald-200 bg-emerald-50 px-3 text-xs font-semibold text-signal">
              <BadgeCheck className="h-4 w-4" aria-hidden="true" />
              {liveReleaseEvidenceRetrieval.status}
            </span>
          }
        >
          <div className="grid gap-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <RetrievalFact
                label="Provider"
                value={liveReleaseEvidenceRetrieval.provider}
              />
              <RetrievalFact label="Branch" value={liveReleaseEvidenceRetrieval.branch} />
              <RetrievalFact
                label="Workflow"
                value={liveReleaseEvidenceRetrieval.workflow}
              />
              <RetrievalFact
                label="Artifact"
                value={liveReleaseEvidenceRetrieval.artifactName}
              />
            </div>
            <div className="rounded border border-slate-200 bg-cloud p-3">
              <div className="text-sm font-semibold text-ink">
                {liveReleaseEvidenceRetrieval.adapter}
              </div>
              <p className="mt-2 text-sm leading-6 text-steel">
                The adapter locates the latest successful main-branch workflow run,
                downloads the release manifest artifact, extracts the manifest from the
                archive, and compares it against the checked-in release contract.
              </p>
            </div>
            <div className="rounded border border-slate-200 p-3">
              <div className="text-sm font-semibold text-ink">Comparison Signals</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {liveReleaseEvidenceRetrieval.comparisonSignals.map((signal) => (
                  <code
                    key={signal}
                    className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-steel"
                  >
                    {signal}
                  </code>
                ))}
              </div>
            </div>
            <div className="rounded border border-slate-200 p-3">
              <div className="flex items-start gap-3">
                <SquareTerminal className="mt-0.5 h-4 w-4 shrink-0 text-signal" />
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-ink">Operator Command</div>
                  <p className="mt-1 text-sm leading-6 text-steel">
                    Uses GitHub Actions as the release evidence source of truth.
                  </p>
                </div>
              </div>
              <code className="mt-3 block overflow-x-auto rounded bg-ink px-3 py-2 text-xs text-white">
                {liveReleaseEvidenceRetrieval.operatorCommand}
              </code>
            </div>
          </div>
        </DataPanel>
      </div>

      <div className="mt-6">
        <DataPanel
          title="API Evidence Drilldown"
          action={
            <button
              type="button"
              onClick={() => retrieveMutation.mutate()}
              disabled={!token || retrieveMutation.isPending}
              className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-steel transition hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw
                className={`h-4 w-4 ${retrieveMutation.isPending ? "animate-spin" : ""}`}
                aria-hidden="true"
              />
              Retrieve evidence
            </button>
          }
        >
          <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded border border-slate-200 p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-ink">
                  <History className="h-4 w-4 text-signal" aria-hidden="true" />
                  Recent Reports
                </div>
                <span className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-steel">
                  {reports.length} loaded
                </span>
              </div>

              <div className="mt-3 grid gap-2">
                {!token ? (
                  <EvidenceStateMessage message="Sign in to load release evidence reports." />
                ) : reportsQuery.error ? (
                  <EvidenceStateMessage
                    tone="danger"
                    message="Release evidence report API request failed."
                  />
                ) : reportsQuery.isFetching && reports.length === 0 ? (
                  <EvidenceStateMessage message="Loading release evidence reports." />
                ) : reports.length === 0 ? (
                  <EvidenceStateMessage message="No release evidence reports have been captured." />
                ) : (
                  reports.map((report) => (
                    <ReleaseEvidenceReportRow
                      key={report.id}
                      report={report}
                      selected={report.id === selectedReport?.id}
                      onSelect={() => setSelectedReportId(report.id)}
                    />
                  ))
                )}
              </div>
            </div>

            <div className="rounded border border-slate-200 p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-ink">
                  <SearchCheck className="h-4 w-4 text-signal" aria-hidden="true" />
                  Report Drilldown
                </div>
                {selectedReport ? <StatusPill status={selectedReport.status} /> : null}
              </div>

              <div className="mt-3">
                {retrieveMutation.error ? (
                  <EvidenceStateMessage
                    tone="danger"
                    message={
                      retrieveMutation.error instanceof Error
                        ? retrieveMutation.error.message
                        : "Release evidence retrieval failed."
                    }
                  />
                ) : null}

                {retrieveMutation.data ? (
                  <EvidenceStateMessage
                    tone={retrieveMutation.data.status === "passed" ? "success" : "warning"}
                    message={`Retrieval recorded as ${retrieveMutation.data.status}.`}
                  />
                ) : null}

                {selectedReport ? (
                  <ReleaseEvidenceReportDetail
                    report={selectedReport}
                    isLoading={detailQuery.isFetching}
                  />
                ) : (
                  <EvidenceStateMessage message="Select or retrieve a release evidence report." />
                )}
              </div>
            </div>
          </div>
        </DataPanel>
      </div>

      <div className="mt-6">
        <DataPanel title="Reviewer Commands">
          <div className="grid gap-3 md:grid-cols-2">
            {reviewerCommands.map((command) => (
              <div key={command.label} className="rounded border border-slate-200 p-3">
                <div className="flex items-start gap-3">
                  <SquareTerminal className="mt-0.5 h-4 w-4 shrink-0 text-signal" />
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-ink">{command.label}</div>
                    <p className="mt-1 text-sm leading-6 text-steel">{command.signal}</p>
                  </div>
                </div>
                <code className="mt-3 block overflow-x-auto rounded bg-ink px-3 py-2 text-xs text-white">
                  {command.command}
                </code>
              </div>
            ))}
          </div>
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <DataPanel title="Quality Gate Coverage">
          <div className="grid gap-3 md:grid-cols-2">
            {qualityGates.map((gate) => (
              <div key={gate.name} className="rounded border border-slate-200 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-ink">
                      {formatGateName(gate.name)}
                    </div>
                    <code className="mt-1 block max-w-full truncate rounded bg-slate-100 px-2 py-1 text-xs text-steel">
                      {gate.name}
                    </code>
                    <p className="mt-2 text-sm leading-6 text-steel">{gate.signal}</p>
                  </div>
                  <span
                    className={`inline-flex h-7 shrink-0 items-center rounded border px-2 text-xs font-semibold ${ownerClass[gate.owner]}`}
                  >
                    {gate.owner}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </DataPanel>

        <DataPanel title="Demo Screenshot Evidence">
          <div className="grid gap-3">
            {screenshotEvidence.map((screenshot) => (
              <div
                key={screenshot.fileName}
                className="grid gap-3 rounded border border-slate-200 p-3 md:grid-cols-[180px_1fr]"
              >
                <div className="flex min-h-[96px] items-center justify-center rounded border border-slate-200 bg-cloud">
                  <Image className="h-5 w-5 text-steel" aria-hidden="true" />
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-ink">
                      {screenshot.fileName}
                    </span>
                    <span className="inline-flex h-7 items-center rounded border border-slate-200 bg-white px-2 text-xs font-semibold text-steel">
                      {screenshot.route}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-steel">{screenshot.signal}</p>
                </div>
              </div>
            ))}
          </div>
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <EvidenceChecklistItem
          icon={<ClipboardCheck className="h-4 w-4" aria-hidden="true" />}
          title="Contract Current"
          detail="Release evidence UX is checked by CI, production readiness, and release manifest contracts."
        />
        <EvidenceChecklistItem
          icon={<BadgeCheck className="h-4 w-4" aria-hidden="true" />}
          title="Reviewer Ready"
          detail="Screenshots and evidence map make the platform easy to validate during interviews."
        />
        <EvidenceChecklistItem
          icon={<Box className="h-4 w-4" aria-hidden="true" />}
          title="Artifact Backed"
          detail="The CI artifact carries checksums and required gates for every release-critical asset."
        />
      </div>
    </>
  );
}

type EvidenceChecklistItemProps = {
  icon: ReactNode;
  title: string;
  detail: string;
};

type RetrievalFactProps = {
  label: string;
  value: string;
};

type EvidenceStateMessageProps = {
  message: string;
  tone?: "neutral" | "success" | "warning" | "danger";
};

type ReleaseEvidenceReportRowProps = {
  report: ReleaseEvidenceReport;
  selected: boolean;
  onSelect: () => void;
};

type ReleaseEvidenceReportDetailProps = {
  report: ReleaseEvidenceReport;
  isLoading: boolean;
};

function RetrievalFact({ label, value }: RetrievalFactProps) {
  return (
    <div className="rounded border border-slate-200 bg-white p-3">
      <div className="text-xs font-semibold uppercase text-steel">{label}</div>
      <div className="mt-2 break-all text-sm font-semibold text-ink">{value}</div>
    </div>
  );
}

function EvidenceStateMessage({
  message,
  tone = "neutral",
}: EvidenceStateMessageProps) {
  const toneClass = {
    neutral: "border-slate-200 bg-slate-50 text-steel",
    success: "border-emerald-200 bg-emerald-50 text-signal",
    warning: "border-amber-200 bg-amber-50 text-amber-700",
    danger: "border-rose-200 bg-rose-50 text-risk",
  }[tone];

  return (
    <div className={`rounded border px-3 py-2 text-sm ${toneClass}`}>
      {tone === "danger" ? (
        <AlertTriangle className="mr-2 inline h-4 w-4 align-text-bottom" />
      ) : null}
      {message}
    </div>
  );
}

function ReleaseEvidenceReportRow({
  report,
  selected,
  onSelect,
}: ReleaseEvidenceReportRowProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded border p-3 text-left transition ${
        selected
          ? "border-emerald-200 bg-emerald-50"
          : "border-slate-200 bg-white hover:border-slate-300"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-ink">
            {formatDate(report.created_at)}
          </div>
          <div className="mt-1 truncate text-xs text-steel">
            {formatNullable(report.repository)} / {formatNullable(report.branch)}
          </div>
        </div>
        <StatusPill status={report.status} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-steel">
        <span>{report.artifact_count} artifacts</span>
        <span>{report.quality_gate_count} gates</span>
      </div>
    </button>
  );
}

function ReleaseEvidenceReportDetail({
  report,
  isLoading,
}: ReleaseEvidenceReportDetailProps) {
  return (
    <div className="mt-3 grid gap-4">
      {isLoading ? <EvidenceStateMessage message="Refreshing report details." /> : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <RetrievalFact label="Provider" value={report.provider} />
        <RetrievalFact label="Branch" value={formatNullable(report.branch)} />
        <RetrievalFact label="Workflow" value={formatNullable(report.workflow)} />
        <RetrievalFact label="Commit" value={formatShortSha(report.manifest_git_sha)} />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <EvidenceList
          title="Missing Artifacts"
          items={report.missing_artifacts}
          emptyLabel="artifact coverage complete"
        />
        <EvidenceList
          title="Missing Quality Gates"
          items={report.missing_quality_gates}
          emptyLabel="gate coverage complete"
        />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded border border-slate-200 p-3">
          <div className="text-xs font-semibold uppercase text-steel">Audit Action</div>
          <code className="mt-2 block rounded bg-slate-100 px-2 py-1 text-xs text-ink">
            {report.status === "passed"
              ? "release_evidence.retrieve"
              : "release_evidence.retrieve_failed"}
          </code>
        </div>
        <div className="rounded border border-slate-200 p-3">
          <div className="text-xs font-semibold uppercase text-steel">Run Evidence</div>
          {report.ci_run_url || report.run_url ? (
            <a
              href={report.ci_run_url ?? report.run_url ?? undefined}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-flex items-center gap-2 break-all text-sm font-semibold text-signal"
            >
              GitHub Actions run
              <ExternalLink className="h-4 w-4 shrink-0" aria-hidden="true" />
            </a>
          ) : (
            <div className="mt-2 text-sm text-steel">run evidence unavailable</div>
          )}
        </div>
      </div>

      {report.error_message ? (
        <EvidenceStateMessage tone="danger" message={report.error_message} />
      ) : null}
    </div>
  );
}

function EvidenceList({
  title,
  items,
  emptyLabel,
}: {
  title: string;
  items: string[];
  emptyLabel: string;
}) {
  return (
    <div className="rounded border border-slate-200 p-3">
      <div className="text-xs font-semibold uppercase text-steel">{title}</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {items.length === 0 ? (
          <span className="rounded border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-semibold text-signal">
            {emptyLabel}
          </span>
        ) : (
          items.map((item) => (
            <code
              key={item}
              className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-700"
            >
              {item}
            </code>
          ))
        )}
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const normalizedStatus = status.toLowerCase();
  const className =
    normalizedStatus === "passed"
      ? "border-emerald-200 bg-emerald-50 text-signal"
      : normalizedStatus === "failed"
        ? "border-rose-200 bg-rose-50 text-risk"
        : "border-slate-200 bg-slate-50 text-steel";
  return (
    <span
      className={`inline-flex h-7 shrink-0 items-center rounded border px-2 text-xs font-semibold ${className}`}
    >
      {normalizedStatus}
    </span>
  );
}

function EvidenceChecklistItem({ icon, title, detail }: EvidenceChecklistItemProps) {
  return (
    <div className="rounded border border-slate-200 bg-white p-4 shadow-panel">
      <div className="flex items-center gap-2 text-sm font-semibold text-ink">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded border border-emerald-200 bg-emerald-50 text-signal">
          {icon}
        </span>
        {title}
      </div>
      <p className="mt-3 text-sm leading-6 text-steel">{detail}</p>
    </div>
  );
}

function formatGateName(name: string): string {
  return name
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatNullable(value: string | null): string {
  return value?.trim() || "not captured";
}

function formatShortSha(value: string | null): string {
  if (!value) {
    return "not captured";
  }
  return value.length > 12 ? value.slice(0, 12) : value;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}
