"""Validação dos contratos canônicos contra a Ontologia Cognitiva Sapiens.

Fonte de catálogo: `pipeline/docs/ontology/ontology_v1.4.json` (versão **1.4.1**).

Contratos validados aqui:

* **Schema Sapiens 2.2** — `validate_item_annotation` (item anotado; nível
  CATÁLOGO aplicado ao item).
* **Especificação do Error Trace v1.0** — `validate_error_trace` (explicação
  diagnóstica de UMA resposta de UM estudante; nível INSTÂNCIA).

A distinção entre os dois é exigida pela Constituição §4.3 e **não pode ser
colapsada**: o catálogo é a fonte da possibilidade, o traço é a fonte da
ocorrência. Um Error Trace nunca é armazenado dentro do item.

Este módulo NÃO cria regra. Cada verificação abaixo cita a cláusula que a
autoriza; onde o corpus não define escala ou vocabulário, o campo é aceito sem
validação de valor e isso está registrado em comentário — nunca preenchido por
suposição.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ONTOLOGY_PATH = Path(__file__).resolve().parent.parent / "docs/ontology/ontology_v1.4.json"

_ID_KEYS = {
    "dominios": "DOM",
    "competencias": "COMP",
    "processos_cognitivos": "PROC",
    "habilidades_observaveis": "HAB",
    "tipos_erro": "ERR",
    "intervencoes_pedagogicas": "INT",
}

# Especificação do Error Trace §3, R-2 — sentinelas são valores de PRIMEIRA
# CLASSE, não ausência de dado. Um elo com sentinela é válido e informativo.
SENTINELAS_ERRO = frozenset({
    "erro-nao-catalogado-nesta-versao",
    "sem-mecanismo-cognitivo-identificavel",
})

# Schema 2.2, bloco `incerteza` / Manual §13 — vocabulário fechado, idêntico
# nos dois documentos.
MARCADORES_INCERTEZA = frozenset({
    "candidato-secundario-incerto",
    "aproximado",
    "erro-nao-catalogado-nesta-versao",
    "sem-mecanismo-cognitivo-identificavel",
    "ambiguidade-fronteira",
    "item-nao-classificavel",
    "tres-ou-mais-processos-necessarios",
})

# Error Trace §7 / Schema 2.2 — vocabulário reconciliado. "Central" e
# "Secundário Necessário" eram prosa do Manual; o rótulo mudou, a semântica não.
PAPEIS = ("nuclear", "secundario")

# Manual §5 — convenção provisória de bins categóricos, não modelo matemático.
PESO_NUCLEAR = 0.7
PESO_SECUNDARIO = 0.3

# Error Trace §5 — bins categóricos de confiança. Os VALORES são [DE, provisório]
# e calibráveis pelo piloto; a FORMA (declarada, obrigatória, não determinística)
# não é.
CONFIANCA_BINS = {"alta": 0.7, "media": 0.4, "baixa": 0.15}

# Error Trace §3, R-4 — profundidade máxima da cadeia. [DE, provisório].
MAX_ELOS = 3

# Manual §4 — limite obrigatório de processos com peso nesta versão.
MAX_PROCESSOS_COM_PESO = 2

# Error Trace §4.3 — vocabulário provisório, prefixo MEC-, sem colisão com
# nenhuma geração de identificador do corpus.
MECANISMOS = frozenset(f"MEC-{i:02d}" for i in range(1, 14))

_TOLERANCIA_PESO = 1e-6


class OntologyRegistry:
    """Carrega e indexa o catálogo canônico. Fonte única de IDs válidos."""

    def __init__(self, path: Path | str = ONTOLOGY_PATH):
        self.path = Path(path)
        with self.path.open(encoding="utf-8") as f:
            self._index(json.load(f))

    @classmethod
    def from_dict(cls, ontology: dict[str, Any]) -> "OntologyRegistry":
        """Indexa um catálogo já em memória (ex.: a ontologia ATIVA no banco).

        Necessário porque uma ontologia importada via `/ontology/import` pode
        não ser a canônica do repositório: validar a anotação contra o catálogo
        errado produziria erros fantasma.
        """
        reg = cls.__new__(cls)
        reg.path = None
        reg._index(ontology)
        return reg

    def _index(self, ontology: dict[str, Any]) -> None:
        self.data: dict[str, Any] = ontology
        self.version: str = self.data.get("version", "?")
        self._by_key: dict[str, dict[str, dict]] = {}
        for key in _ID_KEYS:
            items = self.data.get(key, []) or []
            self._by_key[key] = {it["id"]: it for it in items if isinstance(it, dict) and "id" in it}

        # Cross-index processo -> tipos_erro catalogados PARA ele.
        # Constituição §4.3: relação de catálogo, definida em tempo de
        # construção da ontologia, nunca em tempo de anotação.
        self.err_by_proc: dict[str, set[str]] = {}
        for err in self._by_key.get("tipos_erro", {}).values():
            for proc_id in err.get("processos_cognitivos", []) or []:
                self.err_by_proc.setdefault(proc_id, set()).add(err["id"])

    # ---- IDs válidos ---------------------------------------------------
    def ids(self, key: str) -> set[str]:
        return set(self._by_key.get(key, {}).keys())

    @property
    def dominios(self) -> set[str]: return self.ids("dominios")

    @property
    def competencias(self) -> set[str]: return self.ids("competencias")

    @property
    def processos(self) -> set[str]: return self.ids("processos_cognitivos")

    @property
    def habilidades(self) -> set[str]: return self.ids("habilidades_observaveis")

    @property
    def tipos_erro(self) -> set[str]: return self.ids("tipos_erro")

    @property
    def intervencoes(self) -> set[str]: return self.ids("intervencoes_pedagogicas")

    def get(self, key: str, _id: str) -> dict | None:
        return self._by_key.get(key, {}).get(_id)

    # ---- Derivação (Constituição §4.4) ---------------------------------
    def dominios_de(self, processo_id: str) -> list[str]:
        return list((self.get("processos_cognitivos", processo_id) or {}).get("dominios") or [])

    def competencia_de(self, processo_id: str) -> str | None:
        return (self.get("processos_cognitivos", processo_id) or {}).get("competencia")

    def habilidades_de(self, processo_id: str) -> set[str]:
        return {
            h["id"]
            for h in self._by_key.get("habilidades_observaveis", {}).values()
            if processo_id in (h.get("processos_cognitivos") or [])
        }

    def processos_sem_tipo_erro(self) -> set[str]:
        """Os 13 de 25 processos sem Tipo de Erro catalogado na v1.4.1.

        Para eles, o Manual §7 regra 4 obriga a sentinela
        `erro-nao-catalogado-nesta-versao` — nunca emprestar um erro de outro
        processo por semelhança.
        """
        return {
            p["id"]
            for p in self._by_key.get("processos_cognitivos", {}).values()
            if not (p.get("tipos_erro") or [])
        }


# Constituição §4.5 — as relações Processo↔Domínio e Processo↔Competência são
# de **classificação/organização**, não diagnósticas: "peso é opcional e
# reservado a refinamento futuro (ex.: centralidade), nunca obrigatório, porque
# a função destas relações é navegação e agrupamento, não evidência".
#
# O Schema 2.2 permite os campos `peso_no_item` e `confianca` nos blocos
# derivados, e eles são úteis para ordenar e filtrar. Mas emiti-los como números
# nus faria um consumidor tomá-los por quantidades evidenciais — que é
# exatamente o que a Constituição nega. Por isso cada bloco derivado carrega o
# estatuto declarado abaixo, em vez de depender de o consumidor conhecer §4.5.
ESTATUTO_DERIVADO = {
    "natureza": "classificacao_organizacao",
    "evidencial": False,
    "autoridade": "Constituicao §4.5",
    "nota": (
        "Peso e confianca deste bloco sao de NAVEGACAO E AGRUPAMENTO, nunca de "
        "evidencia. Nao alimentam a camada de crenca sobre o estado de um "
        "estudante. A unica relacao ponderada com valor diagnostico neste "
        "contrato e 'distratores[].erros_esperados[].confianca'."
    ),
    "metodo_confianca": "media_dos_processos_sustentadores",
    "metodo_confianca_provisorio": True,
    "metodo_confianca_motivo": (
        "O Schema 2.2 diz 'confianca herdada dos processos' e NAO define a funcao "
        "de heranca. Nenhum documento de camada C1/C2/C3 a define: o White Paper "
        "2.0.1 §4.2 registra que o Axioma da Crenca Calibrada 'nao exige nenhuma "
        "familia matematica especifica'. A media e decisao de engenharia deste "
        "pipeline, declarada sob GOV-1.0 §6.4 em vez de inserida silenciosamente, "
        "e substituivel sem alteracao de contrato."
    ),
}


def derivar_estrutura(
    processos: list[dict], registry: OntologyRegistry
) -> tuple[list[dict], list[dict]]:
    """Deriva `dominios[]` e `competencias[]` por UNIÃO a partir dos processos.

    Constituição §4.4 proíbe atribuição direta de Domínio a Competência e a
    Habilidade; Schema 2.2 declara que os dois blocos existem para tornar a
    derivação legível e auditável, **nunca** para permitir atribuição divergente
    da dos processos. Por isso não há caminho no código que os anote à parte:
    esta função é a única origem deles.

    Os pesos e confianças produzidos aqui são **não-evidenciais** (§4.5) e
    carregam essa declaração em `_estatuto`.
    """
    dom_peso: dict[str, float] = {}
    dom_conf: dict[str, list[float]] = {}
    dom_origem: dict[str, list[str]] = {}
    comp_peso: dict[str, float] = {}
    comp_conf: dict[str, list[float]] = {}
    comp_origem: dict[str, list[str]] = {}

    for p in processos or []:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        if not pid:
            continue
        peso = _as_float(p.get("peso_no_item"), default=0.0)
        conf = _as_float(p.get("confianca"), default=None)

        for did in registry.dominios_de(pid):
            dom_peso[did] = dom_peso.get(did, 0.0) + peso
            dom_origem.setdefault(did, []).append(pid)
            if conf is not None:
                dom_conf.setdefault(did, []).append(conf)

        cid = registry.competencia_de(pid)
        if cid:
            comp_peso[cid] = comp_peso.get(cid, 0.0) + peso
            comp_origem.setdefault(cid, []).append(pid)
            if conf is not None:
                comp_conf.setdefault(cid, []).append(conf)

    def _mk(pesos, confs, origens):
        out = []
        for _id in sorted(pesos):
            cs = confs.get(_id) or []
            out.append({
                "id": _id,
                "derivado_de": origens[_id],
                "peso_no_item": round(pesos[_id], 6),
                "confianca": round(sum(cs) / len(cs), 6) if cs else None,
                "_estatuto": ESTATUTO_DERIVADO,
            })
        return out

    return _mk(dom_peso, dom_conf, dom_origem), _mk(comp_peso, comp_conf, comp_origem)


def _as_float(v: Any, default: float | None = None) -> float | None:
    if isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        # Aceita o rótulo do bin além do número (Error Trace §5).
        if v in CONFIANCA_BINS:
            return CONFIANCA_BINS[v]
        try:
            return float(v)
        except ValueError:
            return default
    return default


# ---- Resultado -----------------------------------------------------------
@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def err(self, msg: str) -> None:
        self.valid = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {"valid": self.valid, "errors": self.errors, "warnings": self.warnings}


def _check_id(res: ValidationResult, label: str, value: Any, valid: set[str]) -> bool:
    if not isinstance(value, str):
        res.err(f"{label}: esperado string, recebeu {type(value).__name__}")
        return False
    if value not in valid:
        res.err(f"{label}: id '{value}' não existe na ontologia")
        return False
    return True


def _check_ontology_version(res: ValidationResult, obj: dict, reg: OntologyRegistry) -> None:
    """GOV-1.0 §6.1 — nenhum artefato pode referir-se a 'a ontologia vigente'."""
    ov = obj.get("ontology_version")
    if not ov:
        res.err(
            "ontology_version: OBRIGATÓRIO e ausente (GOV-1.0 §6.1). Sem ele o "
            "objeto é indatável e não pode ser remapeado numa mudança MAIOR."
        )
    elif ov != reg.version:
        res.warn(
            f"ontology_version='{ov}' difere do catálogo carregado "
            f"('{reg.version}'): os IDs deste objeto não foram resolvidos contra "
            "este catálogo e exigem remapeamento explícito antes de serem lidos."
        )


# ---- Schema Sapiens 2.2 --------------------------------------------------
def validate_item_annotation(item: dict, registry: OntologyRegistry | None = None) -> ValidationResult:
    """Valida um item anotado contra o **Schema Sapiens 2.2**."""
    reg = registry or OntologyRegistry()
    res = ValidationResult()

    if not isinstance(item, dict):
        res.err("item deve ser um objeto/dict")
        return res

    if item.get("schema_version") != "2.2":
        res.warn(f"schema_version='{item.get('schema_version')}' — esperado '2.2'")
    _check_ontology_version(res, item, reg)

    for f in ("item_id", "item_hash"):
        if not item.get(f):
            res.err(f"campo obrigatório ausente ou vazio: '{f}'")

    ec = item.get("estrutura_cognitiva") or {}
    procs = ec.get("processos") or []
    if not isinstance(procs, list) or not procs:
        res.err("estrutura_cognitiva.processos: pelo menos 1 processo é exigido")
        return res

    # Manual §4 — no máximo 2 processos COM PESO. Um terceiro candidato genuíno
    # vira registro de ambiguidade, nunca uma terceira entrada com peso.
    com_peso = [p for p in procs if isinstance(p, dict) and _as_float(p.get("peso_no_item")) not in (None, 0.0)]
    if len(com_peso) > MAX_PROCESSOS_COM_PESO:
        res.err(
            f"estrutura_cognitiva.processos: {len(com_peso)} processos com peso; "
            f"o máximo é {MAX_PROCESSOS_COM_PESO} (Manual §4). Um terceiro processo "
            "que passe o teste de necessidade obriga a registrar o item como "
            "ambiguidade em 'incerteza.marcadores', nunca a distribuir pesos entre três."
        )

    vistos: set[str] = set()
    nucleares = 0
    total_peso = 0.0
    for i, p in enumerate(procs):
        pref = f"estrutura_cognitiva.processos[{i}]"
        if not isinstance(p, dict):
            res.err(f"{pref}: objeto esperado")
            continue
        pid = p.get("id")
        if not _check_id(res, f"{pref}.id", pid, reg.processos):
            continue
        if pid in vistos:
            res.err(f"{pref}.id: processo '{pid}' repetido")
        vistos.add(pid)

        papel = p.get("papel")
        if papel not in PAPEIS:
            res.err(
                f"{pref}.papel: '{papel}' fora do vocabulário fechado {PAPEIS} "
                "(Error Trace §7; Schema 2.2). 'Central'/'Secundário Necessário' "
                "eram prosa do Manual e foram reconciliados."
            )
        if papel == "nuclear":
            nucleares += 1
            if not (p.get("justificativa") or "").strip():
                res.err(
                    f"{pref}.justificativa: obrigatória para o processo 'nuclear' "
                    "(Manual §12, regra 4) — 1–2 frases reproduzíveis por um "
                    "segundo anotador."
                )

        peso = _as_float(p.get("peso_no_item"))
        if peso is None:
            res.err(f"{pref}.peso_no_item: ausente ou não numérico")
        else:
            total_peso += peso
            esperado = None
            if len(procs) == 1:
                esperado = 1.0
            elif papel == "nuclear":
                esperado = PESO_NUCLEAR
            elif papel == "secundario":
                esperado = PESO_SECUNDARIO
            if esperado is not None and abs(peso - esperado) > 1e-3:
                res.err(
                    f"{pref}.peso_no_item={peso} diverge da convenção do Manual §5 "
                    f"(esperado {esperado} para papel '{papel}' com {len(procs)} processo(s))"
                )

        # Manual §6, regra 1 — a Habilidade pertence ao catálogo do processo-pai.
        for j, h in enumerate(p.get("habilidades") or []):
            hpref = f"{pref}.habilidades[{j}]"
            if not isinstance(h, dict):
                res.err(f"{hpref}: objeto esperado")
                continue
            hid = h.get("id")
            if not _check_id(res, f"{hpref}.id", hid, reg.habilidades):
                continue
            if hid not in reg.habilidades_de(pid):
                res.err(
                    f"{hpref}.id: '{hid}' não é catalogada sob '{pid}' "
                    "(Manual §6, regra 1)"
                )

    if nucleares != 1:
        res.err(
            f"estrutura_cognitiva.processos: exatamente 1 processo 'nuclear' esperado "
            f"(achados: {nucleares})"
        )
    if abs(total_peso - 1.0) > 1e-3:
        res.err(f"pesos dos processos devem somar 1.0 (atual: {total_peso:.6f}) — Manual §5")

    # Domínios e competências são DERIVADOS (Constituição §4.4). Divergência
    # contra a união dos processos é erro de integridade, não alternativa.
    doms_esp, comps_esp = derivar_estrutura(procs, reg)
    _check_derivado(res, "dominios", ec.get("dominios"), doms_esp)
    _check_derivado(res, "competencias", ec.get("competencias"), comps_esp)

    _validate_distratores(res, item, reg, vistos)
    _validate_intervencoes(res, item, reg)
    _validate_incerteza(res, item)

    _validate_estrutura_questao(res, item)
    _validate_portao_crenca(res, item)

    return res


# ---- Portão da camada de crença -----------------------------------------
def _validate_portao_crenca(res: ValidationResult, item: dict) -> None:
    """A regra anterior comparava `apto` com `revisado` — e `apto` era DERIVADO
    de `revisado` uma linha antes, em `normalize_item`. A condição era
    logicamente inalcançável: nunca disparou e nunca poderia disparar, enquanto
    223 itens circulavam com o portão aberto pelo próprio modelo.

    O que sustenta o portão agora é um registro EXTERNO ao item
    (`revisao_humana.COLECAO`), amarrado ao `item_hash` revisado. Este validador
    não tem acesso ao banco, então verifica o que dá para verificar sem ele: a
    presença do vínculo. A conferência contra o registro é feita por
    `revisao_humana.itens_com_revisado_sem_registro` e pelo auditor (GOV-01).
    """
    q = item.get("qualidade") or {}
    apto = q.get("apto_para_camada_de_crenca") or {}
    valor = apto.get("valor") if isinstance(apto, dict) else apto

    if valor is True and not q.get("revisado"):
        res.err(
            "qualidade.apto_para_camada_de_crenca=true sem qualidade.revisado=true "
            "(EXT-WP1-1.0 L13b; Error Trace §6)."
        )

    if q.get("revisado") is True and not isinstance(q.get("revisao"), dict):
        res.err(
            "GOV-01 qualidade.revisado=true sem `qualidade.revisao` "
            "{revisor, revisado_em, item_hash}. Um item não atesta a própria "
            "revisão: o vínculo com o registro humano é obrigatório "
            "(EXT-WP1-1.0 L13b)."
        )

    # EST/ARQ são WARNINGS: EXT-WP1-1.0 L13 permite ARMAZENAR item imperfeito.
    # O que eles bloqueiam é o portão — e é aqui que isso vira efeito.
    achados_bloqueantes = [
        m for m in (res.errors + res.warnings)
        if m.startswith(("EST-", "ARQ-", "GAB-"))
    ]
    if valor is True and achados_bloqueantes:
        res.err(
            f"GOV-02 apto_para_camada_de_crenca=true com {len(achados_bloqueantes)} "
            "achado(s) estrutural(is) aberto(s). Um item que o aluno não consegue "
            "responder corretamente não pode alimentar crença sobre ele."
        )


# ---- Estrutura do bloco `questao` ---------------------------------------
_RE_BLOB = re.compile(r"^[0-9a-f]{64}\.(png|webp|jpg|jpeg)$")
_RE_PLACEHOLDER = re.compile(
    r"\[(Gráfico|Grafico|Tabela|Figura|Imagem|Quadro|Ilustra|Esquema|Diagrama|"
    r"Mapa|Foto|Charge|Tirinha|Texto)[^\]]{0,160}\]",
    re.IGNORECASE,
)


def _validate_estrutura_questao(res: ValidationResult, item: dict) -> None:
    """EST-01..05 e ARQ-01 — o bloco `questao` não era validado por nada.

    O validador cobria ontologia, processos, cadeia de erro, distratores e
    intervenções, e nunca abria `questao`. Resultado medido na auditoria de
    2026-08-26: 2 enunciados vazios, 18 alternativas sem texto, 26 placeholders
    fabricados e 16 nomes de arquivo inventados atravessaram até o aluno.

    Registrado sempre, nunca bloqueia o ARMAZENAMENTO (EXT-WP1-1.0 L13 permite
    guardar item imperfeito). O que estes achados bloqueiam é o portão da
    camada de crença e a circulação — ver `_validate_portao_crenca`.
    """
    questao = item.get("questao") or {}

    if not (questao.get("enunciado") or "").strip():
        res.warn("EST-01 questao.enunciado vazio")

    alternativas = questao.get("alternativas") or []
    if len(alternativas) < 2:
        res.warn(f"EST-04 questao.alternativas: {len(alternativas)} — item sem escolha real")

    letras = [a.get("letra") for a in alternativas if isinstance(a, dict)]
    if len(set(letras)) != len(letras) or any(not l for l in letras):
        res.warn(f"EST-03 questao.alternativas: letras {letras} não são únicas e não vazias")

    # A regra "exatamente 5, A–E" NÃO mora aqui, e o teste
    # `test_item_bem_formado_e_valido` é quem deixou isso claro: o Schema 2.2
    # não fixa a quantidade de alternativas, e um item canônico de 3 é válido.
    # Cinco alternativas A–E é característica do ENEM, não do contrato — a
    # checagem vive em `pipeline/scripts/audit_corpus.py`, que sabe que o
    # corpus auditado é ENEM. Validar perfil de banca aqui produziria alarme
    # falso em qualquer item de outra origem.

    vazias = [
        a.get("letra") for a in alternativas
        if isinstance(a, dict) and not (a.get("texto") or "").strip()
    ]
    if vazias:
        res.warn(
            f"EST-02 questao.alternativas sem texto: {', '.join(str(v) for v in vazias)}. "
            "O frontend renderiza um botão em branco que o aluno consegue selecionar."
        )

    texto_visivel = " ".join(
        [questao.get("enunciado") or ""]
        + [(a.get("texto") or "") for a in alternativas if isinstance(a, dict)]
    )
    marcador = _RE_PLACEHOLDER.search(texto_visivel)
    if marcador:
        res.warn(
            f"EST-05 placeholder fabricado no texto visível: {marcador.group(0)[:70]!r}. "
            "Descrição inventada no lugar de um elemento não transcrito — o aluno lê "
            "um marcador de sistema, e o token entra no alinhamento que decide onde "
            "está a figura."
        )

    recursos = questao.get("recursos") or {}
    for chave, lista in (recursos.items() if isinstance(recursos, dict) else []):
        if not isinstance(lista, list):
            continue
        for rec in lista:
            if not isinstance(rec, dict):
                continue
            arquivo = rec.get("arquivo") or ""
            if arquivo and not _RE_BLOB.match(arquivo):
                res.err(
                    f"ARQ-01 questao.recursos.{chave}[{rec.get('id') or '?'}].arquivo="
                    f"{arquivo!r} não é um blob <sha256>.png|webp. O campo é preenchido "
                    "pelo servidor; um nome vindo do modelo aponta para um blob que "
                    "não existe e faz a imagem sumir na tela do aluno."
                )


def _check_derivado(res: ValidationResult, nome: str, declarado: Any, esperado: list[dict]) -> None:
    if declarado is None:
        res.warn(f"estrutura_cognitiva.{nome}: ausente — deveria ser derivado dos processos")
        return
    ids_decl = {d.get("id") for d in declarado if isinstance(d, dict)}
    ids_esp = {d["id"] for d in esperado}
    if ids_decl != ids_esp:
        res.err(
            f"estrutura_cognitiva.{nome}: {sorted(ids_decl)} diverge da união derivada "
            f"dos processos {sorted(ids_esp)}. Constituição §4.4 proíbe atribuição "
            "direta; divergência aqui é erro de integridade."
        )


def _validate_distratores(
    res: ValidationResult, item: dict, reg: OntologyRegistry, procs_do_item: set[str]
) -> None:
    letras_incorretas = {
        a.get("letra")
        for a in ((item.get("questao") or {}).get("alternativas") or [])
        if isinstance(a, dict) and a.get("correta") is not True
    }
    sem_erro = reg.processos_sem_tipo_erro()

    for i, d in enumerate(item.get("distratores") or []):
        pref = f"distratores[{i}]"
        if not isinstance(d, dict):
            res.err(f"{pref}: objeto esperado")
            continue
        alt = d.get("alternativa")
        if letras_incorretas and alt not in letras_incorretas:
            res.err(f"{pref}.alternativa='{alt}' não é uma alternativa incorreta do item")

        if "erro" in d:
            res.err(
                f"{pref}.erro: campo da 2.1, REMOVIDO na 2.2. Um ID único por "
                "alternativa viola a Constituição §4.4 e o Axioma da Crença "
                "Calibrada. Use 'erros_esperados[]' — lista ordenada com "
                "confiança obrigatória por elo."
            )
        if "processos_afetados" in d:
            res.err(
                f"{pref}.processos_afetados: campo da 2.1, REMOVIDO na 2.2. O "
                "processo afetado passou a ser propriedade de cada elo: "
                "'erros_esperados[].processo_afetado'."
            )

        elos = d.get("erros_esperados")
        if not isinstance(elos, list) or not elos:
            res.err(f"{pref}.erros_esperados: lista ordenada obrigatória (1..{MAX_ELOS} elos)")
            continue
        if len(elos) > MAX_ELOS:
            res.err(
                f"{pref}.erros_esperados: {len(elos)} elos; máximo {MAX_ELOS} "
                "(Error Trace §3, R-4). O excedente vai para observação de campo, "
                "nunca comprimido em um elo existente."
            )

        ordens: list[int] = []
        pares: set[tuple] = set()
        for j, elo in enumerate(elos):
            epref = f"{pref}.erros_esperados[{j}]"
            if not isinstance(elo, dict):
                res.err(f"{epref}: objeto esperado")
                continue
            ordem = elo.get("ordem")
            if not isinstance(ordem, int) or isinstance(ordem, bool):
                res.err(f"{epref}.ordem: inteiro obrigatório")
            else:
                ordens.append(ordem)

            proc = elo.get("processo_afetado")
            proc_ok = _check_id(res, f"{epref}.processo_afetado", proc, reg.processos)

            erro = elo.get("erro")
            if erro in SENTINELAS_ERRO:
                if erro == "erro-nao-catalogado-nesta-versao" and proc_ok and proc not in sem_erro:
                    res.warn(
                        f"{epref}.erro: sentinela 'erro-nao-catalogado-nesta-versao' "
                        f"usada para '{proc}', que TEM tipos de erro catalogados "
                        f"({sorted(reg.err_by_proc.get(proc, set()))}). A sentinela é "
                        "para os 13 processos sem catálogo (Manual §7, regra 4)."
                    )
            elif _check_id(res, f"{epref}.erro", erro, reg.tipos_erro) and proc_ok:
                # Error Trace §3, R-1 — vínculo de catálogo.
                if erro not in reg.err_by_proc.get(proc, set()):
                    res.err(
                        f"{epref}: o par ('{erro}', '{proc}') não existe no catálogo "
                        f"da versão {reg.version}. É proibido emprestar um tipo de erro "
                        "de outro processo por semelhança (Error Trace R-1; Manual §7, regra 4)."
                    )

            # R-3 — proibição de determinismo.
            if _as_float(elo.get("confianca")) is None:
                res.err(
                    f"{epref}.confianca: OBRIGATÓRIA em todo elo (Error Trace §3, R-3). "
                    "Confiança implícita, ausente ou igual a 1 por convenção de "
                    "preenchimento viola o Axioma da Crença Calibrada."
                )

            mec = elo.get("mecanismo")
            if mec is not None and mec not in MECANISMOS:
                res.err(f"{epref}.mecanismo: '{mec}' fora do vocabulário MEC-01..MEC-13 (Error Trace §4.3)")

            par = (elo.get("erro"), proc)
            if par in pares:
                res.err(f"{epref}: par (erro, processo_afetado) repetido na mesma cadeia (R-6)")
            pares.add(par)

        # R-5 — ordem contígua a partir de 1, sem repetição.
        if ordens and sorted(ordens) != list(range(1, len(ordens) + 1)):
            res.err(
                f"{pref}.erros_esperados: 'ordem' deve ser contígua a partir de 1 "
                f"e sem repetição (recebido: {sorted(ordens)}) — Error Trace R-5"
            )


def _validate_intervencoes(res: ValidationResult, item: dict, reg: OntologyRegistry) -> None:
    # Schema 2.2: a intervenção é selecionada a partir do elo de ordem 1,
    # nunca do último elo observado (Error Trace §1.1).
    raizes: set[tuple] = set()
    for d in item.get("distratores") or []:
        if not isinstance(d, dict):
            continue
        for elo in d.get("erros_esperados") or []:
            if isinstance(elo, dict) and elo.get("ordem") == 1:
                raizes.add((elo.get("erro"), elo.get("processo_afetado")))

    for i, it in enumerate(item.get("intervencoes") or []):
        pref = f"intervencoes[{i}]"
        if not isinstance(it, dict):
            res.err(f"{pref}: objeto esperado")
            continue
        _check_id(res, f"{pref}.id", it.get("id"), reg.intervencoes)
        g = it.get("gatilho") or {}
        erro, proc = g.get("erro"), g.get("processo")
        if proc is not None:
            _check_id(res, f"{pref}.gatilho.processo", proc, reg.processos)
        if erro is not None and erro not in SENTINELAS_ERRO:
            if _check_id(res, f"{pref}.gatilho.erro", erro, reg.tipos_erro):
                prescrita = (reg.get("tipos_erro", erro) or {}).get("intervencao")
                if prescrita and it.get("id") != prescrita:
                    res.warn(
                        f"{pref}.id='{it.get('id')}' difere da intervenção prescrita "
                        f"por '{erro}' no catálogo ('{prescrita}')"
                    )
        if raizes and (erro, proc) not in raizes:
            res.warn(
                f"{pref}.gatilho ({erro}, {proc}) não corresponde a nenhum elo de "
                "ordem 1. A intervenção é selecionada a partir da RAIZ da cadeia, "
                "nunca da manifestação de superfície (Error Trace §1.1)."
            )


def _validate_incerteza(res: ValidationResult, item: dict) -> None:
    inc = item.get("incerteza")
    if not isinstance(inc, dict):
        return
    for m in inc.get("marcadores") or []:
        if m not in MARCADORES_INCERTEZA:
            res.err(
                f"incerteza.marcadores: '{m}' fora do vocabulário fechado do "
                f"Schema 2.2 / Manual §13 ({sorted(MARCADORES_INCERTEZA)})"
            )


# ---- Especificação do Error Trace v1.0 -----------------------------------
def validate_error_trace(trace: dict, registry: OntologyRegistry | None = None) -> ValidationResult:
    """Valida um Error Trace contra a **Especificação do Error Trace v1.0**.

    Um traço explica UMA alternativa incorreta de UM estudante. Um item com
    quatro distratores admite até quatro traços independentes; eles não se
    combinam em um objeto único (§2.1).
    """
    reg = registry or OntologyRegistry()
    res = ValidationResult()

    if not isinstance(trace, dict):
        res.err("error trace deve ser um objeto/dict")
        return res

    for f in ("trace_id", "event_id", "item_id", "item_hash", "etrace_version",
              "alternativa_escolhida", "produtor"):
        if not trace.get(f):
            res.err(f"campo obrigatório ausente ou vazio: '{f}' (Error Trace §2.1)")
    _check_ontology_version(res, trace, reg)

    if trace.get("produtor") not in (None, "humano", "modelo", "regra"):
        res.err(f"produtor: '{trace.get('produtor')}' — esperado humano|modelo|regra")
    if not isinstance(trace.get("revisado_por_humano"), bool):
        res.err("revisado_por_humano: booleano obrigatório (§2.1)")
    if _as_float(trace.get("confianca_global")) is None:
        res.err("confianca_global: obrigatória (§2.1)")

    cadeia = trace.get("cadeia")
    if not isinstance(cadeia, list) or not cadeia:
        res.err(f"cadeia: lista ordenada obrigatória (1..{MAX_ELOS} elos)")
        return res
    if len(cadeia) > MAX_ELOS:
        res.err(f"cadeia: {len(cadeia)} elos; máximo {MAX_ELOS} (§3, R-4)")

    sem_erro = reg.processos_sem_tipo_erro()
    ordens: list[int] = []
    pares: set[tuple] = set()
    for i, elo in enumerate(cadeia):
        pref = f"cadeia[{i}]"
        if not isinstance(elo, dict):
            res.err(f"{pref}: objeto esperado")
            continue
        ordem = elo.get("ordem")
        if not isinstance(ordem, int) or isinstance(ordem, bool):
            res.err(f"{pref}.ordem: inteiro obrigatório")
        else:
            ordens.append(ordem)
            if ordem == 1 and not (elo.get("justificativa") or "").strip():
                res.err(
                    f"{pref}.justificativa: obrigatória para o elo de ordem 1 (§2.2) — "
                    "1–2 frases reproduzíveis por um segundo anotador."
                )

        proc = elo.get("processo_afetado")
        proc_ok = _check_id(res, f"{pref}.processo_afetado", proc, reg.processos)

        erro = elo.get("erro")
        if erro in SENTINELAS_ERRO:
            if erro == "erro-nao-catalogado-nesta-versao" and proc_ok and proc not in sem_erro:
                res.warn(
                    f"{pref}.erro: sentinela usada para '{proc}', que tem tipos de "
                    "erro catalogados (§3, R-2)"
                )
        elif _check_id(res, f"{pref}.erro", erro, reg.tipos_erro) and proc_ok:
            if erro not in reg.err_by_proc.get(proc, set()):
                res.err(
                    f"{pref}: o par ('{erro}', '{proc}') não existe no catálogo da "
                    f"versão {reg.version}. O catálogo é a fonte da possibilidade; "
                    "o traço não pode inventar vínculo que a ontologia não autoriza (R-1)."
                )

        if _as_float(elo.get("confianca")) is None:
            res.err(f"{pref}.confianca: OBRIGATÓRIA em todo elo (R-3)")

        mec = elo.get("mecanismo")
        if mec is not None and mec not in MECANISMOS:
            res.err(f"{pref}.mecanismo: '{mec}' fora de MEC-01..MEC-13 (§4.3)")

        par = (erro, proc)
        if par in pares:
            res.err(f"{pref}: par (erro, processo_afetado) repetido na cadeia (R-6)")
        pares.add(par)

    if ordens and sorted(ordens) != list(range(1, len(ordens) + 1)):
        res.err(f"cadeia: 'ordem' deve ser contígua a partir de 1, sem saltos (recebido: {sorted(ordens)}) — R-5")

    return res


def pode_alimentar_crenca(trace: dict) -> bool:
    """Regra de governança de ingestão — Error Trace §6 (EXT-WP1-1.0, L13b).

    Um traço com `produtor` `modelo` ou `regra` NÃO pode influenciar o estado de
    um estudante real sem que seu elo de ordem 1 tenha sido confirmado por ao
    menos um revisor humano. Ele pode ser **armazenado** sem revisão — é a
    distinção que permite ingestão em escala com enriquecimento posterior.
    """
    if trace.get("produtor") == "humano":
        return True
    return bool(trace.get("revisado_por_humano"))


# ---- CLI de sanidade -----------------------------------------------------
if __name__ == "__main__":
    reg = OntologyRegistry()
    print(f"Ontologia v{reg.version}  ({reg.path})")
    print(f"  DOM={len(reg.dominios)} COMP={len(reg.competencias)} "
          f"PROC={len(reg.processos)} HAB={len(reg.habilidades)} "
          f"ERR={len(reg.tipos_erro)} INT={len(reg.intervencoes)}")
    sem = sorted(reg.processos_sem_tipo_erro())
    print(f"  processos sem tipo de erro catalogado: {len(sem)}/{len(reg.processos)}")
    print(f"    {', '.join(sem)}")
