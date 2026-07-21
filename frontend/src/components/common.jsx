export function SemDado({ label = "Sem dado" }) {
  return <span className="sem-dado" data-testid="sem-dado">{label}</span>;
}

export function formatPct(v) {
  if (v == null || Number.isNaN(v)) return null;
  return (v * 100).toFixed(1) + "%";
}

export function heatClass(v) {
  if (v == null) return "";
  if (v < 0.2) return "heat-1";
  if (v < 0.4) return "heat-2";
  if (v < 0.6) return "heat-3";
  if (v < 0.8) return "heat-4";
  return "heat-5";
}

export function Panel({ title, subtitle, right, children, testid }) {
  return (
    <section className="border border-border bg-white" data-testid={testid}>
      <header className="flex items-start justify-between border-b border-border px-4 py-3">
        <div>
          <h2 className="text-base tracking-tight">{title}</h2>
          {subtitle && (
            <div className="text-xs font-mono text-muted-foreground uppercase tracking-wider mt-0.5">
              {subtitle}
            </div>
          )}
        </div>
        {right}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

export function CalcBadge() {
  return (
    <span
      className="inline-block text-[10px] font-mono uppercase tracking-widest px-2 py-0.5 border border-border text-muted-foreground bg-[hsl(0_0%_98%)]"
      title="Métrica derivada apenas de agregações permitidas (soma/média/contagem/percentual) sobre os dados importados."
    >
      Calculado pelo Dashboard
    </span>
  );
}

export function StatCard({ label, value, testid }) {
  const isEmpty = value == null || value === "";
  return (
    <div className="border border-border p-4 bg-white" data-testid={testid}>
      <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-2xl tabular-nums" style={{ fontFamily: 'Chivo, sans-serif' }}>
        {isEmpty ? <SemDado /> : value}
      </div>
    </div>
  );
}

export function EmptyState({ title = "Sem dado", hint }) {
  return (
    <div className="border border-dashed border-border p-12 text-center bg-[hsl(0_0%_98%)]">
      <div className="text-sm font-mono uppercase tracking-widest text-muted-foreground">
        {title}
      </div>
      {hint && <div className="mt-2 text-sm text-muted-foreground">{hint}</div>}
    </div>
  );
}
