import { emailJaTemConta } from "./api";

/* A regra vive de uma comparação de texto contra a mensagem do backend
 * (`auth.py`: 400 + "Email already registered"). É exatamente o tipo de
 * acoplamento que quebra em silêncio — ninguém reclama de um `if` que passou a
 * dar `false`; o aluno só volta a ver a frase em inglês e a tela para de se
 * corrigir sozinha. Estes casos são o alarme. */

const recusa = (status, detail) => ({ response: { status, data: { detail } } });

describe("emailJaTemConta", () => {
  test("reconhece a recusa de cadastro duplicado do backend", () => {
    expect(emailJaTemConta(recusa(400, "Email already registered"))).toBe(true);
  });

  test("não depende de caixa nem do resto da frase", () => {
    expect(emailJaTemConta(recusa(400, "email ALREADY REGISTERED"))).toBe(true);
    expect(emailJaTemConta(recusa(400, "Email already registered (use /login)"))).toBe(true);
  });

  test("o 400 sozinho não basta — é o genérico de outras recusas do cadastro", () => {
    expect(emailJaTemConta(recusa(400, "Cupom inválido."))).toBe(false);
  });

  test("a mesma frase com outro status não é esta recusa", () => {
    expect(emailJaTemConta(recusa(500, "Email already registered"))).toBe(false);
  });

  test("erro sem resposta (a rede caiu) não vira troca de tela", () => {
    expect(emailJaTemConta(new Error("Network Error"))).toBe(false);
    expect(emailJaTemConta(undefined)).toBe(false);
  });

  test("o `detail` de 422 vem como array e não pode explodir a checagem", () => {
    expect(emailJaTemConta(recusa(400, [{ msg: "campo obrigatório" }]))).toBe(false);
  });
});
