/**
 * AS ROTAS DO APP — a fonte única.
 *
 * Antes deste arquivo, o endereço de uma tela era uma string digitada à mão em
 * cada lugar que apontava para ela. `/exams` aparecia em 18 arquivos do
 * frontend e em 5 módulos do backend; `/cognitive-profile` continuou vivo no
 * `mentis_routes.DESTINOS` meses depois de a tela virar `/desempenho`, e
 * ninguém percebeu porque um redirect calado o mantinha funcionando. Rota
 * digitada é rota que diverge: o custo não aparece no dia em que se digita,
 * aparece no dia em que se renomeia.
 *
 * Aqui há três coisas, e só três:
 *
 * 1. `ROTAS` — o endereço canônico de cada destino. **Ninguém escreve `"/..."`
 *    à mão fora deste arquivo.**
 * 2. `LEGADO` — o que cada endereço antigo virou. Toda linha aqui é um
 *    endereço que circulou no WhatsApp, está num favorito ou foi gravado no
 *    banco antes da renomeação. Nenhuma sai sem que o link externo morra.
 * 3. `normalizar` — a função que traduz um endereço antigo no atual. Ela é
 *    usada pelo roteador (para redirecionar), pela barra (para acender a aba
 *    certa quando o aluno chega por um link velho) e pelo backend, que tem a
 *    sua própria cópia em `rotas_do_app.py` — ver a nota no fim.
 *
 * ---------------------------------------------------------------------------
 * A REGRA QUE NÃO SE QUEBRA: normalizar preserva query e hash
 * ---------------------------------------------------------------------------
 *
 * `/exams?area=Matemática` tem de chegar em `/estudar/provas?area=Matemática`,
 * e não em `/estudar/provas`. O Painel, a fila de revisões e a Mentis abrem as
 * provas COM filtro na URL — um redirect que come a query manda o aluno para
 * um caderno genérico e a funcionalidade some sem erro nenhum na tela.
 */

/** As cinco áreas e tudo o que vive dentro delas. */
export const ROTAS = {
  // --- Entrada e telas públicas -------------------------------------------
  LANDING: "/",
  LOGIN: "/login",
  ESQUECI_SENHA: "/esqueci-senha",
  REDEFINIR_SENHA: "/redefinir-senha",
  TERMOS: "/termos",
  PRIVACIDADE: "/privacidade",

  // --- Portões de conta ----------------------------------------------------
  BEM_VINDO: "/bem-vindo",
  COMPLETAR_CADASTRO: "/completar-cadastro",

  // --- 1. HOJE -------------------------------------------------------------
  HOJE: "/hoje",

  // --- 2. ESTUDAR ----------------------------------------------------------
  ESTUDAR: "/estudar",
  PROVAS: "/estudar/provas",
  PROVA: "/estudar/provas/:examId",
  CURSOS: "/estudar/cursos",
  CURSO: "/estudar/cursos/:cursoId",
  ESTACAO: "/estudar/cursos/:cursoId/estacao/:estacaoId",
  EBOOK: "/estudar/ebooks/:ebookId",
  REDACAO: "/estudar/redacao",
  TREINO: "/estudar/treino",
  FOLHEAR: "/estudar/folhear",

  // --- 3. AGENDA -----------------------------------------------------------
  AGENDA: "/agenda",

  // --- 4. PROGRESSO --------------------------------------------------------
  PROGRESSO: "/progresso",
  // Os dois registros do passado do aluno. Continuam sendo tela própria
  // porque são *o documento dele*, não uma seção: um diagnóstico de simulado
  // tem gráfico, texto e data, e some dentro de uma aba.
  ANALISE: "/analysis/:analysisId",
  PLANO: "/plan/:analysisId",

  // --- 5. COMUNIDADE -------------------------------------------------------
  COMUNIDADE: "/comunidade",
  DUVIDA: "/comunidade/:duvidaId",

  // --- Camada e fluxos (fora da navegação principal) -----------------------
  // A Mentis não é aba: ela flutua em toda tela (`MentisWidget`) e esta rota é
  // só a versão em tela cheia da MESMA sessão. Ver `produto/mentis.md`.
  MENTIS: "/mentis",
  SPARKS: "/sparks",
  SUGESTOES: "/sugestoes",
  AULA_AO_VIVO: "/aula-ao-vivo",
  MENTORIA: "/mentoria",

  // --- Aquisição (tráfego externo) -----------------------------------------
  // As landings de campanha. NÃO são área, não entram na navegação e não são
  // alcançáveis de dentro do produto: existem para receber o clique de um
  // anúncio e levar a uma coisa só, o cadastro. Uma variante nova nasce como
  // uma linha aqui e uma rota no `App.js` — ver
  // `Cerebro/produto/landings-de-anuncio.md`.
  //
  // Elas não têm espelho em `rotas_do_app.py` de propósito: aquele arquivo
  // existe porque o BACKEND emite endereço de tela como dado (o bloco do
  // cronograma, o destino da Mentis), e nenhum backend tem o que fazer
  // mandando um aluno para uma landing de anúncio.
  ADS: "/ads",
  ADS_DIAGNOSTICO: "/ads/diagnostico",
  ADS_MESMO_ERRO: "/ads/mesmo-erro",
  ADS_DEZ_QUESTOES: "/ads/10-questoes",
  ADS_COMO_VOCE_ESTUDA: "/ads/como-voce-estuda",
  ADS_RETA_FINAL: "/ads/reta-final",
  ADS_SEM_MENSALIDADE: "/ads/sem-mensalidade",

  // --- Equipe --------------------------------------------------------------
  ADMIN: "/admin",
  PROMOTER: "/promoter",
};

