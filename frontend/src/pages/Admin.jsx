import { useState } from "react";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { toast } from "sonner";

const SAMPLE = `QUESTÃO GABARITO
INGLÊS ESPANHOL
1 D B
2 D A
3 D D
4 E D
5 E E
6 A
7 B
8 C
9 D
10 E
...`;

const COLORS = ["Azul", "Amarela", "Branca", "Cinza", "Rosa", "Verde"];

export default function Admin() {
  const [year, setYear] = useState(new Date().getFullYear());
  const [day, setDay] = useState(1);
  const [color, setColor] = useState("Azul");
  const [raw, setRaw] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!raw.trim()) return toast.error("Cole o gabarito antes de importar.");
    setBusy(true);
    try {
      const { data } = await api.post("/admin/paste-answer-key", {
        provider: "ENEM", year: Number(year), day: Number(day), color, raw_text: raw,
      });
      toast.success(`Gabarito importado: ${data.total} questões (EN: ${data.english ? "sim" : "não"}, ES: ${data.spanish ? "sim" : "não"}).`);
      setRaw("");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Falha ao importar.");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Admin</div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-zinc-950" data-testid="admin-title">Importar gabarito do INEP</h1>
        <p className="mt-3 text-zinc-500 max-w-2xl">
          Cole diretamente o gabarito oficial (Ctrl+C / Ctrl+V) da página do INEP. O Sapiens ignora cabeçalhos e formatação, e cria automaticamente as versões em <b>inglês</b> e <b>espanhol</b>.
        </p>

        <div className="mt-8 grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs font-mono-alt uppercase tracking-[0.2em] text-zinc-500">Ano</label>
            <input type="number" value={year} onChange={e => setYear(e.target.value)}
              className="mt-1 w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm focus:border-zinc-900 outline-none"
              data-testid="admin-year" />
          </div>
          <div>
            <label className="text-xs font-mono-alt uppercase tracking-[0.2em] text-zinc-500">Dia</label>
            <select value={day} onChange={e => setDay(e.target.value)}
              className="mt-1 w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm focus:border-zinc-900 outline-none bg-white"
              data-testid="admin-day">
              <option value={1}>Dia 1 (LC + CH)</option>
              <option value={2}>Dia 2 (CN + MT)</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-mono-alt uppercase tracking-[0.2em] text-zinc-500">Cor</label>
            <select value={color} onChange={e => setColor(e.target.value)}
              className="mt-1 w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm focus:border-zinc-900 outline-none bg-white"
              data-testid="admin-color">
              {COLORS.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>

        <textarea value={raw} onChange={e => setRaw(e.target.value)} placeholder={SAMPLE}
          className="mt-6 w-full h-[420px] font-mono-alt text-xs border border-zinc-200 rounded-2xl p-4 focus:border-zinc-900 outline-none"
          data-testid="admin-paste" />
        <button disabled={busy} onClick={submit}
          className="pill mt-4 bg-zinc-950 hover:bg-zinc-800 disabled:opacity-60 text-white px-6 py-3 rounded-full text-sm font-medium"
          data-testid="admin-submit">
          {busy ? "Importando..." : "Importar gabarito"}
        </button>
      </div>
    </div>
  );
}
