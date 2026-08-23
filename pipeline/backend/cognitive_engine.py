"""Cognitive pipeline engine — usa a API direta do Google Gemini (google-genai).

Dada a ontologia atualmente ativa e um ou mais arquivos (PDF / imagens),
produz um pipeline cognitivo JSON estrito usando somente IDs da ontologia.

Motor único: Google Gemini via `google-genai` (chave em GEMINI_API_KEY).
Modelo configurável em GEMINI_MODEL (default: gemini-3.1-pro-preview).
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Awaitable, Callable

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

import gemini_cache
import gemini_telemetry

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3-flash-preview"

# Nível de raciocínio ("thinking") usado quando GEMINI_THINKING_LEVEL não está
# definido no ambiente. `gemini-3-flash-preview` vem com thinking ligado por
# padrão em "HIGH"; nenhuma chamada deste pipeline configurava isso antes, o
# que a auditoria econômica de 2026-08-22 apontou como a causa mais provável
# do custo real (~R$28/lote de 89) muito acima do esperado (~R$2/lote) —
# tokens de "thinking" são cobrados como saída ($3,00/1M) e nunca eram
# limitados nem medidos.
#
# MEDIUM foi escolhido por teste controlado (8 questões × 3 níveis, chamadas
# reais) em 2026-08-22 — ver `auditoria/AUDITORIA-OTIMIZACAO-CUSTO-GEMINI.md`:
# reduz o custo projetado por questão em ~52% frente a HIGH, sem nenhuma
# queda de validade estrutural na amostra (0/8 inválidas, igual a HIGH) e com
# risco bem menor de bater no teto observado de ~62.9k tokens de thinking em
# HIGH (1/8 ocorrências em MEDIUM vs 3/8 em HIGH — esse teto também coincidiu
# com chamadas de 223–288s, perto do timeout de 5min do frontend). LOW é
# ainda mais barato (~86%) mas teve 1/8 falha de validação na mesma amostra;
# está disponível via `GEMINI_THINKING_LEVEL=LOW` para quem aceitar esse
# risco extra, mas não é o padrão até uma amostra maior confirmar.
DEFAULT_THINKING_LEVEL = "MEDIUM"

# Nova auditoria de custo (2026-08-22, 2ª rodada — ver
# auditoria/AUDITORIA-OTIMIZACAO-CUSTO-GEMINI-2.md): usando os mesmos dados
# reais já pagos no teste controlado da 1ª rodada (24 chamadas, 8 questões
# sintéticas × 3 níveis), simular por questão "tenta LOW; se a validação
# estrutural reprovar, reexecuta UMA vez em MEDIUM" projetou 8/8 válidas
# (igual a MEDIUM fixo) a ~20% do custo médio de MEDIUM fixo — sem gastar
# nenhuma chamada nova, porque os resultados de LOW e MEDIUM por questão já
# existiam. Ver `run_cognitive_pipeline_adaptive`.
DEFAULT_ADAPTIVE_LOW_LEVEL = "LOW"
DEFAULT_ADAPTIVE_ESCALATED_LEVEL = "MEDIUM"

# Callback opcional chamado com o dict de uso (tokens/duração/erro) de cada
# chamada `generate_content` — nunca com conteúdo de prompt ou PDF.
UsageSink = Callable[[dict[str, Any]], Awaitable[None]]

# Callback síncrono e local (nunca deve chamar o Gemini) que recebe o dict
# cru devolvido pelo modelo e decide se ele está estruturalmente aprovado —
# usado por `run_cognitive_pipeline_adaptive` para decidir se escalona.
JudgeFn = Callable[[dict[str, Any]], bool]


def _thinking_strategy() -> str:
    """`ADAPTIVE` (padrão) ou `FIXED`. Controlável sem editar código via
    `GEMINI_THINKING_STRATEGY`; qualquer valor que não seja exatamente
    `FIXED` é tratado como `ADAPTIVE`, para que um typo no env nunca volte
    silenciosamente ao comportamento caro de nível único sem escalonamento."""
    raw = (os.environ.get("GEMINI_THINKING_STRATEGY") or "ADAPTIVE").strip().upper()
    return "FIXED" if raw == "FIXED" else "ADAPTIVE"


def _get_thinking_level(override: str | None = None) -> "types.ThinkingLevel | None":
    """Resolve o `thinking_level` efetivo de uma chamada.

    Ordem de precedência: `override` (passado explicitamente por quem chama
    — ex.: a escolha do usuário para UM processamento de caderno) > variável
    de ambiente `GEMINI_THINKING_LEVEL` > `DEFAULT_THINKING_LEVEL`. `override`
    nunca toca o ambiente do processo — é só para a chamada corrente, o que é
    o que permite escolher um nível por processamento sem mudar o padrão
    global (e sem risco de condição de corrida entre chamadas concorrentes,
    já que nada é mutado em `os.environ`).

    `None` no resultado final — via valor vazio ou um dos sentinelas
    UNSET/DEFAULT/NONE — significa "não configurar `thinking_config`",
    deixando o modelo usar seu próprio padrão (HIGH, para
    `gemini-3-flash-preview`). Valor inválido é logado e ignorado, nunca
    derruba a chamada.
    """
    raw = (override or os.environ.get("GEMINI_THINKING_LEVEL") or DEFAULT_THINKING_LEVEL or "").strip().upper()
    if not raw or raw in {"UNSET", "DEFAULT", "NONE"}:
        return None
    valid = {"MINIMAL", "LOW", "MEDIUM", "HIGH"}
    if raw not in valid:
        # `types.ThinkingLevel(raw)` NÃO levanta para valor desconhecido (é um
        # enum "aberto" do SDK, que só avisa e aceita) — por isso a validação
        # é explícita aqui, não via try/except.
        logger.warning(
            "GEMINI_THINKING_LEVEL=%r inválido (use MINIMAL/LOW/MEDIUM/HIGH); "
            "ignorando — o modelo usará seu próprio padrão.",
            raw,
        )
        return None
    return types.ThinkingLevel(raw)


class GeminiQuotaExhaustedError(RuntimeError):
    """429 cuja violação é de cota DIÁRIA (`quotaId` contém "PerDay").

    Distinto de um 429 de RPM/TPM: aquele se recupera em segundos e o SDK já
    reitera sozinho (`http_options.retry_options`); este só se recupera na
    virada de cota (meia-noite Pacific Time) ou com upgrade de tier — insistir
    dentro do mesmo processo é desperdício. Quem consome o motor (a fila de
    lote) usa este tipo para parar de tentar em vez de queimar tentativas.
    """

    def __init__(self, quota_id: str | None, retry_delay_seconds: float | None, original: Exception):
        self.quota_id = quota_id
        self.retry_delay_seconds = retry_delay_seconds
        self.original = original
        super().__init__(
            f"Cota diária do Gemini esgotada (quotaId={quota_id!r}). "
            f"Origem: {original}"
        )


def _classify_client_error(exc: genai_errors.ClientError) -> tuple[str, float | None, str | None]:
    """Categoriza um `ClientError` 429 já sobrevivente às tentativas do SDK.

    Lê o corpo padrão do Google (`google.rpc.QuotaFailure` / `RetryInfo`) que
    a própria API devolve — não é um formato inventado aqui. Retorna
    (categoria, retry_delay_seconds, quota_id); categoria é "daily" quando o
    `quotaId` menciona "PerDay", "transient" para qualquer outro 429, "other"
    para o resto (não deveria ocorrer, mas nunca deve estourar o parsing).
    """
    details = getattr(exc, "details", None)
    err = details.get("error", details) if isinstance(details, dict) else {}
    quota_id: str | None = None
    retry_delay: float | None = None
    for entry in (err.get("details") or []) if isinstance(err, dict) else []:
        if not isinstance(entry, dict):
            continue
        entry_type = entry.get("@type", "")
        if "QuotaFailure" in entry_type:
            violations = entry.get("violations") or []
            if violations and isinstance(violations[0], dict):
                quota_id = violations[0].get("quotaId")
        elif "RetryInfo" in entry_type:
            raw = str(entry.get("retryDelay") or "").rstrip("s")
            try:
                retry_delay = float(raw)
            except ValueError:
                pass
    if getattr(exc, "code", None) != 429:
        return "other", retry_delay, quota_id
    if quota_id and "PerDay" in quota_id:
        return "daily", retry_delay, quota_id
    return "transient", retry_delay, quota_id


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY não configurada.")
    # Retry nativo do SDK (tenacity por baixo) para 429/5xx — sem isto,
    # `HttpRetryOptions` ausente faz o cliente desistir na primeira tentativa
    # (é o comportamento padrão do google-genai, não uma omissão nossa).
    # Backoff exponencial com jitter: espera ~initial_delay * exp_base^tentativa,
    # limitada a max_delay, com aleatoriedade para não sincronizar retries.
    retry_options = types.HttpRetryOptions(
        attempts=int(os.environ.get("GEMINI_RETRY_ATTEMPTS", "6")),
        initial_delay=float(os.environ.get("GEMINI_RETRY_INITIAL_DELAY_SECONDS", "2.0")),
        max_delay=float(os.environ.get("GEMINI_RETRY_MAX_DELAY_SECONDS", "60.0")),
        exp_base=2.0,
        jitter=1.0,
        http_status_codes=[429, 500, 503, 504],
    )
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(retry_options=retry_options),
    )


def _get_model() -> str:
    return os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL


_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _mime_for(filename: str, default: str = "application/octet-stream") -> str:
    return _MIME_BY_EXT.get(os.path.splitext(filename)[1].lower(), default)


def _ontology_prompt_slice(ontology: dict[str, Any]) -> str:
    """Serializa o catálogo para o prompt, usando os nomes de campo REAIS.

    Até 2026-08-21 esta função pedia `descricao`, `categoria` e `dominio` —
    campos que não existem em nenhum nó do catálogo v1.4.x. O resultado era um
    prompt em que a definição operacional de cada processo, o mecanismo de cada
    erro e a evidência observável chegavam ao modelo como `null`: ele recebia
    apenas IDs e nomes, e classificava por semelhança de nome, exatamente o que
    o Manual §8 proíbe.
    """
    def compact(items: list[dict], keys: list[str]) -> list[dict]:
        return [{k: it[k] for k in keys if k in it} for it in items]

    payload = {
        "versao": ontology.get("version"),
        "dominios": compact(ontology.get("dominios", []), ["id", "nome", "descricao"]),
        # A competência declara os processos que agrupa; não tem domínio próprio
        # (Constituição §4.4 — o domínio dela é derivado dos processos).
        "competencias": compact(ontology.get("competencias", []),
                                ["id", "nome", "processos"]),
        "processos_cognitivos": compact(ontology.get("processos_cognitivos", []),
                                        ["id", "nome", "definicao_operacional",
                                         "dominios", "competencia", "tipos_erro"]),
        "habilidades_observaveis": compact(ontology.get("habilidades_observaveis", []),
                                           ["id", "nome", "processos_cognitivos"]),
        # `processos_cognitivos` em tipos_erro é a relação de CATÁLOGO: quais
        # processos podem legitimamente produzir este erro. O modelo precisa
        # dela para não emprestar erro de outro processo (Manual §7, regra 4).
        "tipos_erro": compact(ontology.get("tipos_erro", []),
                              ["id", "nome", "processos_cognitivos", "mecanismo",
                               "evidencia_observavel", "intervencao"]),
        "intervencoes_pedagogicas": compact(ontology.get("intervencoes_pedagogicas", []),
                                            ["id", "nome", "tipos_erro"]),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Contrato de saída — Schema Sapiens 2.2
# ---------------------------------------------------------------------------
# Fonte: pipeline/docs/Schema anotador de questoes/06 Schema Sapiens 2.1.json.md
# (o nome do arquivo conserva "2.1" por estabilidade de citação; a versão vive
# no campo `schema_version`, conforme GOV-1.0 §6.1).
#
# Até 2026-08-21 este módulo definia um formato próprio ("Formato A": blocos
# `questao`/`classificacao`/`meta`), que não derivava de nenhum documento
# canônico. Ele foi substituído pelo contrato acima. Diferenças que mudam o
# dado, não apenas o nome do campo:
#
#   * `ontology_version` passa a ser obrigatório (GOV-1.0 §6.1).
#   * `papel` perde o valor "facilitador": um processo que apenas facilita
#     falha o teste de necessidade e NÃO é registrado (Manual §5, última linha).
#   * `distratores[].tipo_erro_id` (um erro por alternativa) vira
#     `erros_esperados[]` — cadeia ORDENADA com confiança obrigatória por elo.
#   * domínios e competências deixam de ser anotados e passam a ser DERIVADOS
#     dos processos (Constituição §4.4); o motor não os produz.
SCHEMA_VERSION = "2.2"

DEFAULT_PIPELINE_SCHEMA: dict[str, Any] = {
    "schema_version": "2.2",
    "ontology_version": "<a versão declarada no bloco ONTOLOGIA, copiada literalmente>",
    "fonte": {
        "banca": "string|null",
        "ano": "inteiro|null",
        "prova": "string|null",
        "numero": "inteiro|null",
        "disciplina": "string|null — METADADO. Proibido inferir Domínio/Processo/Erro a partir dele",
        "tema": "string|null",
        "conteudo": "string|null",
        "arquivo_origem": "string|null",
        "pagina": "inteiro|null",
    },
    "questao": {
        "enunciado": "texto integral e fiel da questão",
        "alternativas": [
            {"letra": "A", "texto": "...", "correta": "true|false|null"},
            {"letra": "B", "texto": "...", "correta": "true|false|null"},
        ],
        "recursos": {
            "imagens": [{"id": "IMG-01", "tipo": "grafico|mapa|diagrama|fotografia|ilustracao|outro",
                         "descricao": "...", "arquivo": "", "ocr": ""}],
            "graficos": [{"id": "GRA-01", "descricao": "variáveis, eixos, legendas, tendências"}],
            "tabelas": [{"id": "TAB-01", "descricao": "estrutura e informações relevantes"}],
            "formulas": [{"id": "FOR-01", "latex": "..."}],
        },
    },
    "estrutura_cognitiva": {
        "processos": [
            {
                "id": "PROC-...",
                "papel": "nuclear|secundario",
                "peso_no_item": "0.7 para nuclear e 0.3 para secundario quando há dois; 1.0 quando há um só",
                "confianca": "alta|media|baixa",
                "habilidades": [
                    {"id": "HAB-...", "peso_no_processo": 1.0,
                     "confianca": "alta|media|baixa", "aproximado": False}
                ],
                "evidencias": {
                    "trechos": ["trecho literal do enunciado ou alternativa"],
                    "figuras": ["IMG-01"],
                },
                "justificativa": "1–2 frases. OBRIGATÓRIA para o processo nuclear",
            }
        ]
    },
    "incerteza": {
        "marcadores": ["candidato-secundario-incerto|aproximado|erro-nao-catalogado-nesta-versao|"
                       "sem-mecanismo-cognitivo-identificavel|ambiguidade-fronteira|"
                       "item-nao-classificavel|tres-ou-mais-processos-necessarios"],
        "detalhe": "texto curto explicando cada marcador registrado",
        "requer_arbitragem": False,
    },
    "distratores": [
        {
            "alternativa": "B",
            "erros_esperados": [
                {
                    "ordem": 1,
                    "erro": "ERR-... | erro-nao-catalogado-nesta-versao | sem-mecanismo-cognitivo-identificavel",
                    "processo_afetado": "PROC-...",
                    "confianca": "alta|media|baixa",
                    "mecanismo": "MEC-01..MEC-13 ou omitido",
                }
            ],
            "plausibilidade": {"valor": "alta|media|baixa"},
            "probabilidade_estimada": None,
            "explicacao": "mecanismo cognitivo que torna a alternativa atraente",
        }
    ],
    "intervencoes": [
        {
            "id": "INT-...",
            "gatilho": {"processo": "PROC-...", "erro": "ERR-... (o elo de ordem 1)"},
            "acao": "descrição da estratégia pedagógica correspondente",
            "prioridade": None,
        }
    ],
    "pedagogia": {
        "estrategia": "estratégia geral e cognitivamente justificável",
        "passos": ["sequência ordenada de operações"],
        "erros_comuns": ["erros previsíveis durante a resolução"],
        "dicas": ["orientações que ajudam sem entregar a resposta"],
        "tempo_estimado_segundos": None,
        "nivel_dificuldade": "facil|medio|dificil|null",
    },
    "qualidade": {
        "confianca_global": "alta|media|baixa",
        "revisado": False,
        "observacoes": "notas do motor sobre limites de leitura. NÃO usar para incerteza",
    },
}


_SYSTEM_PROMPT_TEMPLATE = """Você é o motor de anotação cognitiva do sistema Sapiens.

