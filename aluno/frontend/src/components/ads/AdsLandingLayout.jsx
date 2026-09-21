import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../../lib/api";
import Logo from "../Logo";
import { ROTAS } from "../../lib/rotas";
import { destinoComOrigem, lerOrigem, origemSalva, salvarOrigem } from "../../lib/campanha";
import { salvarAtribuicao } from "../../lib/atribuicao";
import { landingView } from "../../lib/rastreio";
import { ContextoDoAnuncio } from "./contexto";
import { CtaGrudento } from "./CTA";

/**
 * A CASCA DAS LANDINGS DE ANÚNCIO.
 *
 * Quatro páginas (`/ads/*`) dividem esta moldura e mudam só a copy e a
 * composição. Ela existe pela mesma razão que `Tela.jsx` existe para o app:
 * sem uma casca, a quinta variante nasce com outra largura, outro respiro e
 * outro destino de CTA — e a comparação entre criativos deixa de medir o
 * criativo.
 *
 * O que a casca resolve, e que nenhuma página precisa repetir:
 *
 * - **a origem do tráfego** (UTM, `campanha_id`, `convite`) é lida, guardada
 *   por 30 dias e colada no destino do CTA — ver `lib/campanha.js`;
 * - **o clique da campanha** é contado uma vez no funil que já existe
 *   (`POST /track/click` → `growth_events`), e só quando há campanha;
 * - **a visualização** vai para o rastreio (`lib/rastreio.js`), que é inerte
 *   enquanto não houver pixel configurado;
 * - **o CTA grudento do celular** aparece só depois que o CTA do herói sai da
 *   tela, nunca por cima da primeira dobra;
 * - **o rodapé mínimo** — marca, Termos, Privacidade. Nada mais.
 *
 * ---------------------------------------------------------------------------
 * ESTA TELA NÃO FALA COM O BACKEND PARA RENDERIZAR
 * ---------------------------------------------------------------------------
 *
 * Nenhum `GET` bloqueia a primeira pintura: a landing é conteúdo estático que
 * o React desenha na montagem. É diferente da `Landing.jsx` da marca, que
 * busca o catálogo de preços (e por isso pode ter seção que aparece tarde) —
 * aqui não há preço nenhum a dizer, e o que se ganha é uma página que não tem
 * como demorar por causa da rede. O único `POST` (o clique) é disparado e
 * esquecido, sem `await` no caminho de render.
 *
 * E, por consequência, **zero leitura do Firestore** por visitante de anúncio.
 */

