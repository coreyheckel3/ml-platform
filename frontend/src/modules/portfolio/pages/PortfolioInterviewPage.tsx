import {
  BadgeCheck,
  BookOpenCheck,
  BriefcaseBusiness,
  ClipboardCheck,
  ExternalLink,
  FileCheck2,
  GitBranch,
  MapPinned,
  Presentation,
  Rocket,
  ShieldCheck,
  SquareTerminal,
  Workflow,
} from "lucide-react";
import type { ReactNode } from "react";

import {
  architectureWalkthroughSteps,
  evidenceExplanations,
  interviewClaims,
  interviewQuestions,
  validationPaths,
  type InterviewEvidence,
} from "../data/interviewMode";
import { Link } from "../../../shared/routing/router";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";

const evidenceKindClass: Record<InterviewEvidence["kind"], string> = {
  code: "border-sky-200 bg-sky-50 text-sky-700",
  contract: "border-emerald-200 bg-emerald-50 text-signal",
  doc: "border-indigo-200 bg-indigo-50 text-indigo-700",
  route: "border-slate-200 bg-slate-50 text-ink",
  test: "border-amber-200 bg-amber-50 text-amber-700",
};

export function PortfolioInterviewPage() {
  return (
    <>
      <PageHeader
        eyebrow="Portfolio Review"
        title="Portfolio Interview Mode"
        description="A reviewer-facing control room that turns ForgeML architecture, ML lifecycle depth, operations evidence, and interview talking points into one validated walkthrough."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Portfolio Claims"
          value={String(interviewClaims.length)}
          detail="mapped to code, contracts, tests, and routes"
          tone="success"
        />
        <MetricCard
          label="Architecture Stages"
          value={String(architectureWalkthroughSteps.length)}
          detail="control plane, execution, serving, governance"
        />
        <MetricCard
          label="Validation Paths"
          value={String(validationPaths.length)}
          detail="local demo, browser, screenshots, CI contracts"
        />
        <MetricCard
          label="Interview Prompts"
          value={String(interviewQuestions.length)}
          detail="prepared anchors for ML, MLOps, and platform roles"
        />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <DataPanel
          title="Reviewer Dashboard"
          action={
            <StatusPill icon={<Presentation className="h-4 w-4" />} label="interview ready" />
          }
        >
          <div className="grid gap-3">
            {interviewClaims.map((claim) => (
              <article
                key={claim.id}
                className="rounded border border-slate-200 bg-white p-4"
              >
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-ink">{claim.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-steel">{claim.summary}</p>
                    <p className="mt-2 text-sm leading-6 text-ink">{claim.proof}</p>
                  </div>
                  <Link
                    to={claim.route}
                    aria-label={`Open ${claim.title}`}
                    className="inline-flex h-9 shrink-0 items-center justify-center gap-2 rounded border border-slate-200 px-3 text-sm font-semibold text-ink transition hover:border-signal hover:text-signal"
                  >
                    <ExternalLink className="h-4 w-4" aria-hidden="true" />
                    Open
                  </Link>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {claim.roleSignals.map((signal) => (
                    <span
                      key={signal}
                      className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-steel"
                    >
                      {signal}
                    </span>
                  ))}
                </div>
                <div className="mt-3 grid gap-2 md:grid-cols-3">
                  {claim.evidence.map((item) => (
                    <EvidenceChip key={`${claim.id}-${item.path}`} evidence={item} />
                  ))}
                </div>
              </article>
            ))}
          </div>
        </DataPanel>

        <DataPanel
          title="Interview Talk Track"
          action={
            <StatusPill
              icon={<BriefcaseBusiness className="h-4 w-4" />}
              label="role mapped"
            />
          }
        >
          <div className="grid gap-3">
            {interviewQuestions.map((item) => (
              <div key={item.question} className="border-b border-slate-100 pb-3 last:border-b-0">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded bg-ink text-white">
                    <BookOpenCheck className="h-4 w-4" aria-hidden="true" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-ink">{item.question}</h3>
                    <p className="mt-2 text-sm leading-6 text-steel">{item.answerAnchor}</p>
                    <Link
                      to={item.evidenceRoute}
                      className="mt-2 inline-flex items-center gap-2 text-sm font-semibold text-signal"
                    >
                      Evidence route
                      <ExternalLink className="h-4 w-4" aria-hidden="true" />
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <DataPanel
          title="Architecture Walkthrough"
          action={
            <StatusPill icon={<GitBranch className="h-4 w-4" />} label="modular monolith" />
          }
        >
          <div className="grid gap-3">
            {architectureWalkthroughSteps.map((step) => (
              <div key={step.stage} className="rounded border border-slate-200 bg-cloud p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-white text-signal">
                    <MapPinned className="h-4 w-4" aria-hidden="true" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-ink">{step.stage}</h3>
                    <p className="mt-2 text-sm leading-6 text-steel">
                      {step.moduleBoundary}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-ink">{step.staffSignal}</p>
                    <p className="mt-2 text-sm leading-6 text-steel">
                      {step.extractionPath}
                    </p>
                    <code className="mt-3 block overflow-x-auto rounded bg-white px-3 py-2 text-xs text-ink">
                      {step.evidencePath}
                    </code>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </DataPanel>

        <DataPanel
          title="Evidence Explanations"
          action={
            <StatusPill icon={<ClipboardCheck className="h-4 w-4" />} label="claim mapped" />
          }
        >
          <div className="grid gap-4 md:grid-cols-2">
            {evidenceExplanations.map((item) => (
              <section key={item.title} className="border-l-2 border-signal pl-4">
                <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                <p className="mt-2 text-sm leading-6 text-steel">{item.whyItMatters}</p>
                <p className="mt-2 text-sm leading-6 text-ink">{item.reviewerMove}</p>
                <code className="mt-3 block overflow-x-auto rounded bg-slate-100 px-3 py-2 text-xs text-ink">
                  {item.evidencePath}
                </code>
              </section>
            ))}
          </div>
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <DataPanel
          title="Validation Paths"
          action={
            <StatusPill icon={<ShieldCheck className="h-4 w-4" />} label="CI enforced" />
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-left text-sm">
              <thead className="text-xs uppercase text-steel">
                <tr>
                  <th className="py-2">Path</th>
                  <th>Command</th>
                  <th>Expected Signal</th>
                  <th>Route</th>
                </tr>
              </thead>
              <tbody>
                {validationPaths.map((path) => (
                  <tr key={path.command} className="border-t border-slate-100">
                    <td className="py-3 font-medium text-ink">{path.label}</td>
                    <td>
                      <code className="rounded bg-ink px-2 py-1 text-xs text-white">
                        {path.command}
                      </code>
                    </td>
                    <td className="max-w-[320px] text-steel">{path.expectedSignal}</td>
                    <td>
                      <Link
                        to={path.route}
                        className="inline-flex items-center gap-2 text-sm font-semibold text-signal"
                      >
                        {path.route}
                        <ExternalLink className="h-4 w-4" aria-hidden="true" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DataPanel>

        <DataPanel
          title="Portfolio Evidence Contract"
          action={
            <StatusPill icon={<FileCheck2 className="h-4 w-4" />} label="release artifact" />
          }
        >
          <div className="grid gap-3">
            <SignalRow
              icon={<BadgeCheck className="h-4 w-4" />}
              label="Contract"
              value="contracts/ops/portfolio-interview-mode.v1.json"
            />
            <SignalRow
              icon={<BookOpenCheck className="h-4 w-4" />}
              label="Reviewer doc"
              value="docs/portfolio/interview-mode.md"
            />
            <SignalRow
              icon={<Workflow className="h-4 w-4" />}
              label="Quality gate"
              value="portfolio_interview_mode_contract"
            />
            <SignalRow
              icon={<Rocket className="h-4 w-4" />}
              label="Demo screenshot"
              value="11-portfolio-interview-mode.png"
            />
            <SignalRow
              icon={<SquareTerminal className="h-4 w-4" />}
              label="Operator path"
              value="make demo-walkthrough"
            />
          </div>
        </DataPanel>
      </div>
    </>
  );
}

function EvidenceChip({ evidence }: { evidence: InterviewEvidence }) {
  return (
    <div className="min-w-0 rounded border border-slate-200 bg-slate-50 p-2">
      <div
        className={[
          "inline-flex rounded border px-2 py-0.5 text-[11px] font-semibold uppercase",
          evidenceKindClass[evidence.kind],
        ].join(" ")}
      >
        {evidence.kind}
      </div>
      <div className="mt-2 text-xs font-semibold text-ink">{evidence.label}</div>
      <code className="mt-1 block truncate text-xs text-steel">{evidence.path}</code>
    </div>
  );
}

function StatusPill({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <span className="inline-flex h-8 items-center gap-2 rounded border border-emerald-200 bg-emerald-50 px-3 text-xs font-semibold text-signal">
      {icon}
      {label}
    </span>
  );
}

function SignalRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded border border-slate-200 bg-cloud p-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-white text-signal">
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-xs font-semibold uppercase text-steel">{label}</div>
        <code className="mt-1 block break-all text-sm font-semibold text-ink">{value}</code>
      </div>
    </div>
  );
}