REGRA ABSOLUTA: sua saída DEVE ser um único objeto JSON válido, sem texto
antes ou depois, sem markdown, sem comentários.

Você recebe:
1. Uma ONTOLOGIA COGNITIVA (única fonte autorizada de IDs).
2. Um ou mais arquivos (PDF, PNG ou JPG) contendo UMA questão de vestibular.

## Ordem obrigatória de decisão (Manual §2)

Cada etapa depende do resultado da anterior. Inverter a ordem produz anotações
que dois avaliadores independentes não conseguem reproduzir.

1. Leia o item por completo — enunciado, TODAS as alternativas e todo recurso
   visual — antes de classificar qualquer coisa.
2. Identifique o Domínio pela OPERAÇÃO MENTAL exigida.
3. Identifique o Processo Cognitivo dominante dentro do Domínio.
4. Só então verifique processos candidatos adicionais.
5. Só então atribua pesos.
6. Só então selecione Habilidades (a Habilidade é definida em função do
   Processo, nunca o contrário).
7. Só então identifique Tipos de Erro — o catálogo de erro é indexado por
   processo.
8. Registre toda incerteza de forma explícita, nunca por omissão.

## Regras de classificação — vinculantes

**Processo dominante (Manual §3).** É aquele cuja ausência tornaria o item
impossível de responder corretamente, mesmo com todos os outros processos
intactos. Teste de substituição de conteúdo: se você trocasse o cenário do item
por um de outra disciplina mantendo a mesma estrutura de raciocínio, o item
continuaria exigindo a mesma operação mental? Se não, provavelmente o item testa
conhecimento de conteúdo, não um Processo desta ontologia.

