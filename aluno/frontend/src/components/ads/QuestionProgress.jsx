import { useEffect, useRef, useState } from "react";
import { Check } from "lucide-react";

/**
 * O PROGRESSO DE UMA RODADA — 1/10 até 10/10.
 *
 * Dez é o número real do produto, não um arredondamento de anúncio:
 * `RODADA_TAMANHO = 10` no frontend (`pages/Provas.jsx`) e no backend
 * (`firestore_routes.py`). Uma rodada de dez questões é a unidade que fecha
 * com devolutiva — acertos, evolução sobre a rodada anterior e padrões de
 * erro, tudo determinístico e de graça. É por isso que a landing do ângulo
 * "desafio" pode dizer "10 questões" sem inventar nada.
 *
 * ---------------------------------------------------------------------------
 * A ANIMAÇÃO SÓ RODA QUANDO A PEÇA ESTÁ NA TELA, E NUNCA DUAS VEZES
 * ---------------------------------------------------------------------------
 *
 * Um contador que já terminou antes de a pessoa rolar até ele é um contador
 * que ninguém viu — e um `setInterval` rodando desde a montagem gasta quadro
 * de celular enquanto ainda se lê o herói. `IntersectionObserver` resolve os
 * dois: nativo, sem biblioteca, e o observador se desliga no primeiro disparo.
 *
 * E ele respeita `prefers-reduced-motion`: quem pediu menos movimento ao
 * sistema recebe a barra já cheia, não uma versão mais lenta do mesmo efeito.
 */
const TOTAL = 10;

export default function QuestionProgress({ legenda = "Seu resultado mostra onde concentrar seus estudos." }) {
  const [feitas, setFeitas] = useState(0);
  const caixa = useRef(null);

  useEffect(() => {
    const alvo = caixa.current;
    if (!alvo) return undefined;

    const semMovimento =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (semMovimento || typeof IntersectionObserver === "undefined") {
      setFeitas(TOTAL);
      return undefined;
    }

    let relogio = null;
    let comecou = false;

    const comecar = () => {
      if (comecou) return;
      comecou = true;
      observador.disconnect();
      clearTimeout(rede);
      relogio = setInterval(() => {
        setFeitas((n) => {
          if (n >= TOTAL) {
            clearInterval(relogio);
            return n;
          }
          return n + 1;
        });
      }, 220);
    };

    const observador = new IntersectionObserver(
      ([entrada]) => { if (entrada.isIntersecting) comecar(); },
      { threshold: 0.4 },
    );
    observador.observe(alvo);

    /**
     * A rede de segurança — e ela não é paranoia, é medição.
     *
     * A primeira notificação de um `IntersectionObserver` só é entregue numa
     * oportunidade de renderização. Numa aba que o navegador está segurando
     * (painel escondido, quadro estrangulado, aba em segundo plano no
     * instante em que a página abriu), essa oportunidade pode não chegar — e
     * foi exatamente o que apareceu na verificação desta peça: o contador
     * ficou em **0/10 por seis segundos**, com o cartão inteiro dentro da
     * tela, e só andou quando uma rolagem forçou um quadro.
     *
     * Num navegador de verdade isso dispara no primeiro quadro e esta linha
     * nunca roda. O ponto é o outro caso: um demo congelado em zero não é uma
     * animação que não aconteceu, é uma landing afirmando que o produto trava.
     * Depois de 1,4s a peça começa sozinha, tenha ou não chegado o aviso.
     */
    const rede = setTimeout(comecar, 1400);

    return () => {
      observador.disconnect();
      clearTimeout(rede);
      if (relogio) clearInterval(relogio);
    };
  }, []);

  const completo = feitas >= TOTAL;

  return (
    <section
      ref={caixa}
      className="superficie rounded-3xl p-5 md:p-6"
      data-testid="ads-progresso"
      data-completo={completo ? "1" : "0"}
    >
      <div className="flex items-baseline justify-between gap-3">
        <div className="secao-olho">Uma rodada</div>
        {/* `font-mono-alt` é tabular: um contador que troca de largura a cada
            dígito faz a linha inteira dançar. */}
        <div className="font-mono-alt text-sm font-bold text-white/80" data-testid="ads-progresso-contador">
          {feitas}/{TOTAL}
        </div>
      </div>

      {/* Dez marcas, uma por questão. Não é uma barra contínua de propósito:
          a pessoa precisa ler "são dez e são poucas", e uma barra a 30% lê
          como "ainda falta muito". */}
      <div className="mt-4 flex gap-1.5" aria-hidden="true">
        {Array.from({ length: TOTAL }, (_, i) => (
          <span
            key={i}
            className={`h-2 flex-1 rounded-full transition-colors duration-300 ${
              i < feitas ? "bg-[#4FD9FF]" : "bg-white/10"
            }`}
          />
        ))}
      </div>

      <p className="sr-only">{feitas} de {TOTAL} questões respondidas.</p>

      <div className="mt-5 min-h-[44px]">
        {completo ? (
          <div className="flex items-start gap-2.5" data-testid="ads-progresso-fim">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#4FD9FF]/15 text-[#4FD9FF]">
              <Check className="h-3.5 w-3.5" />
            </span>
            <p className="text-[14px] leading-relaxed text-white/75">{legenda}</p>
          </div>
        ) : (
          <p className="text-[14px] leading-relaxed text-white/40">
            Cada resposta entra na leitura. No fim da rodada, a devolutiva.
          </p>
        )}
      </div>
    </section>
  );
}
