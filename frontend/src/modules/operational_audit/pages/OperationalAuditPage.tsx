import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  ClipboardList,
  Database,
  FileCheck2,
  Gauge,
  Link as LinkIcon,
  LockKeyhole,
  RefreshCw,
  Rocket,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";

import { readStoredSession, subscribeToSessionChanges } from "../../auth/session/sessionStore";
import { listAuditLog } from "../../settings/api/auditLog";
import { releaseEvidenceAuditEvents } from "../data/releaseEvidenceAuditEvents";
import {
  auditFamilyLabel,
  buildAuditFamilyStats,
  buildOperationalAuditTimeline,
  filterAuditTimeline,
  type AuditFamily,
  type AuditFamilyFilter,
  type AuditSeverity,
  type AuditTimelineEvent,
} from "../lib/auditTimeline";
import { Link } from "../../../shared/routing/router";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";

const familyClass: Record<AuditFamily, string> = {
  release_evidence: "border-emerald-200 bg-emerald-50 text-signal",
  deployment: "border-sky-200 bg-sky-50 text-sky-700",
  retraining: "border-amber-200 bg-amber-50 text-amber-700",
  security: "border-rose-200 bg-rose-50 text-risk",
  training: "border-indigo-200 bg-indigo-50 text-indigo-700",
  registry: "border-violet-200 bg-violet-50 text-violet-700",
  dataset: "border-teal-200 bg-teal-50 text-teal-700",
  monitoring: "border-cyan-200 bg-cyan-50 text-cyan-700",
  platform: "border-slate-200 bg-slate-50 text-ink",
};

const severityClass: Record<AuditSeverity, string> = {
  info: "border-slate-200 bg-slate-50 text-steel",
  success: "border-emerald-200 bg-emerald-50 text-signal",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-rose-200 bg-rose-50 text-risk",
};

