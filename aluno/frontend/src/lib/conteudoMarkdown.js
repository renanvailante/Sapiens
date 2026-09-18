/**
 * O PARSER DO SUBCONJUNTO DE MARKDOWN dos blocos de conteúdo dos cursos.
 *
 * Lógica pura, sem React: recebe texto e devolve uma árvore de tokens. Quem
 * a transforma em elementos é `components/curso/TextoRico.jsx`. A separação
 * existe por um motivo prático — esta é a parte do sistema de conteúdo com
 * mais chance de estar sutilmente errada (precedência de marcadores, ênfase
 * aninhada, cifrão dentro de código), e assim ela é testável sem DOM.
 *
 * O subconjunto é fechado de propósito, e é o mesmo que
 * `conteudo/cursos/README.md` promete a quem escreve o curso:
 *
 *     ## Título      **forte**     *ênfase*     `código`
 *     - lista        1. numerada   > citação    $x^2$
 *
 * Markdown completo aceita HTML embutido, e o conteúdo aqui é gerado por IA
 * em lote. Um subconjunto fechado é a diferença entre "o autor não pode
 * escrever tabela" e "o autor pode injetar qualquer coisa na página".
 *
 * Formato que o subconjunto não cobre NÃO vira um markdown mais esperto:
 * vira um tipo de bloco novo, com renderizador e validação próprios.
 */

// A ordem é a precedência, e ela importa:
//
// * matemática primeiro — dentro de `$…$`, `*` e `_` são sintaxe do LaTeX
//   (`a^*`, `x_1`), não ênfase. Trocar a ordem quebraria toda fórmula com
//   asterisco;
// * código em seguida, pelo mesmo motivo: o que está entre crases é literal;
// * forte antes de ênfase, senão `**x**` casaria como ênfase de `*x*`.
// Os dois padrões de asterisco carregam a mesma guarda, e ela não é
// cosmética: **o marcador não pode encostar em espaço**. Sem isso,
// `3 * 4 * 5 = 60` — que aparece em metade dos enunciados de Matemática
// Básica — casa como ênfase, os asteriscos somem e o aluno lê uma conta
// diferente da que foi escrita. É a regra de "delimitador colado" do
// CommonMark, reduzida ao que este subconjunto precisa.
//
// `forte` é PREGUIÇOSO e aceita um `*` solto no meio, para que
// `**muito *mesmo* aqui**` funcione sem que `**a** e **b**` vire um negrito
// só. O caso `***x***` (negrito e itálico no mesmo par) não faz parte do
// subconjunto — escreva `**muito *mesmo* aqui**`.
const REGRAS = [
  { tipo: "matematica", regex: /\$([^$\n]+)\$/, recursivo: false },
  { tipo: "codigo", regex: /`([^`\n]+)`/, recursivo: false },
  { tipo: "forte", regex: /\*\*(?!\s)((?:[^*\n]|\*(?!\*))+?)(?<!\s)\*\*/, recursivo: true },
  { tipo: "enfase", regex: /(?<![*\w])\*(?![\s*])([^*\n]*[^\s*])\*(?!\*)/, recursivo: true },
];

/**
 * Quebra uma linha nos marcadores inline.
 *
 * Devolve uma lista de tokens `{tipo, conteudo}`, onde `conteudo` é uma
 * string nos tokens folha (`texto`, `codigo`, `matematica`) e uma lista de
 * tokens nos que aceitam aninhamento (`forte`, `enfase`).
 */
export function dividirInline(texto) {
  if (!texto) return [];

  for (const { tipo, regex, recursivo } of REGRAS) {
    const achado = texto.match(regex);
    if (!achado) continue;
    const antes = texto.slice(0, achado.index);
    const depois = texto.slice(achado.index + achado[0].length);
    return [
      ...dividirInline(antes),
      { tipo, conteudo: recursivo ? dividirInline(achado[1]) : achado[1] },
      ...dividirInline(depois),
    ];
  }
  return [{ tipo: "texto", conteudo: texto }];
}

/**
 * Quebra o markdown em blocos, por linha em branco, e classifica cada um.
 *
 * Um bloco é homogêneo: ou é uma lista inteira, ou é um parágrafo inteiro.
 * Misturar `- item` com texto solto no mesmo bloco cai em parágrafo, que é o
 * comportamento previsível — e é o que `README.md` promete.
 */
export function dividirEmBlocos(markdown) {
  return String(markdown || "")
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}/)
    .map((b) => b.trim())
    .filter(Boolean)
    .map((bruto) => {
      const linhas = bruto.split("\n").map((l) => l.trim()).filter(Boolean);
      if (linhas.length === 1 && /^#{2,3}\s+/.test(linhas[0])) {
        return { tipo: "titulo", texto: linhas[0].replace(/^#{2,3}\s+/, "") };
      }
      if (linhas.every((l) => /^>\s?/.test(l))) {
        return { tipo: "citacao", texto: linhas.map((l) => l.replace(/^>\s?/, "")).join(" ") };
      }
      if (linhas.every((l) => /^[-*]\s+/.test(l))) {
        return { tipo: "lista", itens: linhas.map((l) => l.replace(/^[-*]\s+/, "")) };
      }
      if (linhas.every((l) => /^\d+[.)]\s+/.test(l))) {
        return { tipo: "numerada", itens: linhas.map((l) => l.replace(/^\d+[.)]\s+/, "")) };
      }
      return { tipo: "paragrafo", texto: linhas.join(" ") };
    });
}
