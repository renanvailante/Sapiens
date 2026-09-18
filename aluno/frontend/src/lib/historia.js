/**
 * A HISTÓRIA do Sapiens — a copy da landing em um lugar só.
 *
 * Estrutura: os sete passos de Donald Miller (*Building a StoryBrand*). A
 * regra que ela impõe e que este arquivo existe para proteger: **o herói é o
 * aluno, nunca a marca**. O Sapiens é o guia. Toda frase daqui passa por um
 * teste simples — se ela elogia o produto em vez de dizer o que muda na vida
 * de quem lê, ela está errada.
 *
 *   1. herói ................ o vestibulando
 *   2. problema ............. passar; sem teoria individual e sem método
 *   3. guia ................. a Mentis (empatia + autoridade) e Vitor Lara
 *   4. plano ................ três passos, ditos como ordem, não como menu
 *   5. convite à ação ....... um CTA direto, repetido; um transicional
 *   6. evita o fracasso ..... o que está em jogo se nada mudar
 *   7. termina em sucesso ... o dia da lista, descrito em detalhe
 *
 * Copy é constante de módulo e não rota: a landing roda sem sessão e sem
 * backend. Mesmo critério de `lib/mentor.js` e `lib/enem.js`.
 *
 * ATENÇÃO: o bloco `FAQ` daqui é espelhado em JSON-LD dentro de
 * `public/index.html` (FAQPage). O Google exige que a resposta marcada seja a
 * MESMA que a pessoa vê na tela — mudar uma sem a outra é motivo de perda do
 * rich result. Mudou aqui, muda lá.
 */

/** 2. O PROBLEMA. Vilão externo: estudar no escuro. */
export const VILAO = "estudar no escuro";

export const PROBLEMA = [
  {
    titulo: "Você estuda muito e não sabe se está funcionando",
    corpo:
      "Horas de videoaula, caderno cheio, simulado no domingo. E no fim do mês a nota é a mesma. O problema não é esforço — é não ter medida do que o esforço mudou.",
  },
  {
    titulo: "Nenhuma teoria é sua",
    corpo:
      "Cursinho é feito para a média da sala. Mas ninguém erra pela média: você erra por um padrão seu — leitura apressada, excesso de confiança, duas variáveis ao mesmo tempo — e nenhuma apostila foi escrita para ele.",
  },
  {
    titulo: "Ninguém te deu um método",
    corpo:
      "\"Faz questão\" não é método. Método é saber o que estudar hoje, por quê, por quanto tempo e quando revisar — e saber disso na segunda-feira de manhã, sem decidir nada.",
  },
];

/** O que o problema custa por dentro. É a dor, dita sem crueldade. */
export const DOR_INTERNA =
  "O que dá medo não é a prova. É a lista saindo e o seu nome não estar nela — de novo — depois de um ano inteiro dizendo para todo mundo que desta vez ia dar.";

/** 3. O GUIA — autoridade que não afasta. Referências REAIS; nada aqui é
 *  enfeite: cada uma corresponde a um mecanismo que está no produto. */
export const EMBASAMENTO = [
  { fonte: "Ebbinghaus (1885)", uso: "a curva do esquecimento define quando a sua revisão volta." },
  { fonte: "Roediger & Karpicke (2006)", uso: "lembrar ensina mais que reler — por isso o Sapiens te faz responder, não assistir." },
  { fonte: "Bjork (1994)", uso: "dificuldade desejável: o treino intercala matérias de propósito." },
  { fonte: "Bloom (1956)", uso: "cada habilidade tem um degrau — e o seu erro diz em qual você parou." },
];

/** 4. O PLANO. Três passos. Nunca quatro. */
export const PLANO = [
  {
    passo: "1",
    titulo: "Responda 10 questões",
    corpo: "Dez minutos. É só o que a Mentis precisa para ver como você pensa — não quanto você sabe.",
  },
  {
    passo: "2",
    titulo: "Receba o seu plano da semana",
    corpo: "Segunda a domingo, com horário, prioridade e motivo. Você abre o app e já sabe o que fazer agora.",
  },
  {
    passo: "3",
    titulo: "Treine o que falta e veja subir",
    corpo: "Cada erro vira uma missão. Cada acerto de primeira vira progresso visível. A régua é sua, e ela sobe.",
  },
];

/** 6 e 7. O que está em jogo. Os dois lados sempre aparecem juntos: fracasso
 *  sozinho é chantagem, sucesso sozinho é propaganda. */
