type MetricCardProps = {
  label: string;
  value: string;
  detail: string;
  tone?: "neutral" | "success" | "warning" | "danger";
};

const toneClass = {
  neutral: "text-ink",
  success: "text-signal",
  warning: "text-amber-600",
  danger: "text-risk"
};

export function MetricCard({ label, value, detail, tone = "neutral" }: MetricCardProps) {
  return (
    <div className="rounded border border-slate-200 bg-white p-4 shadow-panel">
      <div className="text-xs font-medium uppercase text-steel">{label}</div>
      <div className={`mt-2 text-2xl font-semibold ${toneClass[tone]}`}>{value}</div>
      <div className="mt-2 text-sm text-steel">{detail}</div>
    </div>
  );
}
