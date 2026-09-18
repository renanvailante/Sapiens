import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Sparkles, Loader2 } from "lucide-react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import Mentis from "../components/Mentis";
import GerarQuestoesPainel from "../components/GerarQuestoesPainel";
import Alternativas from "../components/questao/Alternativas";
import Veredito from "../components/questao/Veredito";

/**
 * Questões que a Mentis já gerou (ou reaproveitou de outro aluno) para este
 * aluno — nunca refeitas ao reabrir esta tela. É o mesmo lote que aparece em
 * "Praticar mais" no Treino e no botão de ação da conversa com a Mentis; os
 * dois só levam pra cá.
 */

const DIFICULDADE_LABEL = { FACIL: "Fácil", MEDIO_FACIL: "Médio-fácil", MEDIO: "Médio", DIFICIL: "Difícil" };

function CartaoQuestao({ item, onResolvida }) {
  const [selecionada, setSelecionada] = useState(item.minha_resposta || null);
  // Ao REABRIR uma questão já respondida, o servidor devolve o que o aluno
  // marcou e se acertou, mas nunca o gabarito (`_questao_ia_sem_gabarito` em
  // `treino_routes.py` — de propósito: a lista não pode entregar a resposta
  // de questões ainda não respondidas).
  //
  // Isto aqui montava `gabarito: [minha_resposta]` em qualquer caso, então
  // quem reabria uma questão que tinha ERRADO via a própria alternativa
  // errada pintada de verde, com o tique de "certa" ao lado. A devolutiva
  // mentia justamente para quem mais precisava dela.
  //
  // Só afirmamos que uma letra é a correta quando ela É: no acerto, a
  // marcada; no erro, nenhuma — e aí a escolha do aluno aparece como errada,
  // que é a verdade que temos em mão.
  const [resultado, setResultado] = useState(
    item.respondida
      ? { acertou: item.acertou, gabarito: item.acertou && item.minha_resposta ? [item.minha_resposta] : [] }
      : null
  );
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);

  const responder = (letra) => {
    if (resultado || enviando) return;
    setSelecionada(letra);
    setEnviando(true);
    setErro(null);
    api
      .post(`/treino/questoes-geradas/${item.questao_id}/responder`, { alternativa: letra })
      .then(({ data }) => {
        setResultado(data);
        onResolvida?.(data);
      })
      .catch((e) => setErro(errMsg(e, "Não foi possível registrar sua resposta.")))
      .finally(() => setEnviando(false));
  };

  return (
    // `leitura-clara`: a questão gerada passou a ser lida na MESMA superfície
    // da prova e da missão de treino. Enunciado é texto longo, e o produto já
    // tinha decidido que texto longo se lê em fundo claro — só esta tela
    // tinha ficado de fora, com um cartão escuro e uma terceira paleta de
    // alternativas só dela.
    <article className="card-sapiens leitura-clara rounded-2xl p-5 md:p-6" data-testid="minhas-questoes-item">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-zinc-100 px-3 py-1 text-[11px] font-semibold text-zinc-600">
          {item.habilidade_nome}
        </span>
        <span className="rounded-full bg-zinc-50 px-3 py-1 text-[11px] text-zinc-500">
          {DIFICULDADE_LABEL[item.dificuldade] || item.dificuldade}
        </span>
      </div>

      <p className="whitespace-pre-line text-[15px] leading-relaxed text-zinc-800">{item.enunciado_antes}</p>
      {item.enunciado_depois && (
        <p className="mt-2 whitespace-pre-line text-[15px] leading-relaxed text-zinc-800">{item.enunciado_depois}</p>
      )}

      <div className="mt-4">
        <Alternativas
          alternativas={item.alternativas}
          selecionada={selecionada}
          resultado={resultado}
          desabilitado={enviando}
          aoEscolher={responder}
          testidPrefixo="minhas-questoes-alt"
        />
      </div>

      {erro && <p className="mt-3 text-xs text-rose-600">{erro}</p>}

      <Veredito
        resultado={resultado}
        explicacao={resultado?.elucidacao}
        testid="minhas-questoes-resultado"
      />
    </article>
  );
}

export default function MinhasQuestoes() {
  const [params] = useSearchParams();
  const habId = params.get("hab_id");
  const [itens, setItens] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [saldo, setSaldo] = useState(null);

  // `recarga` sobe a cada geração: as questões novas precisam aparecer na
  // lista sem o aluno recarregar a página que acabou de cobrá-lo.
  const [recarga, setRecarga] = useState(0);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    const qs = habId ? `?hab_id=${encodeURIComponent(habId)}` : "";
    api
      .get(`/treino/questoes-geradas${qs}`)
      .then(({ data }) => { if (ativo) setItens(Array.isArray(data.itens) ? data.itens : []); })
      .catch((e) => { if (ativo) setErro(errMsg(e, "Não foi possível carregar suas questões.")); })
      .finally(() => { if (ativo) setCarregando(false); });
    return () => { ativo = false; };
  }, [habId, recarga]);

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-3xl mx-auto px-4 md:px-10 py-8 md:py-12">
        <div className="flex items-center gap-3 mb-2">
          <Mentis className="w-10 h-10 shrink-0" variante="icone" />
          <div>
            <h1 className="font-display text-2xl md:text-3xl font-extrabold tracking-tighter text-white">
              Minhas questões
            </h1>
            <p className="text-xs text-white/45">Geradas pela Mentis para você, prontas para praticar agora.</p>
          </div>
        </div>

        {typeof saldo === "number" && (
          <div className="mt-1 inline-flex items-center gap-1.5 text-xs text-white/45">
            <Sparkles className="w-3 h-3 text-amber-400" /> saldo {saldo}
          </div>
        )}

        {/* A geração mora AQUI, e não só dentro do briefing de uma habilidade
            do mapa. A tela que lista as questões geradas era a única que não
            sabia gerá-las — mandava o aluno para outra. */}
        <div className="mt-6">
          <GerarQuestoesPainel habIdInicial={habId} aoGerar={() => setRecarga((n) => n + 1)} />
        </div>

        <div className="mt-6 space-y-4">
          {carregando && (
            <div className="flex items-center gap-2 py-16 justify-center text-white/50 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" /> Carregando suas questões…
            </div>
          )}

          {erro && !carregando && (
            <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-200">{erro}</div>
          )}

          {!carregando && !erro && itens.length === 0 && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-8 text-center text-sm text-white/45">
              Nenhuma questão gerada ainda. Escolha um ponto acima e peça as primeiras.
            </div>
          )}

          {!carregando &&
            !erro &&
            itens.map((item) => (
              <CartaoQuestao
                key={item.questao_id}
                item={item}
                onResolvida={(data) => { if (typeof data.sparks_balance === "number") setSaldo(data.sparks_balance); }}
              />
            ))}
        </div>
      </div>
    </div>
  );
}
