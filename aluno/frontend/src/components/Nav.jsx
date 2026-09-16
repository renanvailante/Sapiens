import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import {
  Zap, ShieldCheck, LayoutGrid, GraduationCap, PenLine, MessageCircle, Compass,
  CalendarDays, LogOut,
} from "lucide-react";
import BrandMark from "./BrandMark";
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

// As cinco coisas que o aluno FAZ. A ordem é decisão de produto, revista em
// 2026-09-15: o **Mapa de Treino vem primeiro** — é a superfície de maior
// impacto visual do Sapiens e a que comunica o valor do produto em cinco
// segundos; deixá-lo em terceiro era esconder a vitrine atrás do estoque.
// Depois o Painel (para onde tudo volta), Redação, Cronograma e a Mentis.
//
// "Provas do ENEM" não está aqui porque o Painel abre nelas com o botão
// principal, e tudo o mais mora no LANÇADOR (o botão de grade) — que deixou
// de ser um menu de texto de dez linhas e virou uma grade visual onde cada
// ferramenta aparece com nome e função.
//
// `curto` existe por causa da largura: a barra vive num container de 1152px
// que nenhum monitor largo aumenta. Ver a nota de medição no fim do arquivo.
const PRIMARY_LINKS = [
  { to: "/treino", icon: Compass, label: "Treino", testid: "nav-treino", tour: "nav-treino" },
  { to: "/dashboard", icon: LayoutGrid, label: "Painel", testid: "nav-dashboard", tour: "nav-dashboard" },
  { to: "/redacao", icon: PenLine, label: "Redação", testid: "nav-redacao", tour: "nav-redacao" },
  { to: "/cronograma", icon: CalendarDays, label: "Cronograma", curto: "Semana", testid: "nav-cronograma" },
  { to: "/mentis", icon: MessageCircle, label: "Mentis", testid: "nav-mentis", tour: "nav-mentis", mascote: true },
];

// Saldo de Sparks — sempre visível (mesmo no mobile), mas discreto: um chip
// pequeno, sem chamar mais atenção que os links de navegação.
//
// Relê o saldo quando alguém dispara `sparks:mudou` (ver `avisarSparksMudou`).
// Sem isso o chip busca uma vez na montagem e nunca mais: o aluno gastava 30
// Sparks destacando uma dúvida, via a confirmação na tela, e a barra continuava
// exibindo o saldo antigo até ele trocar de página. Um número de dinheiro que
// mente logo depois da compra é o pior lugar possível para um número mentir.
function SparksChip() {
  const [sparks, setSparks] = useState(null);
  useEffect(() => {
    let ativo = true;
    const ler = () =>
      api.get("/firestore/students/me/sparks")
        .then(({ data }) => { if (ativo) setSparks(data.sparks_balance); })
        .catch(() => {});
    ler();
    window.addEventListener(EVENTO_SPARKS, ler);
    return () => { ativo = false; window.removeEventListener(EVENTO_SPARKS, ler); };
  }, []);
  if (sparks == null) return null;
  return (
    <Link
      to="/sparks"
      className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/8 px-3 py-1.5 text-xs font-medium text-white/70 transition-colors hover:bg-white/15 hover:text-white"
      data-testid="nav-sparks"
      data-tour="nav-sparks"
    >
      <Zap className="h-3.5 w-3.5 text-amber-400" /> {sparks}
    </Link>
  );
}

