import { useCallback, useState } from "react";
import { toast } from "sonner";
import { Award, Loader2, ShieldCheck, X, ArrowRight, BookOpen } from "lucide-react";
import { api, errMsg } from "../../lib/api";
import Bloco from "./Blocos";

/**
 * "JÁ DOMINO ESTE CONTEÚDO" — a porta de quem já sabe.
 *
 * A pergunta mais antiga do ensino é *e quem já sabe?*, e a resposta errada é
 * um botão de pular: ele transforma a trilha em decoração e destrói o dado,
 * porque o produto passa a afirmar que o aluno estudou o que ele não abriu.
 *
 * A resposta daqui é uma PROVA. Três dos exercícios mais difíceis da estação,
 * todos certos **de primeira**. Quem passa, passa — a estação fica marcada
 * como *pulada* (nunca *concluída*) e a seguinte abre. Quem não passa, estuda
 * — e o que respondeu aqui continua valendo, porque eram exercícios de
 * verdade.
 *
 * **A regra aparece antes de começar**, e não depois: descobrir que um erro
 * custava a chance seria uma armadilha. E a chance é uma só, o que também é
 * dito na cara — repetir até passar seria força bruta com quatro
 * alternativas, não evidência de domínio.
 *
 * Quem decide tudo isso é o servidor: quais questões, o que conta e se passou
 * (`cursos_progresso.resultado_da_sondagem`). Esta tela desenha.
 */