export const APOSTAS = {
  sucesso: {
    titulo: "O dia em que a lista sai",
    itens: [
      "Você aperta F3, digita seu nome e ele está lá.",
      "A ligação para a sua mãe — e o silêncio dela antes de chorar.",
      "O grupo da família mudando de nome naquela tarde.",
      "Primeiro dia de aula: jaleco, crachá, o campus que você só tinha visto em foto.",
      "E o resto da vida decidido por uma manhã em que você sentou e fez.",
    ],
  },
  fracasso: {
    titulo: "O dia em que ela sai sem você",
    itens: [
      "Mais um ano explicando para quem pergunta.",
      "Os amigos postando o crachá deles.",
      "A mesma apostila, do mesmo jeito, esperando um resultado diferente.",
      "E a pergunta que não vai embora: o que eu deixei de fazer?",
    ],
  },
};

/**
 * Prova social. **Depoimentos reais, reescritos em forma geral e sem
 * identificação** — a pedido do responsável pelo produto, que tem as mensagens
 * originais mas não as compilou. Por isso aqui não há nome, foto, cidade nem
 * faculdade específica: atribuir uma frase parafraseada a uma pessoa
 * identificável seria inventar um depoimento, e isso não se faz. Quando as
 * mensagens originais forem reunidas, troque o texto E a assinatura — com
 * autorização de quem escreveu.
 */
export const DEPOIMENTOS = [
  {
    texto:
      "Eu já tinha feito dois anos de cursinho. A diferença aqui foi parar de estudar tudo e começar a estudar o que eu errava. Passei.",
    assina: "Aluno aprovado em universidade pública",
  },
  {
    texto:
      "Pela primeira vez eu sentava sabendo o que fazer. Não perdia meia hora decidindo por onde começar — e isso, no fim do ano, é semana ganha.",
    assina: "Aluna aprovada em Medicina, universidade pública",
  },
  {
    texto:
      "Descobri que eu não errava por não saber. Errava por ler rápido demais. Ninguém nunca tinha me falado isso.",
    assina: "Aluno aprovado em universidade pública",
  },
  {
    texto: "Obrigado por não me deixar estudar no escuro. Fez diferença.",
    assina: "Aluna aprovada em universidade pública",
  },
];

/** SEO + objeções na mesma seção. Espelhado em JSON-LD no index.html. */
export const FAQ = [
  {
    p: "O que é o Sapiens?",
    r: "Uma plataforma de estudos para o ENEM e para os vestibulares que analisa os seus erros, descobre o padrão cognitivo por trás deles e monta um plano de estudos semanal personalizado, com revisão espaçada e correção de redação.",
  },
  {
    p: "Preciso pagar para começar?",
    r: "Não. Você cria a conta, recebe Sparks e já faz o diagnóstico, o treino e o plano da semana. Pagar só entra quando você quer mais ferramentas da Mentis, os cursos ou a aula ao vivo.",
  },
  {
    p: "Como o Sapiens é diferente de um cursinho?",
    r: "Cursinho ensina para a média da sala. O Sapiens parte do seu erro: ele mede como você pensa — precisão, velocidade, abstração — e monta uma trilha individual a partir disso, com base em pesquisa sobre memória e aprendizagem.",
  },
  {
    p: "Funciona no celular?",
    r: "Sim. O Sapiens funciona no navegador do Android, do iPhone, do Windows e do Mac, e pode ser instalado na tela de início como aplicativo, sem baixar nada de loja.",
  },
  {
    p: "Quem dá as aulas?",
    r: "Vitor Lara, 1º colocado de Medicina na USP. Ele grava os cursos, dá a aula ao vivo semanal e atende a mentoria individual, que tem lista de espera.",
  },
  {
    p: "O Sapiens corrige redação do ENEM?",
    r: "Sim. A redação é corrigida nas cinco competências do ENEM, com nota por competência e devolutiva explicando o que tirou ponto e como recuperar.",
  },
];

/**
 * A VOZ — o que vale em TODA tela do Sapiens, não só na landing.
 *
 * A regra do guia tem uma consequência prática que se esquece fácil: quem
 * fala é quem já passou por ali, não quem vende. Autoridade sem proximidade
 * vira folheto; proximidade sem autoridade vira colega de cursinho.
 */
export const VOZ = {
  /** O que o produto promete em uma frase — repetida sem variar. Promessa que
   *  muda de palavra a cada tela lê como três promessas diferentes. */
  promessa: "Em 10 minutos você sai sabendo o que estudar amanhã — e por quê.",
  /** O sucesso em forma curta, para caber em cartão e em push. */
  sucesso: "A lista sai. Seu nome está nela.",
  /** O plano em três palavras, para telas onde não cabe o plano inteiro. */
  planoCurto: ["Responda", "Receba o plano", "Treine e suba"],
  /** O que NUNCA se faz, em qualquer tela:
   *  · culpar o aluno pelo erro — erro é informação, é o insumo do produto;
   *  · comemorar com euforia — mentor confirma, não solta confete;
   *  · terminar sem próximo passo — guia que não manda agir não é guia;
   *  · elogiar a plataforma onde caberia dizer o que muda para ele. */
};
