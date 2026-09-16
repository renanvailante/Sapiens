import { useId } from "react";

// A marca do Sapiens: um CÉREBRO de perfil, com um sulco aceso.
//
// Substitui (2026-09-15) o "S" de traço que a marca usava desde o começo. O
// S dizia o nome; não dizia o produto. O cérebro diz: é dele que o Sapiens
// trata, e é dele que o produto tem um mapa.
//
// A massa é uma silhueta SÓLIDA e os sulcos são VAZADOS (máscara), e não
// traços pintados por cima: a marca vive sobre vidro translúcido na barra,
// sobre o navy do app, sobre o branco das telas de leitura clara e sobre a
// aba do navegador. Vazado, o sulco mostra o que estiver atrás e nunca
// carrega uma cor de fundo errada junto. É também o que mantém o desenho
// legível a 20px, o tamanho em que a marca mais aparece (o botão do menu no
// celular): um contorno fino desse tamanho empasta, uma massa cheia não.
//
// O sulco frontal é o único ACESO, no azul da marca — a cor é a única peça
// do "S" antigo que atravessou o redesenho. É a história do produto em um
// traço: de todos os caminhos do cérebro, o Sapiens acende um por vez.
//
// `tone="light"` (padrão) = massa branca, para fundo escuro.
// `tone="dark"` = massa navy, para fundo claro.

// Silhueta de perfil: bossas em cima, lobo frontal à direita, entalhe
// temporal embaixo dele e o cerebelo na base à esquerda. Sem o entalhe e sem
// o cerebelo a forma vira nuvem — foi o que os primeiros desenhos viraram.
const MASSA =
  "M30 71 C20 68 13 58 18 48 C11 40 18 28 28 26 C30 16 43 12 52 17 " +
  "C62 11 76 16 79 26 C89 30 90 44 81 49 C84 56 79 62 73 60 " +
  "C74 70 66 77 57 76 C52 80 44 80 39 76 C34 79 27 77 30 71 Z";

// Os sulcos. O par grande é ESPELHADO — um enrola para um lado, o outro
// para o outro — e é ele que faz a forma ler como cérebro; o terceiro, curto,
// na base, tira a simetria perfeita. Três coisas aprendidas desenhando, cada
// uma o defeito de um desenho anterior:
//
// 1. Curva em S (duas inversões no mesmo traço) devolve a letra antiga por
//    dentro do cérebro — exatamente o que este redesenho veio tirar.
// 2. Três arcos iguais e concêntricos não viram cérebro: viram o símbolo de
//    wifi dentro de uma nuvem.
// 3. Um sulco muito mais longo que os outros vira gancho e puxa o olho para
//    fora do desenho.
const SULCO_TRASEIRO = "M31 61 C23 53 26 40 37 37";
const SULCO_MEIO = "M47 74 C42 68 44 60 50 57";
const SULCO_ACESO = "M70 62 C77 53 74 41 63 38";

export default function BrandMark({ className = "w-7 h-7", tone = "light" }) {
  // Duas marcas na mesma página (barra + lançador) teriam o mesmo `id` de
  // máscara — HTML inválido, e o navegador resolve pela primeira que achar.
  // Os dois-pontos que o `useId` do React põe no meio (`:r3:`) saem: são
  // legais num `id`, mas `url(#:r3:)` é referência frágil demais para
  // apostar a marca do produto.
  const mascara = `sapiens-massa-${useId().replace(/:/g, "")}`;
  const massa = tone === "dark" ? "#132D5C" : "#ffffff";
  const aceso = tone === "dark" ? "#4A85E3" : "#4FD9FF";
  return (
    <svg viewBox="0 0 100 100" className={className} aria-hidden="true">
      <defs>
        <mask id={mascara}>
          <rect width="100" height="100" fill="#000" />
          <path d={MASSA} fill="#fff" />
          {[SULCO_TRASEIRO, SULCO_MEIO, SULCO_ACESO].map((d) => (
            <path
              key={d}
              d={d}
              fill="none"
              stroke="#000"
              strokeWidth="6.5"
              strokeLinecap="round"
            />
          ))}
        </mask>
      </defs>
      <path d={MASSA} fill={massa} mask={`url(#${mascara})`} />
      {/* O filamento aceso vai POR DENTRO do vazado (4.3 de traço num corte
          de 6.5): sobra uma auréola de fundo de cada lado, que é o que faz
          ele parecer aceso e não pintado. */}
      <path
        d={SULCO_ACESO}
        fill="none"
        stroke={aceso}
        strokeWidth="4.3"
        strokeLinecap="round"
      />
    </svg>
  );
}
