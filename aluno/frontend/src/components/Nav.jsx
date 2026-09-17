import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import {
  Zap, ShieldCheck, LayoutGrid, GraduationCap, PenLine, MessageCircle, Compass,
  CalendarDays, Users, LogOut, Megaphone,
} from "lucide-react";
import Logo from "./Logo";
import Mentis from "./Mentis";
import LancadorDeFerramentas from "./LancadorDeFerramentas";

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
const PRIMARY_LINKS = [
  { to: "/treino", icon: Compass, label: "Treino", testid: "nav-treino", tour: "nav-treino" },
  { to: "/dashboard", icon: LayoutGrid, label: "Painel", testid: "nav-dashboard", tour: "nav-dashboard" },
  { to: "/redacao", icon: PenLine, label: "Redação", testid: "nav-redacao", tour: "nav-redacao" },
  { to: "/cronograma", icon: CalendarDays, label: "Cronograma", texto: "Semana", testid: "nav-cronograma" },
  { to: "/comunidade", icon: Users, label: "Comunidade", texto: "Mural", testid: "nav-comunidade" },
  { to: "/mentis", icon: MessageCircle, label: "Mentis", testid: "nav-mentis", tour: "nav-mentis", mascote: true },
];

/** A rota atual, para a aba acender. `/dashboard` é exata porque tudo volta
 *  para ela; as outras casam com as filhas (`/comunidade/:id` mantém o Mural
 *  aceso enquanto a dúvida está aberta). */
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
      className={`chip relative shrink-0 border-amber-300/25 bg-amber-400/10 text-amber-100 hover:border-amber-300/50 hover:bg-amber-400/20 ${ganho ? "recompensa" : ""}`}
      data-testid="nav-sparks"
      data-tour="nav-sparks"
      title={`${sparks} Sparks`}
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
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 md:px-10">
        {/* A MARCA, no canto superior esquerdo, em TODA largura de tela.
            Até 2026-09-16 este canto era o botão de menu do celular e a marca
            simplesmente não existia abaixo de 1024px — o produto se
            apresentava sem nome justamente no aparelho em que a maioria dos
            alunos entra. O menu desceu para a barra inferior, que é onde o
            polegar chega, e o canto voltou a ser da marca. */}
        <Logo
          to={user ? "/dashboard" : "/"}
          tamanho="m"
          className="shrink-0"
          classePalavra="text-xl sm:text-2xl"
          testid="nav-brand"
        />

        {user && (
          <div className="flex items-center gap-1 lg:gap-2">
            {/* Envelope próprio (e não os links soltos) porque o guia de
                primeira sessão aponta para a BARRA inteira num passo só. */}
            <div className="hidden items-center gap-1 lg:flex" data-tour="nav-primarios">
              {PRIMARY_LINKS.map((l) => {
                const ativa = ehRotaAtual(pathname, l.to);
                return (
                  <Link
                    key={l.to}
                    to={l.to}
                    className="nav-elo flex items-center gap-2 rounded-full px-3 py-2 text-sm font-medium"
                    data-ativa={ativa}
                    data-testid={l.testid}
                    data-tour={l.tour}
                    aria-label={l.label}
                    aria-current={ativa ? "page" : undefined}
                    title={l.label}
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

            {/* O lançador: uma grade visual com TODAS as ferramentas. */}
            <button
              onClick={() => setLancador(true)}
              className="nav-elo hidden h-9 w-9 items-center justify-center rounded-full lg:flex"
              data-ativa={lancador}
              data-testid="nav-more"
              data-tour="nav-more"
              aria-label="Todas as ferramentas"
              title="Todas as ferramentas"
            >
              <LayoutGrid className="h-4 w-4" />
            </button>

            {/* A porta das AULAS — a aula ao vivo de quinta com o 1º colocado
                de Medicina da USP, o único compromisso com hora marcada do
                produto. No celular fica só o ícone com o ponto pulsante: a
                palavra custaria os 44px que o chip de Sparks ocupa a 360px, e
                o ponto vermelho já diz que há algo acontecendo. */}
            <Link
              to="/aula-ao-vivo"
              className="btn-calor pill relative inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-full px-2.5 py-2 text-xs sm:px-3.5"
              data-testid="nav-aulas-particulares"
              data-tour="nav-aulas"
              aria-label="Aula ao vivo de quinta"
              title="Aula ao vivo de quinta"
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
                className="pill hidden h-9 shrink-0 items-center gap-1.5 rounded-full border border-emerald-400/30 bg-emerald-500/15 px-3 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/25 lg:inline-flex"
                data-testid="nav-promoter"
                aria-label="Painel do promoter"
                title="Painel do promoter"
              >
                <Megaphone className="h-4 w-4" />
                Promoter
              </Link>
            )}

            {user.is_admin && (
              <Link
                to="/admin"
                className="pill hidden h-9 w-9 shrink-0 items-center justify-center rounded-full border border-emerald-400/30 bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 lg:inline-flex"
                data-testid="nav-admin"
                aria-label="Admin"
                title="Admin"
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
              className="pill btn-vidro hidden h-9 w-9 shrink-0 items-center justify-center rounded-full lg:flex"
              data-testid="nav-logout"
              aria-label="Sair"
              title="Sair"
            >
              <LogOut className="h-4 w-4" />
            </button>

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
