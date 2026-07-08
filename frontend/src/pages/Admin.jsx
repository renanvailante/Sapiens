import { useState } from "react";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { toast } from "sonner";

const SAMPLE = JSON.stringify({
  provider: "ENEM",
  year: 2021,
  color: "Rosa",
  area: "Dia 1 - LC + CH",
  title: "ENEM 2021 • Rosa",
  questions: [
    {
      number: 1, area: "LC", subject: "Português", topic: "Interpretação de texto",
      statement: "Exemplo de enunciado...",
      alternatives: [
        {"letter":"A","text":"..."},{"letter":"B","text":"..."},{"letter":"C","text":"..."},
        {"letter":"D","text":"..."},{"letter":"E","text":"..."}
      ],
      correct_answer: "B",
      difficulty: "medio"
    }
  ]
}, null, 2);

export default function Admin() {
  const [raw, setRaw] = useState(SAMPLE);
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      const body = JSON.parse(raw);
      const { data } = await api.post("/admin/import-exam", body);
      toast.success(`Prova importada: ${data.total} questões.`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Falha ao importar. Verifique o JSON.");
    } finally { setBusy(false); }
  };
  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Admin</div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-zinc-950" data-testid="admin-title">Importar prova</h1>
        <p className="mt-3 text-zinc-500 max-w-lg">Cole o JSON estruturado. Se as etiquetas não forem fornecidas, o Sapiens gera automaticamente com IA.</p>
        <textarea
          value={raw} onChange={e => setRaw(e.target.value)}
          className="mt-6 w-full h-[420px] font-mono-alt text-xs border border-zinc-200 rounded-2xl p-4 focus:border-zinc-900 outline-none"
          data-testid="admin-json"
        />
        <button
          disabled={busy} onClick={submit}
          className="pill mt-4 bg-zinc-950 hover:bg-zinc-800 disabled:opacity-60 text-white px-6 py-3 rounded-full text-sm font-medium"
          data-testid="admin-submit"
        >
          {busy ? "Importando..." : "Importar prova"}
        </button>
      </div>
    </div>
  );
}
