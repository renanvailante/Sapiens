/**
 * A origem do tráfego é matemática de query string, e por isso é testável.
 *
 * Nada aqui precisa de navegador: o que decide se uma campanha é atribuível é
 * se os parâmetros sobrevivem ao clique do CTA — uma função pura. A regra da
 * casa vale inteira aqui: **regra que só se confere abrindo o navegador não se
 * confere**, e esta some em silêncio quando quebra (a página continua
 * abrindo, o botão continua funcionando, e só o relatório do Meta fica vazio
 * três semanas depois).
 */
import { destinoComOrigem, lerOrigem, PARAMS_DE_ORIGEM } from "./campanha";
import { ROTAS } from "./rotas";

const qs = (url) => Object.fromEntries(new URLSearchParams(url.split("?")[1] || ""));

describe("lerOrigem", () => {
  test("lê os UTM que vieram e ignora os que não vieram", () => {
    const origem = lerOrigem("?utm_source=meta&utm_medium=paid&utm_campaign=diagnostico&utm_content=video01");
    expect(origem).toEqual({
      utm_source: "meta",
      utm_medium: "paid",
      utm_campaign: "diagnostico",
      utm_content: "video01",
    });
  });

  test("sem query, não inventa chave nenhuma", () => {
    expect(lerOrigem("")).toEqual({});
    expect(lerOrigem(undefined)).toEqual({});
  });

  test("o id de campanha e o clique do Meta são origem", () => {
    const origem = lerOrigem("?campanha_id=camp_abc123&fbclid=XYZ");
    expect(origem.campanha_id).toBe("camp_abc123");
    expect(origem.fbclid).toBe("XYZ");
  });

  test("`convite` NÃO é guardado aqui — ele tem dono em lib/atribuicao", () => {
    expect(PARAMS_DE_ORIGEM).not.toContain("convite");
    expect(lerOrigem("?convite=RENAN4K7Q")).toEqual({});
  });
});

describe("destinoComOrigem", () => {
  test("o CTA leva ao cadastro com a query inteira preservada", () => {
    const destino = destinoComOrigem("?utm_source=meta&utm_medium=paid&utm_campaign=diagnostico&utm_content=video01");
    expect(destino.startsWith(`${ROTAS.LOGIN}?`)).toBe(true);
    expect(qs(destino)).toEqual({
      utm_source: "meta",
      utm_medium: "paid",
      utm_campaign: "diagnostico",
      utm_content: "video01",
      novo: "1",
    });
  });

  test("`novo=1` abre em “Criar conta”, e vence o que a URL disser", () => {
    expect(qs(destinoComOrigem("")).novo).toBe("1");
    expect(qs(destinoComOrigem("?novo=0")).novo).toBe("1");
  });

  test("um parâmetro que o produto ainda não lê também viaja", () => {
    // A regra: a query de origem viaja inteira. O que ninguém lê hoje não
    // custa nada; o que foi jogado fora custa uma campanha.
    expect(qs(destinoComOrigem("?fbclid=ABC&algo_novo=1")).algo_novo).toBe("1");
    expect(qs(destinoComOrigem("?fbclid=ABC&algo_novo=1")).fbclid).toBe("ABC");
  });

  test("o convite sobrevive ao clique, junto dos UTM", () => {
    // É o que faz um anúncio de influencer funcionar: o código chega ao
    // cadastro e a campanha continua identificável.
    const destino = destinoComOrigem("?convite=RENAN4K7Q&utm_source=meta");
    expect(qs(destino).convite).toBe("RENAN4K7Q");
    expect(qs(destino).utm_source).toBe("meta");
  });

  test("a origem guardada preenche o que falta, e nunca sobrescreve a da URL", () => {
    const salva = { utm_source: "antigo", utm_campaign: "campanha_antiga" };
    const destino = destinoComOrigem("?utm_source=meta", { salva });
    expect(qs(destino).utm_source).toBe("meta");
    expect(qs(destino).utm_campaign).toBe("campanha_antiga");
  });

  test("sem origem nenhuma, o destino continua sendo o cadastro", () => {
    expect(destinoComOrigem("")).toBe(`${ROTAS.LOGIN}?novo=1`);
  });
});
