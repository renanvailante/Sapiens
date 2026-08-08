import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { toast } from "sonner";
import { Upload, Trash2, ChevronDown, ChevronRight, ShieldCheck } from "lucide-react";

const SAMPLE = `{
  "schema_version": "1.0",
  "item": {
    "id": "ITEM-ENEM-2023-MAT-137",
    "fonte": { "banca": "ENEM", "ano": 2023, "caderno": "Azul", "numero": 137 },
    "disciplina": "Matemática",
    "tema_objetivo": "Razão e proporcionalidade",
    "conteudo_curricular": ["Grandezas proporcionais"],
    "enunciado": "...",
    "alternativas": [
      {"id":"A","texto":"..."},{"id":"B","texto":"..."},{"id":"C","texto":"..."},
      {"id":"D","texto":"..."},{"id":"E","texto":"..."}
    ],
    "gabarito": "D"
  },
  "estrutura_cognitiva": {
    "nivel_abstracao": "semi_abstrato",
    "carga_cognitiva": "media",
    "dificuldade_global": 0.54,
    "tipo_raciocinio_predominante": ["quantitativo","proporcional"],
    "operacoes_cognitivas": ["identificar","comparar","calcular","inferir"]
  },
  "processos_ativados": [
    {"cognitive_process_id":"RQ-PROP-003","papel":"nuclear","prioridade":1,
     "peso_ativacao":0.91,"confianca":0.96,"dificuldade_local":0.38,
     "evidencias":["necessidade de escalonamento proporcional"]}
  ],
  "analise_distratores": [
    {"alternativa":"A","error_type_id":7,"cognitive_process_falhou":["RQ-PROP-003"],
     "explicacao":"Aluno não escalou a proporção."}
  ],
  "caracteristicas_item": {
    "possui_texto": true, "necessita_calculo": true, "contexto_cotidiano": true
  },
  "pedagogia": {
    "principal_intervencao": {"cognitive_process_id":"RQ-PROP-003","tipo":"feedback"},
    "explicacao_resolucao": "...",
    "misconceptions": ["Confusão entre razão e diferença"]
  },
  "qualidade_anotacao": {
    "confianca_global": 0.92, "revisado_humano": true, "revisor": "Claude", "data": "2026-07-09"
  }
}`;

