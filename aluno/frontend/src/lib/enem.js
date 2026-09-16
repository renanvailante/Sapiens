/**
 * A contagem regressiva para o ENEM — o único relógio que todo aluno daqui
 * está correndo contra.
 *
 * **As datas são as mesmas de `backend/engajamento.py::DATAS_ENEM`** e
 * precisam mudar juntas, uma vez por ano. Estão duplicadas aqui pelo mesmo
 * motivo de `lib/live.js`: a contagem aparece em CINCO telas, inclusive na
 * landing (onde não há sessão) e no Painel (a tela mais quente do produto), e
 * buscar do servidor uma data que muda uma vez por ano custaria uma
 * requisição por abertura de tela para não descobrir nada novo.
 *
 * O horário de início (13h30 de Brasília) é o padrão do exame e entra aqui
 * porque a contagem tem hora, minuto e segundo: sem ele, o relógio pararia no
 * dia e a última véspera — que é justamente quando a urgência é real —
 * ficaria sem contagem nenhuma.
 *
 * **Sem urgência inventada.** Quando os dois domingos passam, `proximaProva`
 * devolve `null` e toda a contagem some da interface, em vez de mostrar um
 * número negativo ou reciclar o ano seguinte sem alguém ter revisado o
 * calendário.
 */

// AAAA-MM-DD dos dois domingos de prova, na ordem.
export const DATAS_ENEM = ["2026-11-08", "2026-11-22"];

const HORA_INICIO = 13;
const MINUTO_INICIO = 30;

/** `{ data, inicio, fase }` do próximo domingo de prova, ou `null`. */
export function proximaProva(agora = new Date()) {
  for (let i = 0; i < DATAS_ENEM.length; i += 1) {
    const [ano, mes, dia] = DATAS_ENEM[i].split("-").map(Number);
    const inicio = new Date(ano, mes - 1, dia, HORA_INICIO, MINUTO_INICIO, 0, 0);
    if (inicio > agora) return { data: DATAS_ENEM[i], inicio, fase: i + 1 };
  }
  return null;
}

/** `{ dias, horas, minutos, segundos, total }` até `alvo`. Nunca negativo. */
export function tempoRestante(alvo, agora = new Date()) {
  const total = Math.max(0, alvo - agora);
  const s = Math.floor(total / 1000);
  return {
    dias: Math.floor(s / 86400),
    horas: Math.floor((s % 86400) / 3600),
    minutos: Math.floor((s % 3600) / 60),
    segundos: s % 60,
    total,
  };
}

/**
 * Quantos domingos inteiros ainda cabem antes da prova — ou seja, quantas
 * aulas ao vivo de quinta-feira ainda vão acontecer a tempo.
 *
 * É o número que transforma "faltam 54 dias" em uma decisão: cada quinta que
 * passa é uma aula que não volta. Conta as quintas ENTRE agora e a primeira
 * prova, incluindo a desta semana se ela ainda não aconteceu.
 */
export function quintasAteAProva(agora = new Date()) {
  const prova = proximaProva(agora);
  if (!prova) return 0;
  let quintas = 0;
  const cursor = new Date(agora);
  cursor.setHours(20, 0, 0, 0);
  // Anda até a primeira quinta >= agora.
  cursor.setDate(cursor.getDate() + ((4 - cursor.getDay() + 7) % 7));
  while (cursor < prova.inicio) {
    quintas += 1;
    cursor.setDate(cursor.getDate() + 7);
  }
  return quintas;
}
