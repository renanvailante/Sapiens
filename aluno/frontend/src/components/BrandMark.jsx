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
// O sulco frontal é o único ACESO, no azul da marca, e termina num nó —
// o mesmo nó azul que o "S" antigo tinha, a única peça que atravessou o
// redesenho. É a história do produto em um traço: de todos os caminhos do
// cérebro, o Sapiens acende um por vez.
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

// Três sulcos concêntricos, todos curvando para o mesmo lado. Curvas em S
// (duas inversões) devolviam a letra antiga por dentro do cérebro, que é
// exatamente o que este redesenho veio tirar.
const SULCO_TRASEIRO = "M31 64 C21 55 23 41 34 35";
const SULCO_MEIO = "M44 73 C36 64 39 49 50 43";
const SULCO_ACESO = "M59 69 C52 61 55 50 65 47 C74 44 77 34 71 28";

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
      <circle cx="71" cy="28" r="5.6" fill={aceso} />
    </svg>
  );
}
