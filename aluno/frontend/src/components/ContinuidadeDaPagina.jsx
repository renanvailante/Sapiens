import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

/**
 * A PÁGINA DIZ QUE CONTINUA.
 *
 * O problema, medido tela a tela em 2026-09-18: quase toda página do produto
 * TERMINA visualmente antes de o conteúdo acabar. A última coisa dentro da
 * primeira dobra é um card com borda fechada, e abaixo dele vem o fundo — que
 * é exatamente o que uma página acabada também mostra. O aluno não tem como
 * distinguir "acabou" de "tem mais oito seções", e a diferença entre as duas
 * leituras é o produto inteiro: o Painel tem sete dobras, a Landing tem doze.
 *
 * O aluno não rola porque desconfia que há mais. Ele rola quando VÊ que há.
 *
 * A PEÇA. Um véu fixo no pé da janela, que escurece o conteúdo contra o fundo
 * da página em vez de deixá-lo terminar no vazio. Um bloco cortado no meio por
 * uma sombra é a pista mais antiga e mais barata de continuidade que existe em
 * tipografia — é o mesmo que uma coluna de jornal cortada pela dobra do papel.
 * Ele não escreve "role para baixo", não aponta seta nenhuma e não ocupa um
 * pixel de layout: é `pointer-events: none` sobre o que já estava lá.
 *
 * POR QUE AQUI, E NÃO EM CADA TELA. Pelo mesmo motivo da `BarraInferior` e do
 * `LembrarComAMentis`: são 52 páginas, sete usam a casca comum (`Tela.jsx`) e
 * as outras 45 montam a própria. Uma linha por tela garantiria que a próxima
 * tela nova nasceria sem a pista — e a régua do usuário é "TODA página com
 * conteúdo abaixo da dobra indica que continua", não "as que alguém lembrou".
 *
 * O ESTADO REAL DA ROLAGEM, e não um enfeite permanente. O componente publica
 * `--pagina-restante` (0 a 1) na raiz do documento, e o CSS usa esse número
 * como opacidade do véu:
 *
 * · página que cabe na janela ............ 0   — véu invisível, nada a indicar
 * · muito conteúdo abaixo ................ 1   — pista no máximo
 * · chegando ao fim (últimos ~140px) ..... 1→0 — a pista se apaga sozinha
 * · fim da página ........................ 0   — a última seção encerra limpa
 *
 * É a regra 5 do pedido ("considere o estado real do scroll") virada em uma
 * variável só, que qualquer outra peça do sistema pode ler depois.
 *
 * MEDIÇÃO. `scrollHeight - innerHeight - scrollY` é a conta inteira. Ela roda
 * dentro de um `requestAnimationFrame` (nunca duas vezes no mesmo quadro) e é
 * disparada por quatro coisas: rolagem, redimensionamento, troca de rota e
 * — a que importa mais neste produto — mutação do conteúdo, porque quase toda
 * tela nasce em esqueleto e CRESCE quando a API responde. Sem o
 * `ResizeObserver`, uma página que chega curta e fica longa ficaria sem pista
 * até o aluno tocar na tela, que é justamente quando ela não serve mais.
 */

// A janela em que a pista se apaga. 140px porque é pouco mais que uma dobra de
// card (`.superficie` com padding de 20px e duas linhas de texto): quando só
// isso falta, o aluno já enxerga o fim de verdade e a sombra viraria mentira.
const JANELA_DE_APAGAMENTO = 140;

// Abaixo disto a conta é ruído: um resto de 24px é arredondamento de zoom, de
// barra de endereço do iOS encolhendo, de subpixel — não é conteúdo.
const RESTO_IRRELEVANTE = 24;

// O fecho só aparece a partir daqui. O limite é generoso de propósito: o
// próprio traço ocupa 65px com as margens, e uma página que transbordava por
// menos que isso passaria a transbordar POR CAUSA dele. Acima de 200px de
// rolagem, a página rola por mérito do conteúdo.
const ROLAGEM_MINIMA_PARA_FECHO = 200;

