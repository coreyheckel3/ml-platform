import { useQuery } from "@tanstack/react-query";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import { listAlertEvents, listAlertRules } from "../api/alerts";

export function AlertsPage() {
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadAlerts = Boolean(token && projectId);
  const rulesQuery = useQuery({
    queryKey: ["alert-rules", projectId],
    queryFn: () => listAlertRules(projectId ?? "", token ?? ""),
    enabled: canLoadAlerts
  });
  const eventsQuery = useQuery({
    queryKey: ["alert-events", projectId],
    queryFn: () => listAlertEvents(projectId ?? "", token ?? ""),
    enabled: canLoadAlerts
  });
  const rules = rulesQuery.data?.items ?? [];
  const events = eventsQuery.data?.items ?? [];
  const openEvents = events.filter((event) => event.status === "open");
  const criticalEvents = events.filter((event) => event.severity === "critical");

  return (
    <>
      <PageHeader
        eyebrow="Operations"
        title="Alerts"
        description="Alert rules, alert events, severity, acknowledgement, resolution, and runbook routing."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Rules" value={String(rules.length)} detail="configured policies" />
        <MetricCard
          label="Enabled"
          value={String(rules.filter((rule) => rule.enabled).length)}
          detail="actively evaluated"
          tone="success"
        />
        <MetricCard
          label="Open"
          value={String(openEvents.length)}
          detail="active incidents"
          tone={openEvents.length > 0 ? "warning" : "success"}
        />
        <MetricCard
          label="Critical"
          value={String(criticalEvents.length)}
          detail="highest severity"
          tone={criticalEvents.length > 0 ? "danger" : "success"}
        />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <DataPanel title="Alert Events">
          {!canLoadAlerts ? (
            <StateMessage message="No project context is selected." />
          ) : eventsQuery.error ? (
            <StateMessage message="Alert event request failed." tone="danger" />
          ) : events.length === 0 ? (
            <StateMessage
              message={
                eventsQuery.isFetching
                  ? "Loading alert events."
                  : "No alert events have been recorded."
              }
            />
          ) : (
            <div className="space-y-3">
              {events.slice(0, 6).map((event) => (
                <div key={event.id} className={eventClassName(event.severity)}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{event.message}</div>
                      <div className="mt-1 text-xs">
                        observed {event.observed_value.toFixed(4)} / threshold{" "}
                        {event.threshold.toFixed(4)}
                      </div>
                    </div>
                    <span className="rounded bg-white px-2 py-1 text-xs font-medium">
                      {event.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DataPanel>

        <DataPanel title="Alert Rules">
          {!canLoadAlerts ? (
            <StateMessage message="No project context is selected." />
          ) : rulesQuery.error ? (
            <StateMessage message="Alert rule request failed." tone="danger" />
          ) : rules.length === 0 ? (
            <StateMessage
              message={
                rulesQuery.isFetching ? "Loading alert rules." : "No alert rules configured."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Rule</th>
                    <th>Metric</th>
                    <th>Condition</th>
                    <th>Severity</th>
                    <th>State</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.id} className="border-t border-slate-100">
                      <td className="py-3">
                        <div className="font-medium">{rule.name}</div>
                        <div className="text-xs text-steel">{rule.description || rule.slug}</div>
                      </td>
                      <td>{formatMetric(rule.metric)}</td>
                      <td>
                        {rule.operator} {rule.threshold}
                      </td>
                      <td>{rule.severity}</td>
                      <td>{rule.enabled ? "enabled" : "disabled"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>
      </div>
    </>
  );
}

function StateMessage({
  message,
  tone = "neutral"
}: {
  message: string;
  tone?: "neutral" | "danger";
}) {
  const className =
    tone === "danger"
      ? "rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk"
      : "rounded border border-slate-200 bg-cloud p-4 text-sm text-steel";
  return <div className={className}>{message}</div>;
}

function eventClassName(severity: string): string {
  if (severity === "critical") {
    return "rounded border border-rose-200 bg-rose-50 p-3 text-sm text-risk";
  }
  return "rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800";
}

function formatMetric(metric: string): string {
  return metric.replaceAll("_", " ");
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
