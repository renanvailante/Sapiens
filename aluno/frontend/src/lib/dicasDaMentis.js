import { ROTAS } from "./rotas";

/**
 * AS DICAS DA MENTIS — uma frase por área, na primeira vez que o aluno chega.
 *
 * O Duolingo nunca abre uma tela nova sem o personagem dizer, em uma linha,
 * o que se faz ali. É a diferença entre "aprender a usar" e só usar: o aluno
 * não precisa decifrar a tela, alguém diz. Pedido do dono em 2026-10-09:
 * *"parece que eu tenho que aprender a usar a plataforma antes de realmente
 * estudar nela"*.
 *
 * Regras:
 *   · uma frase, no máximo duas — dica não é tutorial;
 *   · aparece UMA vez por área, por aparelho (`localStorage`), e some sozinha;
 *   · nunca por cima de questão: com `item_ids`/`area` na URL o aluno já está
 *     respondendo, e uma dica ali seria a guia atrapalhando;
 *   · o Hoje não tem dica: lá a Mentis já está NO conteúdo, falando.
 */
export const DICAS = {
  [ROTAS.AGENDA]: "Aqui fica o que tem hora marcada: os blocos da sua semana e as questões que voltam para revisão.",
  [ROTAS.ESTUDAR]: "Aqui você escolhe livremente o que estudar. Na dúvida, o seu próximo passo já está escolhido — é só continuar a trilha.",
  [ROTAS.PROVAS]: "Cada caderno é uma prova real do ENEM. Toque num e responda: cada resposta me mostra onde você tropeça.",
  [ROTAS.CURSOS]: "Cursos e e-books para aprender do zero. Toque num curso e siga o caminho dele, estação por estação.",
  [ROTAS.REDACAO]: "Escreva a sua redação aqui (ou mande a foto da folha) e eu corrijo nas cinco competências do ENEM.",
  [ROTAS.TREINO]: "O mapa de treino: cada ponto é uma missão curta. O que está brilhando é por onde começar.",
  [ROTAS.PROGRESSO]: "Aqui você confere se está evoluindo: o seu mapa de habilidades, a trajetória e as conquistas.",
  [ROTAS.COMUNIDADE]: "O mural de dúvidas. Travou? Pergunte. Sabe a resposta? Ajudar um colega fixa o conteúdo em você.",
  [ROTAS.SPARKS]: "Seus Sparks: o saldo e os pacotes. Cumprir as missões da trilha também rende Sparks.",
};

const chave = (rota) => `sapiens:dica-vista:${rota}`;

/** A dica desta tela, ou `null` (sem dica, já vista ou o aluno respondendo). */
export function dicaPara(pathname, search = "") {
  const rota = (pathname || "").replace(/\/+$/, "") || "/";
  const texto = DICAS[rota];
  if (!texto) return null;
  const q = new URLSearchParams(search || "");
  if (q.get("item_ids") || q.get("area") || q.get("hab")) return null;
  try {
    if (localStorage.getItem(chave(rota))) return null;
  } catch {
    // Sem storage não há como lembrar que já foi vista: melhor não mostrar
    // do que mostrar a mesma dica em toda visita.
    return null;
  }
  return { rota, texto };
}

export function marcarDicaVista(rota) {
  try {
    localStorage.setItem(chave(rota), "1");
  } catch {
    /* sem storage: ver `dicaPara` */
  }
}
