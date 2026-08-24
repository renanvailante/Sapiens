import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { toast } from "sonner";
import { Upload, Trash2, ChevronDown, ChevronRight, ShieldCheck } from "lucide-react";

// Exemplo no contrato canônico — Schema Sapiens 2.2.
//
// O exemplo anterior estava no formato legado, com três problemas que o
// tornavam perigoso como modelo a copiar:
//   * "error_type_id": 7 — inteiro. Os tipos de erro do White Paper 1.0 são
//     numerados de 1 a 13 e formam conjunto DISJUNTO dos ERR-01..ERR-13 do
//     catálogo vigente. É a colisão NS-1, classificada BLOQUEANTE: um `7`
//     ingerido e lido como ERR-07 produz diagnóstico plausível e errado.
//   * "RQ-PROP-003" — identificador da geração G0, que não existe no catálogo.
//   * ausência de "ontology_version" — sem ela a anotação é indatável.
//
// `dominios` e `competencias` não aparecem aqui de propósito: são DERIVADOS dos
// processos pelo servidor (Constituição §4.4). Enviá-los divergentes é erro de
// integridade; não enviá-los é o caminho normal.
const SAMPLE = `{
  "schema_version": "2.2",
  "ontology_version": "1.4.1",
  "item_id": "ITEM-INEP-2023-ENEMCAD01-Q137",
  "fonte": {
    "banca": "INEP", "ano": 2023, "prova": "ENEM-CAD01", "numero": 137,
    "disciplina": "Matemática", "tema": "Razão e proporcionalidade"
  },
  "questao": {
    "enunciado": "...",
    "alternativas": [
      {"letra":"A","texto":"...","correta":false},
      {"letra":"B","texto":"...","correta":false},
      {"letra":"C","texto":"...","correta":false},
      {"letra":"D","texto":"...","correta":true},
      {"letra":"E","texto":"...","correta":false}
    ],
    "recursos": {}
  },
  "estrutura_cognitiva": {
    "processos": [
      {
        "id": "PROC-QUANT-02",
        "papel": "nuclear",
        "peso_no_item": 1.0,
        "confianca": "alta",
        "habilidades": [
          {"id":"HAB-03","peso_no_processo":1.0,"confianca":"alta","aproximado":false}
        ],
        "evidencias": {"trechos":["mantendo a mesma taxa"],"figuras":[]},
        "justificativa": "A resposta depende de escalonar uma relação proporcional; o cenário é irrelevante."
      }
    ]
  },
  "distratores": [
    {
      "alternativa": "A",
      "erros_esperados": [
        {"ordem":1,"erro":"ERR-05","processo_afetado":"PROC-QUANT-02","confianca":"alta","mecanismo":"MEC-01"}
      ],
      "plausibilidade": {"valor":"alta"},
      "explicacao": "Trata a relação como diferença, não como razão."
    }
  ],
  "intervencoes": [
    {"id":"INT-03","gatilho":{"processo":"PROC-QUANT-02","erro":"ERR-05"},"acao":"Prática guiada de relações proporcionais."}
  ],
  "qualidade": {
    "confianca_global": "alta",
    "revisado": true,
    "revisor": "nome-ou-id-do-revisor",
    "data_anotacao": "2026-08-21T12:00:00Z"
  }
}`;

