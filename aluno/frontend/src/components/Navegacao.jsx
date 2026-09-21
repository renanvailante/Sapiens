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
 * Agora: `Navegacao` é montada uma vez em `App.js`, desenha a barra de cima em
 * `lg+` e a de baixo abaixo disso, e as duas leem a MESMA lista (`AREAS`).
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
 * A CONTA DE LARGURA
 * ---------------------------------------------------------------------------
 *
 * 1072px úteis em `max-w-6xl px-10`, e nenhum monitor aumenta isso. Com sete
 * primários dava 1020px — 52px de folga, menos que um rótulo.
 *
 * MEDIDO no navegador em 2026-09-18, com a tipografia real do bundle:
 *
 *     viewport   útil     soma    folga
 *     1024px     944px    811px   133px      ← a faixa mais apertada
 *     1280px    1072px    811px   261px
 *     1536px    1072px    811px   261px
 *
 * As cinco abas medem 72 / 92 / 93 / 109 / 126px (Hoje…Comunidade).
 *
 * **A folga de 1024 é a que importa**, e não a de 1536: abaixo de `lg` a barra
 * de cima nem desenha as áreas, e o `px-4` dali dá 944px úteis contra os 1072
 * de `md:px-10`. As economias `2xl:` não ajudam nessa faixa.
 *
 * Os 133px pagam o rótulo aparecer a partir de `lg` e não de `xl` — que é o
 * que tirava o nome das abas justamente no notebook de 13". Um ícone que o
 * aluno precisa decifrar não é navegação, é charada.
 *
 * `lib/navegacao.test.js` trava a contagem: uma sexta área derruba o teste e
 * manda medir de novo, que é a conversa que precisa acontecer.
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
function ChipDeSparks({ className = "" }) {
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
  return (
    <Link
      to={ROTAS.SPARKS}
      className={`chip nav-tip relative shrink-0 border-amber-300/25 bg-amber-400/10 text-amber-100 hover:border-amber-300/50 hover:bg-amber-400/20 ${ganho ? "recompensa" : ""} ${className}`}
      data-testid="nav-sparks"
      data-tour="nav-sparks"
      data-tip="Sparks"
      aria-label={`${sparks} Sparks`}
      data-anterior={anterior ?? undefined}
    >
      <Zap className="h-3.5 w-3.5 text-amber-300" />
      <span className="font-mono-alt">{sparks}</span>
      {ganho && <span className="ganho text-sm">+{ganho}</span>}
    </Link>
  );
}

// ---------------------------------------------------------------------------
// A barra de cima (lg+)
// ---------------------------------------------------------------------------

