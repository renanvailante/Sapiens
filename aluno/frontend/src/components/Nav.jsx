import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import {
  Zap, ShieldCheck, LayoutGrid, GraduationCap, MessageCircle, Compass,
  PlayCircle, LogOut, Megaphone, Grip,
} from "lucide-react";
import Logo from "./Logo";
import Mentis from "./Mentis";
import LancadorDeFerramentas from "./LancadorDeFerramentas";
import { ATALHOS, quantasCabem } from "../lib/atalhos";

export const EVENTO_SPARKS = "sparks:mudou";

/** Avisa a barra que o saldo mudou. Chame depois de QUALQUER ação que credite
 *  ou debite Sparks sem sair da página. Um evento de janela, e não um contexto
 *  de React, porque o chip vive na barra e quem gasta vive na tela — um
 *  provedor para carregar um inteiro entre os dois seria mais encanamento do
 *  que problema. */
export function avisarSparksMudou() {
  window.dispatchEvent(new Event(EVENTO_SPARKS));
}

// As seis coisas que o aluno FAZ. A ordem é decisão de produto, revista em
// 2026-09-15: o **Mapa de Treino vem primeiro** — é a superfície de maior
// impacto visual do Sapiens e a que comunica o valor do produto em cinco
// segundos; deixá-lo em terceiro era esconder a vitrine atrás do estoque.
// Depois o Painel (para onde tudo volta), Redação, Cronograma, a COMUNIDADE
// e a Mentis.
//
// "Provas do ENEM" não está aqui porque o Painel abre nelas com o botão
// principal e a barra INFERIOR do celular tem o alvo elevado dedicado a isso;
// tudo o mais mora no LANÇADOR (o botão de grade), que é uma grade visual com
// nome e função de cada ferramenta.
//
// `texto` é o que a barra DESENHA; `label` continua sendo o nome acessível
// (aria-label e title), sempre por extenso. Ver a nota de medição no fim do
// arquivo: a barra vive num container de 1152px que nenhum monitor largo
// aumenta, e desde 16/09 os rótulos só aparecem a partir de `xl`.
//
// 2026-09-17 — AS DUAS BARRAS PASSARAM A DESENHAR O MESMO CONJUNTO.
//
// Até aqui o desktop tinha seis abas (Treino, Painel, Redação, Semana, Mural,
// Mentis) e o celular tinha quatro outras (Painel, Treino, Praticar, Mentis):
// dois produtos diferentes para a mesma pessoa. Quem começava no telefone e
// abria o notebook à noite não encontrava o que tinha aprendido a usar — e
// "Praticar", o alvo elevado por onde quase tudo começa no celular, não era
// sequer uma aba aqui.
//
// O conjunto agora é o mesmo, na mesma ordem da esquerda para a direita:
// Painel · Treino · Praticar · Mentis, mais a porta do Menu. Quatro verbos
// diários e uma porta — a mesma régua do polegar que a barra de baixo já
// usava, aplicada também ao mouse.
//
// Redação, Semana e Mural não sumiram: desceram para as miniaturas
// (`lib/atalhos`), no topo da prioridade, e continuam no Menu com nome e
// função. O que se perdeu foi um clique de distância; o que se ganhou foi o
// aluno poder trocar de aparelho sem reaprender a navegação.
const PRIMARY_LINKS = [
  { to: "/dashboard", icon: LayoutGrid, label: "Painel", testid: "nav-dashboard", tour: "nav-dashboard" },
  { to: "/treino", icon: Compass, label: "Treino", testid: "nav-treino", tour: "nav-treino" },
  { to: "/exams", icon: PlayCircle, label: "Praticar", testid: "nav-praticar", tour: "nav-praticar" },
  { to: "/mentis", icon: MessageCircle, label: "Mentis", testid: "nav-mentis", tour: "nav-mentis", mascote: true },
];

