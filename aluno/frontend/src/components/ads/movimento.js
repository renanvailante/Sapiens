import { useCallback, useEffect, useRef, useState } from "react";

/**
 * O MOVIMENTO DAS DEMONSTRAÇÕES — uma primitiva, quatro demos.
 *
 * As quatro landings mostram coisas diferentes, mas todas mostram a MESMA
 * forma: uma sequência de estados que avança sozinha, começa quando a peça
 * entra na tela, respeita quem pediu menos movimento e não gasta quadro
 * quando ninguém está olhando. Escrever esse relógio quatro vezes é como se
 * ganham quatro comportamentos ligeiramente diferentes para a mesma coisa —
 * e o produto já pagou esse preço em outras áreas.
 *
 * Duas peças, e só duas:
 *
 * - `useNaTela` — "esta caixa está visível?", com a rede de segurança.
 * - `useRoteiro` — o passo atual de uma sequência temporizada.
 */

/** Quem pediu menos movimento ao sistema. Lido na hora, não memorizado: a
 *  preferência pode mudar com a pessoa na página. */
export function semMovimento() {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * `true` a partir do momento em que a caixa aparece na tela. Não volta a
 * `false`: uma revelação que se desfaz ao rolar de volta é um efeito que a
 * pessoa vê duas vezes e acredita zero.
 *
 * > [!warning] A rede de 1,4s não é paranoia, é medição.
 * > A primeira notificação de um `IntersectionObserver` só é entregue numa
 * > oportunidade de renderização. Numa aba que o navegador está segurando
 * > (painel escondido, quadro estrangulado, aba aberta em segundo plano) essa
 * > oportunidade pode não chegar — e numa landing isso significa a
 * > demonstração inteira congelada no primeiro quadro, ou seja, a página
 * > afirmando que o produto trava. Medido de verdade em 2026-09-21: um
 * > contador ficou em 0/10 por seis segundos com o cartão inteiro visível.
 */
export function useNaTela(margem = "0px 0px -15% 0px") {
  const alvo = useRef(null);
  const [visivel, setVisivel] = useState(false);

  useEffect(() => {
    const el = alvo.current;
    if (!el) return undefined;
    if (typeof IntersectionObserver === "undefined") {
      setVisivel(true);
      return undefined;
    }

    const observador = new IntersectionObserver(
      ([entrada]) => {
        if (!entrada.isIntersecting) return;
        setVisivel(true);
        observador.disconnect();
      },
      { rootMargin: margem, threshold: 0.15 },
    );
    observador.observe(el);

    const rede = setTimeout(() => setVisivel(true), 1400);
    return () => {
      observador.disconnect();
      clearTimeout(rede);
    };
  }, [margem]);

  return [alvo, visivel];
}

/**
 * O PASSO ATUAL DE UMA SEQUÊNCIA.
 *
 * `duracoes` é um array com o tempo de cada passo em milissegundos — array e
 * não um número único porque os passos NÃO duram o mesmo: "analisando" quer
 * respirar, "erro identificado" quer ser lido, e a última tela quer ficar de
 * pé antes de o laço recomeçar. Um valor só produziria uma sequência que
 * corre onde deveria pausar.
 *
 * Três comportamentos que valem para as quatro demos:
 *
 * - **Só anda na tela.** Começa quando a caixa aparece (`useNaTela`).
 * - **Para quando a aba some.** `document.hidden` congela o relógio; voltar
 *   continua de onde parou. Uma demo girando numa aba de fundo é bateria de
 *   celular gasta para ninguém.
 * - **`prefers-reduced-motion` pula para o fim.** Não é uma versão mais lenta
 *   do mesmo efeito: quem pediu menos movimento recebe o RESULTADO, que é o
 *   que a demonstração existe para mostrar, sem a passagem animada.
 *
 * Devolve `[ref, passo, { reiniciar, ultimo, congelado, visivel }]`.
 * `reiniciar` é o botão de rever — e é ele que torna a demo acessível a quem chegou atrasado
 * na animação, em vez de obrigar a pessoa a recarregar a página.
 */
export function useRoteiro(duracoes, { laco = true, pausaDoLaco = 1600 } = {}) {
  const [alvo, visivel] = useNaTela();
  const total = duracoes.length;
  const reduzido = semMovimento();

  const [passo, setPasso] = useState(0);
  // `congelado` é o estado de quem pediu menos movimento: a sequência não
  // corre, e a peça se desenha direto no último quadro.
  const [congelado] = useState(reduzido);

  useEffect(() => {
    if (!visivel) return undefined;
    if (reduzido) {
      setPasso(total - 1);
      return undefined;
    }

    let relogio = null;

    const agendar = () => {
      clearTimeout(relogio);
      setPasso((atual) => {
        const ultimo = atual >= total - 1;
        if (ultimo && !laco) return atual;
        relogio = setTimeout(agendar, ultimo ? pausaDoLaco : duracoes[atual]);
        return ultimo ? 0 : atual + 1;
      });
    };

    // O primeiro passo já está na tela; o relógio agenda a TRANSIÇÃO para o
    // segundo. Agendar o primeiro passo também faria a demo abrir vazia.
    relogio = setTimeout(agendar, duracoes[0]);

    const aoTrocarDeAba = () => {
      if (document.hidden) clearTimeout(relogio);
      else relogio = setTimeout(agendar, duracoes[0]);
    };
    document.addEventListener("visibilitychange", aoTrocarDeAba);

    return () => {
      clearTimeout(relogio);
      document.removeEventListener("visibilitychange", aoTrocarDeAba);
    };
    // `duracoes` é um literal estável no módulo de cada demo; incluí-lo na
    // lista faria o roteiro reiniciar a cada render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visivel, reduzido, total, laco, pausaDoLaco]);

  const reiniciar = useCallback(() => setPasso(0), []);

  return [alvo, passo, { reiniciar, ultimo: total - 1, congelado, visivel }];
}
