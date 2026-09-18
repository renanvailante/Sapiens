import { useCallback, useState } from "react";
import { toast } from "sonner";
import { Check, X, Loader2, FastForward, ArrowRight, BookOpen } from "lucide-react";
import { api, errMsg } from "../../lib/api";
import TextoRico from "./TextoRico";

/**
 * "PULAR ATÉ AQUI" — a prova de quem já sabe o caminho todo.
 *
 * A sondagem de domínio pergunta *"você já sabe esta estação?"*. Esta
 * pergunta outra coisa: *"você já sabe tudo daqui para trás?"* — e é a
 * pergunta de quem chega no produto sabendo metade da matéria. Sem ela, essa
 * pessoa atravessa quinze estações que não lhe ensinam nada para chegar onde
 * trava, e é nesse trajeto que ela some.
 *
 * **É uma prova, e a tela se comporta como prova:** uma questão por vez, sem
 * devolutiva entre elas (explicar cada erro no meio da avaliação seria aula
 * durante a prova — e entregaria o método das questões seguintes), sem voltar
 * atrás. Só o marcador de certo/errado, que é o que dá tensão.
 *
 * **O que a tela NÃO diz**, de propósito: quantos acertos são necessários,
 * que a chance é uma só, e que aqui não se ganha Spark. São regras de jogo, e
 * jogo se aprende jogando. O que está em jogo não custa nada ao aluno — ele
 * não perde progresso nem Spark por tentar; no pior caso, estuda, que é o que
 * ele faria de qualquer jeito.
 *
 * Quem sorteia, corrige e decide é o servidor. Esta tela desenha.
 */

const LETRAS = "ABCDEFGH";

