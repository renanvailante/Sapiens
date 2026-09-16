/**
 * Sequência de dias e fita da semana, a partir das datas de atividade REAL
 * (`GET /firestore/students/me/activity`). Nunca inventa dia: uma bolinha só
 * acende com pelo menos um evento de behavior por trás.
 *
 * Vive aqui, e não dentro do Painel, porque a página de conquistas precisa
 * exatamente do mesmo número — e duas telas contando a ofensiva com códigos
 * diferentes é como se produz o bug em que o Painel diz 12 dias e a outra
 * tela diz 0.
 *
 * Tudo no fuso de São Paulo, não em UTC. O Brasil está em UTC-3: em UTC, quem
 * responde depois das 21h teria a atividade contada no dia seguinte — a
 * bolinha de "hoje" ficaria apagada logo depois de estudar, e a sequência
 * podia zerar sozinha. É exatamente o horário em que vestibulando estuda. O
 * backend grava no mesmo fuso (`firestore_service.dia_local`).
 */

const FUSO_BR = "America/Sao_Paulo";

/** `YYYY-MM-DD` no fuso do aluno. `en-CA` porque é o locale cuja data curta já
 *  sai nesse formato — evita montar a string à mão a partir das partes. */
export function diaLocal(data = new Date()) {
  return data.toLocaleDateString("en-CA", { timeZone: FUSO_BR });
}

/** Dia local deslocado de `dias` (negativo = passado). O deslocamento é feito
 *  ao meio-dia UTC para que o horário de verão, quando existir, nunca faça o
 *  passo de 24h cair no mesmo dia ou pular um. */
export function diaLocalDeslocado(dias) {
  const base = new Date(`${diaLocal()}T12:00:00Z`);
  base.setUTCDate(base.getUTCDate() + dias);
  return base.toISOString().slice(0, 10);
}

export function computeStreak(dates) {
  if (!dates?.length) return 0;
  const set = new Set(dates);
  // Se ainda não estudou hoje, o streak conta a partir de ontem (ainda "vivo").
  let offset = set.has(diaLocal()) ? 0 : -1;
  let streak = 0;
  while (set.has(diaLocalDeslocado(offset))) {
    streak += 1;
    offset -= 1;
  }
  return streak;
}

export function computeWeek(dates) {
  const set = new Set(dates || []);
  const days = [];
  for (let i = 6; i >= 0; i--) {
    const key = diaLocalDeslocado(-i);
    days.push({ key, active: set.has(key), isToday: i === 0 });
  }
  return days;
}