/**
 * Quanto da pista mostrar, dado o estado da rolagem. Função pura e exportada
 * porque é ELA a regra do pedido — "considere o estado real do scroll" — e uma
 * regra que só existe dentro de um `useEffect` não pode ser verificada sem um
 * navegador. Ver `ContinuidadeDaPagina.test.js`.
 */
export function forcaDaPista(alturaTotal, alturaDaJanela, rolagem) {
  const restante = alturaTotal - alturaDaJanela - rolagem;
  const bruto = (restante - RESTO_IRRELEVANTE) / JANELA_DE_APAGAMENTO;
  return Math.max(0, Math.min(1, bruto));
}

export default function ContinuidadeDaPagina() {
  const { pathname } = useLocation();
  const [rolavel, setRolavel] = useState(false);
  // A barra inferior existe nesta rota? Ela some na landing, no login e nas
  // telas de prova (ela mesma decide — ver `BarraInferior.jsx`), e o véu tem
  // de encostar no pé da janela quando ela não está lá. Medir a presença é
  // mais honesto que supor pela largura: supondo, a landing no celular ficava
  // com 68px de conteúdo sem véu embaixo do véu.
  const [temBarra, setTemBarra] = useState(false);

  useEffect(() => {
    const raiz = document.documentElement;
    let quadro = 0;

    const medir = () => {
      quadro = 0;
      const valor = forcaDaPista(
        raiz.scrollHeight,
        window.innerHeight,
        window.scrollY || raiz.scrollTop || 0,
      );
      // Duas casas: o suficiente para a transição parecer contínua e pouco o
      // bastante para não reescrever o estilo a cada pixel de rolagem.
      raiz.style.setProperty("--pagina-restante", valor.toFixed(2));

      // A página ROLA? É outra pergunta, e não se responde com a de cima: o
      // véu depende de quanto falta AGORA (que no fim da página é zero), o
      // fecho depende de a página ter fim diferente do topo (que no fim da
      // página continua sendo verdade).
      //
      // Estado do React, e não uma variável CSS: o traço precisa SAIR DO
      // FLUXO em página curta. Escondê-lo por opacidade deixaria 65px de
      // margem fantasma no pé — e numa página quase do tamanho da janela
      // esses 65px a fariam rolar, ligando o fecho que acabou de ser
      // escondido. `setRolavel` só dispara render quando o valor VIRA.
      setRolavel(raiz.scrollHeight - window.innerHeight > ROLAGEM_MINIMA_PARA_FECHO);
      setTemBarra(!!document.querySelector(".barra-inferior"));
    };

    const agendar = () => {
      if (quadro) return;
      quadro = requestAnimationFrame(medir);
    };

    medir();
    window.addEventListener("scroll", agendar, { passive: true });
    window.addEventListener("resize", agendar);

    // O conteúdo cresce depois da primeira pintura em quase toda tela deste
    // produto (esqueleto → resposta da API). `ResizeObserver` no `body` é o
    // único jeito de saber disso sem cada tela avisar.
    const observador =
      typeof ResizeObserver !== "undefined" ? new ResizeObserver(agendar) : null;
    if (observador) observador.observe(document.body);

    return () => {
      if (quadro) cancelAnimationFrame(quadro);
      window.removeEventListener("scroll", agendar);
      window.removeEventListener("resize", agendar);
      if (observador) observador.disconnect();
      raiz.style.removeProperty("--pagina-restante");
    };
  }, [pathname]);

  return (
    <>
      {/* O FECHO. Fica aqui, e não em cada tela, pela mesma razão do véu — e
          por uma a mais: a regra é "só a última seção encerra", e uma regra
          que depende de 52 autores lembrarem dela não é uma regra.

          Em fluxo normal, no fim do documento: as peças acima (`BarraInferior`,
          `MentisWidget`, `LembrarComAMentis`) são todas `fixed`, então este
          traço cai exatamente depois do conteúdo da rota. Ele some sozinho em
          página que não rola — ver `ROLAGEM_MINIMA_PARA_FECHO`. */}
      {rolavel && <hr className="fim-da-pagina" aria-hidden="true" />}
      <div
        className={`veu-continua${temBarra ? " veu-continua--acima-da-barra" : ""}`}
        aria-hidden="true"
      />
    </>
  );
}
