import { useEffect, useState } from "react";

// Página PÚBLICA do aluno — exibe as questões vindas do Firestore (coleção "itens")
// através do endpoint público GET /api/questoes. NÃO usa nenhuma autenticação:
// nem Firebase Auth, nem GIS, nem token/cookie. Apenas um fetch normal.

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function Alternativa({ alt, revelar }) {
  const correta = alt?.correta === true;
  const base =
    "flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition";
  const cls = revelar && correta
    ? "border-emerald-400 bg-emerald-50"
    : "border-slate-200 bg-white hover:border-indigo-300";
  return (
    <div className={`${base} ${cls}`}>
      <span
        className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
          revelar && correta
            ? "bg-emerald-500 text-white"
            : "bg-slate-100 text-slate-600"
        }`}
      >
        {alt?.letra}
      </span>
      <span className="text-slate-700">{alt?.texto}</span>
    </div>
  );
}

function QuestaoCard({ item, index }) {
  const [revelar, setRevelar] = useState(false);
  const q = item?.pipeline?.questao || item?.questao || {};
  const fonte = item?.pipeline?.fonte || item?.fonte || {};
  const alternativas = Array.isArray(q.alternativas) ? q.alternativas : [];
  const tags = [fonte.disciplina, fonte.ano, fonte.prova, fonte.banca].filter(Boolean);

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-indigo-600 px-3 py-1 text-xs font-semibold text-white">
          Questão {index + 1}
        </span>
        {tags.map((t, i) => (
          <span
            key={i}
            className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600"
          >
            {t}
          </span>
        ))}
      </div>

      <p className="whitespace-pre-line text-[15px] leading-relaxed text-slate-800">
        {q.enunciado || "(Sem enunciado)"}
      </p>

      <div className="mt-4 grid gap-2">
        {alternativas.map((alt, i) => (
          <Alternativa key={i} alt={alt} revelar={revelar} />
        ))}
      </div>

      {alternativas.length > 0 && (
        <button
          onClick={() => setRevelar((v) => !v)}
          className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700"
        >
          {revelar ? "Ocultar resposta" : "Ver resposta"}
        </button>
      )}
    </article>
  );
}

export default function Questoes() {
  const [itens, setItens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/questoes?limit=100`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (ativo) setItens(Array.isArray(data.items) ? data.items : []);
      } catch (e) {
        if (ativo) setErro(e.message || "Falha ao carregar questões");
      } finally {
        if (ativo) setLoading(false);
      }
    })();
    return () => {
      ativo = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-3xl px-4 py-6">
          <h1 className="text-2xl font-bold text-slate-900">Questões</h1>
          <p className="text-sm text-slate-500">
            Banco de questões — acesso livre, sem login.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-5 px-4 py-8">
        {loading && (
          <div className="py-20 text-center text-slate-500">
            Carregando questões…
          </div>
        )}

        {erro && !loading && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-700">
            Não foi possível carregar as questões: {erro}
          </div>
        )}

        {!loading && !erro && itens.length === 0 && (
          <div className="py-20 text-center text-slate-500">
            Nenhuma questão encontrada.
          </div>
        )}

        {!loading &&
          !erro &&
          itens.map((item, i) => (
            <QuestaoCard key={item.id || i} item={item} index={i} />
          ))}
      </main>
    </div>
  );
}
