import { useId } from "react";

// ---------------------------------------------------------------------------
// A MARCA DO SAPIENS — 2026-09-16
// ---------------------------------------------------------------------------
//
// Um CÉREBRO DE FRENTE, simétrico, com os dois hemisférios separados por uma
// fissura vazada e trilhas de circuito impresso correndo por dentro de cada um.
//
// Substitui o cérebro de PERFIL desenhado em 15/09. A forma não foi escolhida
// aqui: ela veio da logo que o produto adotou, e este arquivo a reproduz —
// mesma silhueta de lóbulos bulbosos, mesma fissura central, mesmas trilhas
// com nó na ponta, mesmo degradê claro-em-cima/profundo-embaixo. O que foi
// feito é o que a marca precisava para viver DENTRO do Sapiens:
//
//  1. **Resolução.** O original é um PNG pequeno, com o degradê já em faixas e
//     as trilhas borradas. Aqui a marca é VETOR: a mesma geometria serve o
//     favicon de 16px, o ícone de 512px do aparelho e um cabeçalho de landing
//     em tela 5K, sem um pixel de perda e sem uma requisição de rede.
//  2. **Paleta.** O azul genérico do original virou a luz do produto — o mesmo
//     ciano -> azul -> violeta que a barra de progresso, o traço da aba ativa
//     e o botão primário usam. A marca deixou de ser uma imagem colada por
//     cima do ambiente e passou a ser feita da matéria dele.
//  3. **Sobrevivência em escala.** As trilhas têm traço de 1.7 num viewBox de
//     100 e os nós têm raio 2.1: é o menor par que ainda se separa a 24px, o
//     tamanho em que a marca mais aparece (barra e aba do navegador). A
//     fissura tem 2.8 de vão pelo mesmo motivo — abaixo disso ela fecha no
//     antialias e o cérebro vira uma massa só.
//
// ---------------------------------------------------------------------------
// COMO A SILHUETA É CONSTRUÍDA
// ---------------------------------------------------------------------------
//
// Cada hemisfério é a UNIÃO de sete círculos que se sobrepõem — não um `path`
// de curvas costuradas à mão. Três motivos, e nenhum é preguiça:
//
//  · É assim que a forma original é feita, e é o que dá os lóbulos bulbosos
//    com VALES entre eles. Um contorno desenhado à mão tende a alisar os vales
//    e a forma vira nuvem — foi exatamente o defeito que matou os primeiros
//    desenhos do cérebro de perfil. A regra que mantém o vale: a distância
//    entre dois centros vizinhos tem de ser MAIOR que o maior dos dois raios.
//    Abaixo disso um lóbulo engole o outro e some do contorno.
//  · Ajustar a marca vira mover um círculo, não reescrever uma curva de Bézier
//    de doze pontos de controle.
//  · A união é geometricamente exata em qualquer escala; costura de curvas
//    ganha micro-fendas quando o renderizador arredonda.
//
// **O degradê é pintado UMA vez, na união inteira.** Os círculos entram como
// `clipPath` e quem é pintado é um retângulo do tamanho do viewBox. A primeira
// versão deste arquivo dava o degradê a cada `<circle>`, e como um degradê de
// SVG é resolvido na caixa do próprio elemento, cada lóbulo ganhava a escala
// de cor inteira: a marca lia como um punhado de bolhas de sabão empilhadas,
// não como um cérebro. Um recorte só, uma pintura só, nenhuma costura.
//
// A FISSURA entre os hemisférios é outro recorte, não um traço pintado por
// cima: os círculos avançam além do meio e são cortados numa linha reta em
// x=51.4 e x=48.6. Recortada, a fissura mostra o que estiver ATRÁS — o vidro
// da barra, o abismo do app, o branco da folha de leitura, a aba do navegador
// — e nunca carrega uma cor de fundo errada junto. É a mesma decisão que o
// desenho anterior tomava com os sulcos, e é a que faz a marca funcionar sobre
// qualquer superfície do produto.
//
// `tone="light"` (padrão) = massa clara e fria, para fundo escuro.
// `tone="dark"` = massa navy, para fundo claro (folha de leitura, impressão).
// `halo` acende uma auréola difusa atrás da massa — só onde a marca é
// protagonista (entrada, carregamento, lockup grande). Em tamanho de barra ela
// fica DESLIGADA: a 20px o halo come a fissura e o cérebro vira uma mancha.

// Os sete círculos do hemisfério DIREITO, do miolo para fora. O esquerdo é o
// espelho exato (`100 - cx`) — a marca é simétrica, e derivar o outro lado em
// vez de escrevê-lo é o que garante que ele continue simétrico depois do
// próximo ajuste.
const HEMISFERIO = [
  { cx: 66, cy: 49, r: 20.0 },   // miolo — preenche o corpo do hemisfério
  { cx: 57, cy: 28, r: 12.0 },   // bossa do topo, junto à fissura
  { cx: 71, cy: 30, r: 12.0 },   // bossa superior externa
  { cx: 80, cy: 41, r: 10.5 },   // lóbulo lateral alto (o ponto mais largo)
  { cx: 79, cy: 55, r: 11.0 },   // lóbulo lateral baixo
  { cx: 71, cy: 66, r: 11.5 },   // lóbulo temporal
  { cx: 57, cy: 70, r: 11.5 },   // base, junto à fissura
];

// As trilhas de circuito do hemisfério direito: uma espinha vertical e quatro
// derivações que terminam em nó. Os ângulos são de 90° e 45°, como numa placa
// de verdade — curva orgânica aqui brigaria com a massa, que já é toda
// orgânica, e o contraste entre as duas coisas é o assunto da marca.
//
// Nada passa de x=59 para dentro: assim as trilhas nunca encostam no recorte
// da fissura e não precisam ser cortadas junto com a massa.
const TRILHAS = [
  "M 59 31 L 59 71",             // espinha
  "M 59 37 L 66 30 L 77 30",     // derivação superior
  "M 59 49 L 68 49 L 74 43",     // bifurcação — ramo de cima
  "M 68 49 L 75 55",             // bifurcação — ramo de baixo
  "M 59 60 L 67 68 L 75 68",     // derivação inferior
];