/**
 * As âncoras das seções. Uma seção não é uma rota — mas o link para ela é
 * público (a Mentis manda o aluno para "suas conquistas", o cronograma manda
 * para a fila de revisão), e uma âncora digitada errada falha em silêncio:
 * a página abre no topo e ninguém descobre.
 */
export const ANCORAS = {
  HOJE_MISSOES: "missoes",

  AGENDA_HOJE: "hoje",
  AGENDA_REVISOES: "revisoes",
  AGENDA_LEMBRETES: "lembretes",
  AGENDA_SEMANA: "semana",
  AGENDA_PRIORIDADES: "prioridades",
  AGENDA_EVENTOS: "eventos",

  PROGRESSO_RETRATO: "retrato",
  PROGRESSO_EVOLUCAO: "evolucao",
  PROGRESSO_TRAJETORIA: "trajetoria",
  PROGRESSO_CONQUISTAS: "conquistas",
  PROGRESSO_HISTORICO: "historico",

  ESTUDAR_APRENDER: "aprender",
  ESTUDAR_PRATICAR: "praticar",

  SPARKS_INDICAR: "indicar",
};

/** `com("/agenda", "revisoes")` → `"/agenda#revisoes"`. Existe para ninguém
 *  concatenar `"#"` à mão e errar o lado da cerquilha. */
export function com(rota, ancora) {
  return ancora ? `${rota}#${ancora}` : rota;
}

/**
 * OS ENDEREÇOS ANTIGOS — e por que cada um continua de pé.
 *
 * A chave é o caminho antigo; o valor é o caminho novo. Caminhos com parâmetro
 * usam `:param` dos dois lados e a tradução é posicional.
 *
 * **Não apague uma linha daqui sem saber onde aquele endereço circulou.** Um
 * link de WhatsApp não tem prazo de validade: o aluno que salvou `/exams` em
 * setembro vai clicar nele em novembro.
 */
export const LEGADO = {
  // A renomeação de 2026-09-18: as áreas passaram a se chamar pelo que o aluno
  // pergunta, e a URL passou a dizer o mesmo que a aba.
  "/dashboard": ROTAS.HOJE,
  "/cronograma": ROTAS.AGENDA,
  "/desempenho": ROTAS.PROGRESSO,
  "/cognitive-profile": ROTAS.PROGRESSO,
  "/diagnostico": ROTAS.PROGRESSO,
  "/motor": ROTAS.PROGRESSO,

  // O que era tela própria e virou seção. O destino leva âncora: cair no topo
  // de uma aba de cinco seções, vindo de um link que prometia "conquistas", é
  // o mesmo que não ter redirecionado.
  "/conquistas": com(ROTAS.PROGRESSO, ANCORAS.PROGRESSO_CONQUISTAS),
  "/liga": com(ROTAS.PROGRESSO, ANCORAS.PROGRESSO_CONQUISTAS),
  "/history": com(ROTAS.PROGRESSO, ANCORAS.PROGRESSO_HISTORICO),
  "/trash": `${ROTAS.PROGRESSO}?apagados=1#${ANCORAS.PROGRESSO_HISTORICO}`,
  "/revisoes": com(ROTAS.AGENDA, ANCORAS.AGENDA_REVISOES),
  "/plan": com(ROTAS.AGENDA, ANCORAS.AGENDA_REVISOES),
  "/indicar": com(ROTAS.SPARKS, ANCORAS.SPARKS_INDICAR),

  // O que entrou para dentro de Estudar.
  "/exams": ROTAS.PROVAS,
  "/exam/:examId": ROTAS.PROVA,
  "/cursos": ROTAS.CURSOS,
  "/cursos/ebooks/:ebookId": ROTAS.EBOOK,
  "/cursos/:cursoId": ROTAS.CURSO,
  "/cursos/:cursoId/estacao/:estacaoId": ROTAS.ESTACAO,
  "/redacao": ROTAS.REDACAO,
  "/treino": ROTAS.TREINO,
  "/feed": ROTAS.FOLHEAR,
  // As questões geradas pela Mentis deixaram de ser tela e viraram uma fonte
  // do Treino — o aluno não distingue "questão do banco" de "questão gerada",
  // ele quer praticar aquela habilidade. A query preserva a intenção de quem
  // clicou no link antigo.
  "/minhas-questoes": `${ROTAS.TREINO}?fonte=geradas`,

  // Endereços que já eram redirect antes desta passada. Mantidos: o custo de
  // uma linha é zero e o de um 404 num link de WhatsApp não é.
  "/questoes": ROTAS.PROVAS,
  "/aulas": ROTAS.MENTORIA,
  "/live": ROTAS.AULA_AO_VIVO,
  "/mural": ROTAS.COMUNIDADE,
  "/duvidas": ROTAS.COMUNIDADE,
  // O mapa radial de uma análise antiga era alcançável de um lugar só e foi
  // substituído pelo mapa do Treino. O registro que ele ilustrava continua.
  "/map/:analysisId": ROTAS.ANALISE,
};

