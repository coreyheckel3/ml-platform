import { DataPanel } from "../../../shared/ui/DataPanel";
import { PageHeader } from "../../../shared/ui/PageHeader";

export function SettingsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Settings"
        description="Members, roles, service accounts, API keys, notification channels, retraining policy, and audit access."
      />
      <DataPanel title="Security Defaults">
        <div className="grid gap-3 text-sm md:grid-cols-2">
          <div className="rounded border border-slate-200 p-3">JWT access tokens: 15 minutes</div>
          <div className="rounded border border-slate-200 p-3">RBAC: organization and project scopes</div>
          <div className="rounded border border-slate-200 p-3">API keys: hashed at rest</div>
          <div className="rounded border border-slate-200 p-3">Audit log: security and model lifecycle events</div>
        </div>
      </DataPanel>
    </>
  );
}

