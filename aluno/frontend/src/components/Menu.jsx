import { useNavigate, useLocation } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { Sheet, SheetContent, SheetTitle, SheetDescription } from "./ui/sheet";
import Logo from "./Logo";
import Mentis from "./Mentis";
import BotaoInstalar from "./InstalarApp";
import { InterruptorDeNotificacao } from "./PedidoDeNotificacao";
import { MENU, MENU_ACOES, MENU_EQUIPE } from "../lib/navegacao";
import { ROTAS, com, ANCORAS, ehRotaAtual } from "../lib/rotas";

/**
 * O MENU — a gaveta, e só o que é gaveta.
 *
 * ---------------------------------------------------------------------------
 * A REGRA QUE DEFINE O QUE ENTRA AQUI
 * ---------------------------------------------------------------------------
 *
 * > **Nada aqui é necessário para aprender a usar o produto.** O aluno que
 * > nunca abrir esta gaveta não perde nenhuma ferramenta pedagógica.
 *
 * O `LancadorDeFerramentas` que este arquivo substitui guardava **dezesseis**
 * destinos em quatro grupos — mural, liga, revisões, questões geradas, perfil
 * cognitivo, histórico, mapa de treino, provas, redação, cronograma. Ou seja:
 * metade do produto, atrás de um botão. O comentário dele mesmo dizia o
 * problema — "uma ferramenta dentro de uma lista de texto, atrás de um ícone,
 * **não existe** para quem não sabe que ela existe" — e propunha como solução
 * agrupar melhor a lista. Agrupar uma gaveta não a tira de dentro da gaveta.
 *
 * A solução foi esvaziá-la: as cinco áreas absorveram tudo o que é
 * pedagógico, e aqui ficaram três coisas de natureza diferente:
 *
 *   · **Com Vitor Lara** — os produtos do mentor. Têm data e preço próprios, e
 *     não são "uma ferramenta a mais": a aula ao vivo acontece 60 minutos por
 *     semana. Ela não vive só aqui — aparece como evento datado na Agenda e na
 *     seção do mentor no Hoje, que é quando a informação é verdadeira. Aqui é
 *     índice, não vitrine.
 *   · **Minha conta** — carteira, a conversa em tela cheia e o canal com a
 *     equipe. Nenhum deles ensina nada; todos são "coisas minhas".
 *   · **Sistema** — guia, instalar, admin, sair.
 *
 * É esse esvaziamento que tornou seguro o Menu sair do quinto alvo da barra do
 * celular e subir para o canto da marca, liberando aquele alvo para uma área
 * de verdade. Ver `lib/navegacao.js`.
 *
 * ---------------------------------------------------------------------------
 * POR QUE LISTA, E NÃO GRADE
 * ---------------------------------------------------------------------------
 *
 * Quem abre este painel já sabe para onde quer ir: veio buscar um NOME, não
 * ler sobre uma ferramenta. A linha estreita de largura inteira dá o nome, o
 * alvo de toque é a linha toda, e a `nota` abre no hover — impressa sempre,
 * seriam parágrafos para atravessar antes de achar a palavra que se procura;
 * no `title` nativo, ela apareceria numa caixinha do sistema operacional que
 * não é deste produto.
 */

/** A altura de repouso da linha (44px) é a mesma para destino e para ação —
 *  senão o rodapé fica mais alto que o resto e o ritmo vertical quebra
 *  justamente onde a lista termina. */
const LINHA_CRUA =
  "group flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-[15px] " +
  "font-medium leading-tight text-white/75 transition-colors hover:bg-white/[0.06] hover:text-white";

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
      data-testid={`menu-${(item.chave || item.rota).replace(/\//g, "-")}`}
    >
      <span
        className={`relative flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${
          item.destaque || ativa ? "text-[#7FD8FF]" : "text-white/45 group-hover:text-white/75"
        }`}
      >
        {item.mascote ? (
          <Mentis className="h-[18px] w-[18px]" variante="icone" animada={false} />
        ) : (
          <item.icone className="h-[18px] w-[18px]" strokeWidth={1.9} />
        )}
        {/* O ponto vermelho é o sinal de "isto acontece ao vivo", e precisa ser
            o mesmo em todo lugar que o usa. */}
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
 * O painel entra **de baixo** no celular e **da esquerda** no desktop — e a
 * decisão é de onde o dedo tocou, não desta peça: no celular a porta é a marca
 * no topo, mas o polegar está embaixo, e um painel que entra pela lateral a
 * partir de um gesto no rodapé é movimento que não sai de onde se tocou.
 *
 * `lado` é resolvido por classe utilitária e não por prop, para a `Navegacao`
 * não precisar saber a largura da tela (ela não tem como saber sem um
 * `matchMedia`, e um `matchMedia` só para escolher o lado de um painel é um
 * ouvinte de resize a mais em toda página do produto).
 */
