/**
 * O argumento de venda da aula ao vivo — um por aluno, feito do que ELE fez.
 *
 * O produto tem uma aula por semana com o 1º colocado de Medicina da USP, e
 * 60 minutos com perguntas abertas no fim. O anúncio genérico ("toda quinta,
 * 200 Sparks") diz o que é; não diz por que é para ESTA pessoa. Este módulo
 * responde a segunda pergunta, e responde com o que o aluno já provou sobre
 * si mesmo: a causa raiz que mais se repete nos erros dele, a área que ele
 * menos acerta, a competência de redação que menos pontuou, quantas quintas
 * ainda cabem antes da prova.
 *
 * **Três regras, e elas não são decoração:**
 *
 * 1. **Toda frase é aritmética sobre dado que o aluno gerou.** Nada de
 *    "últimas vagas", "só hoje" ou contador falso. Se o número não existe, a
 *    frase não aparece — `argumentoDaLive` devolve `null` e a tela cai no
 *    anúncio genérico, que é honesto por ser genérico.
 * 2. **Nunca se promete o CONTEÚDO da aula.** Não sabemos o que ele vai
 *    resolver na quinta; sabemos que os últimos minutos são de perguntas
 *    abertas (é o que a página promete e o que o produto combinou). Então o
 *    convite é sempre "leve esta pergunta", nunca "ele vai ensinar isto".
 * 3. **Não se vende o que a pessoa já tem.** Quem tem a live inclusa no
 *    pacote recebe o mesmo argumento com outra finalidade: comparecer, não
 *    comprar. Repetir a oferta a quem já pagou é o jeito mais rápido de fazer
 *    a pessoa duvidar do que comprou.
 *
 * Roda no NAVEGADOR, de propósito, e sem nenhuma requisição nova: o Painel já
 * carrega os sinais todos para desenhar "onde focar", e uma leitura do
 * Firestore por abertura de painel só para escolher uma frase violaria a
 * disciplina de leitura do produto (ver `lib/live.js`, mesmo raciocínio). Os
 * PREÇOS, esses, nunca são inventados aqui: entram como parâmetro, vindos do
 * catálogo do servidor (`GET /sparks/packages`).
 */

/** Uma frase só sobrevive se tiver número verdadeiro atrás. */
const pct = (n) => `${Math.round(n)}%`;

/**
 * Todos os argumentos VERDADEIROS para este aluno, do mais forte para o mais
 * fraco. A tela usa o primeiro; a lista inteira existe para quem quiser
 * mostrar dois (a aba de Cursos mostra) e para deixar o teste ler a ordem.
 *
 * `forca` é a régua: quanto mais específico do aluno, mais forte. Uma causa
 * raiz identificada nas respostas dele ganha de qualquer frase sobre o
 * calendário, que é igual para todo mundo.
 */
export function argumentosDaLive({
  fracos = [],
  focos = [],
  quintasRestantes = 0,
  diasAtivosNaSemana = 0,
  ofensiva = 0,
} = {}) {
  const lista = [];

  // 1. A causa raiz. É o argumento mais forte que o produto tem: não é "você
  //    vai mal em matemática", é "o padrão que se repete nos SEUS erros tem
  //    nome". Só aparece com `erro_dominante` — sem causa nomeada, esta linha
  //    seria a de desempenho com roupa de diagnóstico.
  const raiz = fracos.find((f) => f?.erro_dominante?.nome);
  if (raiz) {
    const medida =
      raiz.percentual_acerto != null
        ? ` Você acerta ${pct(raiz.percentual_acerto)} em ${raiz.processo_nome}.`
        : "";
    lista.push({
      id: "causa-raiz",
      forca: 100,
      titulo: "A pergunta que você devia levar para quinta",
      texto:
        `O padrão que mais se repete nos seus erros é «${raiz.erro_dominante.nome}».${medida}` +
        " Os últimos minutos da aula são de perguntas abertas — essa é a sua.",
    });
  }

  // 2. O ponto fraco medido. `focos` já vem pronto e ordenado do Painel
  //    (área mais fraca do gabarito, habilidade fraca do treino, competência
  //    da redação) e cada item carrega a própria evidência em texto — que é
  //    exatamente o número que esta frase precisa.
  const foco = focos.find((f) => f?.titulo && f?.evidencia);
  if (foco) {
    lista.push({
      id: "ponto-fraco",
      forca: 80,
      titulo: `Leve ${foco.titulo} para a aula`,
      // `evidencia` vem pronta do Painel em formatos diferentes ("38% de
      // acerto em 60 questões", "80 de 200 pontos nessa competência"), então
      // o prefixo tem de ser neutro o bastante para caber em todos.
      texto: `Hoje: ${foco.evidencia}. Quinta você pergunta direto a quem passou em 1º lugar como ele resolvia isso.`,
    });
  }

  // 3. O calendário. Igual para todo mundo, então vale menos que os dois de
  //    cima — mas é aritmética pura (quantas quintas cabem até a prova) e
  //    fica forte sozinha quando o número já é pequeno.
  if (quintasRestantes > 0 && quintasRestantes <= 6) {
    lista.push({
      id: "quintas-restantes",
      forca: 70,
      titulo:
        quintasRestantes === 1
          ? "Esta é a última aula antes da prova"
          : `Só cabem mais ${quintasRestantes} aulas antes da prova`,
      texto:
        quintasRestantes === 1
          ? "Depois desta não existe outra quinta antes do ENEM."
          : `São ${quintasRestantes} quintas até o ENEM. A que passar não volta.`,
    });
  }

  // 4. A rotina. Para quem já está estudando, o argumento não é urgência: é
  //    encaixe. 60 minutos, uma vez por semana, em cima de uma rotina que ele
  //    já provou ter.
  if (ofensiva >= 3 || diasAtivosNaSemana >= 3) {
    const base =
      ofensiva >= 3
        ? `Você está há ${ofensiva} dias seguidos estudando.`
        : `Você estudou ${diasAtivosNaSemana} dos últimos 7 dias.`;
    lista.push({
      id: "rotina",
      forca: 40,
      titulo: "Cabe na sua semana",
      texto: `${base} A aula é uma vez por semana e dura 60 minutos — é a única hora marcada do seu cronograma.`,
    });
  }

  // 5. O aluno novo, que ainda não gerou dado nenhum. Não dá para
  //    personalizar sem inventar, então a frase é o que a aula É — e isso já
  //    é verdade suficiente para vender.
  lista.push({
    id: "generico",
    forca: 10,
    titulo: "60 minutos com quem passou em 1º lugar",
    texto:
      "Não é aula gravada: ele resolve questão na sua frente e responde perguntas ao vivo, toda quinta.",
  });

  return lista.sort((a, b) => b.forca - a.forca);
}

