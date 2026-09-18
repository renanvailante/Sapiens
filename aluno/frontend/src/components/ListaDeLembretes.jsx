import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { BookmarkPlus, Check, ExternalLink, Loader2, MessageCircle, Sparkles, Trash2 } from "lucide-react";
import { api, errMsg } from "../lib/api";
import MentisPedido from "./MentisPedido";
import { EVENTO_LEMBRETES, resumir } from "../lib/lembretes";

/**
 * "O que você marcou" — a fila declarada, dentro da aba de Revisões.
 *
 * A outra fila da mesma tela (`FilaDeRevisao`) é INFERIDA: cada linha nasceu
 * de um erro que o motor cognitivo conseguiu explicar. Esta é o contrário —
 * cada linha nasceu de um aluno lendo algo e dizendo "isto eu ainda não
 * domino". As duas precisam estar na mesma tela e precisam parecer diferentes,
 * senão a segunda vira uma versão pior da primeira.
 *
 * **O pedido à Mentis nunca sai sozinho daqui.** O botão abre o `MentisPedido`
 * com a mensagem já escrita e visível, e o envio é uma segunda decisão, com o
 * preço dela na tela — a mesma regra dos cards de dificuldade do Painel (ver
 * `project_aluno_cards_clicaveis_e_barra`). Guardar o ponto custou 10 Sparks;
 * pedir explicação é outra compra, e ela precisa ser dita como tal.
 */

/** As duas perguntas que um trecho marcado sabe formular sozinho. O texto é
 *  montado aqui, e não no card, para que a Mentis receba sempre a mesma forma
 *  de pergunta — o mesmo desenho de `MentisPedido.pedidosPadrao`. */
function pedidosDoLembrete(lembrete) {
  const onde = lembrete.titulo ? ` (marquei em "${lembrete.titulo}")` : "";
  const trecho = resumir(lembrete.texto, 400);
  return [
    {
      id: "explicar",
      rotulo: "Explicar este ponto",
      icone: MessageCircle,
      texto:
        `Marquei este trecho porque ainda não domino${onde}:\n\n"${trecho}"\n\n` +
        "Explique isto do começo, no nível do ENEM, e me diga qual é o passo que costuma confundir.",
    },
    {
      id: "treinar",
      rotulo: "Treinar com questões",
      icone: Sparkles,
      texto:
        `Quero treinar este ponto que marquei${onde}:\n\n"${trecho}"\n\n` +
        "Monte questões sobre isso, da mais simples para a mais difícil, e diga o que cada erro revelaria.",
    },
  ];
}

function Vazia() {
  return (
    <div className="card-sapiens rounded-2xl p-6" data-testid="lembretes-vazio">
      <div className="font-display text-lg font-bold tracking-tight text-zinc-950">
        Você ainda não marcou nada.
      </div>
      <p className="mt-2 text-sm leading-relaxed text-zinc-600">
        Em qualquer tela do Sapiens — uma aula, um enunciado, um e-book —, selecione o trecho que
        você ainda não domina e toque em <strong>Lembrar-me com a Mentis</strong>. Ele fica
        guardado aqui, com a página de onde veio, para você voltar nele depois.
      </p>
      <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-zinc-100 px-3 py-1.5 text-xs text-zinc-600">
        <BookmarkPlus className="h-3.5 w-3.5" /> No celular, selecione o texto e o botão aparece
        sozinho.
      </div>
    </div>
  );
}

