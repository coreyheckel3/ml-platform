type PageHeaderProps = {
  title: string;
  eyebrow: string;
  description: string;
};

export function PageHeader({ title, eyebrow, description }: PageHeaderProps) {
  return (
    <div className="mb-6">
      <div className="text-xs font-semibold uppercase text-signal">{eyebrow}</div>
      <h1 className="mt-1 text-2xl font-semibold text-ink">{title}</h1>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-steel">{description}</p>
    </div>
  );
}
