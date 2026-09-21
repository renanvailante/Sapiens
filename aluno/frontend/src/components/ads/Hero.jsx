import CTA from "./CTA";

/**
 * A PRIMEIRA DOBRA.
 *
 * O que ela contém é o contrato destas páginas, e não é negociável por
 * variante: **manchete, uma explicação curta, o CTA e a demonstração do
 * produto** — nessa ordem, numa coluna só, dentro de ~430px de largura.
 *
 * Cada elemento a mais aqui custa um leitor. Não entra: menu, prova social,
 * logotipo de imprensa, segundo botão, contador, vídeo.
 *
 * A demonstração (`children`) fica DENTRO do herói de propósito. Uma landing
 * de produto cognitivo que abre com promessa e só mostra o produto depois de
 * uma rolagem está pedindo confiança antes de dar evidência; quem chega de
 * anúncio não tem razão nenhuma para dar essa confiança.
 */
export default function Hero({ olho, titulo, subtexto, cta, notaDoCta, children }) {
  return (
    <section className="pb-10 pt-10 md:pb-14 md:pt-16">
      <div className="grid items-center gap-10 md:grid-cols-2 md:gap-12">
        {/* A coluna do texto. No celular é a única coluna e vem primeiro; no
            desktop ela divide a tela com a demonstração, e o foco visual
            continua no botão. */}
        <div className="text-center md:text-left">
          {olho && <div className="secao-olho">{olho}</div>}
          <h1 className="titulo-heroi mt-2" data-testid="ads-titulo">{titulo}</h1>
          <p
            className="mx-auto mt-5 max-w-md text-[17px] leading-relaxed text-white/65 md:mx-0"
            data-testid="ads-subtexto"
          >
            {subtexto}
          </p>
          <CTA heroi posicao="heroi" nota={notaDoCta} className="mt-8 md:items-start">{cta}</CTA>
        </div>

        {/* A demonstração. `md:order-none` mantém texto à esquerda no desktop;
            no celular ela desce sozinha porque a grade vira uma coluna. */}
        <div className="cascata">{children}</div>
      </div>
    </section>
  );
}
