import { ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAnuncio } from "./contexto";
import { evento } from "../../lib/rastreio";

/**
 * O CONVITE À AÇÃO — um verbo, um destino, a origem colada.
 *
 * Uma landing de anúncio tem **uma** ação. Este é o único botão destas quatro
 * páginas: não há "saiba mais", não há "ver planos", não há login no topo. A
 * mesma disciplina que a landing da marca já segue ("um só verbo, repetido em
 * toda a página: quem muda o texto do botão a cada seção ensina que são
 * coisas diferentes") vale aqui com mais força, porque aqui há cinco segundos
 * e não há segunda visita.
 *
 * ---------------------------------------------------------------------------
 * POR QUE É UM `<a href>` E NÃO UM `<Link>` OU UM `nav()`
 * ---------------------------------------------------------------------------
 *
 * Três motivos, e nenhum é preferência:
 *
 * 1. **O destino aparece na barra de status** ao tocar e segurar. Um botão que
 *    não mostra para onde vai, numa página que a pessoa nunca viu, é a
 *    definição de link suspeito.
 * 2. **Abrir em outra aba continua funcionando** (toque longo, clique do
 *    meio), o que `onClick` sozinho quebra.
 * 3. **Serve como rastro do navegador**: o `/login` com a query de origem fica
 *    no histórico, então voltar e avançar preservam a atribuição.
 *
 * A navegação em si continua sendo do React Router — o `<a>` interno dispara
 * um recarregamento completo, e num app com Firebase no bundle isso custaria
 * segundos. Por isso o clique é interceptado e vira `navigate`, com o
 * `href` intacto para os três motivos acima.
 */
function useIrParaCadastro() {
  const { destino, variante } = useAnuncio();
  const nav = useNavigate();
  return {
    destino,
    aoClicar: (posicao) => (e) => {
      // O rastreio vem antes da navegação, e nunca a atrasa: `evento` é
      // síncrono e engole os próprios erros (ver `lib/rastreio.js`).
      evento("CliqueCTA", { variante, posicao });
      // Modificador de teclado / botão do meio: é o navegador que manda.
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button === 1) return;
      e.preventDefault();
      nav(destino);
    },
  };
}

/**
 * O botão principal.
 *
 * `posicao` diz onde na página ele está ("heroi", "fim", "grudento") e viaja
 * no evento de rastreio: sem isso não dá para saber se a página converte na
 * primeira dobra ou depois da demonstração, que é a única coisa que se
 * aprende de uma landing além do total.
 *
 * `heroi` marca o botão da primeira dobra — é ele que a casca observa para
 * decidir quando o CTA grudente aparece.
 */
export default function CTA({ children, posicao = "heroi", heroi = false, nota = null, className = "" }) {
  const { destino, aoClicar } = useIrParaCadastro();

  return (
    <div className={`flex flex-col items-center gap-3 ${className}`}>
      <a
        href={destino}
        onClick={aoClicar(posicao)}
        // 56px de altura: o alvo de toque confortável do polegar, bem acima
        // dos ~32px que o produto trata como piso.
        className="pill btn-sapiens inline-flex w-full max-w-sm items-center justify-center gap-2 rounded-full px-7 py-4 text-center text-base font-bold md:w-auto"
        // Todo CTA do CORPO carrega esta marca: é por ela que a casca sabe
        // quando o grudente do celular pode aparecer sem concorrer com um
        // botão que já está na tela. Ver `AdsLandingLayout`.
        data-cta-inline=""
        data-cta-heroi={heroi ? "" : undefined}
        data-testid={`ads-cta-${posicao}`}
      >
        {children} <ArrowRight className="h-4 w-4 shrink-0" />
      </a>
      {nota && (
        <p className="max-w-sm text-center text-xs leading-relaxed text-white/45" data-testid={`ads-cta-nota-${posicao}`}>
          {nota}
        </p>
      )}
    </div>
  );
}

/** A versão grudenta do celular. Mesmo destino, mesmo verbo — é o MESMO
 *  botão reaparecendo, não um segundo convite. */
export function CtaGrudento({ label, visivel }) {
  const { destino, aoClicar } = useIrParaCadastro();
  return (
    <a
      href={destino}
      onClick={aoClicar("grudento")}
      className="pill btn-sapiens flex w-full items-center justify-center gap-2 rounded-full px-6 py-4 text-base font-bold"
      tabIndex={visivel ? 0 : -1}
      data-testid="ads-cta-grudento"
    >
      {label} <ArrowRight className="h-4 w-4 shrink-0" />
    </a>
  );
}