function AnnotationRow({ ann, onDelete }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card-sapiens rounded-2xl" data-testid={`ann-row-${ann.item_id}`}>
      <div className="p-4 flex items-center gap-4">
        <button onClick={() => setOpen(o => !o)} className="p-1 hover:bg-zinc-100 rounded" data-testid={`ann-toggle-${ann.item_id}`}>
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-zinc-500">
            {ann.banca} · {ann.ano} · {ann.prova} · Q{ann.numero} · schema v{ann.schema_version} · onto {ann.ontology_version}
          </div>
          <div className="mt-1 font-display font-semibold text-base text-zinc-900 truncate">
            {ann.item_id} <span className="text-zinc-400 font-normal">— {ann.disciplina}</span>
          </div>
          {ann.validacao?.valid === false && (
            <div className="mt-1 text-xs text-rose-700" data-testid={`ann-invalid-${ann.item_id}`}>
              {ann.validacao.errors.length} violação(ões) do contrato — armazenada para revisão,
              não pode alimentar o estado de nenhum aluno.
            </div>
          )}
        </div>
        <div className="text-xs text-zinc-500 font-mono-alt">
          {(ann.payload?.estrutura_cognitiva?.processos || []).length} proc.
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
        const invalidas = data.invalidos_contra_o_catalogo?.length || 0;
        if (data.errors?.length) {
          toast.error(`${data.imported} importadas, ${data.errors.length} rejeitadas por forma.`);
        } else if (invalidas) {
          // Armazenadas, mas fora do contrato: precisam ficar visíveis para
          // revisão humana em vez de sumir num erro de ingestão.
          toast.warning(`${data.imported} importadas · ${invalidas} violam o contrato e aguardam revisão.`);
        } else {
          toast.success(`${data.imported} anotações importadas.`);
        }
      } else {
        const { data } = await api.post("/admin/annotations", parsed);
        if (data.validacao?.valid === false) {
          toast.warning(
            `${data.item_id} armazenada com ${data.validacao.errors.length} violação(ões) do contrato — revise antes de usar.`
          );
        } else {
          toast.success(`Anotação ${data.item_id || ""} armazenada.`);
        }
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
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-3">Admin · Anotações cognitivas</div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-white" data-testid="ann-admin-title">
          Importar anotação cognitiva
        </h1>
        <p className="mt-3 text-white/60 max-w-2xl">
          Cole o JSON gerado pela IA anotadora. O Sapiens valida a estrutura mínima, armazena o payload
          <b> verbatim </b>e disponibiliza a leitura para todas as features (perfil cognitivo, diagnóstico por processos, plano de estudos, feed adaptativo).
        </p>
        <p className="mt-2 text-xs text-white/50 flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-sapiens-accent" />
          Regra: nunca alteramos, inferimos ou recomputamos os campos anotados. Schema é versionado por <code className="font-mono-alt">schema_version</code>.
        </p>

        <div className="mt-6 card-sapiens rounded-2xl p-6">
          <textarea value={raw} onChange={e => setRaw(e.target.value)} placeholder={SAMPLE}
            className="w-full h-[420px] font-mono-alt text-xs border border-zinc-200 rounded-2xl p-4 focus:border-sapiens-accent outline-none"
            data-testid="ann-admin-paste" />

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button disabled={busy} onClick={submit}
              className="pill inline-flex items-center gap-2 btn-sapiens disabled:opacity-60 px-6 py-3 rounded-full text-sm font-medium"
              data-testid="ann-admin-submit">
              <Upload className="w-4 h-4" /> {busy ? "Validando..." : "Ingerir JSON"}
            </button>
            <span className="text-xs text-zinc-500">Aceita objeto único, array `[...]` ou envelope `{`{items: [...]}`}`</span>
          </div>
        </div>

        {/* Filters + list */}
        <div className="mt-12">
          <div className="card-sapiens rounded-2xl p-5 flex flex-wrap items-end gap-3">
            <div>
              <div className="text-[10px] font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Banca</div>
              <input value={filter.banca} onChange={e => setFilter(f => ({ ...f, banca: e.target.value }))}
                className="border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-sapiens-accent" data-testid="ann-filter-banca" />
            </div>
            <div>
              <div className="text-[10px] font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Ano</div>
              <input value={filter.ano} onChange={e => setFilter(f => ({ ...f, ano: e.target.value }))}
                className="w-24 border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-sapiens-accent" data-testid="ann-filter-ano" />
            </div>
            <div>
              <div className="text-[10px] font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Disciplina</div>
              <input value={filter.disciplina} onChange={e => setFilter(f => ({ ...f, disciplina: e.target.value }))}
                className="border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-sapiens-accent" data-testid="ann-filter-disciplina" />
            </div>
            <button onClick={load} className="pill border border-zinc-200 hover:bg-zinc-50 px-4 py-2 rounded-full text-sm font-medium" data-testid="ann-filter-apply">
              Filtrar
            </button>
          </div>

          <div className="mt-4 font-display font-bold text-xl tracking-tight text-white">
            Anotações no banco ({items.length})
          </div>
          <div className="mt-3 space-y-2">
            {items.length === 0 && (
              <div className="card-sapiens rounded-2xl p-8 text-zinc-500 text-sm">
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