**NUNCA classifique pela disciplina, pela prova de origem ou por palavra-chave
do enunciado (Manual §8).** A palavra "proporção" no texto não implica
PROC-QUANT-02 se a resposta correta não depender de raciocínio proporcional.
O campo `fonte.disciplina` é metadado de manifestação: é PROIBIDO inferir
Domínio, Processo, Habilidade ou Erro a partir dele.

**Papel e peso (Manual §4 e §5).** Vocabulário FECHADO: `nuclear` ou
`secundario`. Não existe "facilitador": um processo cuja ausência não muda se o
item é respondível falha o teste de necessidade e NÃO deve ser registrado.
- 1 processo → `nuclear`, peso 1.0
- 2 processos → `nuclear` 0.7 e `secundario` 0.3
- Os pesos somam exatamente 1.0.
- **NO MÁXIMO 2 processos.** Se um terceiro genuinamente passar no teste de
  necessidade, registre os 2 de maior valor diagnóstico e acrescente o marcador
  `tres-ou-mais-processos-necessarios` em `incerteza.marcadores`. NUNCA
  distribua pesos entre três.
- O processo `nuclear` exige `justificativa` de 1–2 frases, escrita de forma que
  um segundo anotador, sem acesso ao seu raciocínio, entenda a decisão.

