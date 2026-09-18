/**
 * QUAL CURSO SUGERIR — e com que frase.
 *
 * Lógica pura, sem React e sem rede, para poder ser testada como regra (é o
 * que `recomendacao.test.js` faz) e para ser o ÚNICO lugar que decide isto.
 * A tela desenha o que sai daqui.
 *
 * **O que esta função é hoje:** uma regra determinística sobre o que o aluno
 * já tem e já andou. Ela não chama IA, não inventa desempenho e não afirma
 * nada que os dados não digam — uma recomendação que soa esperta e está
 * errada custa mais confiança do que uma recomendação óbvia e certa.
 *
 * **O que ela vai ser:** o lugar onde a Mentis entra. Quando o motor
 * pedagógico souber dizer "esta pessoa erra conta, não interpretação", a
 * resposta passa a vir do servidor e esta regra vira o fallback de quem ainda
 * não tem trajetória. Por isso a saída já tem o formato de uma recomendação
 * com MOTIVO: trocar a fonte não muda a tela.
 *
 * A ordem das áreas é a mesma prioridade do ENEM que o resto do produto usa
 * (ver `prioridade_enem.py`): Matemática e Redação primeiro, porque é onde
 * uma nota baixa custa mais e onde estudar rende mais rápido.
 */

export const PRIORIDADE_DAS_AREAS = ["matematica", "redacao", "linguagens", "metodo"];

function pesoDaArea(area) {
  const i = PRIORIDADE_DAS_AREAS.indexOf(area);
  return i === -1 ? PRIORIDADE_DAS_AREAS.length : i;
}

/**
 * Os cursos que o aluno começou e não terminou, do mais avançado para o menos.
 * É a lista de "continue aprendendo": quem tem três cursos abertos quer
 * voltar ao que está quase no fim, não ao que abriu uma vez em agosto.
 */
export function emAndamento(cursos = []) {
  return cursos
    .filter((c) => c.tenho_acesso && c.tem_conteudo && c.progresso?.comecou && c.progresso.percentual < 100)
    .sort((a, b) => b.progresso.percentual - a.progresso.percentual);
}

/** Cursos que o aluno pode estudar e ainda não abriu. */
export function naoComecados(cursos = []) {
  return cursos
    .filter((c) => c.tenho_acesso && c.tem_conteudo && !c.progresso?.comecou)
    .sort((a, b) => pesoDaArea(a.area) - pesoDaArea(b.area));
}

/**
 * A ÚNICA sugestão da vez, com o motivo em linguagem de aluno.
 *
 * Uma e não três: uma lista de recomendações é uma decisão devolvida para
 * quem pediu ajuda para decidir. A ordem das perguntas é a ordem do que
 * ajuda mais:
 *
 * 1. tem curso aberto e parado? → volte para ele;
 * 2. tem curso comprado e nunca aberto? → comece pelo de maior peso no ENEM;
 * 3. não tem nenhum no ar? → o que está à venda com conteúdo publicado;
 * 4. nada disso → nenhuma sugestão (e a tela não inventa uma).
 */
export function recomendar(cursos = []) {
  const abertos = emAndamento(cursos);
  if (abertos.length) {
    const c = abertos[0];
    const faltam = (c.progresso.estacoes || 0) - (c.progresso.concluidas || 0);
    return {
      curso: c,
      motivo: faltam === 1
        ? "Falta uma estação para você terminar este curso."
        : `Faltam ${faltam} estações para você terminar este curso.`,
      acao: "Continuar",
      destino: `/cursos/${c.curso_id}`,
    };
  }

  const novos = naoComecados(cursos);
  if (novos.length) {
    const c = novos[0];
    return {
      curso: c,
      motivo: c.area === "matematica"
        ? "É o que mais aparece na prova — e é o erro que não é de interpretação, é de conta."
        : "Você já tem acesso e ainda não abriu.",
      acao: "Começar",
      destino: `/cursos/${c.curso_id}`,
    };
  }

  const aVenda = cursos
    .filter((c) => !c.tenho_acesso && c.tem_conteudo)
    .sort((a, b) => pesoDaArea(a.area) - pesoDaArea(b.area));
  if (aVenda.length) {
    const c = aVenda[0];
    return {
      curso: c,
      motivo: "Este já está no ar — as aulas existem e você pode começar hoje.",
      acao: "Ver o curso",
      destino: "#cursos",
    };
  }
  return null;
}

/**
 * Os cursos agrupados por área, na ordem do catálogo do servidor.
 *
 * Recebe `areas` do servidor (que é quem sabe a hierarquia) e devolve só as
 * que têm curso — área vazia na tela é uma promessa que ninguém fez.
 *
 * **Sem `areas`, devolve um grupo só com o catálogo inteiro.** Não é
 * paranoia: o app e o servidor sobem separados (o front na Cloudflare, o back
 * na Fly), então existe sempre uma janela em que um é mais novo que o outro.
 * Sem esta saída, um front novo contra um servidor velho agrupa zero áreas e
 * a aba de Cursos fica **sem curso nenhum** — a pior falha possível, porque
 * parece que o produto não tem catálogo.
 */
export function porArea(areas = [], cursos = []) {
  const porId = new Map(cursos.map((c) => [c.curso_id, c]));
  const grupos = (areas || [])
    .map((a) => ({
      ...a,
      itens: (a.cursos || []).map((id) => porId.get(id)).filter(Boolean),
    }))
    .filter((a) => a.itens.length);

  if (grupos.length) return grupos;
  if (!cursos.length) return [];
  return [{ area_id: "todos", titulo: "Todos os cursos", chamada: "", itens: cursos }];
}
