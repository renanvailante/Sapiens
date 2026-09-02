/**
 * Identificação do operador do serviço — exigida pelo Código de Defesa do
 * Consumidor (art. 31) e pela LGPD (art. 9º, que dá ao titular o direito de
 * saber quem trata seus dados e como falar com essa pessoa).
 *
 * ┌──────────────────────────────────────────────────────────────────────┐
 * │ AÇÃO NECESSÁRIA ANTES DO BETA PÚBLICO                                │
 * │ Os campos marcados PENDENTE dependem de dado que só o responsável    │
 * │ legal tem. Enquanto estiverem assim, as telas de Termos e            │
 * │ Privacidade exibem um aviso visível em vez de fingir que estão       │
 * │ completas — publicar um documento legal com dado inventado é pior    │
 * │ que publicá-lo declaradamente incompleto.                            │
 * └──────────────────────────────────────────────────────────────────────┘
 */
export const OPERADOR = {
  nomeFantasia: "Sapiens",
  razaoSocial: null,        // PENDENTE
  cnpj: null,               // PENDENTE
  endereco: null,           // PENDENTE
  emailContato: "sapiens.lab12@gmail.com",
  emailPrivacidade: null,   // PENDENTE — encarregado de dados (LGPD art. 41)
};

/** Campos legais ainda não preenchidos. Vazio = documentos completos. */
export function pendenciasDoOperador() {
  return Object.entries(OPERADOR)
    .filter(([, valor]) => valor === null)
    .map(([campo]) => campo);
}

export const ATUALIZADO_EM = "2 de setembro de 2026";