export default function SaltoAteAqui({ cursoId, estacao, aoAbrir, aoFechar, aoPular }) {
  const [prova, setProva] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [indice, setIndice] = useState(0);
  const [marcas, setMarcas] = useState([]);
  const [enviando, setEnviando] = useState(false);
  const [fim, setFim] = useState(null);
  const [texto, setTexto] = useState("");

  const comecar = useCallback(async () => {
    setCarregando(true);
    try {
      const { data } = await api.post(`/cursos/${cursoId}/saltos/${estacao.estacao_id}`);
      setProva(data);
      // Retomada: a prova fica gravada no servidor, então quem fechou a aba
      // volta na questão em que estava, e não no começo.
      const jaFeitas = data.blocos.filter((b) => b.respondida).length;
      setIndice(Math.min(jaFeitas, Math.max(0, data.blocos.length - 1)));
      setMarcas(data.blocos.map((b) => (b.respondida ? "feita" : null)));
      aoAbrir?.();
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível abrir a avaliação agora."));
      aoFechar?.();
    } finally {
      setCarregando(false);
    }
  }, [cursoId, estacao.estacao_id, aoFechar, aoAbrir]);

  const responder = useCallback(async (resposta) => {
    if (enviando || resposta === "" || resposta === null || resposta === undefined) return;
    const bloco = prova.blocos[indice];
    setEnviando(true);
    try {
      const { data } = await api.post(
        `/cursos/${cursoId}/saltos/${estacao.estacao_id}/resposta`,
        { bloco_id: bloco.bloco_id, resposta },
      );
      setMarcas((atuais) => atuais.map((m, i) => (i === indice ? (data.acertou ? "certa" : "errada") : m)));
      setTexto("");
      if (data.aprovado || data.reprovado) {
        setFim(data);
        if (data.aprovado) aoPular?.(data);
      } else {
        setIndice((i) => Math.min(i + 1, prova.blocos.length - 1));
      }
    } catch (e) {
      toast.error(errMsg(e, "Não conseguimos registrar sua resposta."));
    } finally {
      setEnviando(false);
    }
  }, [cursoId, estacao.estacao_id, prova, indice, enviando, aoPular]);

  // ------------------------------------------------------------------ convite
  if (!prova && !fim) {
    return (
      <button
        type="button"
        onClick={comecar}
        disabled={carregando}
        className="pill btn-vidro inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold disabled:opacity-50"
        data-testid="salto-comecar"
      >
        {carregando ? <Loader2 className="h-4 w-4 animate-spin" /> : <FastForward className="h-4 w-4" />}
        Pular até aqui
      </button>
    );
  }

  // ------------------------------------------------------------------ o fim
  if (fim) {
    const aprovado = fim.aprovado;
    return (
      <div
        className={`rounded-3xl border p-6 text-center ${
          aprovado
            ? "border-violet-400/35 bg-violet-500/12"
            : "border-amber-400/30 bg-amber-500/10"
        }`}
        data-testid={aprovado ? "salto-aprovado" : "salto-reprovado"}
      >
        {aprovado ? (
          <>
            <FastForward className="mx-auto h-7 w-7 text-violet-200" />
            <p className="mt-3 font-display text-xl font-extrabold tracking-tight text-white">
              Caminho aberto.
            </p>
            <p className="mt-1.5 text-sm text-white/65">
              {fim.puladas.length === 1
                ? "Uma estação ficou para trás."
                : `${fim.puladas.length} estações ficaram para trás.`}{" "}
              Você continua de <strong className="font-semibold text-white">{estacao.titulo}</strong>.
            </p>
            <button
              type="button"
              onClick={aoFechar}
              className="pill btn-sapiens mt-5 inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold"
              data-testid="salto-seguir"
            >
              Continuar daqui <ArrowRight className="h-4 w-4" />
            </button>
          </>
        ) : (
          <>
            <p className="font-display text-lg font-bold tracking-tight text-white">
              Ainda não dá para pular tudo isso.
            </p>
            <p className="mt-1.5 text-sm text-white/60">
              Acertou {fim.resultado.acertos} de {fim.resultado.total}. Tente um ponto mais perto
              — ou estude daqui, que é mais rápido do que parece.
            </p>
            <button
              type="button"
              onClick={aoFechar}
              className="pill btn-vidro mt-5 inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold"
              data-testid="salto-voltar"
            >
              <BookOpen className="h-4 w-4" /> Voltar ao caminho
            </button>
          </>
        )}
      </div>
    );
  }

  // ------------------------------------------------------------------ a prova
  const bloco = prova.blocos[indice];

  return (
    <div className="space-y-4" data-testid="salto-prova">
      <div className="flex items-center gap-3">
        <button type="button" onClick={aoFechar} className="chip shrink-0" aria-label="Sair da avaliação">
          <X className="h-3 w-3" />
        </button>
        {/* Os marcadores. Certo e errado também se distinguem por ÍCONE, não
            só por cor — quem não distingue verde de vermelho continua lendo
            o próprio desempenho. */}
        <ol className="flex flex-1 flex-wrap items-center gap-1" aria-label="Progresso da avaliação">
          {marcas.map((m, i) => (
            <li
              key={i}
              className={[
                "h-2 flex-1 min-w-[6px] rounded-full",
                m === "certa" ? "bg-emerald-400"
                  : m === "errada" ? "bg-rose-400"
                  : m === "feita" ? "bg-white/30"
                  : i === indice ? "bg-white/50"
                  : "bg-white/10",
              ].join(" ")}
              title={m === "certa" ? "Acertou" : m === "errada" ? "Errou" : "Ainda não respondida"}
            />
          ))}
        </ol>
        <span className="shrink-0 font-mono-alt text-[11px] text-white/45 tabular-nums">
          {indice + 1}/{prova.blocos.length}
        </span>
      </div>

      <section className="leitura-clara rounded-3xl p-5 text-zinc-800 md:p-7">
        <div className="secao-olho text-sky-700/80">
          {bloco.estacao_titulo}
        </div>
        <div className="mt-3 font-medium text-zinc-950">
          <TextoRico markdown={bloco.enunciado} />
        </div>

        {bloco.formato === "multipla_escolha" ? (
          <div className="mt-5 grid gap-2">
            {(bloco.alternativas || []).map((alt, i) => (
              <button
                key={alt.id}
                type="button"
                data-estado="livre"
                disabled={enviando}
                className="alternativa"
                onClick={() => responder(alt.id)}
                data-testid={`salto-alt-${alt.id}`}
              >
                <span className="alternativa-letra">{LETRAS[i]}</span>
                <span className="text-zinc-700">{alt.texto}</span>
              </button>
            ))}
          </div>
        ) : (
          <form
            className="mt-5 flex flex-col items-stretch gap-2 sm:flex-row sm:items-center sm:flex-wrap"
            onSubmit={(e) => { e.preventDefault(); responder(texto); }}
          >
            <input
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              inputMode={bloco.formato === "numerico" ? "decimal" : "text"}
              placeholder={bloco.formato === "numerico" ? "Sua resposta" : "Escreva sua resposta"}
              disabled={enviando}
              className="min-w-0 flex-1 rounded-2xl border border-zinc-300 bg-white px-4 py-3 text-base text-zinc-900 outline-none focus:border-sky-500"
              data-testid="salto-campo"
            />
            {bloco.unidade && <span className="text-sm text-zinc-500">{bloco.unidade}</span>}
            <button
              type="submit"
              disabled={enviando || !texto.trim()}
              className="pill btn-sapiens inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold disabled:opacity-50 sm:w-auto"
            >
              {enviando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              Responder
            </button>
          </form>
        )}
      </section>
    </div>
  );
}
