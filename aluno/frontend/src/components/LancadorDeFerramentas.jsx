import { useNavigate, useLocation } from "react-router-dom";
import {
  Compass, Trophy, PlayCircle, PenLine, Brain, Zap, GraduationCap,
  CalendarDays, Sparkles, Users, CalendarClock, History, LayoutGrid,
  MessageSquareWarning, ShieldCheck, LogOut, Download, MessageCircle, HelpCircle,
  Radio, Megaphone, UserRoundCheck, Rss, ChevronRight,
} from "lucide-react";
import { Sheet, SheetContent, SheetTitle, SheetDescription } from "./ui/sheet";
import Logo from "./Logo";
import BotaoInstalar from "./InstalarApp";

/**
 * Todas as ferramentas do Sapiens numa tela só, em grade visual.
 *
 * Substitui o menu "…" (dez itens de texto num dropdown) e a lista do menu
 * mobile. O problema que os dois tinham era o mesmo: uma ferramenta dentro de
 * uma lista de texto, atrás de um ícone de três pontos, **não existe** para
 * quem não sabe que ela existe — e metade do produto morava ali (mural,
 * liga, revisões, questões geradas, perfil cognitivo, histórico).
 *
 * Agora é uma LISTA, agrupada pelo que o aluno quer fazer, e não pela ordem em
 * que as telas foram construídas. Nenhuma tela foi removida: só saíram de
 * dentro de um menu e viraram superfície.
 *
 * **Por que lista e não grade (2026-09-17).** A versão anterior era uma grade
 * de dois azulejos por linha, cada um com ícone grande, nome e uma frase de
 * descrição. Vinte azulejos com vinte frases é um parágrafo inteiro para
 * atravessar antes de achar a palavra que se procura — e quem abre este painel
 * já sabe para onde quer ir: ele veio buscar um NOME, não ler sobre uma
 * ferramenta. A lista dá a cada item uma linha estreita de largura inteira,
 * com o ícone à esquerda e o título, e nada mais. O olho desce uma coluna só,
 * o alvo de toque cresce (a linha inteira é clicável) e o painel cabe na tela
 * sem rolagem na maioria dos aparelhos.
 *
 * A `nota` de cada item continua existindo no dado, mas agora ela é o `title`
 * do elemento — quem passa o mouse ainda lê a explicação, quem só quer o nome
 * não paga por ela.
 */