export default function SondagemDeDominio({
  cursoId, estacaoId, jaUsada, aoPular, aoResponder, aoFechar, aberta, aoAbrir,
}) {
  const [carregando, setCarregando] = useState(false);
  const [sondagem, setSondagem] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [respondidos, setRespondidos] = useState({});

  const comecar = useCallback(async () => {
    setCarregando(true);
    try {
      const { data } = await api.post(`/cursos/${cursoId}/estacoes/${estacaoId}/dominio`);
      setSondagem(data);
      setResultado(data.resultado);
      aoAbrir?.();
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível abrir a avaliação agora."));
    } finally {
      setCarregando(false);
    }
  }, [cursoId, estacaoId, aoAbrir]);

  // `aoResponder` (do pai) e `responder` (daqui) têm nomes parecidos e papéis
  // diferentes: o de fora é o AVISO de que uma resposta entrou — é ele que faz
  // o contador de exercícios e o saldo do cabeçalho acompanharem a sondagem,
  // que responde exercícios de verdade.
  const responder = useCallback(async (blocoId, resposta, tempoSegundos) => {
    try {
      const { data } = await api.post(
        `/cursos/${cursoId}/estacoes/${estacaoId}/dominio/resposta`,
        { bloco_id: blocoId, resposta, tempo_segundos: tempoSegundos },
      );
      setResultado(data.resultado);
      setRespondidos((atual) => ({ ...atual, [blocoId]: data.acertou }));
      aoResponder?.(data);
      if (data.pulou_agora) aoPular?.(data);
      return data;
    } catch (e) {
      toast.error(errMsg(e, "Não conseguimos registrar sua resposta."));
      return null;
    }
  }, [cursoId, estacaoId, aoPular, aoResponder]);

  // ------------------------------------------------------------------ convite
  if (!aberta) {
    if (jaUsada) {
      return (
        <p className="text-center text-[12px] text-white/35" data-testid="dominio-ja-usada">
          Você já usou a avaliação de domínio desta estação. O que respondeu nela continua valendo.
        </p>
      );
    }
    return (
      <section className="superficie rounded-3xl p-4" data-testid="dominio-convite">
        {/* Empilha no celular. Com `flex-wrap` e um botão largo ao lado, a
            coluna do texto sobrava com 60px e cada palavra caía numa linha. */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
          <div className="flex min-w-0 flex-1 items-start gap-3">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-violet-300" />
            <div className="min-w-0">
              <h2 className="font-display text-[15px] font-bold tracking-tight text-white">
                Já domina isto?
              </h2>
              <p className="mt-0.5 text-[13px] leading-snug text-white/50">
                Três questões difíceis desta estação, e ela sai do seu caminho.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={comecar}
            disabled={carregando}
            className="pill btn-vidro inline-flex shrink-0 items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
            data-testid="dominio-comecar"
          >
            {carregando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Award className="h-4 w-4" />}
            Provar
          </button>
        </div>
      </section>
    );
  }

  // ------------------------------------------------------------------ a prova
  const aprovado = resultado?.aprovado;
  const reprovado = resultado?.completa && !resultado?.aprovado;

  return (
    <section
      className="superficie superficie-viva rounded-3xl p-5 md:p-6"
      data-testid="dominio-painel"
      aria-label="Avaliação de domínio"
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="secao-olho flex items-center gap-1.5 text-violet-200">
            <Award className="h-3 w-3" /> Avaliação de domínio
          </div>
          <h2 className="mt-1.5 font-display text-lg font-extrabold tracking-tight text-white">
            {sondagem?.titulo}
          </h2>
          <p className="mt-1 text-[13px] text-white/50">
            {resultado?.respondidos ?? 0} de {resultado?.total ?? 0} respondidas
          </p>
        </div>
        <button
          type="button"
          onClick={aoFechar}
          className="chip shrink-0"
          aria-label="Fechar a avaliação e estudar a estação"
          data-testid="dominio-fechar"
        >
          <X className="h-3 w-3" />
        </button>
      </div>

      {/* Os marcadores das três questões. Feedback não dependente de cor: o
          estado também é dito em texto no `title` e no rótulo abaixo. */}
      <ol className="mt-4 flex items-center gap-2" aria-label="Progresso da avaliação">
        {(sondagem?.blocos || []).map((bloco, i) => {
          const certo = respondidos[bloco.bloco_id];
          const respondido = certo !== undefined;
          return (
            <li
              key={bloco.bloco_id}
              className={[
                "flex h-7 w-7 items-center justify-center rounded-full border font-mono-alt text-[11px] font-bold",
                !respondido ? "border-white/15 text-white/40"
                  : certo ? "border-emerald-400/50 bg-emerald-400/15 text-emerald-200"
                  : "border-rose-400/50 bg-rose-400/15 text-rose-200",
              ].join(" ")}
              title={!respondido ? "Ainda não respondida" : certo ? "Acertou" : "Errou"}
            >
              {i + 1}
            </li>
          );
        })}
      </ol>

      {aprovado ? (
        <div className="mt-5 rounded-2xl border border-violet-400/30 bg-violet-500/10 p-5 text-center" data-testid="dominio-aprovado">
          <ShieldCheck className="mx-auto h-6 w-6 text-violet-200" />
          <p className="mt-2 font-display text-lg font-extrabold tracking-tight text-white">
            Você já sabia disto.
          </p>
          <p className="mt-1 text-sm text-white/60">
            A estação foi marcada como <strong className="font-semibold text-violet-200">pulada
            por domínio</strong> — e não como estudada, porque não foi. A próxima já está liberada.
          </p>
        </div>
      ) : reprovado ? (
        <div className="mt-5 rounded-2xl border border-amber-400/30 bg-amber-500/10 p-5" data-testid="dominio-reprovado">
          <p className="font-display text-base font-bold tracking-tight text-white">
            Ainda não é domínio — e tudo bem.
          </p>
          <p className="mt-1 text-sm text-white/60">
            Acertar depois de errar mostra persistência, que é outra coisa. Estude a estação:
            o que você respondeu aqui já está contando.
          </p>
          <button
            type="button"
            onClick={aoFechar}
            className="pill btn-sapiens mt-4 inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold"
            data-testid="dominio-ir-estudar"
          >
            <BookOpen className="h-4 w-4" /> Estudar a estação <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <div className="mt-5 space-y-4">
          {(sondagem?.blocos || []).map((bloco) => (
            <Bloco
              key={bloco.bloco_id}
              bloco={bloco}
              progresso={undefined}
              aoResponder={responder}
              aoVer={() => {}}
            />
          ))}
        </div>
      )}
    </section>
  );
}
