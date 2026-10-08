// Camada de APRESENTAÇÃO dos pontos fracos: o rótulo de produto de cada
// processo, tipo de erro e intervenção do motor cognitivo.
//
// No molde de `components/mapa3d/missoes.js`: o nome do catálogo (a
// ontologia) é a IP do produto e NUNCA aparece para o aluno. Desde
// 2026-10-06 o servidor já troca o nome pelo rótulo antes de responder
// (`aluno/backend/rotulos_de_produto.py`, a fonte) — este espelho existe para
// as telas que só têm o `id` na mão (a causa de um erro que acabou de
// acontecer, o ponto de uma série dirigida). Os dois mapas são o MESMO mapa:
// `tests/test_rotulos_de_produto.py` lê este arquivo e quebra se divergirem.
//
// Mudar um rótulo é mudar UMA linha aqui e a mesma linha no Python.
export const PROCESSOS = {
  "PROC-QUANT-01": "Ordem e comparação",
  "PROC-QUANT-02": "Proporção",
  "PROC-QUANT-03": "Estimativa",
  "PROC-QUANT-04": "Unidades e escala",
  "PROC-ESPACO-01": "Leitura de figuras",
  "PROC-ESPACO-02": "Áreas e volumes",
  "PROC-ESPACO-03": "Forma e função",
  "PROC-MUD-01": "Taxas de variação",
  "PROC-MUD-02": "O que se conserva",
  "PROC-INC-01": "Chance com condição",
  "PROC-INC-02": "Médias",
  "PROC-INC-03": "Espalhamento dos dados",
  "PROC-INC-04": "Contagem de chances",
  "PROC-CAUSAL-01": "Cadeias de causa",
  "PROC-LOGICO-01": "Lógica dos argumentos",
  "PROC-SIMB-01": "Montar a equação",
  "PROC-SIMB-02": "Ler fórmulas",
  "PROC-TEXT-01": "Achar o dado",
  "PROC-TEXT-02": "Ler nas entrelinhas",
  "PROC-TEXT-03": "Cruzar fontes",
  "PROC-EXP-01": "Hipóteses",
  "PROC-EXP-02": "Variáveis do experimento",
  "PROC-SIST-01": "Reação do sistema",
  "PROC-SIST-02": "Fluxos e ciclos",
  "PROC-CLASSIF-01": "Agrupar por critério",
};

export const ERROS = {
  "ERR-01": "Dado que passou batido",
  "ERR-02": "Ir além do texto",
  "ERR-03": "Conta que não é a da situação",
  "ERR-04": "Unidade trocada",
  "ERR-05": "Proporção invertida",
  "ERR-06": "Ponto errado no gráfico",
  "ERR-07": "Coincidência vista como causa",
  "ERR-08": "Conclusão grande demais",
  "ERR-09": "Variável esquecida",
  "ERR-10": "Símbolo mal lido",
  "ERR-11": "Número fora de escala",
  "ERR-12": "Argumento que não fecha",
  "ERR-13": "Critério de aparência",
  "erro-nao-catalogado-nesta-versao": "Padrão ainda sem nome",
  "sem-mecanismo-cognitivo-identificavel": "Padrão ainda sem nome",
};

export const INTERVENCOES = {
  "INT-01": "Reler com roteiro",
  "INT-02": "Do texto ao esquema",
  "INT-03": "Treino de proporção",
  "INT-04": "Leitura atenta de gráficos",
  "INT-05": "Desmontar argumentos",
  "INT-06": "Treino de estimativa",
  "INT-07": "Conferir unidades",
  "INT-08": "Causa ou coincidência",
  "INT-09": "Provar pelo texto",
  "INT-10": "Montar o experimento",
  "INT-11": "Classificar pelo que importa",
};

export const PROCESSO_DESCONHECIDO = "Ponto de atenção";
export const ERRO_DESCONHECIDO = "Padrão de erro";

/** O rótulo de um processo pelo id. Id desconhecido nunca devolve o que veio
 *  junto: devolve o genérico. */
export function rotuloDoProcesso(id) {
  return (typeof id === "string" && PROCESSOS[id]) || PROCESSO_DESCONHECIDO;
}

export function rotuloDoErro(id) {
  return (typeof id === "string" && ERROS[id]) || ERRO_DESCONHECIDO;
}

export function rotuloDaIntervencao(id) {
  return (typeof id === "string" && INTERVENCOES[id]) || null;
}

/** O id do erro em qualquer das formas que as rotas usam: `erro_id`,
 *  `erro_dominante` como string (revisão) ou como objeto (motor). */
export function idDoErro(linha) {
  if (!linha) return null;
  if (typeof linha.erro_id === "string") return linha.erro_id;
  const d = linha.erro_dominante;
  if (typeof d === "string") return d;
  return d?.id || null;
}

/** O rótulo do processo de uma linha qualquer do motor/revisão. */
export function rotuloDaLinha(linha) {
  return rotuloDoProcesso(linha?.processo_id || linha?.processoId);
}