**Habilidades (Manual §6).** Selecione APENAS entre as habilidades catalogadas
sob o processo escolhido — cada habilidade da ontologia declara em
`processos_cognitivos` a que processos pertence. A habilidade precisa
corresponder ao FORMATO DE ESTÍMULO REAL do item: não escolha uma habilidade de
leitura de gráfico se o item não contém gráfico. Se nenhuma corresponder com
exatidão, escolha a mais próxima e marque `"aproximado": true`.

**Tipos de erro (Manual §7).** Para cada alternativa incorreta, pergunte: que
MECANISMO COGNITIVO — não apenas "errou" — explicaria essa escolha?
- Use APENAS tipos de erro que o catálogo vincula ao `processo_afetado`. Cada
  tipo de erro declara em `processos_cognitivos` os processos a que pertence.
  É PROIBIDO emprestar um erro de outro processo por semelhança.
- Se o processo afetado NÃO tem nenhum tipo de erro catalogado, use a sentinela
  `"erro-nao-catalogado-nesta-versao"`.
- Se a alternativa reflete descuido, digitação ou leitura errada do gabarito, e
  não falha cognitiva, use `"sem-mecanismo-cognitivo-identificavel"`.
- As sentinelas são respostas VÁLIDAS e informativas, não falhas suas.

**A cadeia de erro é ORDENADA.** `erros_esperados` é uma lista de 1 a 3 elos com
`ordem` contígua começando em 1. O elo de `ordem: 1` é a RAIZ — a falha que, se
não tivesse ocorrido, tornaria as seguintes improváveis. Os elos seguintes são
decorrentes. Um erro procedimental observado na resposta final pode ter sua raiz
numa leitura deficiente anterior; tratar só a manifestação de superfície torna a
intervenção ineficaz.

**`confianca` é OBRIGATÓRIA em todo elo** (`alta`, `media` ou `baixa`). Nunca
implícita, nunca ausente, nunca "alta" por convenção de preenchimento. Os elos
NÃO são hipóteses concorrentes: são etapas de uma mesma explicação, e suas
confianças não somam 1.