/** A rota atual, para a aba acender. `/dashboard` é exata porque tudo volta
 *  para ela; as outras casam com as filhas (`/comunidade/:id` mantém o Mural
 *  aceso enquanto a dúvida está aberta). */
/** Onde a tira do celular NÃO entra: as mesmas telas em que a barra inferior
 *  não entra. `/exam/:id` guarda gabarito não salvo, `/bem-vindo` é uma
 *  conversa conduzida e o feed tem controles próprios no rodapé. */
const SEM_TIRA = ["/feed", "/bem-vindo", "/exam"];

function ehRotaAtual(pathname, to) {
  if (to === "/dashboard") return pathname === "/dashboard";
  return pathname === to || pathname.startsWith(`${to}/`);
}

// Saldo de Sparks — sempre visível, em toda largura. Um chip pequeno, mas que
// desde 2026-09-16 REAGE: quando o saldo sobe sem trocar de página (resgatar
// missão, responder no mural, comprar), o número novo sobe do próprio chip
// como "+40" e o chip pulsa uma vez.
//
// É o mesmo dado de antes, e continua vindo da mesma leitura. O que muda é
// que o ganho passa a acontecer ONDE o saldo mora, em vez de num toast num
// canto da tela que o olho tem de ir procurar — e um ganho que o aluno não vê
// é um ganho que não motiva ninguém.
//
// Relê o saldo quando alguém dispara `sparks:mudou` (ver `avisarSparksMudou`).
// Sem isso o chip busca uma vez na montagem e nunca mais: o aluno gastava 30
// Sparks destacando uma dúvida, via a confirmação na tela, e a barra continuava
// exibindo o saldo antigo até ele trocar de página. Um número de dinheiro que
// mente logo depois da compra é o pior lugar possível para um número mentir.
function SparksChip() {
  const [sparks, setSparks] = useState(null);
  const [ganho, setGanho] = useState(null);
  // `useRef` e não estado: o saldo anterior serve para COMPARAR, e guardá-lo
  // em estado provocaria uma segunda renderização a cada leitura só para
  // registrar um número que ninguém desenha.
  const anterior = useRef(null);

  useEffect(() => {
    let ativo = true;
    let limpar;
    const ler = () =>
      api.get("/firestore/students/me/sparks")
        .then(({ data }) => {
          if (!ativo) return;
          const novo = data.sparks_balance;
          // A PRIMEIRA leitura nunca anima: entrar numa página com "+320"
          // subindo da barra seria o produto comemorando o saldo que o aluno
          // já tinha antes de abrir a tela.
          if (anterior.current != null && novo > anterior.current) {
            setGanho(novo - anterior.current);
            clearTimeout(limpar);
            limpar = setTimeout(() => setGanho(null), 1500);
          }
          anterior.current = novo;
          setSparks(novo);
        })
        .catch(() => {});
    ler();
    window.addEventListener(EVENTO_SPARKS, ler);
    return () => {
      ativo = false;
      clearTimeout(limpar);
      window.removeEventListener(EVENTO_SPARKS, ler);
    };
  }, []);

  if (sparks == null) return null;
  return (
    <Link
      to="/sparks"
      className={`chip nav-tip relative shrink-0 border-amber-300/25 bg-amber-400/10 text-amber-100 hover:border-amber-300/50 hover:bg-amber-400/20 ${ganho ? "recompensa" : ""}`}
      data-testid="nav-sparks"
      data-tour="nav-sparks"
      data-tip="Sparks"
      aria-label={`${sparks} Sparks`}
    >
      <Zap className="h-3.5 w-3.5 text-amber-300" />
      <span className="font-mono-alt">{sparks}</span>
      {ganho && <span className="ganho text-sm">+{ganho}</span>}
    </Link>
  );
}

