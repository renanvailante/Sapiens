/**
 * QUANDO O SAPIENS COMEMORA — regra pura, sem React, testada.
 *
 * Duas comemorações de tela inteira, as duas do Duolingo:
 *
 * 1. **A ofensiva** — a primeira vez no dia em que o aluno estuda, a chama
 *    acende e o número sobe. Uma vez por dia, por aparelho: a segunda série do
 *    dia não é um dia novo, e comemorar de novo ensinaria que a comemoração
 *    não significa nada.
 * 2. **O presente do Plus** — no instante em que a primeira ofensiva de 5 dias
 *    vira 2 dias de Sapiens Plus. Uma vez por prêmio (`concedido_em`).
 *
 * As duas leem SÓ o que `/engajamento/me` devolveu — `estudou_hoje`, o número
 * da ofensiva, o prazo gravado pelo servidor. Nenhuma comemora o que o
 * servidor não contou (a mesma régua de `recompensaDaSerie`).
 *
 * A memória de "já comemorei" mora no `localStorage`: é uma conveniência do
 * aparelho, não um dado. Se ele estiver bloqueado, a comemoração aparece de
 * novo na próxima visita — melhor do que nunca aparecer.
 */

const CHAVE_OFENSIVA = "sapiens:ofensiva-comemorada";
const CHAVE_PLUS = "sapiens:plus-comemorado";

function ler(chave) {
  try {
    return localStorage.getItem(chave);
  } catch {
    return null;
  }
}

function gravar(chave, valor) {
  try {
    localStorage.setItem(chave, valor);
  } catch {
    /* sem storage: comemora de novo na próxima, e tudo bem */
  }
}

const sufixo = (uid) => (uid ? `:${uid}` : "");

/** Comemorar a ofensiva agora? Só com estudo HOJE e só uma vez no dia. */
export function deveComemorarOfensiva(engajamento, jaComemorado) {
  const o = engajamento?.ofensiva;
  if (!o || !o.estudou_hoje || !(o.dias > 0)) return false;
  const hoje = engajamento.hoje;
  if (!hoje) return false;
  return jaComemorado !== hoje;
}

/** Comemorar o presente do Plus? Só Plus ATIVO e ainda não comemorado. */
export function deveComemorarPlus(plus, jaComemorado) {
  if (!plus?.ativo || !plus.concedido_em) return false;
  return jaComemorado !== plus.concedido_em;
}

export function lerComemoracoes(uid) {
  return {
    ofensiva: ler(CHAVE_OFENSIVA + sufixo(uid)),
    plus: ler(CHAVE_PLUS + sufixo(uid)),
  };
}

export function marcarOfensivaComemorada(uid, dia) {
  if (dia) gravar(CHAVE_OFENSIVA + sufixo(uid), dia);
}

export function marcarPlusComemorado(uid, concedidoEm) {
  if (concedidoEm) gravar(CHAVE_PLUS + sufixo(uid), concedidoEm);
}

/** "até sábado, 17h" — o prazo REAL gravado pelo servidor, na hora de São Paulo. */
export function prazoDoPlus(ateIso) {
  if (!ateIso) return null;
  const d = new Date(ateIso);
  if (Number.isNaN(d.getTime())) return null;
  try {
    const dia = new Intl.DateTimeFormat("pt-BR", { weekday: "long", timeZone: "America/Sao_Paulo" }).format(d);
    const hora = new Intl.DateTimeFormat("pt-BR", {
      hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo",
    }).format(d);
    const [h, m] = hora.split(":");
    return `até ${dia}, ${Number(h)}h${m && m !== "00" ? m : ""}`;
  } catch {
    return null;
  }
}

/** Horas inteiras que faltam (para "faltam 31h"). `null` se já venceu. */
export function horasRestantes(ateIso, agora = Date.now()) {
  const fim = new Date(ateIso).getTime();
  if (!Number.isFinite(fim) || fim <= agora) return null;
  return Math.max(1, Math.round((fim - agora) / 3_600_000));
}

/** As letras da semana sob as bolinhas — "S T Q Q S S D", como no Duolingo. */
export function letraDoDia(isoDia) {
  const d = new Date(`${isoDia}T12:00:00`);
  if (Number.isNaN(d.getTime())) return "";
  return ["D", "S", "T", "Q", "Q", "S", "S"][d.getDay()];
}

/** O que o Plus abre — a MESMA lista de `sparks_store.DIREITOS_DO_PLUS`,
 *  escrita como o aluno lê. Se o backend mudar o Plus, o teste de
 *  `celebracao.test.js` e o de `test_direitos_do_pacote.py` mudam juntos. */
export const BENEFICIOS_DO_PLUS = [
  { chave: "mentis_ilimitada", texto: "Mentis ilimitada", detalhe: "chat, explicações e correções sem gastar Sparks" },
  { chave: "cursos_inclusos", texto: "Todos os cursos e e-books", detalhe: "abertos para estudar no app" },
  { chave: "comunidade_vip", texto: "Sala VIP da comunidade", detalhe: "o mural fechado com os alunos do pacote" },
];

/** Frase do caminho até o presente, para o card e para a tela da ofensiva. */
export function fraseDoDesafio(plus) {
  if (!plus) return null;
  if (plus.ativo) return null;
  if (plus.conquistado) return null;
  const f = plus.faltam;
  if (f <= 0) return null;
  if (plus.progresso === 0) {
    return `Estude ${plus.meta_dias} dias seguidos e ganhe ${plus.presente_dias} dias de Sapiens Plus.`;
  }
  return f === 1
    ? `Falta 1 dia para ganhar ${plus.presente_dias} dias de Sapiens Plus.`
    : `Faltam ${f} dias para ganhar ${plus.presente_dias} dias de Sapiens Plus.`;
}