**`mecanismo` é OPCIONAL e só aceita um ID `MEC-01`..`MEC-13`.** Nunca escreva
prosa nesse campo. Se nenhum dos treze couber, OMITA-O — a anotação continua
válida sem ele.

**Intervenções.** Selecione a intervenção a partir do elo de `ordem: 1`, NUNCA
do último elo. Cada tipo de erro do catálogo declara sua `intervencao` prescrita.

**`fonte` (banca, ano, prova, número): copie apenas o que estiver LITERALMENTE
escrito no documento.** Não deduza, não complete pelo que parece plausível e não
use conhecimento prévio sobre provas do ENEM. Se o ano não estiver impresso na
página, use null — um ano errado é pior que um ausente.

**NÃO produza `estrutura_cognitiva.dominios` nem
`estrutura_cognitiva.competencias`.** Eles são DERIVADOS por união a partir dos
processos e calculados depois, fora do modelo. Atribuí-los à parte é proibido
pela Constituição §4.4.

**NUNCA invente ID.** Todo `DOM-`, `COMP-`, `PROC-`, `HAB-`, `ERR-` e `INT-`
deve existir literalmente na ontologia fornecida. Se algo não couber, use lista
vazia ou a sentinela apropriada — nunca um ID novo, nunca um ID parecido.

Formato de saída OBRIGATÓRIO (JSON estrito, siga EXATAMENTE este schema):

{schema_json}