// ---------------------------------------------------------------------------
// AS FERRAMENTAS — varredura de 2026-09-17
// ---------------------------------------------------------------------------
//
// Eram 20 entradas em três grupos, e o usuário resumiu o problema em uma
// frase: "tem 15 ferramentas e tá muito confuso". Duas coisas foram feitas.
//
// **1. Quatro entradas eram a MESMA coisa duas vezes. Viraram uma linha cada.**
// A regra aplicada: só se une o que responde à mesma pergunta do aluno, e só
// quando o destino que sai do menu continua alcançável de dentro do que fica —
// senão "unir" é esconder.
//
//   · E-books  -> Cursos      · era literalmente a MESMA página (`/cursos#ebooks`);
//                               a prateleira é uma seção dela.
//   · Lixeira  -> Histórico   · a lixeira é o que foi apagado do histórico, e a
//                               tela do histórico já tem o botão "Lixeira".
//   · Indicar  -> Sparks      · indicar é COMO se ganha Spark; a loja já traz o
//                               card do código de indicação.
//   · Liga     -> Conquistas  · as duas respondem "o que meu esforço rendeu".
//                               A ponte dentro de `Conquistas.jsx` entrou junto
//                               com esta união, e é ela que a torna honesta.
//
// **2. Os grupos passaram a ser a pergunta do aluno, não a arquitetura.**
// "Acompanhar" e "Gente" diziam pouco. Agora: o que eu faço agora (Estudar),
// como estou indo (Meu progresso), o que eu compro de quem passou em 1º lugar,
// e quem me responde.
//
// O que NÃO foi unido, e por quê — porque unir coisa diferente é pior do que
// deixar duas linhas:
//
//   · Revisões x Questões da Mentis — uma é repetição espaçada do que você já
//     errou, a outra é questão NOVA gerada sob medida. Mecânicas diferentes.
//   · Aula ao vivo x Mentoria x Cursos — mesma pessoa, três produtos com
//     preços e promessas diferentes (por edição, fila, vitalício).
//   · Painel x Mapa de Treino — um é para onde tudo volta, o outro é onde se
//     estuda.
const GRUPOS = [
  {
    titulo: "Estudar",
    itens: [
      { rota: "/treino", icone: Compass, nome: "Mapa de Treino", nota: "Missões curtas num mapa que se revela conforme você avança", destaque: true },
      { rota: "/exams", icone: PlayCircle, nome: "Provas do ENEM", nota: "Todas as provas, questão por questão, do jeito que caíram" },
      { rota: "/redacao", icone: PenLine, nome: "Redação", nota: "Tema, correção nas cinco competências e foto da folha" },
      { rota: "/revisoes", icone: CalendarClock, nome: "Revisões", nota: "O que você já errou e voltou para ser cobrado hoje" },
      { rota: "/minhas-questoes", icone: Sparkles, nome: "Questões da Mentis", nota: "Questões novas, geradas sob medida para a sua lacuna" },
      { rota: "/cronograma", icone: CalendarDays, nome: "Cronograma", nota: "Sua semana montada nos seus horários, de segunda a domingo" },
    ],
  },
  {
    titulo: "Meu progresso",
    itens: [
      { rota: "/dashboard", icone: LayoutGrid, nome: "Painel", nota: "Onde tudo começa e para onde tudo volta" },
      { rota: "/cognitive-profile", icone: Brain, nome: "Desempenho", nota: "Por que você erra — o padrão, não a quantidade" },
      // Conquistas + Liga. Ver a nota do bloco acima: a ponte para a Liga
      // mora dentro de `Conquistas.jsx`.
      { rota: "/conquistas", icone: Trophy, nome: "Conquistas e liga", nota: "Seus troféus e a sua posição entre os alunos nesta semana" },
      // Histórico + Lixeira. A tela do histórico já tem o botão da lixeira.
      { rota: "/history", icone: History, nome: "Histórico", nota: "Tudo o que você já resolveu — e a lixeira do que apagou" },
      // Sparks + Indicar. A loja já traz o card do código de indicação.
      { rota: "/sparks", icone: Zap, nome: "Sparks", nota: "Saldo, pacotes e o seu código para indicar um amigo" },
    ],
  },
  {
    titulo: "Com o 1º colocado da USP",
    itens: [
      { rota: "/aula-ao-vivo", icone: Radio, nome: "Aula ao vivo · quinta", nota: "60 min ao vivo, uma vez por semana · 200 Sparks por edição", destaque: true, aoVivo: true },
      // Cursos + E-books: a prateleira é uma seção da mesma página.
      { rota: "/cursos", icone: GraduationCap, nome: "Cursos e e-books", nota: "O catálogo por área, mais o material para ler ou imprimir" },
      { rota: "/mentoria", icone: UserRoundCheck, nome: "Mentoria", nota: "Um a um, com lista de espera · 50 Sparks para entrar", destaque: true },
    ],
  },
  {
    titulo: "Quem te responde",
    itens: [
      { rota: "/mentis", icone: MessageCircle, nome: "Mentis", nota: "Ela leu o seu histórico inteiro antes da primeira palavra" },
      { rota: "/comunidade", icone: Users, nome: "Comunidade", nota: "Pergunte, responda e ganhe Sparks no mural de dúvidas" },
      { rota: "/sugestoes", icone: MessageSquareWarning, nome: "Fale com a equipe", nota: "Achou um erro? Tem uma ideia? A gente lê e responde" },
    ],
  },
];

const EXTRAS = [
  { rota: "/feed", icone: Rss, nome: "Feed", nota: "Questões soltas para passar o dedo, sem compromisso" },
];

/**
 * Uma ferramenta = uma linha estreita de largura inteira: ícone, nome e o
 * chevron que diz que a linha leva a algum lugar. **Uma linha nunca divide
 * espaço com outra ferramenta.**
 *
 * **O subtítulo ABRE no hover** (2026-09-17, pedido do usuário), em vez de
 * estar impresso o tempo todo ou escondido num `title` do navegador:
 *
 * · Impresso sempre, eram vinte explicações para atravessar antes de achar o
 *   nome que se procura — quem abre este painel veio buscar um NOME.
 * · No `title` nativo, a explicação aparece depois de um segundo de espera,
 *   numa caixinha amarela do sistema operacional que não é deste produto.
 *
 * A altura é animada por `grid-template-rows: 0fr -> 1fr`, que é a única
 * forma confiável de animar até `height: auto` em CSS. Em aparelho de toque
 * não existe hover e a linha fica só com ícone e nome, que é exatamente o que
 * se quer num celular.
 */