function Cartao({ lembrete, onRemover, onRevisado, ocupado }) {
  const [pedindo, setPedindo] = useState(false);
  const quando = (lembrete.criado_em || "").slice(0, 10).split("-").reverse().join("/");

  return (
    <div className="card-sapiens rounded-2xl p-5" data-testid={`lembrete-${lembrete.lembrete_id}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-400">
          {lembrete.tipo === "objeto" ? "objeto marcado" : "trecho marcado"}
          {quando ? ` · ${quando}` : ""}
        </div>
        <button
          type="button"
          onClick={() => onRemover(lembrete)}
          disabled={ocupado}
          // `-m-2.5 p-2.5`: a receita da casa para alvo de toque de 44px sem
          // mexer no desenho do ícone (ver `project_aluno_mobile_invariantes`).
          className="-m-2.5 shrink-0 p-2.5 text-zinc-400 transition hover:text-rose-600 disabled:opacity-40"
          aria-label="Tirar da fila"
          title="Tirar da fila (não devolve Sparks)"
          data-testid={`lembrete-${lembrete.lembrete_id}-remover`}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <blockquote className="mt-3 border-l-2 border-zinc-200 pl-3 text-sm leading-relaxed text-zinc-700">
        {resumir(lembrete.texto, 320)}
      </blockquote>

      {(lembrete.titulo || lembrete.contexto) && (
        <p className="mt-2 text-xs text-zinc-500">
          {lembrete.contexto || lembrete.titulo}
        </p>
      )}

      {/* Contêiner em coluna no celular e em linha a partir de `sm` — sem
          `flex-wrap`, que não quebra faixa com filho `flex-1 min-w-0`
          (invariante 4 de `project_aluno_mobile_invariantes`). */}
      <div className="mt-4 flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
        <button
          type="button"
          onClick={() => setPedindo(true)}
          className="pill btn-sapiens inline-flex w-full items-center justify-center gap-2 rounded-full px-4 py-2.5 text-sm font-medium sm:w-auto"
          data-testid={`lembrete-${lembrete.lembrete_id}-mentis`}
        >
          <MessageCircle className="h-4 w-4" /> Pedir à Mentis
        </button>
        <button
          type="button"
          onClick={() => onRevisado(lembrete)}
          disabled={ocupado}
          className="pill macio inline-flex w-full items-center justify-center gap-2 rounded-full border border-zinc-200 px-4 py-2.5 text-sm text-zinc-700 disabled:opacity-40 sm:w-auto"
          data-testid={`lembrete-${lembrete.lembrete_id}-revisado`}
        >
          <Check className="h-4 w-4" /> Já domino isto
        </button>
        {lembrete.rota && (
          <Link
            to={lembrete.rota}
            className="inline-flex items-center justify-center gap-1.5 py-2 -my-2 text-xs text-zinc-500 underline-offset-2 hover:text-zinc-800 hover:underline sm:ml-auto"
            data-testid={`lembrete-${lembrete.lembrete_id}-origem`}
          >
            <ExternalLink className="h-3.5 w-3.5" /> Voltar para onde marquei
          </Link>
        )}
      </div>

      {pedindo && (
        <MentisPedido
          aberto={pedindo}
          onFechar={() => setPedindo(false)}
          assunto={resumir(lembrete.texto, 80)}
          pedidos={pedidosDoLembrete(lembrete)}
          testid={`lembrete-${lembrete.lembrete_id}-pedido`}
        />
      )}
    </div>
  );
}

export default function ListaDeLembretes() {
  const [fila, setFila] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [ocupado, setOcupado] = useState(null);
  const emVoo = useRef(false);

  const carregar = useCallback(async () => {
    try {
      const { data } = await api.get("/lembretes");
      setFila(data);
    } catch {
      setFila({ itens: [], indisponivel: true });
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
    // Recarrega quando um trecho é guardado sem sair desta tela — ver
    // `EVENTO_LEMBRETES`.
    window.addEventListener(EVENTO_LEMBRETES, carregar);
    return () => window.removeEventListener(EVENTO_LEMBRETES, carregar);
  }, [carregar]);

  /** Some da lista na hora e só então confirma com o servidor. Se falhar, o
   *  item volta — a lista nunca fica mentindo sobre o que existe. */
  async function agir(lembrete, acao) {
    if (emVoo.current) return;
    emVoo.current = true;
    setOcupado(lembrete.lembrete_id);
    const antes = fila;
    setFila((f) => ({ ...f, itens: (f?.itens || []).filter((i) => i.lembrete_id !== lembrete.lembrete_id) }));
    try {
      if (acao === "remover") await api.delete(`/lembretes/${lembrete.lembrete_id}`);
      else await api.post(`/lembretes/${lembrete.lembrete_id}/revisado`);
      toast.success(acao === "remover" ? "Tirado da fila." : "Marcado como dominado.");
    } catch (e) {
      setFila(antes);
      toast.error(errMsg(e, "Não foi possível atualizar a sua fila."));
    } finally {
      emVoo.current = false;
      setOcupado(null);
    }
  }

  if (carregando) {
    return (
      <div className="flex items-center gap-2 text-sm text-white/60">
        <Loader2 className="h-4 w-4 animate-spin" /> Carregando o que você marcou...
      </div>
    );
  }

  const itens = fila?.itens || [];
  if (!itens.length) return <Vazia />;

  return (
    <div className="space-y-3" data-testid="lembretes-lista">
      {itens.map((l) => (
        <Cartao
          key={l.lembrete_id}
          lembrete={l}
          ocupado={ocupado === l.lembrete_id}
          onRemover={(x) => agir(x, "remover")}
          onRevisado={(x) => agir(x, "revisado")}
        />
      ))}
    </div>
  );
}
