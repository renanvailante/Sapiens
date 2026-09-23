/**
 * Identificação do operador do serviço — exigida pelo Código de Defesa do
 * Consumidor (art. 31) e pela LGPD (art. 9º, que dá ao titular o direito de
 * saber quem trata seus dados e como falar com essa pessoa; e art. 41, que
 * manda indicar o encarregado).
 *
 * ---------------------------------------------------------------------------
 * POR QUE ISTO DEIXOU DE ESTAR "PENDENTE" EM 2026-09-21
 * ---------------------------------------------------------------------------
 *
 * A versão anterior tratava `razaoSocial`, `cnpj`, `endereco` e
 * `emailPrivacidade` como quatro buracos a preencher, e por isso `/termos` e
 * `/privacidade` estampavam em produção: *"Documento em finalização. Faltam
 * os dados de identificação do responsável."* O comentário do arquivo dizia
 * "AÇÃO NECESSÁRIA ANTES DO BETA PÚBLICO".
 *
 * **Comprar tráfego é cruzar essa linha.** Os dois únicos links do rodapé das
 * landings de anúncio apontam para essas duas páginas, e o Sapiens fala com
 * menor de idade. Pagar para levar adolescente a um cadastro cuja política de
 * privacidade se declara incompleta é a pior assimetria de risco do produto:
 * custa quase nada consertar e custa caro se alguém reclamar.
 *
 * O defeito real não era a falta de preenchimento, era o MODELO: ele
 * pressupunha pessoa jurídica. Um operador pessoa física não tem razão social
 * nem CNPJ — e enquanto o modelo exigisse os dois, o aviso de rascunho ficaria
 * no ar para sempre, sem nunca haver o que preencher.
 *
 * Agora o tipo do operador é explícito e cada tipo tem a SUA lista de campos
 * obrigatórios. Virar pessoa jurídica é trocar `tipo` e preencher dois campos.
 */

/** O que cada tipo de operador precisa declarar para o documento estar
 *  completo. Endereço não entra em nenhuma das duas listas de propósito:
 *  para pessoa física ele é o endereço RESIDENCIAL de alguém, e publicá-lo
 *  numa página aberta cria para o operador exatamente o risco que a LGPD
 *  existe para reduzir. O canal de contato obrigatório é o e-mail. */
const OBRIGATORIOS = {
  pessoa_fisica: ["responsavel", "emailContato", "emailPrivacidade"],
  pessoa_juridica: ["razaoSocial", "cnpj", "emailContato", "emailPrivacidade"],
};

export const OPERADOR = {
  tipo: "pessoa_fisica",

  nomeFantasia: "Sapiens",

  /** Quem responde pelo serviço. Em pessoa física é o nome civil de quem
   *  opera; em pessoa jurídica isto some e quem vale é a razão social. */
  responsavel: "Renan Vailante",

  razaoSocial: null, // não se aplica a pessoa física
  cnpj: null, // não se aplica a pessoa física
  endereco: null, // ver o comentário de OBRIGATORIOS

  emailContato: "sapiens.lab12@gmail.com",

  /** Encarregado de dados (LGPD art. 41). Num operador de uma pessoa só, é a
   *  mesma pessoa — e a lei não exige que sejam diferentes. O que ela exige é
   *  que o titular saiba PARA ONDE escrever, e isto responde isso. */
  emailPrivacidade: "sapiens.lab12@gmail.com",
};

/**
 * Campos legais ainda não preenchidos, **para o tipo de operador vigente**.
 * Vazio = documentos completos, e o aviso de rascunho não é montado.
 *
 * Antes isto varria o objeto inteiro procurando `null`, então `razaoSocial` e
 * `cnpj` — que num operador pessoa física são corretamente nulos — contavam
 * como pendência e mantinham o aviso aceso permanentemente.
 */
export function pendenciasDoOperador() {
  const exigidos = OBRIGATORIOS[OPERADOR.tipo] || OBRIGATORIOS.pessoa_juridica;
  return exigidos.filter((campo) => {
    const valor = OPERADOR[campo];
    return valor === null || valor === undefined || String(valor).trim() === "";
  });
}

/** Como o operador se identifica num documento legal, em uma linha. */
export function identificacaoDoOperador() {
  if (OPERADOR.tipo === "pessoa_fisica") {
    return `${OPERADOR.responsavel} (pessoa física), que opera o serviço sob o nome ${OPERADOR.nomeFantasia}`;
  }
  return `${OPERADOR.razaoSocial}, CNPJ ${OPERADOR.cnpj}, que opera o serviço sob o nome ${OPERADOR.nomeFantasia}`;
}

/** A data que os documentos legais exibem.
 *
 *  `ATUALIZADO_EM` é o padrão — a data em que Termos e Privacidade nasceram
 *  juntos. **Cada documento pode ter a sua**, e passa `atualizadoEm` para
 *  `PaginaLegal`: eles mudam em datas diferentes, e uma constante só fazia
 *  corrigir a Privacidade anunciar que os Termos também tinham mudado. Uma
 *  data falsa num documento legal é pior que uma data velha — é ela que o
 *  titular usa para saber se leu a versão que está valendo. */
export const ATUALIZADO_EM = "2 de setembro de 2026";

/** A Política de Privacidade mudou sozinha em 22/09/2026, quando o Meta Pixel
 *  entrou e as seções 2, 3, 4, 5 e 9 tiveram de passar a dizer a verdade. */
export const PRIVACIDADE_ATUALIZADA_EM = "22 de setembro de 2026";
