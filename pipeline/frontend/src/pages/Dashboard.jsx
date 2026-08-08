import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Database, Sparkles, ListTree, Cpu } from "lucide-react";
import api from "@/lib/api";

const disciplineColor = (i) =>
  ["#002FA7", "#059669", "#E11D48", "#09090B", "#52525B", "#7C3AED", "#B45309"][i % 7];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    api
      .get("/stats")
      .then((r) => alive && setStats(r.data))
      .catch(() => alive && setStats({ total_pipelines: 0, ontology: null, top_disciplinas: [] }))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const maxCount = Math.max(1, ...(stats?.top_disciplinas || []).map((d) => d.count));

  return (
    <div className="max-w-6xl px-8 py-10" data-testid="dashboard-page">
      <div className="overline text-muted-foreground">Módulo</div>
      <h1 className="text-5xl font-black tracking-tight mt-1">
        Anotador Cognitivo <span className="text-primary">Sapiens</span>
      </h1>
      <p className="mt-4 max-w-2xl text-muted-foreground leading-relaxed">
        Pipeline automático de anotação cognitiva para questões de vestibulares.
        Envie uma ontologia, envie a prova, obtenha um JSON estruturado com
        domínios, competências, processos cognitivos, distratores e justificativas
        auditáveis.
      </p>

      {/* KPIs */}
      <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-0 border border-border bg-white">
        <div className="p-6 border-b md:border-b-0 md:border-r border-border">
          <div className="overline text-muted-foreground">Questões processadas</div>
          <div className="mt-2 text-4xl font-black" data-testid="stat-total">
            {loading ? "…" : stats?.total_pipelines ?? 0}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">pipelines armazenados</div>
        </div>
        <div className="p-6 border-b md:border-b-0 md:border-r border-border">
          <div className="overline text-muted-foreground">Ontologia ativa</div>
          <div
            className="mt-2 text-lg font-semibold font-mono truncate"
            data-testid="stat-ontology-version"
          >
            {stats?.ontology?.version ?? "—"}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {stats?.ontology?.imported_at
              ? new Date(stats.ontology.imported_at).toLocaleString("pt-BR")
              : "Nenhuma"}
          </div>
        </div>
        <div className="p-6">
          <div className="overline text-muted-foreground">Elementos cognitivos</div>
          <div className="mt-2 text-4xl font-black" data-testid="stat-elements">
            {stats?.ontology
              ? Object.values(stats.ontology.counts).reduce((a, b) => a + b, 0)
              : 0}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            domínios · competências · processos · erros · intervenções
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-4">
        <QuickCard
          to="/ontologia"
          icon={Network}
          title="Ontologia Cognitiva"
          description="Ver, importar ou substituir a ontologia usada pelo motor."
          testId="quick-ontologia"
        />
        <QuickCard
          to="/gerador"
          icon={Sparkles}
          title="Gerar novo pipeline"
          description="Envie PDF ou imagens de uma questão e gere o JSON cognitivo."
          testId="quick-gerador"
        />
        <QuickCard
          to="/questoes"
          icon={ListTree}
          title="Questões processadas"
          description="Busque, filtre e exporte pipelines armazenados."
          testId="quick-questoes"
        />
      </div>

      {/* Top disciplinas */}
      <div className="mt-10 border border-border bg-white">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <div className="overline text-muted-foreground">Distribuição</div>
            <h2 className="text-lg font-bold">Top disciplinas</h2>
          </div>
          <Database className="h-4 w-4 text-muted-foreground" />
        </div>
        {stats?.top_disciplinas?.length ? (
          <ul>
            {stats.top_disciplinas.map((d, i) => (
              <li
                key={d.disciplina}
                className="px-6 py-3 border-b border-border last:border-b-0 flex items-center gap-4"
              >
                <span className="font-mono text-xs text-muted-foreground w-6">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="flex-1 font-medium">{d.disciplina}</span>
                <div className="flex-1 h-2 bg-secondary">
                  <div
                    className="h-full"
                    style={{
                      width: `${(d.count / maxCount) * 100}%`,
                      backgroundColor: disciplineColor(i),
                    }}
                  />
                </div>
                <span className="font-mono text-sm w-10 text-right">{d.count}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="px-6 py-10 text-sm text-muted-foreground flex items-center gap-3">
            <Cpu className="h-4 w-4" />
            Nenhuma questão processada ainda. Vá para o Gerador de Pipeline.
          </div>
        )}
      </div>
    </div>
  );
}

function Network(props) {
  // avoid double import from lucide; alias
  const { className = "" } = props;
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <circle cx="12" cy="4" r="2" />
      <circle cx="4" cy="20" r="2" />
      <circle cx="20" cy="20" r="2" />
      <path d="M12 6v6M6 20l6-8 6 8" />
    </svg>
  );
}

function QuickCard({ to, icon: Icon, title, description, testId }) {
  return (
    <Link
      to={to}
      data-testid={testId}
      className="group block bg-white border border-border p-6 hover:bg-foreground hover:text-white transition-colors"
    >
      <Icon className="h-5 w-5" />
      <div className="mt-6 text-lg font-bold">{title}</div>
      <div className="mt-1 text-sm text-muted-foreground group-hover:text-white/70">
        {description}
      </div>
      <div className="mt-6 flex items-center gap-2 text-sm font-medium">
        Abrir <ArrowRight className="h-4 w-4" />
      </div>
    </Link>
  );
}
