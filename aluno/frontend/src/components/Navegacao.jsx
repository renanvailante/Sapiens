import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import { Zap, Grip } from "lucide-react";
import Logo from "./Logo";
import Mentis from "./Mentis";
import Menu from "./Menu";
import { AREAS, temNavegacao } from "../lib/navegacao";
import { ROTAS, ehRotaAtual } from "../lib/rotas";

export const EVENTO_SPARKS = "sparks:mudou";

/** Avisa a barra que o saldo mudou. Chame depois de QUALQUER ação que credite
 *  ou debite Sparks sem sair da página. Um evento de janela, e não um contexto
 *  de React, porque o chip vive na barra e quem gasta vive na tela — um
 *  provedor para carregar um inteiro entre os dois seria mais encanamento do
 *  que problema. */
export function avisarSparksMudou() {
  window.dispatchEvent(new Event(EVENTO_SPARKS));
}

/**
 * A NAVEGAÇÃO DO PRODUTO — uma peça, montada uma vez, para os dois aparelhos.
 *
 * ---------------------------------------------------------------------------
 * POR QUE ESTE ARQUIVO EXISTE
 * ---------------------------------------------------------------------------
 *
 * Havia `Nav.jsx` (a barra de cima, montada à mão por 38 páginas), `Tela.jsx`
 * (que montava a mesma `Nav` para outras 7), `BarraInferior.jsx` (montada uma
 * vez no `App.js`) e a tira de atalhos do celular (dentro da `Nav`). Quatro
 * peças, três listas de destinos, duas regras de "onde não aparecer" que já
 * divergiam — a de cima escondia a tira em `/exam` e a de baixo em `/exam/`.
 *
 * E a consequência estrutural: **uma página nova nascia sem barra** a menos
 * que lembrasse de montar a sua. Foi o que aconteceu com a barra inferior
 * (abaixo de 1024px o produto passou meses sem navegação nenhuma) e com a
 * camada de continuidade. Por isso as duas acabaram no `App.js`, e por isso
 * esta também está: **o que vale para todas as telas não pode ser montado
 * tela a tela.**
 *
 * Agora: `Navegacao` é montada uma vez em `App.js`, desenha o TRILHO lateral
 * em `lg+` (desde 2026-10-19; antes era uma barra de cima) e a barra de baixo
 * abaixo disso, e os dois leem a MESMA lista (`AREAS`).
 * Página nova não faz nada — e não tem como criar um sistema paralelo, porque
 * não há o que montar.
 *
 * ---------------------------------------------------------------------------
 * O QUE SUMIU, E POR QUÊ
 * ---------------------------------------------------------------------------
 *
 * **A tira de atalhos do celular** (8 pílulas roláveis, `lib/atalhos.js`).
 * Ela existia para compensar a barra inferior ter 4 destinos contra os 7 do
 * desktop. Com as duas barras desenhando as mesmas cinco áreas, ela passou a
 * ser uma segunda navegação para os mesmos lugares, 40px abaixo da primeira.
 *
 * **O quinto alvo "Mais" da barra inferior.** Ele abria a gaveta. A gaveta
 * agora é carteira, suporte e sistema — nada pedagógico —, então ela desceu
 * para o canto da marca (que já a abria no desktop desde 17/09) e o quinto
 * alvo do polegar virou uma área de verdade. Ver a regra em `lib/navegacao.js`.
 *
 * ---------------------------------------------------------------------------
 * A CONTA DE LARGURA (aposentada)
 * ---------------------------------------------------------------------------
 *
 * A barra de cima vivia em 1072px úteis e estourou duas vezes. O trilho
 * empilha as áreas na vertical, e a conta deixou de existir — ver o fim do
 * arquivo.
 */

// ---------------------------------------------------------------------------
// O saldo de Sparks
// ---------------------------------------------------------------------------

/** Sempre visível, em toda largura. Um chip pequeno que REAGE: quando o saldo
 *  sobe sem trocar de página (resgatar missão, responder no mural, comprar), o
 *  número novo sobe do próprio chip como "+40" e o chip pulsa uma vez.
 *
 *  Relê quando alguém dispara `sparks:mudou`. Sem isso o chip busca uma vez na
 *  montagem e nunca mais: o aluno gastava 30 Sparks destacando uma dúvida, via
 *  a confirmação na tela, e a barra continuava exibindo o saldo antigo. Um
 *  número de dinheiro que mente logo depois da compra é o pior lugar possível
 *  para um número mentir. */
