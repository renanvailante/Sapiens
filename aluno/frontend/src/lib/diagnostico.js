/**
 * O diagnóstico do primeiro acesso: as 10 questões que o cadastro abre.
 *
 * Até 2026-10-22 o cadastro levava ao `/bem-vindo` (vídeo e quatro
 * perguntas), depois a um tour de cinco balões e só então a uma questão — e
 * 28 de 43 alunos nunca chegaram a responder a primeira. Agora a ordem é a da
 * landing ("1. Responda 10 questões · 2. Receba o seu plano"): conta criada,
 * questão na tela; o plano vem depois delas.
 *
 * Quem escolhe as questões é o servidor (`GET /questoes/diagnostico`,
 * `backend/diagnostico_inicial.py`): só texto, curtas, sem língua
 * estrangeira, intercalando as quatro áreas.
 */
import { ROTAS } from "./rotas";

export const TOTAL_DO_DIAGNOSTICO = 10;

export const ROTA_DO_DIAGNOSTICO = `${ROTAS.PROVAS}?diagnostico=1`;

/** Para onde vai quem acabou de entrar. Só uma conta que NASCEU agora vai ao
 *  diagnóstico — o botão do Google também é o "Entrar" de quem já é aluno, e
 *  esse volta para o Hoje de sempre. */
export function destinoDepoisDeEntrar({ contaCriada = false } = {}) {
  return contaCriada ? ROTA_DO_DIAGNOSTICO : ROTAS.HOJE;
}

/** A saída grande do fim do diagnóstico: montar o plano enquanto ele ainda
 *  não existe; com o plano feito (quem refaz o diagnóstico), a trilha. */
export function saidaDoDiagnostico({ planoFeito = false } = {}) {
  return planoFeito
    ? { rota: ROTAS.HOJE, rotulo: "Continuar a trilha" }
    : { rota: ROTAS.BEM_VINDO, rotulo: "Montar o meu plano" };
}

/** As etapas do `/bem-vindo`, que virou o plano DEPOIS do diagnóstico.
 *  `diagnostico` só para quem chega sem nenhuma resposta (fechou a aba antes
 *  da primeira questão e voltou pelo Hoje); `whatsapp` só para quem não tem
 *  número na conta. O desafio do Plus é sempre o último — é a última coisa
 *  que o aluno ouve antes da trilha (pedido do dono, 2026-10-08). */
export function etapasDoPlano({ semRespostas = false, semWhatsapp = false } = {}) {
  return [
    ...(semRespostas ? ["diagnostico"] : []),
    "objetivo",
    "meta",
    "dificuldades",
    ...(semWhatsapp ? ["whatsapp"] : []),
    "desafio",
  ];
}