Copie `ontology_version` literalmente do campo `versao` do bloco ONTOLOGIA.
Se um campo não puder ser preenchido com certeza, use null (escalares) ou lista
vazia — exceto os campos declarados obrigatórios acima, que nunca podem ficar
em branco."""


def build_system_prompt(schema: dict[str, Any] | None = None) -> str:
    schema = schema or DEFAULT_PIPELINE_SCHEMA
    schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
    return _SYSTEM_PROMPT_TEMPLATE.replace("{schema_json}", schema_json)


# Backward compatibility — legacy consumers that still import SYSTEM_PROMPT.
SYSTEM_PROMPT = build_system_prompt()


def _extract_json_object(text: str) -> dict:
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    if start == -1:
        raise ValueError("Nenhum JSON encontrado na resposta do modelo.")
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("JSON incompleto na resposta do modelo.")


def _build_parts(files: list[tuple[str, bytes]], user_text: str) -> list:
    parts = []
    for filename, data in files:
        mime = _mime_for(filename)
        parts.append(types.Part.from_bytes(data=data, mime_type=mime))
    parts.append(types.Part.from_text(text=user_text))
    return parts


async def _generate_json(
    system_instruction: str | None,
    user_text: str,
    files: list[tuple[str, bytes]],
    *,
    client: genai.Client | None = None,
    model: str | None = None,
    cached_content: str | None = None,
    on_usage: UsageSink | None = None,
    thinking_level: str | None = None,
) -> dict:
    """Chama `generate_content` e extrai o JSON da resposta.

    Retry de 429/5xx é responsabilidade do `client` (ver `_get_client` —
    `http_options.retry_options`), não deste laço: o SDK já reitera com
    backoff exponencial e jitter antes de deixar a exceção escapar até aqui.
    O que resta fazer aqui é classificar a exceção FINAL, se houver: um 429
    de cota diária vira `GeminiQuotaExhaustedError` (tentar de novo no mesmo
    processo não adianta); qualquer outra coisa apenas propaga.

    `cached_content`, quando presente, substitui `system_instruction`: a API
    do Gemini não aceita as duas coisas na mesma chamada — o conteúdo fixo já
    está no cache, então só o conteúdo novo (`files` + `user_text`) é enviado.

    `on_usage`, quando presente, recebe um dict só de números (tokens de
    entrada/saída/thinking/cache, duração, sucesso) depois de toda chamada —
    inclusive quando ela falha. Nunca recebe `system_instruction`, `user_text`
    nem bytes de arquivo.

    `thinking_level`, quando presente, vale só para ESTA chamada — tem
    precedência sobre `GEMINI_THINKING_LEVEL`/`DEFAULT_THINKING_LEVEL` sem
    tocar nenhum dos dois (ver `_get_thinking_level`).
    """
    client = client or _get_client()
    model = model or _get_model()
    parts = _build_parts(files, user_text)
    resolved_thinking_level = _get_thinking_level(override=thinking_level)
    thinking_label = resolved_thinking_level.value if resolved_thinking_level is not None else "modelo-padrao"
    logger.info(
        "Gemini call · model=%s · files=%d · cached=%s · thinking=%s",
        model, len(files), bool(cached_content), thinking_label,
    )
    config_kwargs: dict[str, Any] = {
        "response_mime_type": "application/json",
        "temperature": 0.2,
    }
    if resolved_thinking_level is not None:
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=resolved_thinking_level)
    if cached_content:
        config_kwargs["cached_content"] = cached_content
    else:
        config_kwargs["system_instruction"] = system_instruction

    start = time.monotonic()
    try:
        resp = await client.aio.models.generate_content(
            model=model,
            contents=parts,
            config=types.GenerateContentConfig(**config_kwargs),
        )
    except genai_errors.ClientError as exc:
        if on_usage is not None:
            duration_ms = (time.monotonic() - start) * 1000
            await on_usage(gemini_telemetry.usage_from_error(
                exc, model=model, cached=bool(cached_content),
                thinking_level=thinking_label, duration_ms=duration_ms,
            ))
        categoria, retry_delay, quota_id = _classify_client_error(exc)
        if categoria == "daily":
            raise GeminiQuotaExhaustedError(quota_id, retry_delay, exc) from exc
        raise
    duration_ms = (time.monotonic() - start) * 1000
    usage = gemini_telemetry.usage_from_response(
        resp, model=model, cached=bool(cached_content),
        thinking_level=thinking_label, duration_ms=duration_ms,
    )
    logger.info(
        "Gemini usage · in=%s cache=%s out=%s thinking=%s total=%s dur=%.0fms",
        usage["prompt_token_count"], usage["cached_content_token_count"],
        usage["candidates_token_count"], usage["thoughts_token_count"],
        usage["total_token_count"], usage["duration_ms"],
    )
    if on_usage is not None:
        await on_usage(usage)
    raw = resp.text or ""
    logger.info("Gemini raw length: %d", len(raw))
    return _extract_json_object(raw)


# ---------------------------------------------------------------------------
# Pipeline cognitivo (uma questão)
# ---------------------------------------------------------------------------
async def run_cognitive_pipeline(
    ontology: dict[str, Any],
    files: list[tuple[str, bytes]],
    session_id: str | None = None,  # kept for backward compatibility
    focus_hint: str | None = None,
    schema: dict[str, Any] | None = None,
    cache_collection: Any = None,
    on_usage: UsageSink | None = None,
    thinking_level: str | None = None,
    book_cache_key: str | None = None,
) -> dict[str, Any]:
    """Roda o motor cognitivo sobre um ou mais arquivos.

    `cache_collection`, se passada (a collection Mongo `gemini_caches`),
    ativa o cache explícito do bloco fixo (prompt de sistema + ontologia):
    ele é criado uma vez por (model, ontology_version, schema_version) e
    reaproveitado por até `GEMINI_CACHE_TTL_SECONDS` (padrão 1h) em todas as
    chamadas seguintes — de qualquer questão, de qualquer caderno — em vez de
    ser reenviado a cada questão. Sem `cache_collection`, o comportamento é
    idêntico ao anterior: tudo inline, em toda chamada.

    `book_cache_key`, quando presente junto com `cache_collection` e
    `files`, estende esse mesmo cache para incluir os PRÓPRIOS `files` (ex.:
    o PDF de 32 páginas de um caderno) — não só a ontologia. Uso pretendido:
    processar N questões do MESMO caderno, uma chamada por questão, todas
    passando o mesmo `book_cache_key` (ex.: o `book_id`). A 1ª chamada sobe
    o PDF uma vez; as seguintes só leem o cache (a ~1/10 do preço de
    reenviar o PDF inteiro) e não reenviam `files` na parte não-cacheada da
    chamada. Chaveado por (model, book_cache_key, ontology_version,
    schema_version) — nunca reaproveitado entre cadernos diferentes, mesmo
    que processados na mesma janela de TTL. Se a criação desse cache
    específico falhar (arquivo grande demais, API sem suporte, etc.), cai
    automaticamente para o cache só-de-ontologia (comportamento anterior) —
    nunca bloqueia a anotação por causa de uma otimização de custo.

    `thinking_level`, quando presente, vale só para esta chamada (ver
    `_get_thinking_level`) — não altera `GEMINI_THINKING_LEVEL` nem o padrão
    global, então processamentos concorrentes com níveis diferentes não
    interferem entre si.
    """
    ontology_text = _ontology_prompt_slice(ontology)
    system_instruction = build_system_prompt(schema)

    client = _get_client()
    model = _get_model()
    cached_content: str | None = None
    key: str | None = None
    files_for_call = files
    if cache_collection is not None:
        ontology_version = str(ontology.get("version") or "sem-versao")
        schema_version = str((schema or DEFAULT_PIPELINE_SCHEMA).get("schema_version") or "sem-versao")
        ttl_seconds = int(os.environ.get("GEMINI_CACHE_TTL_SECONDS", str(gemini_cache.DEFAULT_TTL_SECONDS)))

        if book_cache_key and files:
            book_key = gemini_cache.cache_key(model, "caderno", book_cache_key, ontology_version, schema_version)
            book_parts = [types.Part.from_text(text=ontology_text)] + [
                types.Part.from_bytes(data=data, mime_type=_mime_for(name)) for name, data in files
            ]
            book_cached_content = await gemini_cache.get_or_create_cached_content(
                client,
                cache_collection,
                model=model,
                key=book_key,
                system_instruction=system_instruction,
                contents=book_parts,
                display_name=f"sapiens-caderno-{book_cache_key}-{ontology_version}",
                ttl_seconds=ttl_seconds,
            )
            if book_cached_content:
                cached_content = book_cached_content
                key = book_key
                # O PDF já está no cache — reenviá-lo aqui pagaria 2x pelo
                # mesmo conteúdo (tokens de entrada normais + leitura de cache).
                files_for_call = []

        if not cached_content:
            key = gemini_cache.cache_key(model, "ontologia", ontology_version, schema_version)
            cached_content = await gemini_cache.get_or_create_cached_content(
                client,
                cache_collection,
                model=model,
                key=key,
                system_instruction=system_instruction,
                contents=[types.Part.from_text(text=ontology_text)],
                display_name=f"sapiens-ontologia-{ontology_version}-schema-{schema_version}",
                ttl_seconds=ttl_seconds,
            )

    if cached_content:
        # A ontologia já está no cache — o texto dela NÃO é reenviado.
        user_text = ""
    else:
        user_text = (
            "ONTOLOGIA COGNITIVA (única fonte autorizada, use apenas estes IDs):\n\n"
            f"{ontology_text}\n\n"
        )
    if focus_hint:
        user_text += (
            "FOCO OBRIGATÓRIO: os arquivos anexados podem conter várias questões. "
            f"Extraia e classifique APENAS a seguinte questão: {focus_hint}. "
            "Ignore todas as demais questões do documento. Se figuras, tabelas ou "
            "gráficos pertencerem a esta questão específica, inclua-os na análise "
            "multimodal.\n\n"
        )
    user_text += (
        "Analise os arquivos anexados (podem conter uma ou mais questões, suas "
        "figuras, gráficos, infográficos e alternativas). Produza o JSON conforme "
        "especificado no system message."
    )
    try:
        return await _generate_json(
            None if cached_content else system_instruction,
            user_text,
            files_for_call,
            client=client,
            model=model,
            cached_content=cached_content,
            on_usage=on_usage,
            thinking_level=thinking_level,
        )
    except genai_errors.ClientError as exc:
        # cachedContents pode expirar do lado do servidor antes do TTL local
        # (ex.: apagado manualmente, ou relógio divergente). NOT_FOUND aqui
        # significa "o cache que eu acho válido já não existe" — invalida o
        # registro local e refaz a MESMA chamada uma vez, sem cache, em vez
        # de derrubar a anotação por causa de uma otimização.
        if cached_content and getattr(exc, "code", None) == 404 and cache_collection is not None:
            logger.warning("Gemini cache: %s não encontrado na API, invalidando e refazendo sem cache", cached_content)
            await gemini_cache.invalidate(cache_collection, key)
            fallback_text = (
                "ONTOLOGIA COGNITIVA (única fonte autorizada, use apenas estes IDs):\n\n"
                f"{ontology_text}\n\n"
            ) + user_text
            return await _generate_json(
                system_instruction, fallback_text, files, client=client, model=model,
                on_usage=on_usage, thinking_level=thinking_level,
            )
        raise


async def run_cognitive_pipeline_adaptive(
    ontology: dict[str, Any],
    files: list[tuple[str, bytes]],
    *,
    judge: JudgeFn,
    session_id: str | None = None,
    focus_hint: str | None = None,
    schema: dict[str, Any] | None = None,
    cache_collection: Any = None,
    on_usage: UsageSink | None = None,
    thinking_level: str | None = None,
    book_cache_key: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """`run_cognitive_pipeline` com escalonamento adaptativo de `thinking`.

    Estratégia (padrão, `GEMINI_THINKING_STRATEGY=ADAPTIVE`): 1ª tentativa em
    `GEMINI_THINKING_LEVEL_LOW` (padrão `LOW`, o nível mais barato); `judge`
    decide se a saída está estruturalmente aprovada; se não estiver, UMA
    única reexecução em `GEMINI_THINKING_LEVEL_ESCALATED` (padrão `MEDIUM`).
    Nunca mais que 2 chamadas ao Gemini por questão — não existe uma 3ª
    tentativa nesta função, de propósito, para que uma questão difícil nunca
    vire um laço caro.

    Dois jeitos de desligar isso, sem editar código:
    - `thinking_level` explícito (ex.: o seletor LOW/MEDIUM/HIGH da tela do
      caderno) sempre desliga o modo adaptativo PARA AQUELA CHAMADA —
      escolha humana explícita nunca é sobrescrita por uma heurística de
      custo. Vira uma chamada só, no nível pedido, igual a chamar
      `run_cognitive_pipeline` direto.
    - `GEMINI_THINKING_STRATEGY=FIXED` desliga globalmente — mesmo
      comportamento de antes desta função existir (1 chamada, no nível de
      `GEMINI_THINKING_LEVEL`/`DEFAULT_THINKING_LEVEL`).

    `judge(raw)` deve ser síncrono, local e barato — tipicamente
    `item_contract.normalize_item` + `item_contract.validate`, o mesmo
    validador estrutural de produção. NUNCA deve chamar o Gemini de novo, o
    que duplicaria custo por engano; se `judge` levantar exceção, o resultado
    da 1ª tentativa é aceito sem escalonar (uma falha no validador não pode
    silenciosamente dobrar o custo de toda chamada seguinte).

    Retorna `(raw, meta)`. `raw` é o dict cru de UMA das tentativas (a
    última). `meta` é só para telemetria/log — nunca deve ser persistido
    dentro do item — no formato `{"attempts": [níveis tentados, em ordem],
    "escalated": bool}`.
    """
    if thinking_level or _thinking_strategy() != "ADAPTIVE":
        raw = await run_cognitive_pipeline(
            ontology, files, session_id=session_id, focus_hint=focus_hint, schema=schema,
            cache_collection=cache_collection, on_usage=on_usage, thinking_level=thinking_level,
            book_cache_key=book_cache_key,
        )
        return raw, {"attempts": [thinking_level or "default"], "escalated": False}

    low_level = (os.environ.get("GEMINI_THINKING_LEVEL_LOW") or DEFAULT_ADAPTIVE_LOW_LEVEL).strip().upper()
    raw = await run_cognitive_pipeline(
        ontology, files, session_id=session_id, focus_hint=focus_hint, schema=schema,
        cache_collection=cache_collection, on_usage=on_usage, thinking_level=low_level,
        book_cache_key=book_cache_key,
    )
    try:
        aprovado = bool(judge(raw))
    except Exception:  # noqa: BLE001 — judge quebrado nunca pode dobrar custo por engano
        logger.exception(
            "Gemini adaptive: judge() levantou exceção avaliando a saída em %s; "
            "mantendo o resultado sem escalonar",
            low_level,
        )
        aprovado = True
    if aprovado:
        return raw, {"attempts": [low_level], "escalated": False}

    escalated_level = (
        os.environ.get("GEMINI_THINKING_LEVEL_ESCALATED") or DEFAULT_ADAPTIVE_ESCALATED_LEVEL
    ).strip().upper()
    logger.info(
        "Gemini adaptive: saída em thinking=%s reprovada por judge(); reescalando para %s",
        low_level, escalated_level,
    )
    raw = await run_cognitive_pipeline(
        ontology, files, session_id=session_id, focus_hint=focus_hint, schema=schema,
        cache_collection=cache_collection, on_usage=on_usage, thinking_level=escalated_level,
        book_cache_key=book_cache_key,
    )
    return raw, {"attempts": [low_level, escalated_level], "escalated": True}


# ---------------------------------------------------------------------------
# Manifesto do caderno
# ---------------------------------------------------------------------------
MANIFEST_PROMPT = """Você é um enumerador de cadernos de vestibular.

