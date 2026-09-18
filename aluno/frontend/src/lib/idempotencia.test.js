import { criarPortao, novaChave } from "./idempotencia";

/**
 * O portão guarda QUATRO compras (correção de redação, digitalização da foto,
 * montagem do cronograma e entrada na fila da mentoria). O que estes testes
 * travam é a diferença entre as duas coisas que ele faz, porque confundi-las
 * é o que cobra duas vezes:
 *
 *  · a TRAVA impede duas chamadas ao mesmo tempo (o toque duplo);
 *  · a CHAVE só troca quando a ação terminou bem, para que uma segunda
 *    tentativa depois de um erro de rede seja reconhecida como o mesmo pedido.
 */

describe("novaChave", () => {
  it("nunca repete", () => {
    const chaves = new Set(Array.from({ length: 500 }, () => novaChave()));
    expect(chaves.size).toBe(500);
  });
});

describe("criarPortao", () => {
  it("deixa a primeira entrar e barra a segunda enquanto a primeira está em voo", () => {
    const p = criarPortao();
    expect(p.entrar()).toBe(true);
    expect(p.entrar()).toBe(false);
    expect(p.entrar()).toBe(false);
  });

  it("libera de novo depois de sair", () => {
    const p = criarPortao();
    p.entrar();
    p.sair();
    expect(p.entrar()).toBe(true);
  });

  it("MANTÉM a chave quando a ação falha — a nova tentativa é o mesmo pedido", () => {
    const p = criarPortao();
    const antes = p.chave;
    p.entrar();
    p.sair(); // falhou: nenhum `concluir()`
    expect(p.chave).toBe(antes);
  });

  it("troca a chave depois de concluir — a próxima ação é outra compra", () => {
    const p = criarPortao();
    const antes = p.chave;
    p.entrar();
    p.concluir();
    p.sair();
    expect(p.chave).not.toBe(antes);
  });

  it("dois portões não compartilham chave nem estado", () => {
    const a = criarPortao();
    const b = criarPortao();
    expect(a.chave).not.toBe(b.chave);
    a.entrar();
    expect(b.entrar()).toBe(true);
  });
});
