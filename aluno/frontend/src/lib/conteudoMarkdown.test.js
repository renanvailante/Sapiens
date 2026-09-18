/**
 * O parser do subconjunto de markdown dos cursos.
 *
 * Por que ele merece teste próprio: é a única peça do sistema de conteúdo que
 * roda no navegador sobre texto escrito por OUTRA pessoa (uma IA, em lote) e
 * que pode estar sutilmente errada sem quebrar nada visivelmente — uma
 * fórmula com asterisco lida como itálico, um `**` casando como ênfase, uma
 * lista virando parágrafo. Cada um desses casos está aqui.
 */
import { dividirEmBlocos, dividirInline } from "./conteudoMarkdown";

/** Achata a árvore de tokens em texto, para asserção legível. */
function planificar(tokens) {
  return tokens
    .map((t) => (Array.isArray(t.conteudo) ? planificar(t.conteudo) : t.conteudo))
    .join("");
}

function tipos(tokens) {
  return tokens.map((t) => t.tipo);
}

describe("dividirInline", () => {
  test("texto sem marcador vira um token só", () => {
    expect(dividirInline("regra de três simples")).toEqual([
      { tipo: "texto", conteudo: "regra de três simples" },
    ]);
  });

  test("negrito, itálico e código são reconhecidos", () => {
    expect(tipos(dividirInline("a **b** c *d* e `f`"))).toEqual([
      "texto", "forte", "texto", "enfase", "texto", "codigo",
    ]);
  });

  test("`**` é negrito e nunca duas ênfases", () => {
    const tokens = dividirInline("**importante**");
    expect(tipos(tokens)).toEqual(["forte"]);
    expect(planificar(tokens)).toBe("importante");
  });

  test("a fórmula ganha do itálico — dentro de $…$ o asterisco é LaTeX", () => {
    // Sem a precedência certa, `a^*` abriria uma ênfase e comeria o resto da
    // linha: a fórmula sumiria e o texto seguinte viraria itálico.
    const tokens = dividirInline("vale $a^* \\cdot b_1$ sempre");
    expect(tipos(tokens)).toEqual(["texto", "matematica", "texto"]);
    expect(tokens[1].conteudo).toBe("a^* \\cdot b_1");
  });

  test("dentro de código o conteúdo é literal", () => {
    const tokens = dividirInline("use `x * y` aqui");
    expect(tipos(tokens)).toEqual(["texto", "codigo", "texto"]);
    expect(tokens[1].conteudo).toBe("x * y");
  });

  test("ênfase aninhada dentro de negrito", () => {
    const tokens = dividirInline("**muito *mesmo* aqui**");
    expect(tipos(tokens)).toEqual(["forte"]);
    expect(tipos(tokens[0].conteudo)).toEqual(["texto", "enfase", "texto"]);
    expect(planificar(tokens)).toBe("muito mesmo aqui");
  });

  test("dois negritos na mesma linha não viram um só", () => {
    // O caso que obriga o `forte` a ser preguiçoso: com casamento guloso,
    // `**a** e **b**` viraria um único negrito engolindo o " e " do meio.
    const tokens = dividirInline("**a** e **b**");
    expect(tipos(tokens)).toEqual(["forte", "texto", "forte"]);
    expect(planificar(tokens)).toBe("a e b");
  });

  test("asterisco colado em palavra não abre itálico", () => {
    expect(tipos(dividirInline("x*y*z"))).toEqual(["texto"]);
  });

  test("multiplicação solta não vira itálico", () => {
    // `3 * 4 * 5` aparece em Matemática Básica o tempo todo. Se casasse como
    // ênfase, metade dos enunciados sairia em itálico com os asteriscos
    // sumidos — e o aluno leria uma conta diferente da escrita.
    const tokens = dividirInline("3 * 4 * 5 = 60");
    expect(tipos(tokens)).toEqual(["texto"]);
    expect(planificar(tokens)).toBe("3 * 4 * 5 = 60");
  });

  test("texto vazio não gera token nenhum", () => {
    expect(dividirInline("")).toEqual([]);
  });
});

describe("dividirEmBlocos", () => {
  test("linha em branco separa parágrafos", () => {
    const blocos = dividirEmBlocos("primeiro\n\nsegundo");
    expect(blocos.map((b) => b.tipo)).toEqual(["paragrafo", "paragrafo"]);
  });

  test("quebra simples dentro do parágrafo vira espaço", () => {
    const [bloco] = dividirEmBlocos("uma frase\nque continua");
    expect(bloco).toEqual({ tipo: "paragrafo", texto: "uma frase que continua" });
  });

  test("título, citação, lista e lista numerada", () => {
    const md = [
      "## Um título",
      "> uma nota",
      "- a\n- b",
      "1. primeiro\n2. segundo",
    ].join("\n\n");
    expect(dividirEmBlocos(md).map((b) => b.tipo)).toEqual([
      "titulo", "citacao", "lista", "numerada",
    ]);
  });

  test("a lista preserva os itens sem o marcador", () => {
    const [bloco] = dividirEmBlocos("- fração\n- porcentagem");
    expect(bloco.itens).toEqual(["fração", "porcentagem"]);
  });

  test("bloco misto cai em parágrafo em vez de virar meia-lista", () => {
    const [bloco] = dividirEmBlocos("veja:\n- a\n- b");
    expect(bloco.tipo).toBe("paragrafo");
  });

  test("markdown vazio, nulo ou só espaço não produz bloco", () => {
    expect(dividirEmBlocos("")).toEqual([]);
    expect(dividirEmBlocos(null)).toEqual([]);
    expect(dividirEmBlocos("   \n\n  ")).toEqual([]);
  });

  test("quebra de linha do Windows não duplica bloco", () => {
    expect(dividirEmBlocos("a\r\n\r\nb").map((b) => b.texto)).toEqual(["a", "b"]);
  });
});