function BarraDeCima({ pathname, aoAbrirMenu, menuAberto }) {
  // A barra endurece ao rolar: em repouso é quase só vidro sobre o ambiente, e
  // a partir de 8px o fundo fecha e a linha de baixo acende. É o que separa
  // "barra flutuando sobre a página" de "barra colada por cima do conteúdo" —
  // sem isso, texto claro passando por baixo de vidro claro é a falha clássica
  // de barra translúcida.
  const [rolou, setRolou] = useState(false);

  useEffect(() => {
    const aoRolar = () => setRolou(window.scrollY > 8);
    aoRolar();
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => window.removeEventListener("scroll", aoRolar);
  }, []);

  return (
    <div
      className="glass sticky top-0 z-40 transition-shadow duration-300"
      style={rolou ? undefined : { boxShadow: "none", borderBottomColor: "transparent" }}
      data-rolou={rolou}
      data-testid="barra-superior"
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 md:px-10">
        {/* A MARCA, no canto superior esquerdo, em TODA largura de tela — e,
            logado, ela É a porta do Menu. O gatilho mais óbvio do produto para
            abrir o menu é a própria marca. */}
        <Logo
          onClick={aoAbrirMenu}
          tamanho="m"
          className="shrink-0"
          classePalavra="text-xl sm:text-2xl"
          testid="nav-brand"
        />

        <div className="flex items-center gap-1 lg:gap-2">
          {/* Envelope próprio (e não os links soltos) porque o guia de primeira
              sessão aponta para a BARRA inteira num passo só. */}
          <div className="hidden items-center gap-1.5 lg:flex" data-tour="nav-areas">
            {AREAS.map((area) => {
              const ativa = ehRotaAtual(pathname, area.rota);
              return (
                <Link
                  key={area.chave}
                  to={area.rota}
                  className="nav-elo nav-tip flex items-center gap-1.5 rounded-full px-2.5 py-2 text-sm font-medium"
                  data-ativa={ativa}
                  data-testid={area.testid}
                  data-tour={area.tour}
                  data-tip={area.pergunta}
                  aria-label={`${area.nome} — ${area.pergunta}`}
                  aria-current={ativa ? "page" : undefined}
                >
                  <area.icone className="h-4 w-4 shrink-0" strokeWidth={ativa ? 2.3 : 1.9} />
                  {/* O nome, SEMPRE, a partir de `lg`. Era `hidden xl:inline`, e
                      a faixa de 1024–1279px (notebook de 13") ficava só com
                      ícones. Com cinco áreas a folga paga o rótulo. */}
                  <span>{area.nome}</span>
                </Link>
              );
            })}
          </div>

          <ChipDeSparks />

          {/* O Menu: a mesma gaveta que a marca abre. Ela existe também como
              botão porque um alvo nomeado é mais descobrível que um logotipo
              clicável — mas os dois abrem a MESMA coisa, e é por isso que o
              ícone é o mesmo `Grip` nos dois lugares. */}
          <button
            onClick={aoAbrirMenu}
            className="btn-vidro pill nav-tip hidden h-9 shrink-0 items-center gap-2 rounded-full px-3 text-xs font-semibold lg:inline-flex xl:px-4"
            data-ativa={menuAberto}
            data-testid="nav-menu"
            data-tour="nav-menu"
            data-tip="Menu"
            aria-label="Minha conta e mais"
            aria-haspopup="dialog"
            aria-expanded={menuAberto}
          >
            <Grip className="h-4 w-4" />
            <span className="hidden xl:inline">Menu</span>
          </button>
        </div>
      </div>
    </div>
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
                <area.icone className="h-6 w-6" strokeWidth={2.1} />
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
            data-ativa={ativa}
            data-testid={`barra-${area.chave}`}
            aria-label={`${area.nome} — ${area.pergunta}`}
            aria-current={ativa ? "page" : undefined}
          >
            <area.icone className="h-[22px] w-[22px]" strokeWidth={ativa ? 2.2 : 1.8} />
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
            className="btn-vidro pill flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
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
      {/* Desktop: a barra completa. Celular: só marca + saldo + porta do Menu;
          as áreas ficam na barra de baixo, onde o polegar chega. */}
      <div className="hidden lg:block">
        <BarraDeCima pathname={pathname} aoAbrirMenu={abrirMenu} menuAberto={menu} />
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
// MEDIÇÃO DA BARRA — refeita em 2026-09-18, com cinco áreas
// ---------------------------------------------------------------------------
//
// A barra vive num `max-w-6xl` com `px-10`: 1072px de conteúdo útil a partir
// de 1152px de viewport, e NENHUM monitor mais largo aumenta isso. Toda vez
// que um item entra aqui, a soma dos filhos tem de ser MEDIDA — não estimada.
//
// MEDIDO em 2026-09-18 (DOM real, `getBoundingClientRect`, sem sessão — ver a
// receita de medir sem login em `Cerebro/operacao/ambiente-local.md`):
//
//     viewport   útil     soma    folga
//     1024px     944px    811px   133px     ← a faixa mais apertada
//     1280px    1072px    811px   261px
//     1536px    1072px    811px   261px
//
// Abas: Hoje 72 · Agenda 92 · Estudar 93 · Progresso 109 · Comunidade 126.
//
// Para a passada anterior, com sete primários, a soma era 1020px — 52px de
// folga. Foram duas coisas que compraram o espaço: as duas áreas a menos
// (Redação e Aulas desceram para dentro de Estudar e do Menu) e o "sair", que
// saiu da barra para o rodapé do Menu, onde já morava no celular.
//
// Como medir (a intuição erra por dezenas de px, e `scrollWidth - clientWidth`
// dá 0 sempre que cabe, porque `justify-between` come a sobra):
//
//     const n = document.querySelector('[data-testid="barra-superior"] > div');
//     const cs = getComputedStyle(n);
//     const soma = [...n.children].reduce((t,c) => t + c.getBoundingClientRect().width, 0);
//     n.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - soma
//
// Rode em 1024, 1280 e 1536. Ver `Cerebro/ux/navegacao.md`.
