interface KpiProps {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "warn";
}

export function Kpi({ label, value, hint, tone = "default" }: KpiProps) {
  return (
    <div className={`kpi kpi-${tone}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {hint && <div className="kpi-hint">{hint}</div>}
    </div>
  );
}