export default function Menu({ aberto, aoFechar, user, aoSair }) {
  const nav = useNavigate();
  const { pathname } = useLocation();

  // `de` é a tela de onde a pessoa saiu — o canal de sugestões usa para a
  // queixa chegar à equipe já dizendo de onde veio. Ver `engajamento.md`:
  // nunca `document.referrer`, que numa SPA aponta para fora do site.
  const ir = (rota) => {
    aoFechar();
    nav(rota, { state: { de: pathname } });
  };

  return (
    <Sheet open={aberto} onOpenChange={(v) => { if (!v) aoFechar(); }}>
      <SheetContent
        side="bottom"
        className="flex max-h-[86dvh] flex-col rounded-t-[26px] border-t border-white/12 p-0 lg:inset-y-0 lg:right-auto lg:h-full lg:max-h-none lg:w-[92vw] lg:max-w-md lg:rounded-none lg:border-r"
        style={{ background: "rgba(9,17,31,0.97)", backdropFilter: "blur(16px)" }}
        data-testid="menu"
      >
        {/* A alça diz, sem texto, que o painel se fecha puxando para baixo.
            `dvh` e não `vh`: com a barra de endereço do Safari na tela, `vh`
            mede a janela SEM ela e o rodapé do painel fica por baixo do
            navegador. */}
        <div className="mx-auto mt-3 h-1 w-10 shrink-0 rounded-full bg-white/20 lg:hidden" />

        <SheetTitle className="sr-only">Minha conta e mais</SheetTitle>
        <SheetDescription className="sr-only">
          Os produtos do mentor, a sua carteira e as configurações da conta.
        </SheetDescription>

        <div className="px-5 pb-2 pt-5">
          <Logo tamanho="m" testid="menu-marca" />
        </div>

        <div className="flex-1 overflow-y-auto px-3 pb-4">
          {MENU.map((grupo) => (
            <section key={grupo.titulo} className="mb-4">
              <div className="mb-1 px-3 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-white/25">
                {grupo.titulo}
              </div>
              <div className="space-y-0.5">
                {grupo.itens.map((item) => (
                  <Linha
                    key={item.rota}
                    item={item}
                    aoIr={ir}
                    ativa={ehRotaAtual(pathname, item.rota)}
                  />
                ))}
              </div>
            </section>
          ))}

          <section className="mb-2 border-t border-white/8 pt-3">
            <div className="mb-1 px-3 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-white/25">
              Sistema
            </div>
            <div className="space-y-0.5">
              {/* O guia mora no Hoje (é lá que estão os alvos que ele aponta).
                  Daqui a porta é o endereço: `?guia=1` é a mesma porta que
                  `/bem-vindo` usa, e nenhuma delas mexe na marca do servidor. */}
              <button
                type="button"
                onClick={() => ir(`${ROTAS.HOJE}?guia=1`)}
                className={LINHA_CRUA}
                data-testid="menu-guia"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center text-white/45 group-hover:text-white/75">
                  <MENU_ACOES.guia.icone className="h-[18px] w-[18px]" strokeWidth={1.9} />
                </span>
                <span className="min-w-0 flex-1 truncate">{MENU_ACOES.guia.nome}</span>
              </button>

              {/* Some sozinho quando o app já está instalado. */}
              <BotaoInstalar className={LINHA_CRUA} testid="menu-instalar">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center text-white/45 group-hover:text-white/75">
                  <MENU_ACOES.instalar.icone className="h-[18px] w-[18px]" strokeWidth={1.9} />
                </span>
                <span className="min-w-0 flex-1 truncate">{MENU_ACOES.instalar.nome}</span>
              </BotaoInstalar>

              {/* Ligar e desligar o aviso no celular a qualquer hora — quem
                  disse "agora não" no fim da série muda de ideia por aqui.
                  Some sozinho onde o navegador não tem push. */}
              <InterruptorDeNotificacao className={LINHA_CRUA} />

              {MENU_EQUIPE.map((item) =>
                user?.[`is_${item.chave}`] ? (
                  <button
                    key={item.chave}
                    type="button"
                    onClick={() => ir(item.rota)}
                    className={`${LINHA_CRUA} text-emerald-300 hover:text-emerald-200`}
                    data-testid={`menu-${item.chave}`}
                  >
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center">
                      <item.icone className="h-[18px] w-[18px]" strokeWidth={1.9} />
                    </span>
                    <span className="min-w-0 flex-1 truncate">{item.nome}</span>
                  </button>
                ) : null,
              )}
            </div>
          </section>
        </div>

        <div className="border-t border-white/10 px-5 pb-6 pt-3">
          <button
            type="button"
            onClick={async () => { aoFechar(); await aoSair(); }}
            className="pill inline-flex w-full items-center justify-center gap-2 rounded-full border border-white/12 bg-white/5 px-4 py-3 text-sm font-medium text-white/70 hover:text-white"
            data-testid="menu-sair"
          >
            <MENU_ACOES.sair.icone className="h-4 w-4" /> {MENU_ACOES.sair.nome}
          </button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

/** O endereço da carteira com a âncora da indicação — usado pelo Hoje e pela
 *  loja. Exportado daqui porque é a única composição de âncora que mais de uma
 *  tela precisa montar, e montá-la à mão erraria o lado da cerquilha. */
export const ROTA_INDICAR = com(ROTAS.SPARKS, ANCORAS.SPARKS_INDICAR);