export default function AdsLandingLayout({ variante, ctaLabel, children }) {
  const { search } = useLocation();
  const [grudentoVisivel, setGrudentoVisivel] = useState(false);
  const rodape = useRef(null);

  // A origem, calculada uma vez por query. A da URL vence a guardada.
  const { destino, origem } = useMemo(() => {
    const daUrl = lerOrigem(search);
    return {
      origem: daUrl,
      destino: destinoComOrigem(search, { salva: origemSalva() }),
    };
  }, [search]);

  /**
   * Estas páginas não entram no índice do Google, e isso é decisão, não
   * esquecimento.
   *
   * São quatro variantes da mesma oferta, com pouco texto e copy escrita para
   * um anúncio específico. Indexadas, elas competem com a landing da marca
   * (`/`) pelas mesmas palavras, canibalizam o resultado que o produto
   * realmente quer no orgânico e mostram no Google um texto que só faz
   * sentido depois de um criativo. Tráfego pago chega por link direto e não
   * precisa de índice.
   *
   * A marca é posta no `<head>` em vez de no `index.html` porque o
   * `index.html` é um só para o app inteiro — o Googlebot renderiza o JS e lê
   * o que estiver aqui, mesma razão pela qual o `<title>` da landing vem do
   * `TituloDaPagina` da rota e não do HTML estático.
   */
  useEffect(() => {
    // A tag do `index.html` é EDITADA e devolvida ao sair, em vez de uma
    // segunda ser acrescentada ao lado dela. Duas `meta[name=robots]`
    // conflitantes até funcionam — a diretiva mais restritiva vence —, mas
    // deixam a página afirmando as duas coisas, e a próxima pessoa que
    // inspecionar o `<head>` daqui não tem como saber qual estava valendo.
    const existente = document.querySelector('meta[name="robots"]');
    const anterior = existente?.content ?? null;
    const marca = existente || Object.assign(document.createElement("meta"), { name: "robots" });
    if (!existente) document.head.appendChild(marca);
    marca.content = "noindex, nofollow";

    return () => {
      // Sair para `/login` é troca de rota numa SPA: sem devolver o valor, a
      // tela de cadastro (e todo o resto do app depois dela) herdaria o
      // `noindex` desta landing.
      if (anterior === null) marca.remove();
      else marca.content = anterior;
    };
  }, []);

  useEffect(() => {
    salvarOrigem(origem);
    landingView(variante);

    /* O código de convite (`ADS-DIAG`, `ADS-ERRO`…) passa a ser guardado JÁ
       NA CHEGADA, e não só quando a pessoa alcança `/login`.
     *
     * `Login.jsx` sempre salvou o `?convite=` da URL dele — mas quem clica no
     * anúncio, lê a landing, fecha a aba e volta dois dias depois pelo link
     * sem parâmetro nunca chegava ao `/login` COM o código, e a atribuição
     * daquela campanha se perdia em silêncio. Guardando aqui, a janela de 30
     * dias começa a contar do clique no anúncio, que é quando a aquisição de
     * fato aconteceu.
     *
     * Reusa `lib/atribuicao.js` — o dono desse dado —, em vez de uma segunda
     * cópia em `lib/campanha.js`. Duas janelas de 30 dias para o mesmo código
     * divergiriam no dia em que uma expirasse antes da outra, e é por isso
     * que `convite` não está em `PARAMS_DE_ORIGEM`. */
    const convite = new URLSearchParams(search || "").get("convite");
    if (convite) salvarAtribuicao(convite.trim().toUpperCase());

    // O clique da campanha entra no funil que já existe. Só com
    // `campanha_id`: `registrar_clique` grava `referral_click` quando não há
    // campanha, e um `referral_click` sem código nem campanha não pode ser
    // atribuído a nada — seria uma escrita no Mongo para produzir uma linha
    // que nenhum relatório consegue ler.
    if (origem.campanha_id) {
      api.post("/track/click", {
        campanha_id: origem.campanha_id,
        utm_source: origem.utm_source || null,
      }).catch(() => {});
    }
  }, [origem, variante, search]);

  /**
   * O CTA grudente do celular.
   *
   * A regra: **nunca há dois convites na tela ao mesmo tempo.** O grudento é o
   * mesmo botão reaparecendo enquanto nenhum CTA do corpo está visível — some
   * na primeira dobra (onde o do herói já está lá) e some de novo no fim da
   * página (onde o último já está lá). Sem isso a página termina com dois
   * botões idênticos empilhados, que é exatamente o "múltiplos CTAs
   * concorrentes" que estas páginas não podem ter — foi o que apareceu na
   * primeira medição no navegador, a 375px.
   *
   * Um observador só, com todos os CTAs do corpo (`[data-cta-inline]`) dentro:
   * o estado é "algum deles está na tela?", e um `Set` dos que estão responde
   * isso sem depender da ordem em que as entradas chegam.
   *
   * `IntersectionObserver` é nativo e custa zero biblioteca; um listener de
   * `scroll` faria a mesma coisa recalculando layout a cada quadro.
   */
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return undefined;
    const inlines = document.querySelectorAll("[data-cta-inline]");
    if (!inlines.length) return undefined;

    const naTela = new Set();
    const observador = new IntersectionObserver(
      (entradas) => {
        for (const entrada of entradas) {
          if (entrada.isIntersecting) naTela.add(entrada.target);
          else naTela.delete(entrada.target);
        }
        setGrudentoVisivel(naTela.size === 0);
      },
      // A margem negativa embaixo é o que impede o piscar: sem ela o grudento
      // aparece no instante em que o botão do corpo encosta na borda inferior,
      // ou seja, com os dois ainda visíveis.
      { rootMargin: "0px 0px -72px 0px" },
    );
    inlines.forEach((el) => observador.observe(el));
    return () => observador.disconnect();
  }, []);

  // Sobre o rodapé o grudento se apaga: um botão fixo por cima dos links
  // legais é um botão que esconde os links legais.
  useEffect(() => {
    const pe = rodape.current;
    if (!pe || typeof IntersectionObserver === "undefined") return undefined;
    const observador = new IntersectionObserver(
      ([entrada]) => { if (entrada.isIntersecting) setGrudentoVisivel(false); },
      { threshold: 0.15 },
    );
    observador.observe(pe);
    return () => observador.disconnect();
  }, []);

  return (
    <ContextoDoAnuncio.Provider value={{ destino, variante }}>
      <div className="topo-seguro min-h-screen" data-testid={`ads-${variante}`}>
        {/* Sem navbar, por desenho: uma landing de aquisição tem uma ação, e
            um menu é a lista das outras. A marca não é link — não há para
            onde ir daqui que não seja o CTA. */}
        <header className="mx-auto flex max-w-5xl items-center px-5 pt-6 md:px-8">
          <Logo tamanho="m" testid="ads-brand" />
        </header>

        <main className="mx-auto max-w-5xl px-5 pb-16 md:px-8">{children}</main>

        <footer
          ref={rodape}
          className="mx-auto max-w-5xl border-t border-white/8 px-5 py-8 md:px-8"
          data-testid="ads-rodape"
        >
          <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 text-xs text-white/40">
            <span>© {new Date().getFullYear()} Sapiens</span>
            {/* `py-2 -my-2` é o jeito da casa de crescer o alvo de toque sem
                mover o desenho: medido a 320px, estes dois links tinham 16px
                de altura, metade do piso de ~32px que o produto trata como
                bug. Ver `ux/mobile.md`.

                `Link` e não `<a href>`: um âncora comum recarrega o bundle
                inteiro para abrir uma página que já está no mesmo app. */}
            <div className="flex flex-wrap gap-x-5">
              <Link to={ROTAS.TERMOS} className="py-2 -my-2 transition-colors hover:text-white/75">Termos de Uso</Link>
              <Link to={ROTAS.PRIVACIDADE} className="py-2 -my-2 transition-colors hover:text-white/75">Privacidade</Link>
            </div>
          </div>
        </footer>

        {/* O grudento vive fora do `<main>` e só existe no celular. O respiro
            de baixo é `env(safe-area-inset-bottom)` — sem ele o botão encosta
            na barra de gestos do iPhone e o toque cai no sistema. */}
        <div
          className={`ads-grudento md:hidden ${grudentoVisivel ? "ads-grudento-visivel" : ""}`}
          aria-hidden={!grudentoVisivel}
        >
          <CtaGrudento label={ctaLabel} visivel={grudentoVisivel} />
        </div>
      </div>
    </ContextoDoAnuncio.Provider>
  );
}
