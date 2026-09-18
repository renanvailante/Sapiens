import { useCallback, useEffect, useRef, useState } from "react";

/**
 * A FILEIRA QUE DIZ QUE CONTINUA — o mesmo problema do véu, deitado.
 *
 * Uma fileira rolável cujo último card visível termina exatamente na borda da
 * tela parece uma fileira COMPLETA. Não há nada na imagem que distinga "são
 * estes quatro" de "são estes quatro e mais quatro à direita", e o aluno não
 * arrasta o que não sabe que existe. Na tira de atalhos do celular isso vale
 * oito portas do produto: as quatro últimas nunca eram tocadas.
 *
 * A correção não é uma seta na lateral. É deixar o próximo card visivelmente
 * CORTADO pela borda — que é o que o olho já sabe ler desde a primeira revista
 * com página sangrada. Aqui o corte é uma máscara que dissolve os últimos
 * pixels: o conteúdo não some, ele se apaga, e "se apagando" é a única forma
 * gráfica que significa "tem mais" em vez de "quebrou".
 *
 * O ESTADO REAL DA ROLAGEM, dos dois lados. A máscara da direita só existe
 * enquanto há o que rolar para a direita; assim que a fileira chega ao fim ela
 * sai, porque ali ela seria mentira. E a da esquerda entra quando o aluno já
 * rolou, pelo mesmo motivo: o que ficou para trás também continua existindo.
 * Uma fileira que cabe inteira na tela não recebe máscara nenhuma.
 *
 * COMO SE USA. Substitui o `<div>` do scroller, não envolve um:
 *
 *     <TiraRolavel className="gap-2 px-4 pb-2.5">
 *       {itens.map(...)}
 *     </TiraRolavel>
 *
 * O `flex`, o `overflow-x-auto` e a barra de rolagem invisível já vêm de
 * dentro; o resto (respiro, gap, alinhamento) continua sendo de quem usa.
 */
/**
 * De que lado a fileira continua. Pura e exportada pelo mesmo motivo da
 * `forcaDaPista`: é a regra ("a pista não aparece quando não há mais nada
 * daquele lado"), e regra se trava em teste. Ver `TiraRolavel.test.js`.
 *
 * `folga` de 2px porque `scrollLeft` volta fracionário em tela com zoom ou
 * densidade não inteira: sem ela, a máscara da direita nunca sai — fica
 * eternamente faltando meio pixel para o fim.
 */
export function ondeContinua(rolagem, larguraTotal, larguraVisivel, folga = 2) {
  const maximo = larguraTotal - larguraVisivel;
  return {
    inicio: rolagem > folga,
    fim: rolagem < maximo - folga,
  };
}

/**
 * A MEDIÇÃO, separada do layout — e separada de propósito.
 *
 * Nem todo rolador horizontal deste produto é uma fileira flex. A grade da
 * semana no Cronograma é um grid, o calendário do perfil é um `inline-flex`
 * de colunas e um bloco de curso pode ser uma `<table>`. Todos sofrem do mesmo
 * mal — terminam na borda da tela e por isso parecem inteiros — mas nenhum
 * deles sobrevive a ganhar `display: flex` do envelope.
 *
 * Então o que se compartilha é a MEDIÇÃO e a máscara, não a caixa. Quem já
 * tem o próprio layout chama o hook e espalha `atributos` no elemento que
 * rola; quem só quer uma fileira usa `TiraRolavel` logo abaixo.
 *
 *     const { ref, atributos } = useCortesDaRolagem();
 *     <div ref={ref} {...atributos} className="minha-grade overflow-x-auto">
 */
export function useCortesDaRolagem(dependencia, refExterno = null) {
  // `refExterno` para quem JÁ tem um ref no rolador — o calendário do perfil
  // usa o dele para nascer rolado no dia de hoje. Dois refs no mesmo elemento
  // seria a alternativa, e a segunda atribuição venceria em silêncio.
  const interno = useRef(null);
  const ref = refExterno || interno;
  const [corte, setCorte] = useState({ inicio: false, fim: false });

  const medir = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const { inicio, fim } = ondeContinua(el.scrollLeft, el.scrollWidth, el.clientWidth);
    setCorte((antes) =>
      antes.inicio === inicio && antes.fim === fim ? antes : { inicio, fim },
    );
    // `ref` na lista porque ele é ESCOLHIDO (externo ou interno) e não criado
    // aqui; os dois são estáveis, então na prática a função nunca se refaz.
  }, [ref]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    medir();
    el.addEventListener("scroll", medir, { passive: true });
    window.addEventListener("resize", medir);
    // O conteúdo cresce depois: os atalhos chegam do estado do aluno, os
    // blocos de um curso chegam da API. Sem observar, uma tira que nasce com
    // três itens e recebe mais cinco continua sem máscara.
    const observador =
      typeof ResizeObserver !== "undefined" ? new ResizeObserver(medir) : null;
    if (observador) {
      observador.observe(el);
      for (const filho of el.children) observador.observe(filho);
    }
    return () => {
      el.removeEventListener("scroll", medir);
      window.removeEventListener("resize", medir);
      if (observador) observador.disconnect();
    };
  }, [medir, dependencia, ref]);

  return {
    ref,
    atributos: {
      "data-corta-inicio": corte.inicio ? "1" : "0",
      "data-corta-fim": corte.fim ? "1" : "0",
    },
    corte,
  };
}

export default function TiraRolavel({ className = "", children, testid, ...resto }) {
  const { ref, atributos } = useCortesDaRolagem(children);

  return (
    <div
      ref={ref}
      className={`corta-rolagem tira-rolavel rolagem-invisivel flex overflow-x-auto ${className}`}
      {...atributos}
      data-testid={testid}
      {...resto}
    >
      {children}
    </div>
  );
}