O usuário anexa um PDF (e opcionalmente imagens) contendo múltiplas questões
de uma prova. Sua tarefa é IDENTIFICAR cada questão distinta no documento
e devolver um manifesto JSON, sem processá-las cognitivamente.

FORMATO OBRIGATÓRIO:

{
  "questoes": [
    {
      "numero": "1",
      "titulo": "resumo do enunciado, ≤ 90 chars",
      "paginas": [3, 4],
      "disciplina": "estimativa da disciplina ou null",
      "tem_figura": true
    }
  ]
}

REGRAS:
- Saída DEVE ser um único JSON válido, sem markdown, sem texto ao redor.
- Preserve a numeração original da prova. Se não houver, use 1, 2, 3...
- Se o PDF não contém questões, devolva {"questoes": []}.
- NÃO extraia enunciado completo aqui — apenas o índice."""


async def run_book_manifest(files: list[tuple[str, bytes]]) -> list[dict]:
    user_text = "Enumere todas as questões distintas do caderno anexado."
    parsed = await _generate_json(MANIFEST_PROMPT, user_text, files)
    questoes = parsed.get("questoes", []) or []
    clean: list[dict] = []
    for q in questoes:
        if not isinstance(q, dict):
            continue
        clean.append(
            {
                "numero": str(q.get("numero") or q.get("number") or ""),
                "titulo": q.get("titulo") or q.get("title") or "",
                "paginas": q.get("paginas") or q.get("pages") or [],
                "disciplina": q.get("disciplina") or q.get("discipline"),
                "tem_figura": bool(q.get("tem_figura") or q.get("has_figure")),
            }
        )
    return clean


# ---------------------------------------------------------------------------
# Parser de ontologia (PDF/DOCX/MD/TXT)
# ---------------------------------------------------------------------------
ONTOLOGY_PARSE_PROMPT = """Você é um extrator de ontologias cognitivas.

