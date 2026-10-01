import { useCallback, useEffect, useMemo, useState } from "react";
import { MENTOR } from "../lib/mentor";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { EVENTO_SPARKS } from "../components/Navegacao";
import PainelDeProgresso from "../components/PainelDeProgresso";
import ProximoPasso, { escolherPasso } from "../components/ProximoPasso";
import OQueMudou, { conquistasDoDia } from "../components/OQueMudou";
import PortaisDaJornada from "../components/PortaisDaJornada";
import ExplorarOSapiens from "../components/ExplorarOSapiens";
import EsqueletoDoPainel from "../components/Esqueleto";
import OnboardingTour from "../components/OnboardingTour";
import { COMPETENCIAS_REDACAO } from "../constants/redacao";
import { computeStreak, computeWeek } from "../lib/atividade";
import { avaliarConquistas } from "../lib/conquistas";
import { proximaQuinta, temAcessoLocal } from "../lib/live";
import { argumentoDaLive } from "../lib/venda";
import { quintasAteAProva } from "../lib/enem";
import MentorUSP from "../components/MentorUSP";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import {
  ArrowRight, CloudOff, RotateCw, HelpCircle, Video, Medal, Target,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import { ROTAS, ANCORAS } from "../lib/rotas";

/**
 * O PAINEL — uma pergunta por dobra.
 *
 * Esta tela foi reordenada três vezes em três dias, e a terceira passada
 * deixou duas aberturas ao mesmo tempo: as dez Portas e o Próximo Passo, uma
 * em cima da outra. São duas respostas para a mesma pergunta — "e agora?" — e
 * a de cima ganha sempre. O comentário do próprio `ProximoPasso` já dizia que
 * escolher entre dez coisas é o jeito mais confiável de não fazer nenhuma; a
 * vitrine tinha sido posta exatamente acima dele.
 *
 * A regra desta reescrita (2026-09-17) é uma só: **cada dobra responde a uma
 * pergunta, e nenhuma pergunta é respondida duas vezes.**
 *
 *   1. **Agora** — a única ação primária. Revisão vencida > bloco de hoje >
 *      missão atual > praticar. A vitrine do Mapa continua sendo o fundo
 *      desta peça: mostrar o produto e dizer o que fazer não competem mais.
 *   2. **Seu ritmo** — ofensiva, nível, liga, relógio do ENEM e as missões do
 *      dia, em azulejos baixos. O "como vai indo" numa varredura.
 *   3. **Seu foco** — a causa (cards acionáveis) e o mapa (domínio por
 *      frente) numa seção só, com UM link para o desempenho. Eram duas
 *      seções e três links para a mesma tela, com três nomes diferentes.
 *   4. **Hoje** — o que tem hora marcada. A fila de revisão só entra quando
 *      não é o passo do topo.
 *   5. **Com o mentor** — mentoria e aula ao vivo, juntas.
 *   6. **Explorar** — as dez Portas, atrás de um clique, abertas por padrão
 *      só para quem ainda não respondeu nada (ver `ExplorarOSapiens`).
 *   7. **Conquistas** — o reforço, no fim, onde reforço pertence.
 *   8. **Rodapé** — instalar o app e falar com a equipe.
 *
 * O QUE SAIU, e por quê: a grade "Ferramentas" (sete azulejos que já existiam
 * no Lançador e nas Portas) e a linha da Mentis (que já tem aba no topo, alvo
 * na barra do celular e ícone flutuante em toda tela). O Painel tinha três
 * menus de ferramentas e quatro portas para a mesma Mentis; de ~30 alvos
 * simultâneos passou a ~12 com a seção Explorar fechada.
 *
 * A espera continua nascendo com a própria silhueta
 * (`components/Esqueleto.jsx`), então o conteúdo não empurra nada quando
 * chega.
 */

// `by_area` (do fluxo de gabarito/Analysis) usa códigos ENEM curtos; o filtro
// `area` de GET /questoes (fluxo de banco de questões) usa os rótulos
// canônicos de `_AREAS_ENEM` (server.py) — esta é a ÚNICA ponte entre as duas
// taxonomias, só para o CTA "Treinar agora" abrir a prática já filtrada.
const AREA_CODE_TO_LABEL = {
  CN: "Ciências da Natureza",
  MT: "Matemática",
  CH: "Ciências Humanas",
  LC: "Linguagens e Códigos",
  "LC-Idioma": "Linguagens e Códigos",
};

/**
 * A SEMANA — subiu da quarta dobra para a segunda.
 *
 * Duas coisas estavam erradas aqui, e a segunda vinha da primeira.
 *
 * **Primeira: a posição.** O cronograma respondia "o que eu faço na quinta",
 * que é a única pergunta de PLANEJAMENTO do produto, e estava abaixo de
 * conquistas, domínio e cards de foco. Quem monta a semana monta para
 * cumprir; enterrar o plano abaixo do acompanhamento é pedir para ele ser
 * esquecido.
 *
 * **Segunda: o escopo.** A peça mostrava só HOJE, porque no rodapé era tudo o
 * que cabia. Hoje ela mostra os sete dias — seg→dom, com a coluna de hoje
 * acesa e a altura de cada dia proporcional ao que foi marcado nele. O aluno
 * vê de relance se a semana está equilibrada ou se ele empilhou tudo no
 * domingo, que é a informação que faz o plano ser ajustado em vez de
 * abandonado.
 *
 * A FILA DE REVISÃO entra aqui, e só quando existe. Ela tinha um card
 * estrutural próprio que, sem nada vencendo, ou desaparecia deixando um buraco
 * ou — pior — ocupava uma dobra para dizer "nada para revisar". Revisão não é
 * um lugar, é um PRAZO: ela pertence ao calendário, como um aviso, e some sem
 * deixar cicatriz quando não há prazo nenhum.
 */
function ChamadaDaLive({ inclusa = false, argumento = null, custoLive = null }) {
  const { edicao, inicio, aoVivoAgora } = proximaQuinta();
  // `inclusa` vem do direito do pacote de Sparks, que chega de carona na
  // leitura de saldo que o Painel já faz — nenhuma requisição a mais. Sem
  // ele, quem comprou o pacote que inclui as lives leria "· 200 Sparks" para
  // uma aula que ele nunca mais vai pagar.
  const jaTenho = inclusa || temAcessoLocal(edicao);
  const dias = Math.max(0, Math.ceil((inicio - Date.now()) / 86400000));
  const quando = inicio.toLocaleDateString("pt-BR", { day: "numeric", month: "long" });
  const hora = inicio.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

  return (
    <Link
      to="/aula-ao-vivo"
      className="lift flex flex-col items-stretch gap-4 rounded-[26px] border border-rose-400/25 bg-gradient-to-r from-rose-500/[0.12] via-amber-400/[0.07] to-transparent p-5 transition-colors hover:border-rose-400/50 sm:flex-row sm:items-center"
      data-testid="dash-live"
      data-tour="dash-live"
    >
      {/* O rosto e o texto continuam LADO A LADO no celular — é o botão que
          desce para a linha de baixo. Eles em coluna dariam um card de meia
          tela de altura com um retrato solto no topo. */}
      <div className="flex min-w-0 flex-1 items-start gap-4 sm:items-center">
        {/* O ROSTO, e não um ícone: quem dá a aula é o argumento. */}
        <span className="relative shrink-0">
          <MentorUSP tamanho="m" testid="dash-live-mentor" />
          <span className="absolute -right-1 -top-1 flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-500 opacity-80" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-rose-500" />
          </span>
        </span>
        <div className="min-w-0 flex-1">
          <div className="secao-olho text-rose-300/85">
            {aoVivoAgora ? "Acontecendo agora" : "Ao vivo · toda quinta"}
          </div>
          <div className="mt-1 font-display text-base font-bold leading-tight tracking-tight text-white md:text-lg">
            Aula ao vivo com {MENTOR.nome}
          </div>
          <div className="mt-0.5 text-xs text-white/50">
            {aoVivoAgora
              ? "A sala está aberta. Entre agora."
              : `${quando}, às ${hora} · ${dias === 0 ? "é hoje" : dias === 1 ? "amanhã" : `faltam ${dias} dias`}`}
            {inclusa
              ? " · inclusa no seu pacote"
              : !jaTenho && custoLive
                ? ` · ${custoLive} Sparks`
                : ""}
          </div>
          {/* O motivo de ESTE aluno entrar — feito do que ele mesmo respondeu
              (ver `lib/venda.js`). Custa zero: os sinais já estão carregados
              nesta página. Para quem já tem a vaga, o mesmo argumento deixa de
              vender e passa a convocar. */}
          {argumento && (
            <div
              className="mt-2 border-l-2 border-rose-400/40 pl-2.5 text-xs leading-relaxed text-white/70"
              data-testid="dash-live-argumento"
            >
              <span className="font-semibold text-white/90">{argumento.titulo}.</span>{" "}
              {argumento.texto}
            </div>
          )}
        </div>
      </div>
      <span
        className={`pill inline-flex w-full shrink-0 items-center justify-center gap-2 rounded-full px-5 py-3 text-xs font-bold sm:w-auto ${
          jaTenho ? "btn-vidro" : "btn-calor"
        }`}
      >
        {inclusa ? (
          <><Video className="h-4 w-4" /> Entrar na aula</>
        ) : jaTenho ? (
          <><Video className="h-4 w-4" /> Sua vaga está garantida</>
        ) : (
          <>Garantir minha vaga <ArrowRight className="h-3.5 w-3.5" /></>
        )}
      </span>
    </Link>
  );
}

/**
 * A MENTORIA no Painel.
 *
 * Ela existia aqui como um azulejo entre dez outros, lá embaixo, do mesmo
 * tamanho de "Minhas questões" — e é o ativo mais valioso do produto. Um
 * atendimento um a um com o primeiro colocado de Medicina da USP não compete
 * em pé de igualdade com um atalho de utilidade: ou tem peso próprio na
 * página, ou não é visto.
 *
 * O que dá peso aqui é o mesmo que dá peso na `/mentoria`: o ROSTO em tamanho
 * grande e a credencial por extenso. O resto da peça é curto de propósito —
 * quem quiser o argumento inteiro abre a página, que é onde ele mora.
 *
 * A escassez é dita porque é verdadeira (uma pessoa, agenda finita), nunca
 * como contador de vagas inventado. Mesma linha ética de `lib/venda.js`.
 */
function ChamadaDaMentoria() {
  return (
    <Link
      to="/mentoria"
      className="lift group relative flex flex-col items-stretch gap-5 overflow-hidden rounded-[26px] border border-amber-300/35 bg-gradient-to-r from-amber-400/[0.14] via-[#4FD9FF]/[0.07] to-transparent p-5 transition-colors hover:border-amber-300/70 sm:flex-row sm:items-center md:p-6"
      data-testid="dash-mentoria"
      data-tour="dash-mentoria"
    >
      <div className="flex min-w-0 flex-1 items-start gap-4 sm:items-center sm:gap-5">
        {/* Retrato "g" tem 160px no celular: numa linha com o texto ao lado,
            sobravam ~130px para a frase, uma palavra por linha (medido a
            375px em 2026-09-30 — o defeito 4 de `Cerebro/ux/mobile.md`).
            No celular entra o "m"; do `sm` para cima, o de sempre. */}
        <span className="shrink-0 sm:hidden"><MentorUSP tamanho="m" testid="dash-mentoria-mentor-celular" /></span>
        <span className="hidden shrink-0 sm:block"><MentorUSP tamanho="g" testid="dash-mentoria-mentor" /></span>

        <div className="min-w-0 flex-1">
          <div className="secao-olho inline-flex items-center gap-1.5 text-amber-200/90">
            <Medal className="h-3.5 w-3.5" /> O mais valioso que o Sapiens tem
          </div>
          <div className="mt-1.5 font-display text-lg font-bold leading-snug tracking-tight text-white sm:text-xl md:text-2xl">
            Mentoria um a um com {MENTOR.nome}
          </div>
          <p className="mt-1.5 max-w-xl text-[13px] leading-relaxed text-white/80 sm:text-sm">
            {MENTOR.titulo}. Ele olha a <strong className="font-semibold text-white">sua</strong> semana,
            diz o que cortar e o que você está estudando à toa.
          </p>
          <p className="mt-1.5 text-[13px] text-amber-100/80 sm:text-sm">
            É uma pessoa só, com agenda finita — por isso é lista de espera, não agendamento.
          </p>
        </div>
      </div>

      <span className="pill btn-calor inline-flex w-full shrink-0 items-center justify-center gap-2 rounded-full px-6 py-3.5 text-sm font-bold sm:w-auto">
        Entrar na lista
        <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}

// Marca LOCAL de "este aluno já viu o guia". Ver `abrirGuiaSeNunca`.
//
// A fonte da verdade é o servidor (`flags.guia_visto`); isto aqui é só o
// atalho que evita o guia piscar meio segundo enquanto a resposta vem, e que
// faz o comportamento certo sobreviver a uma falha de rede.
//
// **Por aluno, e não por navegador**: sem o `user_id` na chave, dois irmãos
// no mesmo computador dividiriam a marca, e o segundo nunca veria o guia.
const chaveDoGuia = (userId) => `sapiens:guia-visto:${userId || "anonimo"}`;

export default function Hoje() {
  const { user } = useAuth();
  const [analyses, setAnalyses] = useState([]);
  const [sparks, setSparks] = useState(null);
  // Direitos permanentes do pacote de Sparks (`sparks_store.DIREITOS`). Vêm
  // na MESMA resposta do saldo — o `students/{uid}` é um documento só.
  const [direitos, setDireitos] = useState({});
  const [activityDates, setActivityDates] = useState([]);
  const [hubs, setHubs] = useState([]);
  const [totalRespondidas, setTotalRespondidas] = useState(0);
  const [rounds, setRounds] = useState([]);
  // A fila INTEIRA do motor cognitivo (`habilidades_prioritarias`). Até
  // 2026-09-28 o Painel guardava só as linhas com causa e as usava para o
  // anúncio da aula; o Próximo Passo não as via. Agora é a fila que decide
  // o degrau "padrão de erro" — e `fracos` (o recorte da venda) sai dela.
  const [prioritarias, setPrioritarias] = useState([]);
  // A trajetória por habilidade (marcos de revisão acertada e de acerto em
  // contexto novo): é daqui que saem as microvitórias do "O que mudou".
  const [trajetoria, setTrajetoria] = useState(null);
  const [habilidades, setHabilidades] = useState([]);
  const [redacoes, setRedacoes] = useState([]);
  const [revisoes, setRevisoes] = useState(null);
  const [cronograma, setCronograma] = useState(null);
  const [onboarding, setOnboarding] = useState(null);
  const [custoLive, setCustoLive] = useState(null);
  // O estado de engajamento (ofensiva, nível, liga, missões) passou a ser
  // carregado AQUI em 2026-09-16, e não mais dentro de `PainelDeProgresso`:
  // o "próximo passo" precisa saber se a ofensiva está em risco, e duas
  // chamadas ao mesmo endereço na mesma tela é desperdício puro.
  const [engajamento, setEngajamento] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [falhou, setFalhou] = useState(false);
  const [showTour, setShowTour] = useState(false);
  const nav = useNavigate();
  const { hash } = useLocation();
  const [params, setParams] = useSearchParams();

  // Todas as chamadas são O(1): documento único do aluno no Firestore ou
  // consulta indexada no Mongo. Nenhuma varre eventos — ver
  // `project_aluno_disciplina_leitura_firestore`.
  //
  // `allSettled` mantém a página utilizável quando UMA falha, mas registra
  // que houve falha: sem isso, o backend fora do ar produzia um painel
  // impecável mostrando "0 dias de sequência" e "Sparks —", e o aluno não
  // tinha como distinguir isso de "meu progresso sumiu".
  const carregar = useCallback(() => {
    setFalhou(false);
    Promise.allSettled([
      api.get("/analyses").then(({ data }) => data),
      api.get("/firestore/students/me/sparks").then(({ data }) => data),
      api.get("/firestore/students/me/activity").then(({ data }) => data.dates || []),
      api.get("/skills-map").then(({ data }) => data.hubs || []),
      api.get("/firestore/students/me/respondidas").then(({ data }) => (data.item_ids || []).length),
      api.get("/firestore/students/me/rounds").then(({ data }) => data.rounds || []),
      // A fila do motor: onde os erros começam, e por quê. Memorizado no
      // servidor por `total_respostas`.
      api.get("/motor/perfil").then(({ data }) => data.habilidades_prioritarias || []),
      api.get("/treino/habilidades").then(({ data }) => data.habilidades || []),
      api.get("/redacao", { params: { limit: 3 } }).then(({ data }) => data.items || []),
      api.get("/revisao/fila").then(({ data }) => data),
      api.get("/cronograma").then(({ data }) => data),
      // O que o aluno declarou no primeiro acesso: 1 `find_one` por chave
      // primária no Mongo. É daqui que sai a meta que o cabeçalho mostra.
      api.get("/onboarding").then(({ data }) => data),
      api.get("/engajamento/me").then(({ data }) => data),
      // Preço da aula ao vivo (`ChamadaDaLive`) — nunca escrito à mão aqui;
      // sai de `cursos.LIVE_CUSTO_SPARKS` via `GET /cursos/precos`.
      api.get("/cursos/precos").then(({ data }) => data.custo_live),
      // UMA leitura de `students/{uid}` (o bloco `revisao`), O(1) — nunca
      // varre eventos. Falhar aqui só apaga a microvitória, nada mais.
      api.get("/revisao/trajetoria").then(({ data }) => data),
    ]).then((resultados) => {
      const [a, s, dates, h, respondidas, r, f, habs, reds, fila, semana, onb, eng, live, traj] = resultados;
      const valor = (res, vazio) => (res.status === "fulfilled" ? res.value : vazio);

      setAnalyses(valor(a, []));
      setSparks(valor(s, null)?.sparks_balance ?? null);
      setDireitos(valor(s, null)?.direitos || {});
      setActivityDates(valor(dates, []));
      setHubs(valor(h, []));
      setTotalRespondidas(valor(respondidas, 0));
      setRounds(valor(r, []));
      setPrioritarias(valor(f, []));
      setTrajetoria(valor(traj, null));
      setHabilidades(valor(habs, []));
      setRedacoes(valor(reds, []));
      setRevisoes(valor(fila, null));
      setCronograma(valor(semana, null));
      setOnboarding(valor(onb, null));
      setEngajamento(valor(eng, null));
      setCustoLive(valor(live, null));
      setFalhou(resultados.some((res) => res.status === "rejected"));
      setLoaded(true);
    });
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  /** Relê só o engajamento. Resgatar uma missão muda ofensiva, XP, liga e a
   *  própria missão — mas nada do resto da página. Recarregar o Painel
   *  inteiro seria pagar treze chamadas por uma. */
  const recarregarEngajamento = useCallback(() => {
    api.get("/engajamento/me").then(({ data }) => setEngajamento(data)).catch(() => {});
  }, []);

  // UMA VEZ NA VIDA — revisto em 2026-09-17.
  //
  // Era uma vez por sessão do navegador: quem entrava na plataforma via o
  // guia de novo, todo dia, vinte e um balões. Um tutorial que reaparece a
  // cada entrada deixa de ser ajuda e vira pedágio, e a única coisa que ele
  // ensina a partir da segunda vez é onde fica o "Pular".
  //
  // Agora a marca é PERMANENTE e mora em dois lugares, de propósito:
  //
  // · `flags.guia_visto` no servidor é a fonte da verdade. É ela que faz o
  //   guia não voltar depois de um logout, de uma troca de aparelho ou de uma
  //   janela anônima — que é exatamente o que o `sessionStorage` anterior não
  //   conseguia, porque morria junto com a aba.
  // · `localStorage`, por aluno, é o atalho: evita o balão piscar enquanto a
  //   resposta do servidor não chega, e mantém o comportamento certo se a
  //   rede falhar.
  //
  // Quem quiser rever tem duas portas explícitas, e as duas continuam de pé:
  // o botão "Guia" no topo do Painel e o "Rever o guia" no menu.
  const marcarGuiaVisto = useCallback(() => {
    try { localStorage.setItem(chaveDoGuia(user?.user_id), "1"); } catch { /* bloqueado */ }
  }, [user]);

  const jaViuOGuia = useCallback(() => {
    try { return Boolean(localStorage.getItem(chaveDoGuia(user?.user_id))); }
    catch { return false; }
  }, [user]);

  // O guia da Mentis. Três portas: `?guia=1` (com que `/bem-vindo` termina),
  // os botões "Guia" / "Rever o guia", e a ABERTURA AUTOMÁTICA a cada entrada
  // na plataforma. A porta antiga (`flags.onboarded === false` no Firestore)
  // continua mandando o aluno para `/bem-vindo` — o tour é a segunda metade
  // daquela conversa, não um onboarding paralelo.
  // `?guia=1` num efeito próprio, que OUVE a URL: quem clica em "Rever o guia"
  // no lançador já estando no Painel só muda a query — não há remontagem, e um
  // efeito de montagem não veria esse clique nunca.
  useEffect(() => {
    if (!params.get("guia")) return;
    // Pedido explícito ("Rever o guia"): abre mesmo já tendo sido visto, e
    // sem mexer na marca — rever não é ver pela primeira vez.
    setShowTour(true);
    const limpo = new URLSearchParams(params);
    limpo.delete("guia");
    setParams(limpo, { replace: true });
  }, [params, setParams]);

  useEffect(() => {
    if (params.get("guia")) return; // tratado no efeito acima
    if (jaViuOGuia()) return;       // atalho local: nem chega a perguntar

    // `sessionStorage`: a marca que `/bem-vindo` deixa ao ser pulado ou
    // concluído. Sem ela, um PUT que falhou (rede oscilando) deixava
    // `flags.onboarded` em `false` no servidor e esta linha mandava o aluno
    // de volta ao onboarding — que o devolveria para cá — em laço.
    let jaPassouPeloBemVindo = false;
    try {
      jaPassouPeloBemVindo = Boolean(sessionStorage.getItem("sapiens:onboarding-visto"));
    } catch { /* navegador com armazenamento bloqueado: segue o fluxo normal */ }

    api.get("/firestore/students/me/behavior")
      .then(({ data }) => {
        const flags = data?.flags || {};
        // Já viu em outro aparelho ou antes de um logout: alinha a marca
        // local e não mostra nada.
        if (flags.guia_visto === true) {
          marcarGuiaVisto();
          return;
        }
        // Primeiro acesso de todos: `/bem-vindo` vem antes, e ele termina
        // mandando para cá com `?guia=1`. Abrir o tour aqui só faria o balão
        // piscar meio segundo antes do redirecionamento.
        if (flags.onboarded === false && !jaPassouPeloBemVindo) {
          nav("/bem-vindo", { replace: true });
          return;
        }
        setShowTour(true);
      })
      // Falha de rede não pode custar o PRIMEIRO guia: ele não depende de
      // nada do servidor para ser exibido, e quem já o viu está protegido
      // pela marca local lida lá em cima.
      .catch(() => setShowTour(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // `/dashboard#missoes` é o endereço que a Mentis e o guia usam para levar
  // às missões do dia. O React Router empurra a URL sem rolar a página (é
  // navegação de aplicação, não do documento), então a rolagem é feita aqui —
  // depois do `loaded`, senão o alvo ainda não existe no DOM.
  useEffect(() => {
    if (!loaded || hash !== "#missoes") return;
    document.getElementById("missoes")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [loaded, hash]);

  // O saldo muda DENTRO desta página (resgatar missão credita sem trocar de
  // rota). Só o saldo é relido — recarregar o painel a cada moeda seria pagar
  // treze chamadas por uma.
  useEffect(() => {
    const relerSaldo = () =>
      api.get("/firestore/students/me/sparks")
        .then(({ data }) => {
          setSparks(data.sparks_balance);
          setDireitos(data.direitos || {});
        })
        .catch(() => {});
    window.addEventListener(EVENTO_SPARKS, relerSaldo);
    return () => window.removeEventListener(EVENTO_SPARKS, relerSaldo);
  }, []);

  // O recorte que a venda da aula sempre usou: só linhas com causa nomeada.
  const fracos = useMemo(
    () => prioritarias.filter((l) => l.origem === "error_trace" && l.erro_dominante),
    [prioritarias],
  );

  const latest = analyses[0];
  const streak = computeStreak(activityDates);
  const weekActiveDays = computeWeek(activityDates).filter((d) => d.active).length;

  const areaEntries = latest
    ? Object.entries(latest.by_area || {})
        .map(([area, v]) => ({ area, pct: v.total ? Math.round((100 * v.correct) / v.total) : 0, total: v.total }))
        .filter((e) => e.total > 0)
    : [];
  const weakestArea = areaEntries.length ? [...areaEntries].sort((a, b) => a.pct - b.pct)[0] : null;

  const ultimaRedacao = redacoes.find((r) => r.avaliacao) || null;
  const competenciaFraca = useMemo(() => {
    const comps = ultimaRedacao?.avaliacao?.competencias || [];
    if (!comps.length) return null;
    return [...comps].sort((a, b) => (a.nivel_pontos ?? 0) - (b.nivel_pontos ?? 0))[0];
  }, [ultimaRedacao]);
  const melhorRedacao = redacoes.reduce((m, r) => Math.max(m, r.avaliacao?.nota_total ?? 0), 0);

  // "Onde focar": área mais fraca do último gabarito, habilidades fracas do
  // treino, competência fraca da redação e — logo depois — as dificuldades
  // com CAUSA identificada. Uma seção só: antes eram duas, com o mesmo
  // formato de card e a mesma promessa, e o aluno tinha de descobrir sozinho
  // por que a mesma coisa aparecia em dois lugares.
  const focos = useMemo(() => {
    const lista = [];
    if (weakestArea) {
      const rotulo = AREA_CODE_TO_LABEL[weakestArea.area] || weakestArea.area;
      lista.push({
        key: `area-${weakestArea.area}`,
        titulo: rotulo,
        descricao: "Sua área mais fraca no último gabarito.",
        medida: `${weakestArea.pct}%`,
        medidaLabel: "de acerto",
        evidencia: `${weakestArea.pct}% de acerto em ${weakestArea.total} questões dessa área`,
        treino: AREA_CODE_TO_LABEL[weakestArea.area]
          ? { href: `${ROTAS.PROVAS}?area=${encodeURIComponent(rotulo)}`, rotulo: "Praticar a área" }
          : null,
      });
    }
    habilidades
      .filter((h) => h.respondidas > 0 && h.classificacao === "fraco")
      .sort((a, b) => (a.percentual ?? 100) - (b.percentual ?? 100))
      .slice(0, 2)
      .forEach((h) => {
        lista.push({
          key: `hab-${h.hab_id}`,
          titulo: h.nome,
          descricao: "Há uma missão curta do mapa sobre isto.",
          medida: `${Math.round(h.percentual ?? 0)}%`,
          medidaLabel: "no treino",
          evidencia: `${h.acertos} de ${h.respondidas} questões certas nessa habilidade`,
          treino: { href: `${ROTAS.TREINO}?hab=${h.hab_id}`, rotulo: "Abrir a missão" },
        });
      });
    if (competenciaFraca) {
      const rotulo = COMPETENCIAS_REDACAO[competenciaFraca.id] || competenciaFraca.id;
      lista.push({
        key: `red-${competenciaFraca.id}`,
        titulo: `Redação · ${rotulo}`,
        descricao: "A competência que menos pontuou.",
        medida: `${competenciaFraca.nivel_pontos ?? 0}`,
        medidaLabel: "de 200",
        evidencia: `${competenciaFraca.nivel_pontos ?? 0} de 200 pontos nessa competência da redação`,
        treino: { href: ROTAS.REDACAO, rotulo: "Escrever de novo" },
      });
    }
    return lista.slice(0, 3);
  }, [weakestArea, habilidades, competenciaFraca]);

  useDeclararContextoMentis(
    focos.length ? `Na aba Hoje. Ponto de atenção em destaque: "${focos[0].titulo}".` : "Na aba Hoje do Sapiens.",
  );

  // O argumento da aula ao vivo, feito dos sinais que esta página JÁ tem na
  // mão — zero requisição a mais, que é a condição para o anúncio do Painel
  // existir (ver `lib/live.js`).
  const argumentoDaAula = useMemo(
    () =>
      argumentoDaLive({
        fracos,
        focos,
        quintasRestantes: quintasAteAProva(),
        diasAtivosNaSemana: weekActiveDays,
        ofensiva: streak,
      }),
    [fracos, focos, weekActiveDays, streak],
  );

  const conquistas = avaliarConquistas({
    totalRespondidas, streak, hubs, analyses, rounds, weekActiveDays,
    redacoesCorrigidas: redacoes.filter((r) => r.avaliacao).length,
    melhorRedacao,
  });

  // Só a conquista que é notícia HOJE chega ao "O que mudou" — ver
  // `conquistasDoDia`. A marca de "já vista" é por aparelho (localStorage),
  // e falhar em ler ou gravar só cala a linha, nunca quebra o Painel.
  const chaveVistas = `sapiens:conquistas-vistas:${user?.user_id || "anon"}`;
  const conquistasNovas = useMemo(() => {
    if (!loaded) return [];
    let vistas = null;
    try { vistas = JSON.parse(localStorage.getItem(chaveVistas) || "null"); } catch { return []; }
    const { doDia, vistas: atualizadas } = conquistasDoDia(conquistas, vistas);
    try { localStorage.setItem(chaveVistas, JSON.stringify(atualizadas)); } catch { /* bloqueado */ }
    return doDia;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, chaveVistas, conquistas.filter((c) => c.desbloqueada).length]);

  // O MESMO passo que a peça do topo vai desenhar — a mesma função, não uma
  // segunda regra parecida. O Painel precisa dele aqui embaixo só para não
  // repetir a pendência: quando a ação do dia já é a fila de revisão, o card
  // da fila em "Hoje" sai de cena. Duas peças diferentes cobrando a mesma
  // coisa na mesma rolagem leem como duas coisas a fazer.
  const passoAtual = useMemo(
    () => escolherPasso({ revisoes, cronograma, habilidades, padroes: prioritarias, totalRespondidas }),
    [revisoes, cronograma, habilidades, prioritarias, totalRespondidas],
  );

  if (!loaded) {
    return (
      <div className="min-h-screen">
        <div className="mx-auto max-w-5xl px-5 py-8 md:px-10 md:py-10">
          <EsqueletoDoPainel />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="mx-auto max-w-5xl px-5 py-7 md:px-10 md:py-10">
        {/* CABEÇALHO — nome, meta declarada e a porta do guia. Nada mais. */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 flex-wrap items-center gap-2.5">
            <h1 className="titulo-tela" data-testid="dash-title">
              Olá, {user?.name?.split(" ")[0] || "aluno"}.
            </h1>
            {onboarding?.meta && (
              <span
                className="chip"
                data-testid="dash-meta"
                title="Sua meta declarada no primeiro acesso"
              >
                <Target className="h-3.5 w-3.5 text-[#7FD8FF]" />
                {onboarding.meta.acertos_min}–{onboarding.meta.acertos_max} acertos
              </span>
            )}
          </div>
          <button
            onClick={() => setShowTour(true)}
            // `ml-auto`: a 375px o cabeçalho quebra em duas linhas e, sem
            // isto, o botão do guia caía alinhado à ESQUERDA embaixo do nome,
            // parecendo um segundo título.
            className="chip pill ml-auto shrink-0"
            data-testid="dash-rever-tour"
          >
            <HelpCircle className="h-3.5 w-3.5" /> Guia
          </button>
        </div>

        {falhou && (
          <div
            className="superficie mb-4 flex flex-col items-stretch gap-3 border-amber-300/30 bg-amber-400/[0.08] px-5 py-4 sm:flex-row sm:items-center"
            data-testid="dash-erro-parcial"
          >
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <CloudOff className="h-5 w-5 shrink-0 text-amber-300" />
              <div className="min-w-0 flex-1 text-sm text-amber-100">
                <strong>Não conseguimos carregar tudo.</strong> É falha de conexão nossa, não perda do seu progresso.
              </div>
            </div>
            <button
              onClick={carregar}
              className="pill inline-flex w-full shrink-0 items-center justify-center gap-2 rounded-full bg-amber-950 px-4 py-2 text-xs font-semibold text-amber-50 hover:brightness-110 sm:w-auto"
              data-testid="dash-erro-retry"
            >
              <RotateCw className="h-3.5 w-3.5" /> Tentar de novo
            </button>
          </div>
        )}

        {/* `cascata`: os blocos entram em sequência, 45ms de passo, com teto
            no sexto. É o que dá ritmo à chegada da tela sem transformar a
            rolagem numa espera. */}
        <div className="cascata space-y-7">
          {/* -------------------------------------------------------------
              1. AGORA — a ÚNICA ação primária da tela.

              Esta posição foi disputada três vezes em três dias (mapa de
              missões → próximo passo → dez portas) e a disputa era o próprio
              problema: quem abre o app às sete da noite com uma hora livre
              não precisa ser convencido de que o produto tem coisas, precisa
              saber onde pisar. A vitrine continua existindo — desceu para a
              seção "Explorar", no fim desta mesma tela, onde ela convida sem
              disputar a decisão.

              Uma pergunta por dobra. Esta dobra responde "e agora?".
              ------------------------------------------------------------- */}
          <ProximoPasso
            habilidades={habilidades}
            revisoes={revisoes}
            cronograma={cronograma}
            padroes={prioritarias}
            totalRespondidas={totalRespondidas}
            ofensiva={engajamento?.ofensiva?.dias ?? 0}
            estudouHoje={engajamento?.ofensiva?.estudou_hoje ?? true}
            diasNaSemana={weekActiveDays}
          />

          {/* -------------------------------------------------------------
              2. O QUE MUDOU — os EVENTOS, não os resumos das outras abas.

              Aqui havia QUATRO blocos, e cada um era o resumo de outra aba: a
              tira da semana (Agenda), o aviso de revisão (Agenda de novo), a
              grade de focos e domínio (Progresso) e a fileira de conquistas
              (Progresso de novo). Somados com o resto, davam ~12 blocos
              simultâneos e três respostas para "e agora?" na mesma rolagem.

              Nenhum deles era a coisa em si — eram vitrines de vitrines, e o
              aluno que clicasse em qualquer uma encontrava a MESMA informação
              maior do lado de lá. O Hoje deixou de resumir as outras abas e
              passou a dizer o que ACONTECEU: um resumo existe sempre e por
              isso não chama atenção; um evento só existe quando aconteceu.

              Ver `components/OQueMudou.jsx` — e a regra de zero requisição
              nova, que é a mesma do Próximo Passo.
              ------------------------------------------------------------- */}
          <OQueMudou
            revisoes={revisoes}
            cronograma={cronograma}
            redacoes={redacoes}
            engajamento={engajamento}
            conquistas={conquistasNovas}
            passoAtual={passoAtual}
            trajetoria={trajetoria}
          />

          {/* -------------------------------------------------------------
              3. SUA SEQUÊNCIA — ofensiva, XP e as missões do dia.
              `id="missoes"`: a Mentis e o guia levam direto até aqui.
              ------------------------------------------------------------- */}
          <div className="scroll-mt-24" id={ANCORAS.HOJE_MISSOES} data-tour="hoje-missoes">
            {/* As missões de prática levam ao MESMO padrão que o Próximo
                Passo anuncia — duas peças, um destino. */}
            <PainelDeProgresso
              dados={engajamento}
              aoMudar={recarregarEngajamento}
              pratica={passoAtual?.dirigida || null}
            />
          </div>

          {/* -------------------------------------------------------------
              4. COM O MENTOR. Duas peças, nesta ordem, e a ordem é o
              argumento: a MENTORIA (um a um, o ativo mais valioso do produto)
              e depois a AULA AO VIVO (um para muitos, toda quinta).

              As duas são o mesmo mentor em graus diferentes de proximidade,
              então ficam juntas: separá-las fazia a mentoria competir com
              atalhos de utilidade lá embaixo, onde ela perdia sempre.
              ------------------------------------------------------------- */}
          <div className="space-y-3">
            <ChamadaDaMentoria />
            <ChamadaDaLive
              inclusa={Boolean(direitos.lives_inclusas)}
              argumento={argumentoDaAula}
              custoLive={custoLive}
            />
          </div>

          {/* -------------------------------------------------------------
              5. EXPLORAR — a descoberta, atrás de um clique.

              As dez portas continuam inteiras aqui dentro. O que mudou é que
              elas não disputam mais a primeira dobra com a ação do dia: quem
              já tem trajetória encontra a seção fechada, e quem ainda não
              respondeu nada a encontra aberta, porque para ele a vitrine é a
              peça forte e o Próximo Passo é o degrau genérico.
              ------------------------------------------------------------- */}
          <ExplorarOSapiens abertoInicial={totalRespondidas === 0} testid="dash-explorar">
            <PortaisDaJornada
              habilidades={habilidades}
              revisoes={revisoes}
              cronograma={cronograma}
              redacoes={redacoes}
              engajamento={engajamento}
              conquistas={conquistas}
              totalRespondidas={totalRespondidas}
              compacto
              testid="dash-portais"
            />
          </ExplorarOSapiens>

        </div>
      </div>

      {loaded && showTour && (
        <OnboardingTour
          onDone={() => { setShowTour(false); marcarGuiaVisto(); }}
        />
      )}
    </div>
  );
}
