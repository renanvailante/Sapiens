/**
 * A ordem da trilha — uma só, para o produto inteiro.
 *
 * Esta ordem já morava dentro de `TrilhaDeMissoes.jsx`, com um comentário
 * avisando que duas cópias dela em telas diferentes divergiriam. Quando o
 * Painel passou a anunciar QUAL é o próximo passo (2026-09-16), a segunda
 * cópia deixou de ser hipótese: o desenho da trilha e a frase que diz "sua
 * próxima missão é esta" têm de apontar para o MESMO nó, ou o produto
 * contradiz a si mesmo na mesma dobra da tela.
 *
 * A regra, e o porquê de cada degrau:
 *
 * 1. **Uma dominada na frente.** Só uma, e só para a trilha não começar em
 *    terreno desconhecido: o primeiro nó é uma vitória que o aluno já teve.
 * 2. **O que foi praticado e ainda não é forte, do pior para o melhor.** É
 *    onde o estudo rende mais, e é medida real — `percentual` de acertos.
 * 3. **O que ainda não foi tocado.** Território novo vem por último: tratar
 *    lacuna conhecida antes de abrir frente nova.
 *
 * `missaoAtual` devolve o nó em que o aluno ESTÁ — o primeiro que não está
 * dominado. É o mesmo nó que a trilha desenha com halo e com a Mentis ao
 * lado.
 */

export function ordenarMissoes(habilidades, limite = Infinity) {
  const todas = habilidades || [];
  const fracas = todas
    .filter((h) => h.respondidas > 0 && h.classificacao !== "forte")
    .sort((a, b) => (a.percentual ?? 100) - (b.percentual ?? 100));
  const dominadas = todas.filter((h) => h.classificacao === "forte").slice(0, 1);
  const intocadas = todas.filter((h) => !h.respondidas);
  return [...dominadas, ...fracas, ...intocadas].slice(0, limite);
}

export function missaoAtual(habilidades) {
  return ordenarMissoes(habilidades).find((h) => h.classificacao !== "forte") || null;
}