export function OperationalAuditPage() {
  const [session, setSession] = useState(() => readStoredSession());
  const [activeFamily, setActiveFamily] = useState<AuditFamilyFilter>("all");
  const token = session?.accessToken ?? "";
  const auditQuery = useQuery({
    queryKey: ["operational-audit", token],
    queryFn: () => listAuditLog(token, { limit: 100 }),
    enabled: Boolean(token),
    retry: false,
  });
  const timeline = useMemo(
    () =>
      buildOperationalAuditTimeline(
        auditQuery.data?.items ?? [],
        releaseEvidenceAuditEvents,
      ),
    [auditQuery.data?.items],
  );
  const filteredTimeline = useMemo(
    () => filterAuditTimeline(timeline, activeFamily),
    [activeFamily, timeline],
  );
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const selectedEvent =
    filteredTimeline.find((event) => event.id === selectedEventId) ?? filteredTimeline[0];
  const stats = buildAuditFamilyStats(timeline);
  const apiEventCount = timeline.filter((event) => event.source === "api").length;
  const highImpactCount = timeline.filter(
    (event) =>
      event.family === "deployment" ||
      event.family === "retraining" ||
      event.severity === "danger",
  ).length;

  useEffect(
    () => subscribeToSessionChanges(() => setSession(readStoredSession())),
    [],
  );

  useEffect(() => {
    if (!selectedEvent || selectedEvent.id !== selectedEventId) {
      setSelectedEventId(selectedEvent?.id ?? null);
    }
  }, [selectedEvent, selectedEventId]);

  return (
    <>
      <PageHeader
        eyebrow="Governance"
        title="Operational Audit"
        description="Unified operator timeline for live platform audit events, release evidence annotations, and route-level follow-up across the ML control plane."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Timeline Events"
          value={String(timeline.length)}
          detail="live and release-evidence events"
        />
        <MetricCard
          label="Live Audit Events"
          value={String(apiEventCount)}
          detail={token ? "loaded from admin audit API" : "sign in to load API events"}
          tone={token ? "success" : "warning"}
        />
        <MetricCard
          label="Release Evidence"
          value={String(releaseEvidenceAuditEvents.length)}
          detail="CI and reviewer proof annotations"
          tone="success"
        />
        <MetricCard
          label="High Impact"
          value={String(highImpactCount)}
          detail="deployment, retraining, and incident-risk activity"
          tone={highImpactCount > 0 ? "warning" : "neutral"}
        />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        <DataPanel
          title="Audit Timeline"
          action={
            <button
              type="button"
              onClick={() => auditQuery.refetch()}
              disabled={!token || auditQuery.isFetching}
              className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-steel transition hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Refresh
            </button>
          }
        >
          <div className="grid gap-4">
            {!token ? (
              <StateMessage message="Sign in to load organization audit events. Release evidence annotations remain visible for local review." />
            ) : auditQuery.error ? (
              <StateMessage
                tone="danger"
                message="Audit API request failed. Release evidence annotations are still available."
              />
            ) : auditQuery.isFetching && apiEventCount === 0 ? (
              <StateMessage message="Loading organization audit events." />
            ) : null}

            <AuditFamilyFilters
              activeFamily={activeFamily}
              stats={stats}
              totalCount={timeline.length}
              onChange={setActiveFamily}
            />

            {filteredTimeline.length === 0 ? (
              <StateMessage message="No audit events match this family." />
            ) : (
              <div className="grid gap-3">
                {filteredTimeline.map((event) => (
                  <AuditTimelineRow
                    key={event.id}
                    event={event}
                    selected={event.id === selectedEvent?.id}
                    onSelect={() => setSelectedEventId(event.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </DataPanel>

        <AuditEventDetail event={selectedEvent} />
      </div>
    </>
  );
}

function AuditFamilyFilters({
  activeFamily,
  stats,
  totalCount,
  onChange,
}: {
  activeFamily: AuditFamilyFilter;
  stats: ReturnType<typeof buildAuditFamilyStats>;
  totalCount: number;
  onChange: (family: AuditFamilyFilter) => void;
}) {
  const filters: Array<{ family: AuditFamilyFilter; count: number }> = [
    { family: "all", count: totalCount },
    ...stats.map((stat) => ({ family: stat.family, count: stat.count })),
  ];

  return (
    <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-4">
      {filters.map((filter) => {
        const selected = filter.family === activeFamily;
        return (
          <button
            key={filter.family}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(filter.family)}
            className={`inline-flex h-9 items-center gap-2 rounded border px-3 text-xs font-semibold transition ${
              selected
                ? "border-ink bg-ink text-white"
                : "border-slate-200 bg-white text-steel hover:text-ink"
            }`}
          >
            {filter.family === "all" ? (
              <ClipboardList className="h-4 w-4" aria-hidden="true" />
            ) : (
              <AuditFamilyIcon family={filter.family} />
            )}
            {auditFamilyLabel(filter.family)}
            <span className="rounded bg-white/70 px-1.5 py-0.5 text-[11px] text-ink">
              {filter.count}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function AuditTimelineRow({
  event,
  selected,
  onSelect,
}: {
  event: AuditTimelineEvent;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={`Inspect ${event.title}`}
      onClick={onSelect}
      className={`grid min-h-[112px] w-full gap-3 rounded border p-3 text-left transition md:grid-cols-[140px_minmax(0,1fr)_170px] ${
        selected
          ? "border-ink bg-slate-50"
          : "border-slate-200 bg-white hover:border-slate-300"
      }`}
    >
      <div className="min-w-0">
        <div className="text-xs font-semibold uppercase text-steel">Time</div>
        <div className="mt-2 text-sm font-medium text-ink">
          {formatDateTime(event.createdAt)}
        </div>
        <div className="mt-2 text-xs text-steel">{event.source}</div>
      </div>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex h-7 items-center gap-1 rounded border px-2 text-xs font-semibold ${familyClass[event.family]}`}
          >
            <AuditFamilyIcon family={event.family} />
            {auditFamilyLabel(event.family)}
          </span>
          <span
            className={`inline-flex h-7 items-center rounded border px-2 text-xs font-semibold ${severityClass[event.severity]}`}
          >
            {event.severity}
          </span>
        </div>
        <div className="mt-3 break-words text-sm font-semibold text-ink">
          {event.title}
        </div>
        <p className="mt-2 text-sm leading-6 text-steel">{event.summary}</p>
      </div>

      <div className="min-w-0">
        <div className="text-xs font-semibold uppercase text-steel">Resource</div>
        <div className="mt-2 truncate text-sm font-medium text-ink">
          {event.resourceType}
        </div>
        <div className="mt-1 truncate text-xs text-steel">{event.resourceId}</div>
      </div>
    </button>
  );
}

function AuditEventDetail({ event }: { event: AuditTimelineEvent | undefined }) {
  if (!event) {
    return (
      <DataPanel title="Event Detail">
        <StateMessage message="Select an audit event to inspect metadata." />
      </DataPanel>
    );
  }

  return (
    <DataPanel
      title="Event Detail"
      action={
        <Link
          to={event.route}
          className="inline-flex h-8 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-semibold text-steel transition hover:text-ink"
        >
          <LinkIcon className="h-4 w-4" aria-hidden="true" />
          Open
        </Link>
      }
    >
      <div className="grid gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex h-8 w-8 items-center justify-center rounded border ${familyClass[event.family]}`}
            >
              <AuditFamilyIcon family={event.family} />
            </span>
            <div className="min-w-0">
              <div className="break-words text-sm font-semibold text-ink">
                {event.title}
              </div>
              <div className="mt-1 text-xs text-steel">{event.action}</div>
            </div>
          </div>
          <p className="mt-3 text-sm leading-6 text-steel">{event.summary}</p>
        </div>

        <dl className="grid gap-3">
          <DetailRow label="Time" value={formatDateTime(event.createdAt)} />
          <DetailRow label="Actor" value={event.actor} />
          <DetailRow label="Resource" value={event.resource} />
          <DetailRow label="Route" value={event.route} />
        </dl>

        <div className="border-t border-slate-200 pt-4">
          <div className="text-xs font-semibold uppercase text-steel">Metadata</div>
          <div className="mt-3 grid gap-2">
            {Object.entries(event.metadata).length === 0 ? (
              <div className="rounded bg-field px-3 py-2 text-xs text-steel">none</div>
            ) : (
              Object.entries(event.metadata).map(([key, value]) => (
                <div
                  key={key}
                  className="grid gap-1 rounded bg-field px-3 py-2 text-xs md:grid-cols-[128px_minmax(0,1fr)]"
                >
                  <div className="font-semibold text-steel">{key}</div>
                  <div className="break-words font-medium text-ink">
                    {formatMetadataValue(value)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </DataPanel>
  );
}

function AuditFamilyIcon({ family }: { family: AuditFamily }): ReactNode {
  const className = "h-4 w-4 shrink-0";
  if (family === "release_evidence") {
    return <FileCheck2 className={className} aria-hidden="true" />;
  }
  if (family === "deployment") {
    return <Rocket className={className} aria-hidden="true" />;
  }
  if (family === "retraining") {
    return <RefreshCw className={className} aria-hidden="true" />;
  }
  if (family === "security") {
    return <LockKeyhole className={className} aria-hidden="true" />;
  }
  if (family === "training") {
    return <Workflow className={className} aria-hidden="true" />;
  }
  if (family === "registry") {
    return <BrainCircuit className={className} aria-hidden="true" />;
  }
  if (family === "dataset") {
    return <Database className={className} aria-hidden="true" />;
  }
  if (family === "monitoring") {
    return <Gauge className={className} aria-hidden="true" />;
  }
  return <Activity className={className} aria-hidden="true" />;
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 rounded bg-field px-3 py-2">
      <dt className="text-xs font-semibold uppercase text-steel">{label}</dt>
      <dd className="break-words text-sm font-medium text-ink">{value}</dd>
    </div>
  );
}

function StateMessage({
  message,
  tone = "neutral",
}: {
  message: string;
  tone?: "neutral" | "danger";
}) {
  const className =
    tone === "danger"
      ? "rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk"
      : "rounded border border-slate-200 bg-cloud p-4 text-sm text-steel";
  const Icon = tone === "danger" ? AlertTriangle : ShieldCheck;
  return (
    <div className={className}>
      <div className="flex items-start gap-2">
        <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>{message}</span>
      </div>
    </div>
  );
}

function formatDateTime(value: string): string {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return "invalid date";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(timestamp));
}

function formatMetadataValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "none";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}