/** Os caminhos legados com parâmetro, pré-partidos — `normalizar` roda em
 *  cada navegação e não deve refazer este trabalho toda vez. */
const LEGADO_COM_PARAMETRO = Object.entries(LEGADO)
  .filter(([antigo]) => antigo.includes(":"))
  .map(([antigo, novo]) => ({
    partes: antigo.split("/").filter(Boolean),
    novo,
  }));

/**
 * O endereço atual de um caminho — o antigo se ele for antigo, ele mesmo se
 * já for canônico.
 *
 * Recebe só o `pathname` (sem query, sem hash) e devolve o caminho novo, que
 * PODE trazer query e hash próprios (`/trash` vira
 * `/progresso?apagados=1#historico`). Quem chama é responsável por juntar a
 * query de origem — ver `destinoLegado`.
 */
export function normalizar(pathname) {
  const caminho = (pathname || "/").replace(/\/+$/, "") || "/";
  const direto = LEGADO[caminho];
  if (direto) return direto;

  const partes = caminho.split("/").filter(Boolean);
  for (const { partes: molde, novo } of LEGADO_COM_PARAMETRO) {
    if (molde.length !== partes.length) continue;
    const valores = {};
    const casa = molde.every((parte, i) => {
      if (parte.startsWith(":")) {
        valores[parte.slice(1)] = partes[i];
        return true;
      }
      return parte === partes[i];
    });
    if (!casa) continue;
    return novo.replace(/:([A-Za-z0-9_]+)/g, (_, nome) => valores[nome] ?? "");
  }
  return caminho;
}

/** `true` quando o caminho é um endereço antigo que precisa ser redirecionado. */
export function ehLegado(pathname) {
  return normalizar(pathname) !== ((pathname || "/").replace(/\/+$/, "") || "/");
}

/**
 * O destino completo de uma navegação legada: o caminho novo, com a query de
 * origem e a do próprio destino somadas, e o hash resolvido.
 *
 * A soma das queries é o que faz `/trash?x=1` chegar em
 * `/progresso?apagados=1&x=1#historico`. A do DESTINO vem primeiro porque ela
 * é a tradução (é ela que diz "abra nos apagados"); a de origem é do aluno e
 * vence em caso de conflito de chave.
 */
export function destinoLegado({ pathname, search = "", hash = "" }) {
  const novo = normalizar(pathname);
  const [caminho, resto = ""] = novo.split("#");
  const [base, queryDoDestino = ""] = caminho.split("?");

  const params = new URLSearchParams(queryDoDestino);
  new URLSearchParams(search).forEach((valor, chave) => params.set(chave, valor));
  const query = params.toString();

  // O hash do aluno vence o do destino: se ele pediu uma seção explicitamente,
  // é nela que ele quer cair.
  const ancora = (hash || "").replace(/^#/, "") || resto;

  return `${base}${query ? `?${query}` : ""}${ancora ? `#${ancora}` : ""}`;
}

/**
 * A rota atual está "dentro" deste destino?
 *
 * Regra única para a barra de cima, a de baixo e o Menu — eram três cópias com
 * três comportamentos, e a de cima acendia `/hoje` em `/hoje/qualquer-coisa`
 * enquanto a de baixo não.
 *
 * `/hoje` casa exato porque tudo volta para ela. Os outros casam com as filhas
 * — `/comunidade/:id` mantém Comunidade acesa enquanto a dúvida está aberta, e
 * `/estudar/provas/:id` mantém Estudar aceso durante a prova.
 */
export function ehRotaAtual(pathname, destino) {
  const base = (destino || "").split(/[?#]/)[0];
  const atual = (pathname || "/").replace(/\/+$/, "") || "/";
  if (base === ROTAS.HOJE || base === "/") return atual === base;
  return atual === base || atual.startsWith(`${base}/`);
}
