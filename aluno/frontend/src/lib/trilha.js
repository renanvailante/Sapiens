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

/**
 * A PRÓXIMA MISSÃO, a partir do mapa já com a camada de progressão aplicada
 * (`aplicarProgressao`) — é o que o desfecho de uma missão oferece.
 *
 * O desfecho terminava em "Voltar ao mapa": o aluno que acabava cinco
 * questões tinha de reabrir o globo 3D, achar um ponto e decidir sozinho, que
 * é exatamente o momento em que se fecha o app. A escolha segue a MESMA regra
 * da trilha acima, restrita ao que o mapa já deixa tocar (`acesso ===
 * "acessivel"`) e sem repetir a missão que acabou (as questões dela seriam as
 * mesmas):
 *
 *   1. lacuna conhecida — praticada e ainda não dominada, do pior acerto para
 *      o melhor;
 *   2. território que ESTA missão abriu — vizinho dela no grafo, ainda sem
 *      resposta. É o desbloqueio que o aluno acabou de ver acontecer;
 *   3. qualquer outro ponto acessível ainda não tocado.
 *
 * `null` quando não sobra nada — aí o desfecho só oferece o mapa.
 */
export function proximaMissaoNoMapa(biomas, arestas, atualId) {
  const nos = (biomas || []).flatMap((b) => b?.nodes || []);
  const acessiveis = nos.filter((n) => n?.acesso === "acessivel" && n.hab_id !== atualId);
  const taxa = (n) => (n.respondidas ? (n.acertos || 0) / n.respondidas : 1);

  const lacunas = acessiveis
    .filter((n) => n.respondidas > 0 && (n.estadoBackend || n.estado) !== "mastered")
    .sort((a, b) => taxa(a) - taxa(b));
  if (lacunas.length) return lacunas[0];

  const vizinhos = new Set(
    (arestas || []).flatMap((a) =>
      a.source === atualId ? [a.target] : a.target === atualId ? [a.source] : [],
    ),
  );
  const intocados = acessiveis.filter((n) => !n.respondidas);
  return intocados.find((n) => vizinhos.has(n.hab_id)) || intocados[0] || null;
}
