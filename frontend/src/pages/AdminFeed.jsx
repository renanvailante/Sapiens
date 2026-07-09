import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { toast } from "sonner";
import { Plus, Save, Trash2, Eye, EyeOff } from "lucide-react";

const TYPES = ["question", "flashcard", "explanation", "diagram", "video"];
const THEMES = ["slate", "violet", "emerald", "amber", "rose", "ocean"];

const EMPTY = {
  content_type: "question",
  sequence_order: 0,
  question_data: { prompt: "", subject_hint: "" },
  answer_options: [
    { key: "A", label: "", is_correct: false },
    { key: "B", label: "", is_correct: false },
    { key: "C", label: "", is_correct: false },
    { key: "D", label: "", is_correct: false },
  ],
  explanation_data: { text: "" },
  multimedia_assets: [],
  metadata: {},
  cognitive_mapping_reference: "",
  difficulty_reference: "",
  learning_objectives: [],
  background_theme: "slate",
  published: true,
};

export default function AdminFeed() {
  const [items, setItems] = useState([]);
  const [draft, setDraft] = useState(EMPTY);
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/admin/feed-items").then(({ data }) => setItems(data));
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!draft.question_data.prompt.trim()) return toast.error("Adicione um prompt.");
    setBusy(true);
    try {
      await api.post("/admin/feed-items", draft);
      toast.success("Card criado.");
      setDraft(EMPTY);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Erro ao criar."); }
    finally { setBusy(false); }
  };

  const togglePublish = async (it) => {
    await api.patch(`/admin/feed-items/${it.content_id}`, { published: !it.published });
    load();
  };
  const remove = async (it) => {
    if (!window.confirm("Excluir este card do feed?")) return;
    await api.delete(`/admin/feed-items/${it.content_id}`);
    toast.success("Card excluído.");
    load();
  };
  const patchOrder = async (it, newOrder) => {
    await api.patch(`/admin/feed-items/${it.content_id}`, { sequence_order: Number(newOrder) });
    load();
  };

  const updateOption = (idx, patch) => {
    setDraft(d => ({
      ...d,
      answer_options: d.answer_options.map((o, i) => i === idx ? { ...o, ...patch } : o),
    }));
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-5xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Admin · Feed</div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-zinc-950" data-testid="feed-admin-title">
          Gerenciar cards do feed
        </h1>
        <p className="mt-3 text-zinc-500 max-w-2xl">
          Cada card aparece como uma tela cheia no feed vertical. O modelo cognitivo, a variável de dificuldade e o mapeamento de habilidades serão conectados posteriormente por outra camada.
        </p>

        {/* Composer */}
        <div className="mt-8 bg-white border border-zinc-200 rounded-2xl p-6">
          <div className="font-display font-bold text-xl tracking-tight text-zinc-950">Novo card</div>
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
            <label className="text-xs">
              <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Tipo</div>
              <select value={draft.content_type} onChange={e => setDraft(d => ({ ...d, content_type: e.target.value }))}
                className="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm bg-white outline-none focus:border-zinc-900"
                data-testid="feed-admin-type">
                {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            <label className="text-xs">
              <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Tema visual</div>
              <select value={draft.background_theme} onChange={e => setDraft(d => ({ ...d, background_theme: e.target.value }))}
                className="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm bg-white outline-none focus:border-zinc-900"
                data-testid="feed-admin-theme">
                {THEMES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            <label className="text-xs">
              <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Ordem (0 = automática)</div>
              <input type="number" value={draft.sequence_order} onChange={e => setDraft(d => ({ ...d, sequence_order: Number(e.target.value) }))}
                className="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900"
                data-testid="feed-admin-order" />
            </label>
          </div>

          <label className="block mt-4 text-xs">
            <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Prompt principal</div>
            <textarea rows={2} value={draft.question_data.prompt}
              onChange={e => setDraft(d => ({ ...d, question_data: { ...d.question_data, prompt: e.target.value } }))}
              className="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900"
              placeholder="Escreva o enunciado ou conceito..."
              data-testid="feed-admin-prompt" />
          </label>

          {draft.content_type === "question" && (
            <div className="mt-4 space-y-2">
              <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 text-xs mb-1">Alternativas</div>
              {draft.answer_options.map((o, i) => (
                <div key={o.key} className="flex items-center gap-2" data-testid={`feed-admin-opt-${o.key}`}>
                  <div className="w-8 text-center text-xs font-mono-alt text-zinc-500">{o.key}</div>
                  <input value={o.label} onChange={e => updateOption(i, { label: e.target.value })}
                    className="flex-1 border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900"
                    placeholder={`Alternativa ${o.key}`} />
                  <label className="flex items-center gap-1 text-xs text-zinc-600">
                    <input type="radio" name="correct" checked={o.is_correct}
                      onChange={() => setDraft(d => ({
                        ...d,
                        answer_options: d.answer_options.map((oo, ii) => ({ ...oo, is_correct: ii === i })),
                      }))}
                      data-testid={`feed-admin-opt-correct-${o.key}`} /> correta
                  </label>
                </div>
              ))}
            </div>
          )}

          <label className="block mt-4 text-xs">
            <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Explicação / resposta</div>
            <textarea rows={3} value={draft.explanation_data.text}
              onChange={e => setDraft(d => ({ ...d, explanation_data: { ...d.explanation_data, text: e.target.value } }))}
              className="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900"
              data-testid="feed-admin-explanation" />
          </label>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="text-xs">
              <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Cognitive mapping ref</div>
              <input value={draft.cognitive_mapping_reference}
                onChange={e => setDraft(d => ({ ...d, cognitive_mapping_reference: e.target.value }))}
                className="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900"
                placeholder="ex.: skill.prop.explicit"
                data-testid="feed-admin-cog-ref" />
            </label>
            <label className="text-xs">
              <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Difficulty ref</div>
              <input value={draft.difficulty_reference}
                onChange={e => setDraft(d => ({ ...d, difficulty_reference: e.target.value }))}
                className="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900"
                placeholder="ex.: tri.b=1.2" data-testid="feed-admin-diff-ref" />
            </label>
          </div>

          <button disabled={busy} onClick={create}
            className="pill mt-6 inline-flex items-center gap-2 bg-zinc-950 hover:bg-zinc-800 disabled:opacity-60 text-white px-6 py-3 rounded-full text-sm font-medium"
            data-testid="feed-admin-create">
            <Plus className="w-4 h-4" /> {busy ? "Criando..." : "Criar card"}
          </button>
        </div>

        {/* List */}
        <div className="mt-10">
          <div className="font-display font-bold text-xl tracking-tight text-zinc-950 mb-4">Cards existentes ({items.length})</div>
          <div className="space-y-2">
            {items.map(it => (
              <div key={it.content_id} className="bg-white border border-zinc-200 rounded-2xl p-4 flex items-center gap-4" data-testid={`feed-admin-row-${it.content_id}`}>
                <input type="number" defaultValue={it.sequence_order}
                  onBlur={e => { if (Number(e.target.value) !== it.sequence_order) patchOrder(it, e.target.value); }}
                  className="w-16 text-center border border-zinc-200 rounded-lg px-2 py-1 text-sm font-mono-alt"
                  data-testid={`feed-admin-order-${it.content_id}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-zinc-500">
                    {it.content_type} · {it.background_theme}
                  </div>
                  <div className="mt-1 font-display font-semibold text-base text-zinc-900 truncate">
                    {it.question_data?.prompt || "(sem prompt)"}
                  </div>
                </div>
                <button onClick={() => togglePublish(it)}
                  className="p-2 rounded-full hover:bg-zinc-100" title={it.published ? "Publicado" : "Rascunho"}
                  data-testid={`feed-admin-toggle-${it.content_id}`}>
                  {it.published ? <Eye className="w-4 h-4 text-emerald-500" /> : <EyeOff className="w-4 h-4 text-zinc-400" />}
                </button>
                <button onClick={() => remove(it)}
                  className="p-2 rounded-full hover:bg-rose-50 text-rose-600"
                  data-testid={`feed-admin-delete-${it.content_id}`}>
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
