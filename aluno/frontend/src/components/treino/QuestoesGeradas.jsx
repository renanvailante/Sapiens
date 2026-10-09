import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Sparkles, Loader2 } from "lucide-react";
import { api, errMsg } from "../../lib/api";
import GerarQuestoesPainel from "../GerarQuestoesPainel";
import Alternativas from "../questao/Alternativas";
import Veredito from "../questao/Veredito";
import { reagirAResposta } from "../../lib/reacao";

/**
 * AS QUESTÕES QUE A MENTIS GEROU — uma fonte de prática do Treino, não uma tela.
 *
 * Era `/minhas-questoes`, e a separação nunca fez sentido do lado do aluno:
 * ele não abre o app querendo "o módulo de questões geradas", ele quer praticar
 * uma habilidade. As duas fontes do Treino atacam a MESMA lacuna —
 *
 *   · o **mapa** dá as questões que já existem no acervo para aquele ponto;
 *   · a **Mentis** gera questões novas sob medida quando o acervo acaba.
 *
 * — e o próprio produto já dizia isso: "Praticar mais", dentro do desfecho de
 * uma missão do mapa, levava exatamente para cá. Era uma tela cujo único
 * caminho de entrada natural era outra tela.
 *
 * O que continua sendo verdade e não pode mudar: as questões **nunca são
 * refeitas** ao reabrir — o mesmo lote volta, e o aluno não paga duas vezes
 * por olhar de novo.
 */

const DIFICULDADE_LABEL = {
  FACIL: "Fácil", MEDIO_FACIL: "Médio-fácil", MEDIO: "Médio", DIFICIL: "Difícil",
};

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
      : null,
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
        reagirAResposta(Boolean(data.acertou));
        onResolvida?.(data);
      })
      .catch((e) => setErro(errMsg(e, "Não foi possível registrar sua resposta.")))
      .finally(() => setEnviando(false));
  };

  return (
    // `leitura-clara`: a questão gerada é lida na MESMA superfície da prova e
    // da missão de treino. Enunciado é texto longo, e o produto já tinha
    // decidido que texto longo se lê em fundo claro.
    <article className="card-sapiens leitura-clara rounded-2xl p-5 md:p-6" data-testid="questao-gerada">
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
          testidPrefixo="questao-gerada-alt"
        />
      </div>

      {erro && <p className="mt-3 text-xs text-rose-600">{erro}</p>}

      <Veredito
        resultado={resultado}
        explicacao={resultado?.elucidacao}
        testid="questao-gerada-resultado"
      />
    </article>
  );
}

export default function QuestoesGeradas() {
  const [params] = useSearchParams();
  // `hab_id` e `hab` são a mesma intenção com dois nomes: o primeiro vinha dos
  // links de `/minhas-questoes`, o segundo é o do mapa. Ler os dois é o que
  // mantém os links antigos apontando para a habilidade certa.
  const habId = params.get("hab_id") || params.get("hab");

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
    <div data-testid="questoes-geradas">
      {typeof saldo === "number" && (
        <div className="mb-3 inline-flex items-center gap-1.5 text-xs text-white/45">
          <Sparkles className="h-3 w-3 text-amber-400" /> saldo {saldo}
        </div>
      )}

      {/* A geração mora AQUI, junto da lista. A tela que listava as questões
          geradas era a única que não sabia gerá-las — mandava o aluno a outra. */}
      <GerarQuestoesPainel habIdInicial={habId} aoGerar={() => setRecarga((n) => n + 1)} />

      <div className="mt-6 space-y-4">
        {carregando && (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-white/50">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando suas questões…
          </div>
        )}

        {erro && !carregando && (
          <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-200">
            {erro}
          </div>
        )}

        {!carregando && !erro && itens.length === 0 && (
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-8 text-center text-sm text-white/45">
            Nenhuma questão gerada ainda. Escolha um ponto acima e peça as primeiras.
          </div>
        )}

        {!carregando && !erro && itens.map((item) => (
          <CartaoQuestao
            key={item.questao_id}
            item={item}
            onResolvida={(data) => {
              if (typeof data.sparks_balance === "number") setSaldo(data.sparks_balance);
            }}
          />
        ))}
      </div>
    </div>
  );
}
