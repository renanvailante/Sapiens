import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { api, errMsg } from "../lib/api";

// Navegação do acervo de questões — EXIGE SESSÃO.
//
// Era pública e usava `fetch` cru, sem credencial, contra um `/api/questoes`
// que também era aberto e devolvia `alternativas[].correta`: o gabarito do
// banco inteiro estava a um clique de qualquer pessoa, e esta página ainda
// tinha um botão "Ver resposta" para exibi-lo.
//
// Agora usa o cliente `api` (que envia a sessão) e o gabarito não vem mais na
// resposta — quem decide certo/errado é o servidor, na prática, quando o aluno
// responde de fato.

function Alternativa({ alt }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-left">
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-bold text-slate-600">
        {alt?.letra}
      </span>
      <span className="text-slate-700">{alt?.texto}</span>
    </div>
  );
}

function QuestaoCard({ item, index }) {
  // `questoes_public` é plano: `questao` e `fonte` no topo do documento. O
  // caminho `item.pipeline.questao` era resíduo do Formato A, aninhamento que
  // esta coleção nunca teve — e, por ser testado primeiro, teria mascarado a
  // leitura correta se algum documento voltasse a trazê-lo.
  const q = item?.questao || {};
  const fonte = item?.fonte || {};
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
          <Alternativa key={i} alt={alt} />
        ))}
      </div>

      {/* Sem "Ver resposta": o gabarito não é mais enviado ao navegador. Para
          saber se acertou, o caminho é responder de verdade na prática, onde a
          correção acontece no servidor e o resultado vira progresso. */}
      <Link
        to="/exams"
        className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-indigo-700 hover:underline"
      >
        Responder na prática <ArrowRight className="w-3.5 h-3.5" />
      </Link>
    </article>
  );
}

export default function Questoes() {
  const [itens, setItens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    let ativo = true;
    api.get("/questoes?limit=100")
      .then(({ data }) => { if (ativo) setItens(Array.isArray(data.items) ? data.items : []); })
      .catch((e) => { if (ativo) setErro(errMsg(e, "Falha ao carregar questões.")); })
      .finally(() => { if (ativo) setLoading(false); });
    return () => { ativo = false; };
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-3xl px-4 py-6">
          <h1 className="text-2xl font-bold text-slate-900">Questões</h1>
          <p className="text-sm text-slate-500">
            Navegue pelo acervo. Para responder e registrar progresso, use a prática.
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