export default function Nav() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const { pathname } = useLocation();
  const [lancador, setLancador] = useState(false);
  // A barra endurece ao rolar: em repouso ela é quase só vidro sobre o
  // ambiente, e a partir de 8px de rolagem o fundo fecha e a linha de baixo
  // acende. É o que separa "barra flutuando sobre a página" de "barra colada
  // por cima do conteúdo" — sem isso, texto claro passando por baixo de vidro
  // claro é a falha clássica de barra translúcida.
  const [rolou, setRolou] = useState(false);

  // QUANTAS MINIATURAS CABEM — medido, nunca estimado.
  //
  // A barra vive num container de 1152px que nenhum monitor largo aumenta, e
  // a conta muda por conta: um admin que também é promoter carrega dois chips
  // a mais, e a medição de 2026-09-17 mostrou que essa conta chega a 1119px
  // dos 1152 disponíveis — 33px de folga, não os ~330 que a nota antiga
  // registrava para um aluno comum. Ou seja: uma lista fixa de miniaturas
  // estoura para uns e sobra para outros.
  //
  // Então a barra se mede sozinha. Ela soma o que é obrigatório (marca, abas
  // primárias, botões fixos), divide o que sobra por 40px (o ícone de 36 mais
  // o vão) e desenha só essa quantidade. Em 1280 com conta comum cabem
  // algumas; em 1920 cabem todas; num notebook de 13" com admin, nenhuma — e
  // em nenhum desses casos a barra quebra. Tudo o que não coube continua a um
  // clique no "Menu" e na tira do celular.
  const barraRef = useRef(null);
  const marcaRef = useRef(null);
  const primariosRef = useRef(null);
  const fixosRef = useRef(null);
  const [quantasMiniaturas, setQuantasMiniaturas] = useState(0);

  const medir = useCallback(() => {
    const barra = barraRef.current;
    if (!barra) return;
    // Abaixo de `lg` a barra de cima não tem abas nem miniaturas: quem navega
    // é a barra inferior e a tira rolável.
    if (window.innerWidth < 1024) return setQuantasMiniaturas(0);
    const largura = (el) => (el ? el.getBoundingClientRect().width : 0);
    const obrigatorio =
      largura(marcaRef.current) + largura(primariosRef.current) + largura(fixosRef.current);
    setQuantasMiniaturas(quantasCabem(barra.clientWidth, obrigatorio));
  }, []);

  useLayoutEffect(() => {
    medir();
    const ro = new ResizeObserver(medir);
    if (barraRef.current) ro.observe(barraRef.current);
    window.addEventListener("resize", medir);
    // A fonte muda a largura das abas depois de carregar: medir só na
    // montagem daria a conta da fonte de fallback, que é mais estreita.
    document.fonts?.ready?.then(medir).catch(() => {});
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", medir);
    };
  }, [medir]);

  useEffect(() => {
    const aoRolar = () => setRolou(window.scrollY > 8);
    aoRolar();
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => window.removeEventListener("scroll", aoRolar);
  }, []);

  const doLogout = async () => { await logout(); nav("/"); };

  return (
    <div
      className="glass sticky top-0 z-40 transition-shadow duration-300"
      style={rolou ? undefined : { boxShadow: "none", borderBottomColor: "transparent" }}
      data-rolou={rolou}
    >
      <div ref={barraRef} className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 md:px-10">
        {/* A MARCA, no canto superior esquerdo, em TODA largura de tela.
            Até 2026-09-16 este canto era o botão de menu do celular e a marca
            simplesmente não existia abaixo de 1024px — o produto se
            apresentava sem nome justamente no aparelho em que a maioria dos
            alunos entra. O menu desceu para a barra inferior, que é onde o
            polegar chega, e o canto voltou a ser da marca.
            Desde 2026-09-17, logado, tocar na marca ABRE o mesmo lançador do
            botão "Menu" — o gatilho mais óbvio do produto para abrir o menu é
            a própria marca, e não só um botão de grade a três alvos dali. */}
        <span ref={marcaRef} className="shrink-0">
        <Logo
          to={user ? null : "/"}
          onClick={user ? () => setLancador(true) : null}
          tamanho="m"
          className="shrink-0"
          classePalavra="text-xl sm:text-2xl"
          testid="nav-brand"
        />
        </span>

        {user && (
          <div className="flex items-center gap-1 lg:gap-2">
            {/* Envelope próprio (e não os links soltos) porque o guia de
                primeira sessão aponta para a BARRA inteira num passo só. */}
            <div ref={primariosRef} className="hidden items-center gap-1 lg:flex" data-tour="nav-primarios">
              {PRIMARY_LINKS.map((l) => {
                const ativa = ehRotaAtual(pathname, l.to);
                return (
                  <Link
                    key={l.to}
                    to={l.to}
                    className="nav-elo nav-tip flex items-center gap-2 rounded-full px-3 py-2 text-sm font-medium"
                    data-ativa={ativa}
                    data-testid={l.testid}
                    data-tour={l.tour}
                    data-tip={l.label}
                    aria-label={l.label}
                    aria-current={ativa ? "page" : undefined}
                  >
                    {l.mascote
                      ? <Mentis className="h-5 w-5 shrink-0" variante="icone" animada={false} />
                      : <l.icon className="h-4 w-4 shrink-0" strokeWidth={ativa ? 2.3 : 1.9} />}
                    {/* O rótulo só a partir de `xl`. Entre 1024 e 1279 a barra
                        fica em ícones puros com o traço aceso marcando onde se
                        está: é a faixa dos notebooks de 13", onde a soma dos
                        filhos com os seis rótulos escritos ESTOURAVA o
                        container (ver a medição no fim do arquivo). */}
                    <span className="hidden xl:inline">{l.texto || l.label}</span>
                  </Link>
                );
              })}
            </div>

            {/* AS MINIATURAS. A barra do desktop tinha ~330px de folga a
                1536px e ~188px a 1280px (medição no fim do arquivo), e essa
                folga não estava comprando nada: o aluno de notebook via seis
                abas e um botão de menu, enquanto o produto tem doze telas que
                ele usa toda semana. Aqui elas viram ícone redondo de 32px com
                o nome no `title` — miniatura, não aba: a aba diz onde você
                está, a miniatura leva onde você ainda não foi.

                Cada uma acende a partir da largura que couber (`min` em
                `lib/atalhos`), e é a MESMA lista que a tira do celular
                desenha logo abaixo — uma fonte só para as duas barras, senão
                o celular volta a ter metade das portas do desktop. */}
            {quantasMiniaturas > 0 && (
            <div className="hidden items-center gap-1 lg:flex" data-testid="nav-miniaturas">
              <span aria-hidden className="mx-1 h-5 w-px shrink-0 bg-white/10" />
              {ATALHOS.slice(0, quantasMiniaturas).map((m) => {
                const ativa = ehRotaAtual(pathname, m.rota);
                return (
                  <Link
                    key={m.rota}
                    to={m.rota}
                    className="nav-elo nav-tip inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
                    data-ativa={ativa}
                    data-testid={`nav-mini-${m.rota.slice(1)}`}
                    data-tip={m.label}
                    aria-label={m.label}
                    aria-current={ativa ? "page" : undefined}
                  >
                    <m.icone className="h-4 w-4" strokeWidth={ativa ? 2.3 : 1.9} />
                  </Link>
                );
              })}
            </div>
            )}

            <div ref={fixosRef} className="flex items-center gap-1 lg:gap-2">
            {/* O lançador: uma grade visual com TODAS as ferramentas.
                O ícone é `Grip` e não `LayoutGrid` desde 2026-09-17. Até ali
                a barra desenhava o MESMO símbolo duas vezes, a três alvos de
                distância um do outro: `LayoutGrid` era o ícone do Painel e
                era também o deste botão. Dois alvos idênticos lado a lado não
                são dois ícones parecidos — são um ícone que não significa
                nada, e quem clicava no botão esperando o Painel abria um
                painel deslizante. `Grip` (a malha de pontos) é o gesto de
                "tudo o que existe", e não colide com nada na barra. */}
            <button
              onClick={() => setLancador(true)}
              className="btn-vidro pill nav-tip hidden h-9 shrink-0 items-center gap-2 rounded-full px-3 text-xs font-semibold lg:inline-flex xl:px-4"
              data-ativa={lancador}
              data-testid="nav-more"
              data-tour="nav-more"
              data-tip="Menu"
              aria-label="Todas as ferramentas"
              aria-haspopup="dialog"
              aria-expanded={lancador}
            >
              <Grip className="h-4 w-4" />
              {/* A palavra a partir de `xl`, como os rótulos das abas: até
                  2026-09-17 este era um círculo de 36px sem contorno, sem
                  fundo e sem texto no meio de seis abas iguais a ele — o
                  botão que abre METADE do produto era o elemento menos
                  visível da barra. Agora ele tem superfície (`btn-vidro`),
                  o que já o separa das abas, e nome onde cabe. */}
              <span className="hidden xl:inline">Menu</span>
            </button>

            {/* A porta das AULAS — a aula ao vivo de quinta com o 1º colocado
                de Medicina da USP, o único compromisso com hora marcada do
                produto. No celular fica só o ícone com o ponto pulsante: a
                palavra custaria os 44px que o chip de Sparks ocupa a 360px, e
                o ponto vermelho já diz que há algo acontecendo. */}
            <Link
              to="/aula-ao-vivo"
              className="btn-calor pill nav-tip relative inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-full px-2.5 py-2 text-xs sm:px-3.5"
              data-testid="nav-aulas-particulares"
              data-tour="nav-aulas"
              data-tip="Aula ao vivo de quinta"
              aria-label="Aula ao vivo de quinta"
            >
              <span className="relative">
                <GraduationCap className="h-4 w-4" />
                <span className="absolute -right-1 -top-1 flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-500 opacity-80" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-rose-500" />
                </span>
              </span>
              <span className="hidden sm:inline">Aulas</span>
            </Link>

            <SparksChip />

            {/* O promoter não é admin — o botão dele leva a um painel à
                parte (`/promoter`), que só sabe quem usou O CUPOM dele e
                quanto essas pessoas gastaram. Verde por pedido explícito,
                com a palavra escrita (e não só o ícone) porque, ao contrário
                do admin, esta conta pode não reconhecer o ícone sozinho. */}
            {user.is_promoter && (
              <Link
                to="/promoter"
                className="pill nav-tip hidden h-9 shrink-0 items-center gap-1.5 rounded-full border border-emerald-400/30 bg-emerald-500/15 px-3 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/25 lg:inline-flex"
                data-testid="nav-promoter"
                data-tip="Painel do promoter"
                aria-label="Painel do promoter"
              >
                <Megaphone className="h-4 w-4" />
                Promoter
              </Link>
            )}

            {user.is_admin && (
              <Link
                to="/admin"
                className="pill nav-tip hidden h-9 w-9 shrink-0 items-center justify-center rounded-full border border-emerald-400/30 bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 lg:inline-flex"
                data-testid="nav-admin"
                data-tip="Admin"
                aria-label="Admin"
              >
                <ShieldCheck className="h-4 w-4" />
              </Link>
            )}

            {/* Sair fica só no desktop. No celular ele mora no rodapé do
                lançador, que agora abre pela barra inferior — e um botão de
                sair ao lado da marca, no alcance do polegar, é a saída
                acidental mais fácil de dar num produto de estudo. */}
            <button
              onClick={doLogout}
              className="pill btn-vidro nav-tip hidden h-9 w-9 shrink-0 items-center justify-center rounded-full lg:flex"
              data-testid="nav-logout"
              data-tip="Sair"
              aria-label="Sair"
            >
              <LogOut className="h-4 w-4" />
            </button>

            </div>

            <LancadorDeFerramentas
              aberto={lancador}
              aoFechar={() => setLancador(false)}
              user={user}
              aoSair={doLogout}
            />
          </div>
        )}

        {!user && (
          <Link
            to="/login"
            className="pill btn-sapiens rounded-full px-5 py-2 text-sm font-semibold"
            data-testid="nav-entrar"
          >
            Entrar
          </Link>
        )}
      </div>

      {/* A TIRA DO CELULAR — a paridade com o desktop.
          A barra inferior tem cinco alvos e isso é invariante (é o que o
          polegar alcança sem pensar), então o celular alcançava cinco telas
          em um toque contra as doze do desktop; o resto vivia atrás do
          lançador, que só abre quem já sabe que ele existe. A tira rola na
          horizontal, tem alvo de 32px de altura e mostra a MESMA lista de
          `lib/atalhos` — no iPhone e no Android, as mesmas portas do
          notebook, na mesma ordem.

          `rolagem-invisivel` esconde a barra de rolagem sem tirar a rolagem
          (o Android desenha uma barra cinza por cima do conteúdo). A borda
          some nas telas em que a barra inferior também some. */}
      {user && !SEM_TIRA.some((r) => pathname === r || pathname.startsWith(`${r}/`)) && (
        <div className="lg:hidden" data-testid="nav-tira-atalhos">
          <div className="rolagem-invisivel flex gap-2 overflow-x-auto px-4 pb-2.5 pt-0.5">
            {ATALHOS.map((m) => {
              const ativa = ehRotaAtual(pathname, m.rota);
              return (
                <Link
                  key={m.rota}
                  to={m.rota}
                  className="nav-elo flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-3 text-xs font-semibold"
                  data-ativa={ativa}
                  data-testid={`nav-tira-${m.rota.slice(1)}`}
                  aria-label={m.label}
                  aria-current={ativa ? "page" : undefined}
                >
                  <m.icone className="h-3.5 w-3.5 shrink-0" strokeWidth={ativa ? 2.3 : 1.9} />
                  {m.nome}
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MEDIÇÃO DA BARRA — revista em 2026-09-16, com usuário ADMIN (o caso mais largo)
// ---------------------------------------------------------------------------
//
// A barra vive num `max-w-6xl` com `px-10`: 1072px de conteúdo útil a partir
// de 1152px de viewport, e NENHUM monitor mais largo aumenta isso. Toda vez
// que um item entra aqui, a soma dos filhos tem de ser MEDIDA — não estimada.
//
// O que mudou nesta passada, e o que cada mudança comprou:
//
//   · O menu do celular SAIU da barra e virou a barra inferior. O canto
//     superior esquerdo voltou a ser da marca, com a palavra "Sapiens" ao
//     lado dela em toda largura — inclusive no celular, onde a marca não
//     aparecia de jeito nenhum.
//   · Os rótulos dos seis primários agora aparecem só a partir de `xl`. Entre
//     1024 e 1279 a barra é de ícones, e quem diz onde se está é o traço
//     aceso da aba ativa, que antes não existia em nenhuma largura.
//   · "Sair" passou a ser só ícone em vidro, e some abaixo de `lg` (vive no
//     rodapé do lançador).
//
// Folga medida com a Manrope carregada, somando o retângulo de cada filho:
//
//   viewport   antes (6 abas escritas)   agora
//   360px             —  (sem barra)      ~96px   (marca + aulas + sparks)
//   1024px            84px                ~220px  (ícones puros)
//   1280px           113px                ~188px  (rótulos ligados)
//   1536px            37px                ~330px
//
// A folga a 1536 saiu de 37px para ~330px. Era ali que a barra estava a uma
// fonte de fallback de estourar, e é a folga que paga o próximo item que
// alguém quiser pôr aqui — de preferência, nenhum.
