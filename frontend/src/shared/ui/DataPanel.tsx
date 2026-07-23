import type { ReactNode } from "react";

type DataPanelProps = {
  title: string;
  action?: ReactNode;
  children: ReactNode;
};

export function DataPanel({ title, action, children }: DataPanelProps) {
  return (
    <section className="rounded border border-slate-200 bg-white shadow-panel">
      <div className="flex min-h-12 items-center justify-between border-b border-slate-200 px-4">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