O usuário anexa um documento (PDF/DOCX/MD/TXT) contendo a descrição de uma
ontologia cognitiva para anotação de questões de vestibular. Sua tarefa é
converter o conteúdo em UM ÚNICO JSON no schema abaixo.

REGRAS:
- Saída DEVE ser um único objeto JSON válido, sem texto antes ou depois,
  sem markdown, sem comentários.
- NUNCA invente elementos. Se algo não estiver no documento, deixe a lista vazia.
- Preserve os IDs exatamente como aparecem no documento (ex: DOM-QUANT, COMP-01,
  PROC-05, ERR-03, INT-02). Se o documento não fornecer IDs explícitos, gere IDs
  sequenciais no padrão: DOM-01, COMP-01, PROC-01, ERR-01, INT-01.
- Se o documento contiver descrição de "pipeline padrão" ou instruções que não
  sejam elementos ontológicos, ignore-as (esta rotina extrai apenas a ontologia).

SCHEMA (obrigatório):
{
  "version": "string extraído do documento ou 'imported-<timestamp>'",
  "name": "nome da ontologia (ou vazio)",
  "description": "descrição curta (ou vazio)",
  "dominios": [
    {"id":"DOM-...", "nome":"...", "descricao":"..."}
  ],
  "competencias": [
    {"id":"COMP-...", "nome":"...", "dominio":"DOM-... ou vazio",
     "descricao":"..."}
  ],
  "processos_cognitivos": [
    {"id":"PROC-...", "nome":"...", "categoria":"opcional",
     "descricao":"..."}
  ],
  "habilidades_observaveis": [
    {"id":"HAB-...", "nome":"...", "processos_cognitivos":["PROC-..."],
     "descricao":"opcional"}
  ],
  "tipos_erro": [
    {"id":"ERR-...", "nome":"...", "descricao":"..."}
  ],
  "intervencoes_pedagogicas": [
    {"id":"INT-...", "nome":"...", "descricao":"..."}
  ]
}
"""


async def parse_ontology_with_gemini(
    filename: str, data: bytes, mime_type: str
) -> dict[str, Any]:
    user_text = (
        "Extraia a ontologia do arquivo anexado e devolva o JSON no schema "
        "especificado no system message."
    )
    parsed = await _generate_json(ONTOLOGY_PARSE_PROMPT, user_text, [(filename, data)])
    for key in (
        "dominios",
        "competencias",
        "processos_cognitivos",
        "habilidades_observaveis",
        "tipos_erro",
        "intervencoes_pedagogicas",
    ):
        parsed.setdefault(key, [])
    return parsed