/** O argumento mais forte, ou `null` quando só sobrou o genérico e a tela
 *  prefere não dizer nada. */
export function argumentoDaLive(sinais = {}) {
  const [primeiro] = argumentosDaLive(sinais);
  return primeiro || null;
}

/**
 * O que o aluno gastaria comprando avulso o que o pacote já inclui.
 *
 * **É a única aritmética de venda do produto, e ela tem de ser conferível.**
 * As quintas que ainda cabem antes da prova vezes o preço da edição, mais os
 * cursos vezes o preço do curso. Nada de "economize até X": o número é uma
 * multiplicação que o aluno pode refazer de cabeça.
 *
 * `null` quando não há o que comparar (sem pacote, sem preço, ou quando o
 * aluno já tem os dois direitos — aí não existe compra a fazer).
 */
export function economiaDoPacote({
  pacote,
  quintasRestantes = 0,
  precos,
  direitos = {},
} = {}) {
  if (!pacote || !precos) return null;

  const daLive = (pacote.direitos || []).includes("lives_inclusas");
  const dosCursos = (pacote.direitos || []).includes("cursos_inclusos");
  // Só conta o que ESTE pacote inclui E o aluno ainda não tem. Somar um
  // direito que ele já comprou inflaria a conta — e seria mentira na parte
  // que mais importa.
  const contaLives = daLive && !direitos.lives_inclusas;
  const contaCursos = dosCursos && !direitos.cursos_inclusos;
  if (!contaLives && !contaCursos) return null;

  const sparksLives = contaLives ? quintasRestantes * (precos.live_sparks || 0) : 0;
  const sparksCursos = contaCursos
    ? (precos.total_cursos || 0) * (precos.curso_sparks || 0)
    : 0;
  const total = sparksLives + sparksCursos;
  if (total <= 0) return null;

  const partes = [];
  if (sparksLives > 0) {
    partes.push(
      `${quintasRestantes} ${quintasRestantes === 1 ? "aula ao vivo" : "aulas ao vivo"} × ${precos.live_sparks} = ${sparksLives} Sparks`,
    );
  }
  if (sparksCursos > 0) {
    partes.push(
      `${precos.total_cursos} cursos × ${precos.curso_sparks} = ${sparksCursos} Sparks`,
    );
  }

  return {
    sparksLives,
    sparksCursos,
    total,
    partes,
    // O pacote inclui tudo isso E credita os Sparks. As duas coisas são
    // verdade ao mesmo tempo, e é por isso que a frase não precisa de
    // adjetivo nenhum para funcionar.
    sparksDoPacote: pacote.sparks_amount,
    incluiLives: contaLives,
    incluiCursos: contaCursos,
  };
}

/** O pacote VISÍVEL mais barato que concede este direito — a porta de entrada,
 *  nunca a mais cara. Espelha `sparks_store.pacote_com_direito`: o catálogo
 *  chega em ordem crescente de preço e quem decide continua sendo o servidor. */
export function pacoteComDireito(pacotes = [], direito) {
  return (
    pacotes.find((p) => !p.oculto && (p.direitos || []).includes(direito)) || null
  );
}
