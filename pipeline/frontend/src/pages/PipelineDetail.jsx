import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Download } from "lucide-react";
import api, { API_BASE } from "@/lib/api";
import PipelineResult from "@/components/PipelineResult";

export default function PipelineDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    api
      .get(`/pipeline/${id}`)
      .then((r) => alive && setData(r.data))
      .catch(() => toast.error("Pipeline não encontrado"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-7xl px-8 py-10 text-sm text-muted-foreground">Carregando…</div>
    );
  }
  if (!data) return null;

  return (
    <div className="max-w-7xl px-8 py-10">
      <button
        onClick={() => nav("/questoes")}
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6"
        data-testid="back-to-list"
      >
        <ArrowLeft className="h-4 w-4" /> Voltar para lista
      </button>

      {/* Artefatos */}
      <div className="mb-6 border border-border bg-white">
        <div className="px-5 py-3 border-b border-border overline text-muted-foreground">
          Artefatos armazenados
        </div>
        <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
          <ArtifactLink id={id} kind="original" label="Questão original" data={data} />
          <ArtifactLink id={id} kind="extraction" label="Extração estruturada" data={data} />
          <ArtifactLink id={id} kind="pipeline" label="Pipeline cognitivo" data={data} />
        </div>
      </div>

      <PipelineResult data={data} onReset={() => nav("/questoes")} onUpdate={setData} />
    </div>
  );
}

function ArtifactLink({ id, kind, label, data }) {
  const originals = data?.artifacts?.originals || [];
  if (kind === "original" && originals.length > 1) {
    return (
      <div className="border border-border p-3">
        <div className="overline text-muted-foreground mb-2">{label}</div>
        <ul className="space-y-1">
          {originals.map((o, i) => (
            <li key={o.path}>
              <a
                href={`${API_BASE}/pipeline/${id}/artifact/original?index=${i}`}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 text-sm text-primary underline"
              >
                <Download className="h-3 w-3" /> {o.filename}
              </a>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  return (
    <a
      href={`${API_BASE}/pipeline/${id}/artifact/${kind}`}
      target="_blank"
      rel="noreferrer"
      className="border border-border p-4 bg-white hover:bg-foreground hover:text-white transition-colors"
      data-testid={`artifact-${kind}`}
    >
      <div className="overline text-muted-foreground">{label}</div>
      <div className="mt-2 flex items-center gap-2 text-sm font-medium">
        <Download className="h-4 w-4" /> Baixar
      </div>
    </a>
  );
}