function Linha({ item, aoIr, ativa }) {
  return (
    <button
      type="button"
      onClick={() => aoIr(item.rota)}
      aria-current={ativa ? "page" : undefined}
      className={[
        "group flex w-full items-start gap-3 rounded-xl px-3 py-2 text-left transition-colors",
        ativa
          ? "bg-[#4FD9FF]/[0.14] text-white"
          : "text-white/75 hover:bg-white/[0.06] hover:text-white",
      ].join(" ")}
      data-testid={`lancador-${(item.chave || item.rota).replace(/\//g, "-")}`}
    >
      <span
        className={`relative flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${
          item.destaque || ativa ? "text-[#7FD8FF]" : "text-white/45 group-hover:text-white/75"
        }`}
      >
        <item.icone className="h-[18px] w-[18px]" strokeWidth={1.9} />
        {/* Mesma marca que a barra usa: o ponto vermelho é o sinal de "isto
            acontece ao vivo", e ele precisa ser o mesmo nos dois lugares. */}
        {item.aoVivo && (
          <span className="absolute -right-0.5 -top-0.5 flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-500 opacity-80" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-rose-500" />
          </span>
        )}
      </span>

      <span className="min-w-0 flex-1">
        <span className="block truncate py-0.5 text-[15px] font-medium leading-tight">
          {item.nome}
        </span>
        {item.nota && (
          <span className="linha-nota" aria-hidden="true">
            <span className="min-h-0 overflow-hidden">
              <span className="block pb-1 pr-2 pt-1 text-[11px] leading-snug text-white/45">
                {item.nota}
              </span>
            </span>
          </span>
        )}
      </span>

      <ChevronRight className="mt-1.5 h-4 w-4 shrink-0 text-white/15 transition-colors group-hover:text-white/40" />
    </button>
  );
}

/**
 * `lado` decide de onde o painel entra, e a decisão é de quem abre, não daqui:
 *
 * · `"left"` — a barra de cima do desktop, onde o botão da grade fica à
 *   esquerda e o painel sai debaixo dele.
 * · `"bottom"` — o "Mais" da barra inferior do celular. Um painel que entra
 *   pela lateral a partir de um botão no rodapé é movimento que não sai de
 *   onde o dedo tocou, e é a diferença entre um menu que parece abrir e um
 *   que parece aparecer.
 */
/** O mesmo desenho da `Linha`, para itens que não são rota: instalar o app,
 *  sair. Existe para que uma ação não pareça um destino nem quebre o ritmo
 *  vertical da lista. */
const LINHA_CRUA =
  // `py-2` e não `py-2.5`: a mesma altura de repouso da `Linha` (44px), senão
  // o rodapé fica 4px mais alto que o resto e o ritmo vertical da coluna
  // quebra justamente onde a lista termina.
  "group flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-[15px] " +
  "font-medium leading-tight text-white/75 transition-colors hover:bg-white/[0.06] hover:text-white";

/** A rota de uma linha está acesa? Mesma regra da barra de cima: `/dashboard`
 *  é exata (tudo volta para ela) e as outras casam com as filhas. O `#` de
 *  `/cursos#ebooks` não entra na comparação — é a mesma página. */