export default function Nav() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [lancador, setLancador] = useState(false);
  const doLogout = async () => { await logout(); nav("/"); };

  return (
    <div className="glass sticky top-0 z-40">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6 md:px-10">
        {user ? (
          <button
            onClick={() => setLancador(true)}
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-sapiens-accent/50 bg-sapiens-accent/20 text-white transition-transform active:scale-95 lg:hidden"
            data-testid="nav-mobile-trigger"
            // No celular é ESTE botão que abre o lançador — o guia aponta
            // para ele no lugar do `nav-more`, que não existe abaixo de `lg`.
            data-tour="nav-mobile-trigger"
            aria-label="Abrir menu"
          >
            <BrandMark className="h-5 w-5" />
          </button>
        ) : (
          <span className="lg:hidden" />
        )}
        <Link
          to={user ? "/dashboard" : "/"}
          className="hidden items-center gap-2 font-display text-2xl font-extrabold tracking-tighter text-white lg:flex 2xl:gap-2.5"
          data-testid="nav-brand"
        >
          <BrandMark className="h-7 w-7 lg:h-8 lg:w-8" />
          Sapiens
        </Link>
        {user && (
          <div className="flex items-center gap-1 lg:gap-2 2xl:gap-3">
            {/* Envelope próprio (e não os links soltos) porque o guia de
                primeira sessão aponta para a BARRA inteira num passo só. */}
            <div className="hidden items-center gap-0.5 lg:flex 2xl:gap-1" data-tour="nav-primarios">
              {PRIMARY_LINKS.map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  className="flex items-center gap-1.5 rounded-full px-2 py-2 text-sm text-white/60 transition-colors hover:text-white 2xl:gap-2 2xl:px-2.5"
                  data-testid={l.testid}
                  data-tour={l.tour}
                  aria-label={l.label}
                  title={l.label}
                >
                  {l.mascote ? <Mentis className="h-5 w-5" variante="icone" /> : <l.icon className="h-4 w-4" />}
                  {l.curto ? (
                    <>
                      <span className="hidden 2xl:inline">{l.label}</span>
                      <span className="2xl:hidden">{l.curto}</span>
                    </>
                  ) : (
                    <span>{l.label}</span>
                  )}
                </Link>
              ))}
            </div>

            {/* O lançador. Mesma largura do antigo "…", conteúdo completamente
                outro: uma grade visual com TODAS as ferramentas em vez de uma
                lista de texto escondida atrás de três pontos. */}
            <button
              onClick={() => setLancador(true)}
              className="hidden h-9 w-9 items-center justify-center rounded-full text-white/60 transition-colors hover:bg-white/10 hover:text-white lg:flex"
              data-testid="nav-more"
              data-tour="nav-more"
              aria-label="Todas as ferramentas"
              title="Todas as ferramentas"
            >
              <LayoutGrid className="h-4 w-4" />
            </button>

            {/* A porta das AULAS. Mesmo rótulo curto e mesma largura de antes
                (ver a nota de medição no fim do arquivo: a barra tem ~51px de
                folga a 1536 e nenhum monitor a aumenta) — o que mudou é o
                destino: em vez de abrir um modal de pedido de aula, leva à aba
                de Cursos, onde moram a AULA AO VIVO de quinta com o 1º
                colocado de Medicina da USP e os cursos. O ponto pulsante é a
                única coisa acrescentada, e ele é posicionado em cima do
                ícone: custa 0px de largura. */}
            <Link
              to="/cursos"
              className="btn-calor pill relative hidden shrink-0 items-center gap-2 whitespace-nowrap rounded-full px-3.5 py-2 text-xs lg:inline-flex 2xl:text-sm"
              data-testid="nav-aulas-particulares"
              data-tour="nav-aulas"
              title="Cursos e a aula ao vivo de quinta"
            >
              <span className="relative">
                <GraduationCap className="h-4 w-4" />
                <span className="absolute -right-1 -top-1 flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-500 opacity-80" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-rose-500" />
                </span>
              </span>
              Aulas
            </Link>

            <SparksChip />

            {user.is_admin && (
              <Link
                to="/admin"
                className="pill hidden items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-500/15 px-3 py-2 text-xs font-medium text-emerald-300 hover:bg-emerald-500/25 lg:inline-flex 2xl:text-sm"
                data-testid="nav-admin"
                aria-label="Admin"
                title="Admin"
              >
                <ShieldCheck className="h-4 w-4" /> <span className="hidden 2xl:inline">Admin</span>
              </Link>
            )}
            <button
              onClick={doLogout}
              className="pill btn-sapiens hidden h-10 w-10 items-center justify-center rounded-full text-sm font-medium lg:flex"
              data-testid="nav-logout"
              aria-label="Sair"
              title="Sair"
            >
              {/* Só o ícone, em toda largura de desktop. A barra vive num
                  container de 1152px que nenhum monitor largo aumenta, e a
                  medição de 2026-09-12 mostrou 6px de folga com o rótulo
                  "Sair" escrito — folga que qualquer fonte de fallback come.
                  A porta de sair é a última coisa que pode ficar cortada. */}
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
      </div>
    </div>
  );
}