function ChipDeSparks({ className = "", variante = "chip" }) {
  const [sparks, setSparks] = useState(null);
  const [ganho, setGanho] = useState(null);
  // `useRef` seria uma segunda importação para guardar um número que ninguém
  // desenha; aqui a comparação cabe numa variável do próprio efeito.
  const [anterior, setAnterior] = useState(null);

  useEffect(() => {
    let ativo = true;
    let limpar;
    let ultimo = null;
    const ler = () =>
      api
        .get("/firestore/students/me/sparks")
        .then(({ data }) => {
          if (!ativo) return;
          const novo = data.sparks_balance;
          // A PRIMEIRA leitura nunca anima: entrar numa página com "+320"
          // subindo da barra seria o produto comemorando o saldo que o aluno
          // já tinha antes de abrir a tela.
          if (ultimo != null && novo > ultimo) {
            setGanho(novo - ultimo);
            clearTimeout(limpar);
            limpar = setTimeout(() => setGanho(null), 1500);
          }
          ultimo = novo;
          setAnterior(novo);
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

  // No trilho o saldo é uma linha como as áreas — ícone âmbar e o número no
  // lugar do nome —, para o pé da coluna ler como parte dela.
  if (variante === "trilho") {
    return (
      <Link
        to={ROTAS.SPARKS}
        className={`trilho-elo nav-tip ${ganho ? "recompensa" : ""} ${className}`}
        style={{ "--cor": "#FFB547" }}
        data-testid="nav-sparks"
        data-tour="nav-sparks"
        data-tip={`${sparks} Sparks`}
        aria-label={`${sparks} Sparks`}
        data-anterior={anterior ?? undefined}
      >
        <Zap strokeWidth={2.4} fill="currentColor" />
        <span className="trilho-rotulo font-mono-alt text-[#FFB547]">{sparks}</span>
        {ganho && <span className="ganho text-sm">+{ganho}</span>}
      </Link>
    );
  }

  return (
    <Link
      to={ROTAS.SPARKS}
      className={`chip nav-tip relative shrink-0 ${ganho ? "recompensa" : ""} ${className}`}
      data-testid="nav-sparks"
      data-tour="nav-sparks"
      data-tip="Sparks"
      aria-label={`${sparks} Sparks`}
      data-anterior={anterior ?? undefined}
    >
      <Zap className="h-4 w-4 text-[#FFB547]" fill="currentColor" />
      <span className="font-mono-alt text-[#FFB547]">{sparks}</span>
      {ganho && <span className="ganho text-sm">+{ganho}</span>}
    </Link>
  );
}

// ---------------------------------------------------------------------------
// O trilho (lg+) — a navegação do desktop desde 2026-10-19
// ---------------------------------------------------------------------------

/** Uma coluna fixa à esquerda, como nos prints do Duolingo que o dono mandou:
 *  a marca no topo, as cinco áreas com ícone grande e colorido, e no pé o
 *  saldo e o Menu. Substituiu a barra de cima, que vivia presa a 1072px de
 *  largura útil e já tinha estourado duas vezes; aqui uma área a mais custa
 *  altura, que sobra.
 *
 *  Entre 1024 e 1279px o trilho tem 88px e mostra só os ícones (o nome vem no
 *  balão ao passar o mouse); de 1280px para cima, ícone + nome. Quem empurra
 *  o conteúdo é o CSS, por `html[data-trilho]`, que o componente liga
 *  enquanto está montado. */
function Trilho({ pathname, aoAbrirMenu, menuAberto }) {
  useEffect(() => {
    document.documentElement.dataset.trilho = "sim";
    return () => { delete document.documentElement.dataset.trilho; };
  }, []);

  return (
    <nav className="trilho" aria-label="Navegação principal" data-testid="barra-superior">
      {/* A MARCA é a porta do Menu, como sempre foi. */}
      <div className="trilho-marca">
        <Logo
          onClick={aoAbrirMenu}
          tamanho="m"
          classePalavra="hidden xl:inline"
          testid="nav-brand"
        />
      </div>

      {/* Envelope próprio porque o guia de primeira sessão aponta para o
          conjunto das áreas num passo só. */}
      <div className="flex flex-col gap-1.5" data-tour="nav-areas">
        {AREAS.map((area) => {
          const ativa = ehRotaAtual(pathname, area.rota);
          return (
            <Link
              key={area.chave}
              to={area.rota}
              className="trilho-elo nav-tip"
              style={{ "--cor": area.cor }}
              data-ativa={ativa}
              data-testid={area.testid}
              data-tour={area.tour}
              data-tip={area.pergunta}
              aria-label={`${area.nome} — ${area.pergunta}`}
              aria-current={ativa ? "page" : undefined}
            >
              <area.icone strokeWidth={2.4} />
              <span className="trilho-rotulo">{area.nome}</span>
            </Link>
          );
        })}
      </div>

      <div className="trilho-pe">
        <ChipDeSparks variante="trilho" />
        {/* O Menu: a mesma gaveta que a marca abre. Como linha nomeada porque
            um alvo com nome é mais descobrível que um logotipo clicável. */}
        <button
          type="button"
          onClick={aoAbrirMenu}
          className="trilho-elo nav-tip"
          style={{ "--cor": "#C2CFE6" }}
          data-ativa={menuAberto}
          data-testid="nav-menu"
          data-tour="nav-menu"
          data-tip="Conta, Sparks e mais"
          aria-label="Minha conta e mais"
          aria-haspopup="dialog"
          aria-expanded={menuAberto}
        >
          <Grip strokeWidth={2.4} />
          <span className="trilho-rotulo">Mais</span>
        </button>
      </div>
    </nav>
  );
}

// ---------------------------------------------------------------------------
// A barra de baixo (celular)
// ---------------------------------------------------------------------------

/** Cinco alvos, e o do meio é elevado e aceso. O critério não é quantas telas
 *  existem, é quantas o polegar precisa alcançar sem pensar — e, desde que o
 *  Menu subiu para a marca, as cinco vagas são cinco ÁREAS, não quatro áreas e
 *  uma gaveta. */
function BarraDeBaixo({ pathname }) {
  return (
    <nav
      className="barra-inferior lg:hidden"
      aria-label="Navegação principal"
      data-testid="barra-inferior"
      data-tour="barra-inferior"
    >
      {AREAS.map((area) => {
        const ativa = ehRotaAtual(pathname, area.rota);

        // A AÇÃO. Fora do fluxo de rótulo das outras para poder subir 22px
        // acima da barra sem empurrar as vizinhas.
        if (area.acao) {
          return (
            <Link
              key={area.chave}
              to={area.rota}
              className="flex flex-1 flex-col items-center justify-start"
              data-testid={`barra-${area.chave}`}
              data-ativa={ativa}
              aria-label={`${area.nome} — ${area.pergunta}`}
              aria-current={ativa ? "page" : undefined}
            >
              <span className="aba-acao">
                <area.icone className="h-7 w-7" strokeWidth={2.4} />
              </span>
              <span className="aba-acao-rotulo">{area.nome}</span>
            </Link>
          );
        }

        return (
          <Link
            key={area.chave}
            to={area.rota}
            className="aba-inferior"
            style={{ "--cor": area.cor }}
            data-ativa={ativa}
            data-testid={`barra-${area.chave}`}
            aria-label={`${area.nome} — ${area.pergunta}`}
            aria-current={ativa ? "page" : undefined}
          >
            <area.icone className="h-6 w-6" strokeWidth={2.3} />
            <span>{area.nome}</span>
          </Link>
        );
      })}
    </nav>
  );
}

/** O botão que abre o Menu no celular, onde não há barra de cima com espaço
 *  para um alvo nomeado: ele mora no canto da marca, que é o mesmo gesto do
 *  desktop. Desenhado aqui, e não na `BarraDeCima`, porque abaixo de `lg` a
 *  barra de cima é só marca + saldo. */
function MarcaDoCelular({ aoAbrirMenu }) {
  return (
    <div className="glass sticky top-0 z-40 lg:hidden" data-testid="barra-superior-celular">
      <div className="flex h-14 items-center justify-between gap-3 px-4">
        <Logo onClick={aoAbrirMenu} tamanho="p" classePalavra="text-lg" testid="nav-brand-celular" />
        <div className="flex items-center gap-2">
          <ChipDeSparks />
          <button
            type="button"
            onClick={aoAbrirMenu}
            className="chip flex h-9 w-9 shrink-0 items-center justify-center !p-0"
            data-testid="nav-menu-celular"
            data-tour="nav-menu-celular"
            aria-label="Minha conta e mais"
            aria-haspopup="dialog"
          >
            <Grip className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

export default function Navegacao() {
  const { user, loading, logout } = useAuth() || {};
  const { pathname } = useLocation();
  const nav = useNavigate();
  const [menu, setMenu] = useState(false);

  // Fecha o Menu ao trocar de rota. Sem isso, clicar numa linha do Menu
  // navegava E deixava o painel aberto por cima da tela nova.
  useEffect(() => { setMenu(false); }, [pathname]);

  if (loading || !user) return null;
  if (!temNavegacao(pathname)) return null;

  const sair = async () => {
    await logout();
    nav(ROTAS.LANDING);
  };

  const abrirMenu = () => setMenu(true);

  return (
    <>
      {/* Desktop: o trilho à esquerda. Celular: só marca + saldo + porta do
          Menu em cima; as áreas ficam na barra de baixo, onde o polegar chega. */}
      <div className="hidden lg:block">
        <Trilho pathname={pathname} aoAbrirMenu={abrirMenu} menuAberto={menu} />
      </div>
      <MarcaDoCelular aoAbrirMenu={abrirMenu} />

      <BarraDeBaixo pathname={pathname} />

      <Menu
        aberto={menu}
        aoFechar={() => setMenu(false)}
        user={user}
        aoSair={sair}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// A MEDIÇÃO DE LARGURA QUE MORAVA AQUI
// ---------------------------------------------------------------------------
//
// Até 2026-10-19 este arquivo terminava com a conta de largura da barra de
// cima (1072px úteis, 811px de soma, 133px de folga a 1024px). O trilho
// lateral aposentou a conta: as áreas empilham na vertical. O que continua
// valendo é o teto de cinco áreas, por causa da barra do celular — ver
// `lib/navegacao.test.js` e `Cerebro/ux/navegacao.md`.
