import { tocar } from "./som";
import { soltarConfete } from "./confete";

/**
 * A reação do produto a UMA resposta — o "plim" e o confetinho do Duolingo.
 *
 * Uma função só para as telas de questão (provas, treino, questões geradas):
 * o aluno deve reconhecer o acerto pelo ouvido em qualquer uma delas, do
 * mesmo jeito que já reconhece pelo verde (ver `components/questao`).
 *
 * O confete sai da alternativa que o aluno MARCOU, é pequeno e não bloqueia
 * nada — o botão de seguir continua clicável no meio dele.
 */
export const MARCOS_DE_COMBO = [3, 5, 10, 15, 20];

export function reagirAResposta(acertou, { seguidas = 0 } = {}) {
  if (!acertou) {
    tocar("erro");
    return;
  }
  const marco = MARCOS_DE_COMBO.includes(seguidas);
  tocar(marco ? "combo" : "acerto");
  const alvo = typeof document !== "undefined"
    ? document.querySelector('.alternativa[data-escolhida="true"]')
    : null;
  soltarConfete({ de: alvo, quantidade: marco ? 55 : 24, forca: marco ? 9 : 7, espalhar: 65 });
}

/** Elogio do acerto quando o servidor não mandou título próprio. Fixo por
 *  veredito (escolhido na montagem), para não trocar de palavra a cada render. */
const ELOGIOS = ["Mandou bem!", "Excelente!", "Isso aí!", "Perfeito!", "Muito bom!", "Certíssimo!"];
export function elogio() {
  return ELOGIOS[Math.floor(Math.random() * ELOGIOS.length)];
}