// Os nós. Ponta de trilha sem nó lê como risco solto; com nó, lê como
// circuito. Os dois das extremidades da espinha fecham o desenho.
const NOS = [
  { cx: 59, cy: 31 }, { cx: 77, cy: 30 }, { cx: 74, cy: 43 },
  { cx: 75, cy: 55 }, { cx: 75, cy: 68 }, { cx: 59, cy: 71 },
];

export default function BrandMark({ className = "w-7 h-7", tone = "light", halo = false }) {
  // Duas marcas na mesma página (barra + lançador + rodapé) teriam os mesmos
  // `id` de degradê e de recorte — HTML inválido, e o navegador resolve pela
  // primeira que achar. Os dois-pontos que o `useId` do React põe no meio
  // (`:r3:`) saem: são legais num `id`, mas `url(#:r3:)` é referência frágil
  // demais para apostar a marca do produto.
  const uid = useId().replace(/:/g, "");
  const claro = tone !== "dark";
  const corTrilha = claro ? "#F2FBFF" : "#DCEAFD";

  const id = (nome) => `sap-${nome}-${uid}`;

  /** O recorte da massa de um hemisfério: os sete círculos, espelhados ou não. */
  const recorteDaMassa = (espelho) => (
    <clipPath id={id(espelho ? "massaE" : "massaD")} key={espelho ? "mE" : "mD"}>
      {HEMISFERIO.map((c) => (
        <circle key={`${c.cx}-${c.cy}`} cx={espelho ? 100 - c.cx : c.cx} cy={c.cy} r={c.r} />
      ))}
    </clipPath>
  );

  /** Um hemisfério inteiro: massa + reflexo + trilhas, tudo dentro da metade. */
  const hemisferio = (espelho) => {
    const x = (v) => (espelho ? 100 - v : v);
    return (
      <g clipPath={`url(#${id(espelho ? "meiaE" : "meiaD")})`}>
        <g clipPath={`url(#${id(espelho ? "massaE" : "massaD")})`}>
          <rect x="0" y="0" width="100" height="100" fill={`url(#${id("tinta")})`} />
          {/* O reflexo do alto do lóbulo. É o que dá o volume envernizado da
              logo original sem precisar de sombra interna — e, recortado pela
              massa, ele acompanha os lóbulos em vez de aparecer como uma
              mancha clara solta por cima deles. */}
          <ellipse cx={x(64)} cy="32" rx="23" ry="17" fill={`url(#${id("brilho")})`} />
        </g>

        {TRILHAS.map((d) => (
          <path
            key={d}
            d={d}
            transform={espelho ? "translate(100,0) scale(-1,1)" : undefined}
            fill="none"
            stroke={corTrilha}
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="0.94"
          />
        ))}
        {NOS.map((n) => (
          <circle key={`n-${n.cx}-${n.cy}`} cx={x(n.cx)} cy={n.cy} r="2.1" fill={corTrilha} />
        ))}
      </g>
    );
  };

  return (
    <svg viewBox="0 0 100 100" className={className} aria-hidden="true">
      <defs>
        {/* O degradê da massa. A diagonal (alto-esquerda -> baixo-direita) é a
            da logo original; as cores são as do Sapiens. `userSpaceOnUse` é
            obrigatório: sem ele o degradê seria recalculado na caixa de cada
            forma recortada, que é o bug que fazia a marca virar bolhas. O
            violeta entra só no último trecho, onde lê como profundidade e não
            como uma segunda cor de marca. */}
        <linearGradient id={id("tinta")} gradientUnits="userSpaceOnUse" x1="14" y1="14" x2="86" y2="84">
          {claro ? (
            <>
              <stop offset="0%" stopColor="#A9F0FF" />
              <stop offset="26%" stopColor="#5FDCFF" />
              <stop offset="58%" stopColor="#3E86E8" />
              <stop offset="84%" stopColor="#2E62C8" />
              <stop offset="100%" stopColor="#4B4FB8" />
            </>
          ) : (
            <>
              <stop offset="0%" stopColor="#4A85E3" />
              <stop offset="55%" stopColor="#23509B" />
              <stop offset="100%" stopColor="#0C1C3A" />
            </>
          )}
        </linearGradient>

        <radialGradient id={id("brilho")} cx="50%" cy="42%" r="58%">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity={claro ? 0.4 : 0.2} />
          <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
        </radialGradient>

        <radialGradient id={id("aureola")} cx="50%" cy="50%" r="50%">
          <stop offset="42%" stopColor="#4FD9FF" stopOpacity="0" />
          <stop offset="76%" stopColor="#4FD9FF" stopOpacity="0.32" />
          <stop offset="100%" stopColor="#8B7BFF" stopOpacity="0" />
        </radialGradient>

        {recorteDaMassa(false)}
        {recorteDaMassa(true)}

        {/* A fissura: 2.8 unidades de vão num viewBox de 100. */}
        <clipPath id={id("meiaD")}>
          <rect x="51.4" y="0" width="48.6" height="100" />
        </clipPath>
        <clipPath id={id("meiaE")}>
          <rect x="0" y="0" width="48.6" height="100" />
        </clipPath>
      </defs>

      {halo && <circle cx="50" cy="50" r="49" fill={`url(#${id("aureola")})`} />}

      {hemisferio(false)}
      {hemisferio(true)}
    </svg>
  );
}
