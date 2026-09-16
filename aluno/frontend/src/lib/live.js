/**
 * Quando é a próxima aula ao vivo — versão do navegador.
 *
 * **A fonte da verdade é o servidor** (`backend/cursos.py::proxima_live`): é
 * ele que decide qual edição está sendo vendida, cobra por ela e entrega o
 * link. Este arquivo existe por um motivo estreito e específico: o **Painel**
 * anuncia a live em todo carregamento, e o Painel é a tela mais quente do
 * produto. Buscar `/cursos` ali custaria uma leitura do Firestore por
 * abertura de painel, por aluno, para exibir um anúncio — exatamente o tipo de
 * custo por requisição que a disciplina de leitura do produto proíbe.
 *
 * Então o anúncio é calculado aqui, de graça, e QUEM DECIDE continua sendo o
 * servidor: clicar leva para `/cursos`, que carrega o estado real. O pior caso
 * de divergência (relógio do aparelho errado, aluno em outro fuso) é um
 * anúncio que mostra a quinta certa com uma hora local diferente — e a página
 * de destino corrige.
 *
 * As constantes abaixo espelham `backend/cursos.py`. Se a aula mudar de dia ou
 * de horário, os dois arquivos mudam juntos.
 */

const DIA_SEMANA = 4;         // 0 = domingo ... 4 = quinta (Date.getDay)
const HORA = 20;              // 20h
const DURACAO_MINUTOS = 90;
const ABRE_MINUTOS_ANTES = 30;

const CHAVE_ACESSO = "sapiens:live-acesso";

/** `{ edicao, inicio, fim, aoVivoAgora }` da edição que está valendo agora. */
export function proximaQuinta(agora = new Date()) {
  const inicio = new Date(agora);
  inicio.setHours(HORA, 0, 0, 0);
  inicio.setDate(inicio.getDate() + ((DIA_SEMANA - agora.getDay() + 7) % 7));

  let fim = new Date(inicio.getTime() + DURACAO_MINUTOS * 60000);
  // Hoje é quinta e a aula já acabou: a próxima é a da semana que vem. A
  // mesma regra do servidor — durante a aula, a edição corrente continua
  // sendo a de hoje, que é justamente quando mais gente entra.
  if (agora > fim) {
    inicio.setDate(inicio.getDate() + 7);
    fim = new Date(inicio.getTime() + DURACAO_MINUTOS * 60000);
  }

  const abre = new Date(inicio.getTime() - ABRE_MINUTOS_ANTES * 60000);
  const iso = `${inicio.getFullYear()}-${String(inicio.getMonth() + 1).padStart(2, "0")}-${String(
    inicio.getDate(),
  ).padStart(2, "0")}`;

  return { edicao: iso, inicio, fim, aoVivoAgora: agora >= abre && agora <= fim };
}

/**
 * Lembra, SÓ NESTE APARELHO, que o aluno já comprou a edição X.
 *
 * Serve para o Painel não oferecer "garanta sua vaga" a quem acabou de pagar.
 * Não é autorização de nada: o link da sala nunca sai do servidor sem a
 * compra registrada lá (ver `cursos_routes._montar_live`). Outro aparelho vê o
 * convite de venda de novo e, ao clicar, a página de Cursos mostra o acesso
 * que ele já tem — sem cobrar segunda vez.
 */
export function marcarAcessoDaLive(edicao) {
  try {
    localStorage.setItem(CHAVE_ACESSO, edicao);
  } catch {
    /* navegador com armazenamento bloqueado: o anúncio só fica menos preciso */
  }
}

export function temAcessoLocal(edicao) {
  try {
    return localStorage.getItem(CHAVE_ACESSO) === edicao;
  } catch {
    return false;
  }
}