function ehRotaAtual(pathname, rota) {
  const base = (rota || "").split(/[?#]/)[0];
  if (base === "/dashboard") return pathname === "/dashboard";
  return pathname === base || pathname.startsWith(`${base}/`);
}

export default function LancadorDeFerramentas({ aberto, aoFechar, user, aoSair, lado = "left" }) {
  const nav = useNavigate();
  const { pathname } = useLocation();

  // `de` é a tela de onde a pessoa saiu — hoje só a página de reclamações e
  // sugestões usa, para a queixa chegar à equipe já dizendo de onde veio.
  const ir = (rota) => {
    aoFechar();
    nav(rota, { state: { de: pathname } });
  };

  return (
    <Sheet open={aberto} onOpenChange={(v) => { if (!v) aoFechar(); }}>
      <SheetContent
        side={lado}
        className={
          lado === "bottom"
            // `dvh` e não `vh`: com a barra de endereço do Safari na tela, `vh`
            // mede a janela SEM ela e o rodapé do painel (o botão de sair) fica
            // por baixo do navegador.
            ? "flex max-h-[86dvh] flex-col rounded-t-[26px] border-t border-white/12 p-0"
            : "flex w-[92vw] max-w-md flex-col border-r border-white/10 p-0"
        }
        style={{ background: "rgba(9,17,31,0.97)", backdropFilter: "blur(16px)" }}
        data-testid="lancador"
      >
        {/* A alça. Só na variante de baixo, e só porque ela diz, sem texto,
            que o painel se fecha puxando para baixo. */}
        {lado === "bottom" && (
          <div className="mx-auto mt-3 h-1 w-10 shrink-0 rounded-full bg-white/20" />
        )}
        <SheetTitle className="sr-only">Ferramentas do Sapiens</SheetTitle>
        <SheetDescription className="sr-only">
          Todas as telas do Sapiens, agrupadas pelo que você quer fazer.
        </SheetDescription>

        <div className="px-5 pb-2 pt-5">
          <Logo tamanho="m" testid="lancador-marca" />
        </div>

        <div className="flex-1 overflow-y-auto px-3 pb-4">
          {GRUPOS.map((g) => (
            <section key={g.titulo} className="mb-4">
              <div className="mb-1 px-3 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-white/25">
                {g.titulo}
              </div>
              <div className="space-y-0.5">
                {g.itens.map((i) => (
                  <Linha
                    key={i.chave || i.rota}
                    item={i}
                    aoIr={ir}
                    ativa={ehRotaAtual(pathname, i.rota)}
                  />
                ))}
              </div>
            </section>
          ))}

          {/* O rodapé da lista: o que é sistema, e não estudo. Mesmas linhas,
              mesma altura — a fileira de pílulas minúsculas que vivia aqui era
              um terceiro desenho dentro do mesmo painel. */}
          <section className="mb-2 border-t border-white/8 pt-3">
            <div className="mb-1 px-3 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-white/25">
              Mais
            </div>
            <div className="space-y-0.5">
              {EXTRAS.map((e) => (
                <Linha key={e.rota} item={e} aoIr={ir} ativa={ehRotaAtual(pathname, e.rota)} />
              ))}
              {/* O guia da Mentis vive no Painel (é lá que estão os alvos que
                  ele aponta). Daqui a porta é o endereço: `?guia=1` é a mesma
                  porta que `/bem-vindo` usa. */}
              <button
                type="button"
                onClick={() => ir("/dashboard?guia=1")}
                className={LINHA_CRUA}
                data-testid="lancador-guia"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center text-white/45 group-hover:text-white/75">
                  <HelpCircle className="h-[18px] w-[18px]" strokeWidth={1.9} />
                </span>
                <span className="min-w-0 flex-1 truncate">Rever o guia</span>
              </button>
              {/* Instalar some sozinho quando o app já está instalado. */}
              <BotaoInstalar className={LINHA_CRUA} testid="lancador-instalar">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center text-white/45 group-hover:text-white/75">
                  <Download className="h-[18px] w-[18px]" strokeWidth={1.9} />
                </span>
                <span className="min-w-0 flex-1 truncate">Instalar o app</span>
              </BotaoInstalar>
              {user?.is_admin && (
                <button
                  type="button"
                  onClick={() => ir("/admin")}
                  className={`${LINHA_CRUA} text-emerald-300 hover:text-emerald-200`}
                  data-testid="lancador-admin"
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center">
                    <ShieldCheck className="h-[18px] w-[18px]" strokeWidth={1.9} />
                  </span>
                  <span className="min-w-0 flex-1 truncate">Admin</span>
                </button>
              )}
              {user?.is_promoter && (
                <button
                  type="button"
                  onClick={() => ir("/promoter")}
                  className={`${LINHA_CRUA} text-emerald-300 hover:text-emerald-200`}
                  data-testid="lancador-promoter"
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center">
                    <Megaphone className="h-[18px] w-[18px]" strokeWidth={1.9} />
                  </span>
                  <span className="min-w-0 flex-1 truncate">Promoter</span>
                </button>
              )}
            </div>
          </section>
        </div>

        <div className="border-t border-white/10 px-5 pb-6 pt-3">
          <button
            type="button"
            onClick={async () => { aoFechar(); await aoSair(); }}
            className="pill inline-flex w-full items-center justify-center gap-2 rounded-full border border-white/12 bg-white/5 px-4 py-3 text-sm font-medium text-white/70 hover:text-white"
            data-testid="lancador-sair"
          >
            <LogOut className="h-4 w-4" /> Sair
          </button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
