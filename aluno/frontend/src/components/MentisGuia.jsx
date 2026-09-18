import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Mentis from "./Mentis";
import MentisPedido from "./MentisPedido";
import { ChevronLeft, ChevronRight, Play, Pause, ArrowRight, Sparkles } from "lucide-react";

/**
 * A MENTIS LENDO O PAINEL COM O ALUNO.
 *
 * A tela tem onze gráficos. Onze gráficos sem ninguém junto viram um painel de
 * controle de avião: tudo verdadeiro, nada acionável. O que transforma isso em
 * produto é alguém que olhe com o aluno e diga **qual deles importa hoje** — e
 * é isso que esta peça faz.
 *
 * Três regras de produto moram aqui:
 *
 * 1. **É de graça e não chama modelo nenhum.** Cada leitura é montada no
 *    servidor a partir dos mesmos números que estão no gráfico ao lado
 *    (`perfil_painel._leituras`). Cobrar Sparks para o aluno saber o que os
 *    próprios dados dele dizem seria cobrar pedágio na porta de casa. O que
 *    custa é a conversa — e aí o preço aparece antes do clique, como em toda
 *    parte (ver `MentisPedido`).
 * 2. **Ela aponta.** Trocar de leitura rola a tela até o gráfico que sustenta
 *    a frase e o acende. Sem isso, o texto vira horóscopo: uma afirmação sobre
 *    o aluno sem a evidência à vista.
 * 3. **Mentor, não bichinho.** A direção de arte da Mentis é explícita quanto
 *    a isso (ver `Mentis.jsx`): ela acompanha, confirma e concentra — não
 *    comemora, não pula e não enche a tela de confete.
 */

const INTERVALO_GUIADO = 9000;

const TOM = {
  bom: { anel: "rgba(95, 233, 188, 0.45)", texto: "text-emerald-700" },
  atencao: { anel: "rgba(255, 201, 120, 0.45)", texto: "text-amber-700" },
  neutro: { anel: "rgba(79, 217, 255, 0.40)", texto: "text-sky-700" },
};

export default function MentisGuia({ leituras, indice, aoTrocar, aoSaldo }) {
  const nav = useNavigate();
  const [guiando, setGuiando] = useState(false);
  const [pedido, setPedido] = useState(null);
  const relogio = useRef(null);

  const total = leituras?.length || 0;
  const atual = total ? leituras[Math.min(indice, total - 1)] : null;

  // O passeio guiado anda sozinho e para sozinho ao chegar no fim — nunca dá
  // a volta. Dar a volta faria a tela parecer um letreiro.
  useEffect(() => {
    clearInterval(relogio.current);
    if (!guiando || total === 0) return undefined;
    relogio.current = setInterval(() => {
      aoTrocar((i) => {
        if (i >= total - 1) {
          setGuiando(false);
          return i;
        }
        return i + 1;
      });
    }, INTERVALO_GUIADO);
    return () => clearInterval(relogio.current);
  }, [guiando, total, aoTrocar]);

  if (!atual) return null;

  const tom = TOM[atual.tom] || TOM.neutro;
  const ir = (delta) => {
    setGuiando(false);
    aoTrocar((i) => Math.max(0, Math.min(total - 1, i + delta)));
  };

  const executar = () => {
    const acao = atual.acao;
    if (!acao) return;
    setGuiando(false);
    if (acao.tipo === "ir") nav(acao.href);
    else setPedido(acao);
  };

  return (
    <>
      <div
        className="card-sapiens rounded-[26px] p-4 md:p-5"
        style={{ boxShadow: `0 0 52px -24px ${tom.anel}, 0 24px 60px -30px rgba(0,0,0,0.9)` }}
        data-testid="mentis-guia"
        data-tour="tour-mentis-guia"
      >
        <div className="flex items-start gap-3 md:gap-4">
          <div className="shrink-0">
            <Mentis
              className="h-14 w-14 md:h-16 md:w-16"
              estado={atual.tom === "atencao" ? "analise" : "confirmando"}
              title="Mentis"
            />
          </div>

          <div className="min-w-0 flex-1">
            <div className="secao-olho flex items-center gap-1.5">
              <Sparkles className="h-3 w-3" /> A Mentis leu o seu painel
            </div>
            <h2
              className="mt-1.5 font-display text-lg font-bold leading-snug tracking-tight text-zinc-950 md:text-xl"
              data-testid="mentis-guia-titulo"
            >
              {atual.titulo}
            </h2>
            <p className="mt-1.5 text-sm leading-relaxed text-zinc-600" data-testid="mentis-guia-texto">
              {atual.texto}
            </p>

            <div className="mt-3.5 flex flex-wrap items-center gap-2">
              {atual.acao && (
                <button
                  type="button"
                  onClick={executar}
                  className="pill btn-sapiens inline-flex min-h-[34px] items-center gap-1.5 rounded-full px-4 py-2 text-xs font-medium"
                  data-testid="mentis-guia-acao"
                >
                  {atual.acao.tipo === "mentis" ? (
                    <Mentis className="h-4 w-4" variante="icone" animada={false} />
                  ) : (
                    <ArrowRight className="h-3.5 w-3.5" />
                  )}
                  {atual.acao.rotulo}
                </button>
              )}
              <button
                type="button"
                onClick={() => setGuiando((g) => !g)}
                className="pill inline-flex min-h-[34px] items-center gap-1.5 rounded-full border border-zinc-200 px-3.5 py-2 text-xs font-medium text-sapiens-navy hover:border-sapiens-accent"
                data-testid="mentis-guia-passeio"
              >
                {guiando ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                {guiando ? "Pausar" : "Me guie pelo painel"}
              </button>
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between gap-3 border-t border-zinc-100 pt-3">
          <button
            type="button"
            onClick={() => ir(-1)}
            disabled={indice === 0}
            aria-label="Leitura anterior"
            className="pill inline-flex h-9 w-9 items-center justify-center rounded-full border border-zinc-200 text-zinc-400 disabled:opacity-30"
            data-testid="mentis-guia-anterior"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>

          {/* Os pontos são navegáveis, não enfeite: cada um é uma leitura, e o
              alvo de toque tem 32px mesmo com o ponto tendo 6. */}
          <div className="flex flex-1 items-center justify-center gap-0.5">
            {leituras.map((l, i) => (
              <button
                key={l.id}
                type="button"
                onClick={() => { setGuiando(false); aoTrocar(() => i); }}
                aria-label={l.titulo}
                aria-current={i === indice}
                className="inline-flex h-8 w-5 items-center justify-center"
              >
                <span
                  className="block h-1.5 rounded-full transition-all"
                  style={{
                    width: i === indice ? 18 : 6,
                    background: i === indice ? "var(--bio-ciano)" : "rgba(175,196,224,0.3)",
                  }}
                />
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => ir(1)}
            disabled={indice >= total - 1}
            aria-label="Próxima leitura"
            className="pill inline-flex h-9 w-9 items-center justify-center rounded-full border border-zinc-200 text-zinc-400 disabled:opacity-30"
            data-testid="mentis-guia-proxima"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {pedido && (
        <MentisPedido
          aberto
          onFechar={() => setPedido(null)}
          assunto={pedido.assunto}
          evidencia={pedido.evidencia}
          onSaldo={aoSaldo}
          testid="mentis-guia-pedido"
        />
      )}
    </>
  );
}