function AnnotationRow({ ann, onDelete }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-white border border-zinc-200 rounded-2xl" data-testid={`ann-row-${ann.item_id}`}>
      <div className="p-4 flex items-center gap-4">
        <button onClick={() => setOpen(o => !o)} className="p-1 hover:bg-zinc-100 rounded" data-testid={`ann-toggle-${ann.item_id}`}>
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-zinc-500">
            {ann.banca} · {ann.ano} · {ann.caderno} · Q{ann.numero} · v{ann.schema_version}
          </div>
          <div className="mt-1 font-display font-semibold text-base text-zinc-900 truncate">
            {ann.item_id} <span className="text-zinc-400 font-normal">— {ann.disciplina}</span>
          </div>
        </div>
        <div className="text-xs text-zinc-500 font-mono-alt">
          {(ann.payload?.processos_ativados || []).length} proc.
        </div>
        <button onClick={() => onDelete(ann)} className="p-2 rounded-full hover:bg-rose-50 text-rose-600" data-testid={`ann-delete-${ann.item_id}`}>
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
      {open && (
        <pre className="border-t border-zinc-100 px-4 py-3 text-[11px] font-mono-alt overflow-auto max-h-96 whitespace-pre-wrap text-zinc-700">
          {JSON.stringify(ann.payload, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default function AdminAnnotations() {
  const [raw, setRaw] = useState("");
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState({ banca: "", ano: "", disciplina: "" });

  const load = async () => {
    const params = {};
    if (filter.banca) params.banca = filter.banca;
    if (filter.ano) params.ano = Number(filter.ano);
    if (filter.disciplina) params.disciplina = filter.disciplina;
    const { data } = await api.get("/annotations", { params });
    setItems(data.items);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const submit = async () => {
    if (!raw.trim()) return toast.error("Cole um JSON de anotação.");
    setBusy(true);
    try {
      let parsed;
      try { parsed = JSON.parse(raw); }
      catch { toast.error("JSON inválido — verifique a sintaxe."); setBusy(false); return; }

      if (Array.isArray(parsed) || (parsed && Array.isArray(parsed.items))) {
        const arr = Array.isArray(parsed) ? parsed : parsed.items;
        const { data } = await api.post("/admin/annotations/bulk", { items: arr });
        if (data.errors?.length) {
          toast.error(`${data.imported} importadas, ${data.errors.length} com erro.`);
        } else {
          toast.success(`${data.imported} anotações importadas.`);
        }
      } else {
        await api.post("/admin/annotations", parsed);
        toast.success(`Anotação ${parsed.item?.id || ""} armazenada.`);
      }
      setRaw("");
      load();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Falha na validação — verifique o schema.");
    } finally { setBusy(false); }
  };

  const remove = async (ann) => {
    if (!window.confirm(`Excluir anotação ${ann.item_id}?`)) return;
    await api.delete(`/admin/annotations/${encodeURIComponent(ann.item_id)}`);
    load();
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-5xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Admin · Anotações cognitivas</div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-zinc-950" data-testid="ann-admin-title">
          Importar anotação cognitiva
        </h1>
        <p className="mt-3 text-zinc-500 max-w-2xl">
          Cole o JSON gerado pela IA anotadora. O Sapiens valida a estrutura mínima, armazena o payload
          <b> verbatim </b>e disponibiliza a leitura para todas as features (perfil cognitivo, diagnóstico por processos, plano de estudos, feed adaptativo).
        </p>
        <p className="mt-2 text-xs text-zinc-500 flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-emerald-500" />
          Regra: nunca alteramos, inferimos ou recomputamos os campos anotados. Schema é versionado por <code className="font-mono-alt">schema_version</code>.
        </p>

        <textarea value={raw} onChange={e => setRaw(e.target.value)} placeholder={SAMPLE}
          className="mt-6 w-full h-[420px] font-mono-alt text-xs border border-zinc-200 rounded-2xl p-4 focus:border-zinc-900 outline-none"
          data-testid="ann-admin-paste" />

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button disabled={busy} onClick={submit}
            className="pill inline-flex items-center gap-2 bg-zinc-950 hover:bg-zinc-800 disabled:opacity-60 text-white px-6 py-3 rounded-full text-sm font-medium"
            data-testid="ann-admin-submit">
            <Upload className="w-4 h-4" /> {busy ? "Validando..." : "Ingerir JSON"}
          </button>
          <span className="text-xs text-zinc-500">Aceita objeto único, array `[...]` ou envelope `{`{items: [...]}`}`</span>
        </div>

        {/* Filters + list */}
        <div className="mt-12">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <div className="text-[10px] font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Banca</div>
              <input value={filter.banca} onChange={e => setFilter(f => ({ ...f, banca: e.target.value }))}
                className="border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900" data-testid="ann-filter-banca" />
            </div>
            <div>
              <div className="text-[10px] font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Ano</div>
              <input value={filter.ano} onChange={e => setFilter(f => ({ ...f, ano: e.target.value }))}
                className="w-24 border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900" data-testid="ann-filter-ano" />
            </div>
            <div>
              <div className="text-[10px] font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Disciplina</div>
              <input value={filter.disciplina} onChange={e => setFilter(f => ({ ...f, disciplina: e.target.value }))}
                className="border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900" data-testid="ann-filter-disciplina" />
            </div>
            <button onClick={load} className="pill border border-zinc-200 hover:bg-zinc-50 px-4 py-2 rounded-full text-sm font-medium" data-testid="ann-filter-apply">
              Filtrar
            </button>
          </div>

          <div className="mt-4 font-display font-bold text-xl tracking-tight text-zinc-950">
            Anotações no banco ({items.length})
          </div>
          <div className="mt-3 space-y-2">
            {items.length === 0 && (
              <div className="bg-white border border-zinc-200 rounded-2xl p-8 text-zinc-500 text-sm">
                Nenhuma anotação ainda. Cole o primeiro JSON acima.
              </div>
            )}
            {items.map(a => <AnnotationRow key={a.item_id} ann={a} onDelete={remove} />)}
          </div>
        </div>
      </div>
    </div>
  );
}
