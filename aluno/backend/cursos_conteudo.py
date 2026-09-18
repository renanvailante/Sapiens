"""O conteúdo pedagógico dos cursos: trilhas, estações e blocos.

Este módulo é a **fronteira entre quem escreve o curso e quem roda o produto**.
Ele carrega arquivos JSON de `conteudo/cursos/`, VALIDA cada um contra um
contrato explícito e entrega objetos que as rotas servem. Não fala com banco,
não sabe quem é o aluno e não cobra nada.

Por que arquivo e não banco
---------------------------
O conteúdo é produzido fora daqui (uma IA escreve, outra revisa, outra gera
volume de exercícios) e entra no produto por commit. Arquivo em git dá as
quatro coisas que um formulário de admin não dá: revisão antes de publicar,
diff do que mudou, rollback de uma versão ruim e custo ZERO de leitura em
produção — a biblioteca inteira é carregada uma vez no boot e vive em memória
(ver o incidente de cota do Firestore de 2026-09-04: nada em caminho quente
pode custar uma leitura por acesso).

`CURSOS_CONTEUDO_DIR` troca a raiz sem tocar em código, que é o gancho para o
dia em que o conteúdo passar a ser montado num volume ou baixado de um bucket.

A hierarquia, e o que cada nível significa
------------------------------------------
    curso      → produto, vive em `cursos.py` (título, preço, status)
      trilha   → um caminho dentro do curso, com estações EM ORDEM
        estação → a unidade de estudo (10-20 min), a menor coisa que se conclui
          bloco → a menor coisa que se lê, assiste ou responde

O curso NÃO é definido aqui de propósito. `cursos.CURSOS` é a vitrine (o que
se vende, por quanto, com que status) e isto é a pedagogia (o que se aprende,
em que ordem). São dois times, dois ritmos de mudança e dois riscos
diferentes. O que amarra os dois é uma regra só: todo `curso_id` com conteúdo
precisa existir no catálogo — um diretório órfão é erro de validação, não uma
página fantasma.

As cinco regras que o validador existe para impedir
---------------------------------------------------
1. **Preço não mora em conteúdo.** Nenhum arquivo pode declarar custo,
   desconto ou Spark. Preço é decisão de produto, mora em `cursos.py` e em
   `sparks_store.py`, e é o servidor que cobra. Um arquivo gerado por IA que
   inventasse `"custo_sparks": 50` viraria promessa de preço no ar.
2. **Do simples ao avançado, de verdade.** O `nivel` dos exercícios de uma
   estação não pode retroceder. "Progressão" não é intenção do autor: é
   invariante verificável, senão o quinto exercício acaba mais fácil que o
   primeiro sem ninguém perceber.
3. **Gabarito existe e é único.** Alternativa apontada por `gabarito` precisa
   existir; formato numérico precisa de tolerância; texto curto precisa de
   pelo menos uma resposta aceita.
4. **Pré-requisito aponta para estação que existe, e não tem ciclo.** Uma
   estação que depende de si mesma trava o aluno para sempre, em silêncio.
5. **Identificador não se repete.** `estacao_id` é único no curso e `bloco_id`
   é único na estação — os dois são chave de progresso e de analytics, e um
   id repetido faz dois blocos diferentes compartilharem a mesma linha de
   histórico.

Curso inválido não é servido
----------------------------
Se QUALQUER arquivo de um curso tiver problema, o curso inteiro sai do ar e
aparece no relatório do admin com a lista exata de problemas. Servir metade
de uma trilha é pior que não servir: o aluno estuda uma sequência com buraco
e o pré-requisito seguinte nunca libera. Como o conteúdo entra por commit e a
suíte valida a pasta inteira (`tests/test_cursos_conteudo.py`), na prática
isto é cinto de segurança, não fluxo normal.

O dissertativo é o único formato que o servidor NÃO corrige sozinho
------------------------------------------------------------------
`formato: "dissertativo"` tem `criterios` (a régua, que o aluno VÊ antes de
escrever) e `referencia` (a resposta esperada, que ele nunca vê). `corrigir()`
recusa julgá-lo de propósito: quem dá o veredito é a Mentis, por Sparks, na
rota dedicada. Um "acertou" inventado aqui concluiria a estação sem ninguém
ler o que o aluno escreveu.

O que ainda NÃO existe aqui, e onde entra quando existir
--------------------------------------------------------
* Vídeo é sempre opcional e nunca conclui nada. Um bloco de vídeo com
  `ref: null` é um lugar declarado para o vídeo que ainda vai ser gravado:
  não é renderizado para o aluno e aparece como pendência no inventário.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger("sapiens.cursos.conteudo")

# Versão MAIOR do contrato de conteúdo. Arquivo que declara outra maior é
# recusado com mensagem explícita em vez de ser lido "na sorte" — mudança
# incompatível de esquema precisa de migração consciente do conteúdo.
SCHEMA_VERSION = "1.0"

_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_HABILIDADE = re.compile(r"^HAB-\d{2,3}$")

TIPOS_DE_BLOCO = ("texto", "tabela", "exemplo", "video", "exercicio", "desafio")
FORMATOS = ("multipla_escolha", "numerico", "texto_curto", "dissertativo")
VARIANTES_DE_TEXTO = ("padrao", "destaque", "atencao")
PROVEDORES_DE_VIDEO = ("youtube", "vimeo", "arquivo")

NIVEL_MIN, NIVEL_MAX = 1, 5

# Teto de critérios de um dissertativo. Não é gosto: cada critério vira uma
# linha da devolutiva da Mentis, e uma régua de quinze linhas não é régua.
MAX_CRITERIOS = 6

# Palavras que NÃO podem aparecer como chave em arquivo de conteúdo. É a
# regra 1 do topo, e ela é verificada por chave e não por texto: o enunciado
# de um exercício pode perfeitamente falar de preço e de desconto (é
# Matemática Básica), o que não pode é o ARQUIVO declarar um.
CHAVES_PROIBIDAS = ("custo", "custo_sparks", "preco", "preço", "sparks", "valor_sparks", "desconto")

# Critérios de conclusão aceitos. Nada de string livre: a tela do aluno
# promete uma condição de término, e ela precisa ser a mesma que o servidor
# confere.
CONCLUSAO_TODOS = "todos_os_exercicios"
CONCLUSAO_MINIMO = "minimo_de_acertos"
CRITERIOS = (CONCLUSAO_TODOS, CONCLUSAO_MINIMO)


class ConteudoInvalido(ValueError):
    """Um arquivo de conteúdo não obedece ao contrato. Sempre com a lista
    completa de problemas — corrigir de um em um, recarregando entre eles,
    é o que torna revisão de conteúdo gerado em lote insuportável."""


@dataclass(frozen=True)
class Estacao:
    estacao_id: str
    curso_id: str
    trilha_id: str          # preenchido pelo manifesto, não pelo arquivo
    titulo: str
    objetivo: str
    versao: str
    blocos: tuple[dict, ...]
    pre_requisitos: tuple[str, ...] = ()
    habilidades: tuple[str, ...] = ()
    # O vocabulário do PRÓPRIO curso ("ordem-de-operacoes", "bhaskara"). Ao
    # contrário de `habilidades` (que é o catálogo `HAB-NN` compartilhado com
    # o treino e com a prova), isto é livre e local: serve para a análise por
    # assunto dentro do curso, e nunca aparece para o aluno.
    conceitos: tuple[str, ...] = ()
    # A posição declarada pelo autor ("estação 07"). A ordem que vale é a do
    # manifesto; este número existe para a tela poder mostrar o mesmo rótulo
    # que o material impresso usa.
    numero: int | None = None
    duracao_minutos: int | None = None
    conclusao: dict = field(default_factory=lambda: {"tipo": CONCLUSAO_TODOS})
    ordem: int = 0          # posição dentro da trilha

    @property
    def exercicios(self) -> tuple[dict, ...]:
        """Só os que CONTAM para concluir: desafio é extra por definição, e
        exercício marcado `opcional` é prática a mais para quem quiser."""
        return tuple(
            b for b in self.blocos
            if b["tipo"] == "exercicio" and not b.get("opcional")
        )

    @property
    def avaliaveis(self) -> tuple[dict, ...]:
        """Tudo que se responde — inclusive desafio e opcional. É o conjunto
        que a rota de resposta aceita, que é maior que o que conclui."""
        return tuple(b for b in self.blocos if b["tipo"] in ("exercicio", "desafio"))

    def bloco(self, bloco_id: str) -> dict | None:
        for b in self.blocos:
            if b.get("bloco_id") == bloco_id:
                return b
        return None

    @property
    def acertos_para_concluir(self) -> int:
        if self.conclusao.get("tipo") == CONCLUSAO_MINIMO:
            return min(int(self.conclusao.get("minimo", 0)), len(self.exercicios))
        return len(self.exercicios)


@dataclass(frozen=True)
class Trilha:
    trilha_id: str
    curso_id: str
    titulo: str
    estacoes: tuple[str, ...]
    resumo: str | None = None


@dataclass(frozen=True)
class CursoConteudo:
    curso_id: str
    versao: str
    trilhas: tuple[Trilha, ...]
    estacoes: dict[str, Estacao]

    @property
    def ordem_das_estacoes(self) -> tuple[str, ...]:
        """Todas as estações do curso na ordem em que o aluno as encontra."""
        return tuple(e for t in self.trilhas for e in t.estacoes)


@dataclass(frozen=True)
class Problema:
    curso_id: str
    arquivo: str
    mensagem: str

    def __str__(self) -> str:  # pragma: no cover - conveniência de log
        return f"[{self.curso_id}] {self.arquivo}: {self.mensagem}"


@dataclass(frozen=True)
class Biblioteca:
    """O que foi carregado e o que foi recusado — as duas metades juntas.

    Recusa não é exceção: é dado de operação. O painel do admin mostra os
    problemas, e é por ele que quem escreveu o conteúdo descobre o que
    consertar sem precisar ler log de servidor.
    """
    cursos: dict[str, CursoConteudo]
    problemas: tuple[Problema, ...]
    raiz: str

    def curso(self, curso_id: str) -> CursoConteudo | None:
        return self.cursos.get(curso_id)

    def estacao(self, curso_id: str, estacao_id: str) -> Estacao | None:
        curso = self.cursos.get(curso_id)
        return curso.estacoes.get(estacao_id) if curso else None

    def tem_conteudo(self, curso_id: str) -> bool:
        curso = self.cursos.get(curso_id)
        return bool(curso and curso.estacoes)


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------
#
# Funções puras: recebem o dicionário cru do JSON e devolvem a LISTA de
# problemas (vazia = válido). Nenhuma levanta exceção no meio do caminho,
# porque quem revisa conteúdo gerado em lote precisa da lista inteira de uma
# vez, não do primeiro erro.


def _texto(valor: Any) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


def _chaves_proibidas(dados: Any, caminho: str = "") -> list[str]:
    """Varre o documento inteiro atrás de preço declarado em conteúdo."""
    achados: list[str] = []
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            onde = f"{caminho}.{chave}" if caminho else str(chave)
            if str(chave).lower() in CHAVES_PROIBIDAS:
                achados.append(
                    f"`{onde}` declara preço/moeda em arquivo de conteúdo. "
                    "Preço é decisão de produto e mora em `cursos.py`/`sparks_store.py`."
                )
            achados += _chaves_proibidas(valor, onde)
    elif isinstance(dados, list):
        for i, item in enumerate(dados):
            achados += _chaves_proibidas(item, f"{caminho}[{i}]")
    return achados


def _validar_schema_version(dados: dict) -> list[str]:
    versao = dados.get("schema_version")
    if not _texto(versao):
        return [f"falta `schema_version` (esperado \"{SCHEMA_VERSION}\")"]
    maior_arquivo = str(versao).split(".")[0]
    maior_codigo = SCHEMA_VERSION.split(".")[0]
    if maior_arquivo != maior_codigo:
        return [
            f"`schema_version` {versao} é incompatível com {SCHEMA_VERSION} "
            "— versão MAIOR diferente exige migração do conteúdo."
        ]
    return []


def validar_manifesto(dados: dict) -> list[str]:
    """`curso.json`: quais trilhas existem e em que ordem as estações vêm."""
    problemas = _validar_schema_version(dados) + _chaves_proibidas(dados)

    if not _texto(dados.get("curso_id")) or not _ID.match(dados.get("curso_id", "")):
        problemas.append("`curso_id` ausente ou fora do formato slug (a-z, 0-9 e hífen)")
    if not _texto(dados.get("versao")):
        problemas.append("`versao` ausente — é ela que separa quem estudou o quê nos dados")

    trilhas = dados.get("trilhas")
    if not isinstance(trilhas, list) or not trilhas:
        problemas.append("`trilhas` precisa ser uma lista com pelo menos uma trilha")
        return problemas

    vistas: set[str] = set()
    estacoes_citadas: list[str] = []
    for i, trilha in enumerate(trilhas):
        onde = f"trilhas[{i}]"
        if not isinstance(trilha, dict):
            problemas.append(f"{onde} não é um objeto")
            continue
        tid = trilha.get("trilha_id", "")
        if not _texto(tid) or not _ID.match(tid):
            problemas.append(f"{onde}.trilha_id ausente ou fora do formato slug")
        elif tid in vistas:
            problemas.append(f"{onde}.trilha_id `{tid}` repetido no mesmo curso")
        else:
            vistas.add(tid)
        if not _texto(trilha.get("titulo")):
            problemas.append(f"{onde}.titulo ausente")
        estacoes = trilha.get("estacoes")
        if not isinstance(estacoes, list) or not estacoes:
            problemas.append(f"{onde}.estacoes precisa listar pelo menos uma estação")
            continue
        for e in estacoes:
            if not _texto(e) or not _ID.match(e):
                problemas.append(f"{onde}.estacoes tem id inválido: {e!r}")
            else:
                estacoes_citadas.append(e)

    repetidas = {e for e in estacoes_citadas if estacoes_citadas.count(e) > 1}
    for e in sorted(repetidas):
        problemas.append(
            f"estação `{e}` aparece em mais de um lugar do manifesto — "
            "a mesma estação em duas trilhas teria dois progressos e um id só"
        )
    return problemas


def _validar_exercicio(bloco: dict, onde: str) -> list[str]:
    problemas: list[str] = []
    formato = bloco.get("formato")
    if formato not in FORMATOS:
        problemas.append(f"{onde}.formato inválido: {formato!r} (aceitos: {', '.join(FORMATOS)})")
        return problemas

    if not _texto(bloco.get("enunciado")):
        problemas.append(f"{onde}.enunciado ausente")

    nivel = bloco.get("nivel")
    if not isinstance(nivel, int) or not (NIVEL_MIN <= nivel <= NIVEL_MAX):
        problemas.append(f"{onde}.nivel precisa ser inteiro de {NIVEL_MIN} a {NIVEL_MAX}")

    gabarito = bloco.get("gabarito")
    feedback = bloco.get("feedback") or {}
    if not isinstance(feedback, dict):
        problemas.append(f"{onde}.feedback precisa ser um objeto")
        feedback = {}

    if formato == "multipla_escolha":
        alternativas = bloco.get("alternativas")
        if not isinstance(alternativas, list) or len(alternativas) < 2:
            problemas.append(f"{onde}.alternativas precisa ter pelo menos duas opções")
            return problemas
        ids: list[str] = []
        for j, alt in enumerate(alternativas):
            if not isinstance(alt, dict) or not _texto(alt.get("id")) or not _texto(alt.get("texto")):
                problemas.append(f"{onde}.alternativas[{j}] precisa de `id` e `texto`")
                continue
            ids.append(alt["id"])
        if len(set(ids)) != len(ids):
            problemas.append(f"{onde}.alternativas têm `id` repetido")
        if gabarito not in ids:
            problemas.append(f"{onde}.gabarito `{gabarito!r}` não corresponde a nenhuma alternativa")
        sobrando = [k for k in feedback if k not in ids]
        if sobrando:
            problemas.append(
                f"{onde}.feedback tem chave que não é alternativa: {', '.join(map(str, sobrando))}"
            )
    elif formato == "numerico":
        if not isinstance(gabarito, dict) or not isinstance(gabarito.get("valor"), (int, float)):
            problemas.append(f"{onde}.gabarito precisa ser {{\"valor\": número, \"tolerancia\": número}}")
        elif not isinstance(gabarito.get("tolerancia", 0), (int, float)) or gabarito.get("tolerancia", 0) < 0:
            problemas.append(f"{onde}.gabarito.tolerancia precisa ser um número não negativo")
        _feedback_binario(feedback, onde, problemas)
    elif formato == "texto_curto":
        aceitos = (gabarito or {}).get("aceitos") if isinstance(gabarito, dict) else None
        if not isinstance(aceitos, list) or not aceitos or not all(_texto(a) for a in aceitos):
            problemas.append(f"{onde}.gabarito precisa ser {{\"aceitos\": [\"…\"]}} com ao menos uma resposta")
        _feedback_binario(feedback, onde, problemas)
    elif formato == "dissertativo":
        # Sem critério não há correção: a Mentis precisa de uma régua escrita
        # por quem fez a questão, senão cada aluno é corrigido por um padrão
        # diferente e a nota não quer dizer nada.
        criterios = bloco.get("criterios")
        if not isinstance(criterios, list) or not criterios or not all(_texto(c) for c in criterios):
            problemas.append(
                f"{onde}.criterios precisa ser uma lista com ao menos um critério de correção"
            )
        elif len(criterios) > MAX_CRITERIOS:
            problemas.append(f"{onde}.criterios tem mais de {MAX_CRITERIOS} itens")
        if gabarito is not None:
            problemas.append(f"{onde}.gabarito não existe no dissertativo — a régua são os `criterios`")
        _feedback_binario(feedback, onde, problemas)

    return problemas


def _feedback_binario(feedback: dict, onde: str, problemas: list[str]) -> None:
    sobrando = [k for k in feedback if k not in ("correto", "incorreto")]
    if sobrando:
        problemas.append(
            f"{onde}.feedback só aceita `correto` e `incorreto` neste formato "
            f"(veio: {', '.join(map(str, sobrando))})"
        )


def _validar_bloco(bloco: Any, onde: str) -> list[str]:
    if not isinstance(bloco, dict):
        return [f"{onde} não é um objeto"]

    problemas: list[str] = []
    bloco_id = bloco.get("bloco_id", "")
    if not _texto(bloco_id) or not _ID.match(bloco_id):
        problemas.append(f"{onde}.bloco_id ausente ou fora do formato slug")

    tipo = bloco.get("tipo")
    if tipo not in TIPOS_DE_BLOCO:
        problemas.append(f"{onde}.tipo inválido: {tipo!r} (aceitos: {', '.join(TIPOS_DE_BLOCO)})")
        return problemas

    if tipo == "texto":
        if not _texto(bloco.get("markdown")):
            problemas.append(f"{onde}.markdown ausente")
        variante = bloco.get("variante", "padrao")
        if variante not in VARIANTES_DE_TEXTO:
            problemas.append(f"{onde}.variante inválida: {variante!r}")
    elif tipo == "tabela":
        colunas = bloco.get("colunas")
        if not isinstance(colunas, list) or len(colunas) < 2 or not all(_texto(c) for c in colunas):
            problemas.append(f"{onde}.colunas precisa ter pelo menos dois cabeçalhos de texto")
            return problemas
        linhas = bloco.get("linhas")
        if not isinstance(linhas, list) or not linhas:
            problemas.append(f"{onde}.linhas precisa ter pelo menos uma linha")
            return problemas
        for j, linha in enumerate(linhas):
            if not isinstance(linha, list) or len(linha) != len(colunas):
                problemas.append(
                    f"{onde}.linhas[{j}] tem {len(linha) if isinstance(linha, list) else '?'} "
                    f"célula(s) e o cabeçalho tem {len(colunas)} — tabela torta não é "
                    "renderizável, é um dado perdido"
                )
    elif tipo == "exemplo":
        if not _texto(bloco.get("enunciado")):
            problemas.append(f"{onde}.enunciado ausente")
        passos = bloco.get("passos")
        if not isinstance(passos, list) or not passos:
            problemas.append(f"{onde}.passos precisa ter pelo menos um passo")
        else:
            for j, passo in enumerate(passos):
                if not isinstance(passo, dict) or not _texto(passo.get("texto")):
                    problemas.append(f"{onde}.passos[{j}] precisa de `texto`")
    elif tipo == "video":
        if not _texto(bloco.get("titulo")):
            problemas.append(f"{onde}.titulo ausente")
        provedor = bloco.get("provedor")
        if provedor not in PROVEDORES_DE_VIDEO:
            problemas.append(f"{onde}.provedor inválido: {provedor!r}")
        ref = bloco.get("ref", None)
        # `ref: null` é PENDÊNCIA declarada, não erro: o lugar do vídeo existe
        # no roteiro e a gravação ainda não. Só string vazia é erro, porque aí
        # não dá para saber se é pendência ou um id que se perdeu.
        if ref is not None and not _texto(ref):
            problemas.append(f"{onde}.ref precisa ser o id/URL do vídeo ou `null` (pendente)")
    elif tipo in ("exercicio", "desafio"):
        problemas += _validar_exercicio(bloco, onde)

    return problemas


def validar_estacao(dados: dict) -> list[str]:
    """Um arquivo de estação inteiro. Devolve todos os problemas de uma vez."""
    problemas = _validar_schema_version(dados) + _chaves_proibidas(dados)

    eid = dados.get("estacao_id", "")
    if not _texto(eid) or not _ID.match(eid):
        problemas.append("`estacao_id` ausente ou fora do formato slug")
    if not _texto(dados.get("titulo")):
        problemas.append("`titulo` ausente")
    if not _texto(dados.get("objetivo")):
        problemas.append(
            "`objetivo` ausente — é a frase que diz o que o aluno sai sabendo FAZER, "
            "e é o que dá sentido à ordem das estações"
        )
    if not _texto(dados.get("versao")):
        problemas.append("`versao` ausente")

    duracao = dados.get("duracao_minutos")
    if duracao is not None and (not isinstance(duracao, int) or duracao <= 0):
        problemas.append("`duracao_minutos` precisa ser inteiro positivo ou ausente")

    numero = dados.get("numero")
    if numero is not None and (not isinstance(numero, int) or numero <= 0):
        problemas.append("`numero` precisa ser inteiro positivo ou ausente")

    for c in dados.get("conceitos") or []:
        if not _texto(c) or not _ID.match(c):
            problemas.append(f"conceito `{c!r}` fora do formato slug")

    for h in dados.get("habilidades") or []:
        if not _texto(h) or not _HABILIDADE.match(h):
            problemas.append(f"habilidade `{h!r}` fora do formato HAB-NN")

    for p in dados.get("pre_requisitos") or []:
        if not _texto(p) or not _ID.match(p):
            problemas.append(f"pré-requisito `{p!r}` fora do formato slug")

    conclusao = dados.get("conclusao") or {"tipo": CONCLUSAO_TODOS}
    if not isinstance(conclusao, dict) or conclusao.get("tipo") not in CRITERIOS:
        problemas.append(f"`conclusao.tipo` precisa ser um de: {', '.join(CRITERIOS)}")
        conclusao = {"tipo": CONCLUSAO_TODOS}

    blocos = dados.get("blocos")
    if not isinstance(blocos, list) or not blocos:
        problemas.append("`blocos` precisa ser uma lista com pelo menos um bloco")
        return problemas

    ids: list[str] = []
    for i, bloco in enumerate(blocos):
        problemas += _validar_bloco(bloco, f"blocos[{i}]")
        if isinstance(bloco, dict) and _texto(bloco.get("bloco_id")):
            ids.append(bloco["bloco_id"])
    repetidos = {b for b in ids if ids.count(b) > 1}
    for b in sorted(repetidos):
        problemas.append(f"`bloco_id` repetido na estação: {b}")

    problemas += _validar_progressao(blocos)

    obrigatorios = [
        b for b in blocos
        if isinstance(b, dict) and b.get("tipo") == "exercicio" and not b.get("opcional")
    ]
    if conclusao.get("tipo") == CONCLUSAO_MINIMO:
        minimo = conclusao.get("minimo")
        if not isinstance(minimo, int) or minimo <= 0:
            problemas.append("`conclusao.minimo` precisa ser inteiro positivo")
        elif minimo > len(obrigatorios):
            problemas.append(
                f"`conclusao.minimo` ({minimo}) é maior que o número de exercícios "
                f"que contam ({len(obrigatorios)}) — a estação nunca poderia ser concluída"
            )
    elif not obrigatorios:
        problemas.append(
            "estação sem nenhum exercício que conte para a conclusão: com "
            f"`{CONCLUSAO_TODOS}` ela seria concluída sem o aluno responder nada. "
            "Use exercícios, ou declare outro critério."
        )

    return problemas


def _validar_progressao(blocos: list) -> list[str]:
    """Regra 2: o nível dos exercícios não retrocede dentro da estação, e o
    desafio nunca é mais fácil que o último exercício.

    É a única forma de "do simples ao avançado" virar garantia. Sem isto, a
    ordem depende de quem gerou o lote ter prestado atenção — e a estação em
    que ela se perde é indistinguível das outras até um aluno travar."""
    problemas: list[str] = []
    maior = 0
    for i, bloco in enumerate(blocos):
        if not isinstance(bloco, dict) or bloco.get("tipo") != "exercicio":
            continue
        nivel = bloco.get("nivel")
        if not isinstance(nivel, int):
            continue
        if nivel < maior:
            problemas.append(
                f"blocos[{i}] (nível {nivel}) vem depois de um exercício de nível {maior}: "
                "a progressão da estação retrocede"
            )
        maior = max(maior, nivel)

    for i, bloco in enumerate(blocos):
        if not isinstance(bloco, dict) or bloco.get("tipo") != "desafio":
            continue
        nivel = bloco.get("nivel")
        if isinstance(nivel, int) and maior and nivel < maior:
            problemas.append(
                f"blocos[{i}] é um desafio de nível {nivel}, abaixo do maior exercício "
                f"da estação (nível {maior}) — desafio é o teto, não um degrau para trás"
            )
    return problemas


def _validar_integridade(
    manifesto: dict, estacoes: dict[str, dict], curso_ids_do_catalogo: Iterable[str],
) -> list[str]:
    """O que só dá para verificar com o curso inteiro na mão."""
    problemas: list[str] = []
    curso_id = manifesto.get("curso_id")

    if curso_id and curso_id not in set(curso_ids_do_catalogo):
        problemas.append(
            f"`{curso_id}` não existe em `cursos.CURSOS` — conteúdo sem produto "
            "correspondente não tem como ser vendido nem acessado"
        )

    citadas = [e for t in manifesto.get("trilhas") or [] for e in (t.get("estacoes") or [])]
    for e in citadas:
        if e not in estacoes:
            problemas.append(f"trilha cita a estação `{e}`, mas não existe `estacoes/{e}.json`")
    for e in estacoes:
        if e not in citadas:
            problemas.append(
                f"`estacoes/{e}.json` existe mas nenhuma trilha o cita — "
                "estação órfã é conteúdo escrito que ninguém alcança"
            )

    # Pré-requisitos: existem, e não formam ciclo.
    grafo = {e: list(d.get("pre_requisitos") or []) for e, d in estacoes.items()}
    for eid, pres in grafo.items():
        for p in pres:
            if p not in estacoes:
                problemas.append(f"`{eid}` exige a estação `{p}`, que não existe neste curso")
    ciclo = _primeiro_ciclo({e: [p for p in pres if p in grafo] for e, pres in grafo.items()})
    if ciclo:
        problemas.append(
            "pré-requisitos formam um ciclo (" + " → ".join(ciclo) + "): "
            "nenhuma das estações envolvidas jamais liberaria"
        )
    return problemas


def _primeiro_ciclo(grafo: dict[str, list[str]]) -> list[str] | None:
    """Busca em profundidade com pilha; devolve o ciclo achado, para a
    mensagem de erro poder mostrar o caminho em vez de só acusar sua
    existência."""
    BRANCO, CINZA, PRETO = 0, 1, 2
    cor = {n: BRANCO for n in grafo}

    def visitar(no: str, caminho: list[str]) -> list[str] | None:
        cor[no] = CINZA
        for viz in grafo.get(no, []):
            if cor.get(viz) == CINZA:
                return caminho[caminho.index(viz):] + [viz] if viz in caminho else [viz, no, viz]
            if cor.get(viz) == BRANCO:
                achado = visitar(viz, caminho + [viz])
                if achado:
                    return achado
        cor[no] = PRETO
        return None

    for no in grafo:
        if cor[no] == BRANCO:
            achado = visitar(no, [no])
            if achado:
                return achado
    return None


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------


def raiz_do_conteudo() -> Path:
    """`CURSOS_CONTEUDO_DIR` manda; senão, `conteudo/cursos` ao lado deste
    arquivo — que é onde ele está tanto no repo quanto na imagem Docker
    (`COPY aluno/backend/ /app/` leva a pasta junto, ao contrário do canon da
    redação, que precisou de uma linha própria)."""
    override = os.environ.get("CURSOS_CONTEUDO_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / "conteudo" / "cursos"


def _ler_json(caminho: Path) -> tuple[dict | None, str | None]:
    try:
        with caminho.open(encoding="utf-8") as f:
            dados = json.load(f)
    except FileNotFoundError:
        return None, "arquivo não encontrado"
    except json.JSONDecodeError as exc:
        return None, f"JSON inválido: {exc}"
    except OSError as exc:  # noqa: BLE001
        return None, f"não foi possível ler: {exc}"
    if not isinstance(dados, dict):
        return None, "o arquivo precisa conter um objeto JSON"
    return dados, None


def carregar(raiz: Path | str | None = None, *, catalogo: Iterable[str] | None = None) -> Biblioteca:
    """Lê a pasta inteira e devolve o que é servível + o que foi recusado.

    `catalogo` é a lista de `curso_id` que existem no produto; por padrão sai
    de `cursos.CURSOS`. É parâmetro para o teste poder validar conteúdo contra
    um catálogo de mentira sem mexer no de verdade.
    """
    if catalogo is None:
        import cursos as _catalogo_de_produto
        catalogo = [c.curso_id for c in _catalogo_de_produto.CURSOS]

    base = Path(raiz) if raiz else raiz_do_conteudo()
    cursos_ok: dict[str, CursoConteudo] = {}
    problemas: list[Problema] = []

    if not base.is_dir():
        # Não é erro: é o estado normal enquanto o conteúdo está sendo
        # produzido. A aba de Cursos continua vendendo a pré-venda e as telas
        # de estudo simplesmente não aparecem.
        logger.info("Sem pasta de conteúdo de cursos em %s — nada a carregar.", base)
        return Biblioteca(cursos={}, problemas=(), raiz=str(base))

    for pasta in sorted(p for p in base.iterdir() if p.is_dir()):
        curso_id = pasta.name
        manifesto, erro = _ler_json(pasta / "curso.json")
        if erro:
            problemas.append(Problema(curso_id, "curso.json", erro))
            continue

        locais = validar_manifesto(manifesto)
        if manifesto.get("curso_id") and manifesto["curso_id"] != curso_id:
            locais.append(
                f"`curso_id` do arquivo (`{manifesto['curso_id']}`) é diferente do nome da "
                f"pasta (`{curso_id}`) — o caminho é o endereço, os dois têm de concordar"
            )
        problemas += [Problema(curso_id, "curso.json", m) for m in locais]

        brutas: dict[str, dict] = {}
        pasta_estacoes = pasta / "estacoes"
        if pasta_estacoes.is_dir():
            for arquivo in sorted(pasta_estacoes.glob("*.json")):
                dados, erro = _ler_json(arquivo)
                if erro:
                    problemas.append(Problema(curso_id, f"estacoes/{arquivo.name}", erro))
                    continue
                nome = arquivo.stem
                erros = validar_estacao(dados)
                if dados.get("estacao_id") and dados["estacao_id"] != nome:
                    erros.append(
                        f"`estacao_id` (`{dados['estacao_id']}`) é diferente do nome do "
                        f"arquivo (`{nome}.json`)"
                    )
                problemas += [Problema(curso_id, f"estacoes/{arquivo.name}", m) for m in erros]
                if not erros:
                    brutas[nome] = dados
        else:
            problemas.append(Problema(curso_id, "estacoes/", "pasta `estacoes/` ausente"))

        if not locais:
            problemas += [
                Problema(curso_id, "curso.json", m)
                for m in _validar_integridade(manifesto, brutas, catalogo)
            ]

        if any(p.curso_id == curso_id for p in problemas):
            # Regra do topo: curso com qualquer problema não é servido. Melhor
            # ausente e visível no painel do que pela metade e silencioso.
            logger.warning(
                "Curso `%s` fora do ar: %d problema(s) de conteúdo.",
                curso_id, sum(1 for p in problemas if p.curso_id == curso_id),
            )
            continue

        cursos_ok[curso_id] = _montar(curso_id, manifesto, brutas)

    if problemas:
        logger.warning("Conteúdo de cursos com %d problema(s).", len(problemas))
    logger.info("Conteúdo de cursos carregado: %d curso(s) de %s.", len(cursos_ok), base)
    return Biblioteca(cursos=cursos_ok, problemas=tuple(problemas), raiz=str(base))


def _montar(curso_id: str, manifesto: dict, brutas: dict[str, dict]) -> CursoConteudo:
    trilhas: list[Trilha] = []
    estacoes: dict[str, Estacao] = {}

    for trilha in manifesto["trilhas"]:
        ids = tuple(trilha["estacoes"])
        trilhas.append(Trilha(
            trilha_id=trilha["trilha_id"],
            curso_id=curso_id,
            titulo=trilha["titulo"],
            resumo=trilha.get("resumo"),
            estacoes=ids,
        ))
        for ordem, eid in enumerate(ids):
            d = brutas[eid]
            estacoes[eid] = Estacao(
                estacao_id=eid,
                curso_id=curso_id,
                trilha_id=trilha["trilha_id"],
                titulo=d["titulo"],
                objetivo=d["objetivo"],
                versao=str(d["versao"]),
                blocos=tuple(d["blocos"]),
                pre_requisitos=tuple(d.get("pre_requisitos") or ()),
                habilidades=tuple(d.get("habilidades") or ()),
                conceitos=tuple(d.get("conceitos") or ()),
                numero=d.get("numero"),
                duracao_minutos=d.get("duracao_minutos"),
                conclusao=dict(d.get("conclusao") or {"tipo": CONCLUSAO_TODOS}),
                ordem=ordem,
            )

    return CursoConteudo(
        curso_id=curso_id,
        versao=str(manifesto["versao"]),
        trilhas=tuple(trilhas),
        estacoes=estacoes,
    )


_BIBLIOTECA: Biblioteca | None = None
# Cursos que não vieram de arquivo: foram compilados de texto no painel do
# admin e vivem no Mongo (ver `cursos_publicados`). Entram por cima do disco e
# são servidos exatamente como os outros — quem estuda não tem como saber de
# onde o conteúdo veio, e é assim que tem de ser.
_PUBLICADOS: dict[str, CursoConteudo] = {}
_MESCLADA: Biblioteca | None = None


def _mesclar() -> Biblioteca:
    """Disco + publicados pelo admin, numa biblioteca só.

    A regra de precedência é uma: **o que foi publicado pelo admin vence**. Ele
    é o mais recente por definição (o arquivo em git precisa de deploy para
    mudar; o painel muda agora), e a alternativa — o arquivo vencer — faria o
    admin publicar uma correção e não ver diferença nenhuma na tela.
    """
    base = _BIBLIOTECA or Biblioteca(cursos={}, problemas=(), raiz=str(raiz_do_conteudo()))
    if not _PUBLICADOS:
        return base
    return Biblioteca(
        cursos={**base.cursos, **_PUBLICADOS},
        problemas=base.problemas,
        raiz=base.raiz,
    )


def biblioteca() -> Biblioteca:
    """A biblioteca em memória. Custa I/O uma vez por processo."""
    global _BIBLIOTECA, _MESCLADA
    if _BIBLIOTECA is None:
        _BIBLIOTECA = carregar()
        _MESCLADA = None
    if _MESCLADA is None:
        _MESCLADA = _mesclar()
    return _MESCLADA


def recarregar(raiz: Path | str | None = None) -> Biblioteca:
    """Relê do disco. Usado no boot, nos testes e pelo botão do admin — que
    existe para conferir conteúdo recém-publicado sem reiniciar o processo."""
    global _BIBLIOTECA, _MESCLADA
    _BIBLIOTECA = carregar(raiz)
    _MESCLADA = None
    return biblioteca()


def do_disco() -> Biblioteca:
    """Só o que veio de arquivo, sem o que o admin publicou por cima.

    É a base sobre a qual o conteúdo do painel é montado: acrescentar uma
    estação a um curso que já existe em arquivo exige enxergar o arquivo
    original, e não o resultado da última mesclagem (que já teria a estação
    nova dentro, e se somaria a si mesmo a cada publicação)."""
    global _BIBLIOTECA
    if _BIBLIOTECA is None:
        _BIBLIOTECA = carregar()
    return _BIBLIOTECA


def aplicar_publicados(cursos: dict[str, CursoConteudo]) -> Biblioteca:
    """Troca o conjunto de cursos publicados pelo admin. Chamada por
    `cursos_publicados` depois de ler o Mongo — aqui não se fala com banco."""
    global _PUBLICADOS, _MESCLADA
    _PUBLICADOS = dict(cursos)
    _MESCLADA = None
    return biblioteca()


def compor(
    curso_id: str,
    manifesto: dict,
    estacoes: dict[str, dict],
    *,
    catalogo: Iterable[str] | None = None,
) -> tuple[CursoConteudo | None, list[str]]:
    """Valida um curso inteiro que veio de memória (e não de arquivo).

    É o MESMO validador do disco, de propósito: conteúdo publicado pelo painel
    passa pelas mesmas cinco regras que conteúdo publicado por commit —
    gabarito que existe, progressão que não retrocede, id que não se repete,
    pré-requisito sem ciclo e nenhum preço declarado em conteúdo. Um segundo
    validador "mais fácil" para o caminho do admin seria uma porta dos fundos
    para o conteúdo quebrado que a regra do topo deste arquivo existe para
    impedir.

    Devolve `(curso, problemas)`. Com qualquer problema, o curso é `None`:
    servir metade é pior que não servir.
    """
    if catalogo is None:
        import cursos as _catalogo_de_produto
        catalogo = [c.curso_id for c in _catalogo_de_produto.CURSOS]

    do_manifesto = validar_manifesto(manifesto)
    problemas = list(do_manifesto)
    if manifesto.get("curso_id") and manifesto["curso_id"] != curso_id:
        problemas.append(
            f"`curso_id` do manifesto (`{manifesto['curso_id']}`) é diferente do curso "
            f"que está sendo publicado (`{curso_id}`)"
        )
    validas: dict[str, dict] = {}
    for eid, dados in estacoes.items():
        erros = validar_estacao(dados)
        if dados.get("estacao_id") and dados["estacao_id"] != eid:
            erros.append(
                f"`estacao_id` (`{dados['estacao_id']}`) é diferente do endereço "
                f"da estação (`{eid}`)"
            )
        problemas += [f"{eid}: {m}" for m in erros]
        if not erros:
            validas[eid] = dados

    # Integridade só faz sentido com o manifesto de pé: com ele quebrado, a
    # varredura de trilhas produziria uma cascata de erros derivados do
    # primeiro, e quem lê a lista não acha o que consertar.
    if not do_manifesto:
        problemas += _validar_integridade(manifesto, validas, catalogo)

    if problemas:
        return None, problemas
    return _montar(curso_id, manifesto, validas), []


def estacao_para_dados(estacao: Estacao) -> dict:
    """O caminho de volta: uma `Estacao` carregada vira o dicionário que a
    gerou. É o que permite ACRESCENTAR uma estação a um curso que já existe em
    arquivo sem reescrever o arquivo — o admin publica o conjunto inteiro, e o
    conjunto inteiro precisa incluir o que já estava lá."""
    dados = {
        "schema_version": SCHEMA_VERSION,
        "estacao_id": estacao.estacao_id,
        "titulo": estacao.titulo,
        "objetivo": estacao.objetivo,
        "versao": estacao.versao,
        "blocos": [dict(b) for b in estacao.blocos],
        "conclusao": dict(estacao.conclusao),
    }
    if estacao.numero is not None:
        dados["numero"] = estacao.numero
    if estacao.duracao_minutos is not None:
        dados["duracao_minutos"] = estacao.duracao_minutos
    for campo, valor in (
        ("pre_requisitos", estacao.pre_requisitos),
        ("habilidades", estacao.habilidades),
        ("conceitos", estacao.conceitos),
    ):
        if valor:
            dados[campo] = list(valor)
    return dados


def manifesto_do_curso(curso: CursoConteudo) -> dict:
    """Idem, para o manifesto: trilhas e ordem, do jeito que o validador lê."""
    return {
        "schema_version": SCHEMA_VERSION,
        "curso_id": curso.curso_id,
        "versao": curso.versao,
        "trilhas": [
            {
                "trilha_id": t.trilha_id,
                "titulo": t.titulo,
                **({"resumo": t.resumo} if t.resumo else {}),
                "estacoes": list(t.estacoes),
            }
            for t in curso.trilhas
        ],
    }


# ---------------------------------------------------------------------------
# O que o aluno pode ver, e a correção
# ---------------------------------------------------------------------------


def sanitizar_bloco(bloco: dict) -> dict:
    """O bloco como ele vai para o navegador.

    Gabarito, dica, feedback e solução NUNCA saem daqui: quem corrige é o
    servidor, e o aluno recebe cada uma dessas coisas na hora em que ela
    ensina alguma coisa (ver `feedback_da_tentativa`). O produto já tem um
    teste dedicado a isso no banco de questões (`test_gabarito_nao_vaza`);
    esta é a mesma regra, do outro lado da casa.
    """
    if bloco.get("tipo") not in ("exercicio", "desafio"):
        return dict(bloco)

    limpo = {
        k: v for k, v in bloco.items()
        # `referencia` é a resposta esperada do dissertativo: sai daqui pelo
        # mesmo motivo que o gabarito. `criterios` FICA — é a régua, e o aluno
        # escreve melhor sabendo o que vai ser cobrado.
        if k not in ("gabarito", "feedback", "dica", "solucao", "referencia")
    }
    if bloco.get("formato") == "multipla_escolha":
        limpo["alternativas"] = [
            {"id": a["id"], "texto": a["texto"]} for a in bloco.get("alternativas", [])
        ]
    # A tela precisa saber que existe dica sem saber qual é: é ela que decide
    # mostrar "pedir uma dica" em vez de um botão morto.
    limpo["tem_dica"] = bool(bloco.get("dica"))
    return limpo


def _normalizar(texto: str) -> str:
    import unicodedata
    sem_acento = unicodedata.normalize("NFKD", texto.strip().lower())
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento)


def corrigir(bloco: dict, resposta: Any) -> tuple[bool, str]:
    """Corrige uma resposta. Devolve `(acertou, chave_do_feedback)`.

    A chave é o que endereça o feedback específico: a alternativa escolhida no
    múltipla escolha (é ali que mora a explicação do erro que ESTA pessoa
    cometeu), e `correto`/`incorreto` nos demais formatos.
    """
    formato = bloco.get("formato")

    if formato == "multipla_escolha":
        escolha = str(resposta).strip() if resposta is not None else ""
        return escolha == bloco.get("gabarito"), escolha

    if formato == "numerico":
        gabarito = bloco.get("gabarito") or {}
        try:
            valor = float(str(resposta).strip().replace(",", "."))
        except (TypeError, ValueError):
            return False, "incorreto"
        tolerancia = float(gabarito.get("tolerancia", 0) or 0)
        acertou = abs(valor - float(gabarito["valor"])) <= tolerancia
        return acertou, "correto" if acertou else "incorreto"

    if formato == "texto_curto":
        aceitos = {(_normalizar(a)) for a in (bloco.get("gabarito") or {}).get("aceitos", [])}
        acertou = _normalizar(str(resposta or "")) in aceitos
        return acertou, "correto" if acertou else "incorreto"

    if formato == "dissertativo":
        # Deliberado: o servidor não tem como julgar um texto. Quem chama
        # `corrigir()` num dissertativo errou de caminho — a rota dedicada
        # (`/dissertativa`) pede o veredito à Mentis e o traz pronto.
        raise ValueError("dissertativo não se corrige aqui: o veredito vem da Mentis")

    # Formato desconhecido chegou até aqui = validador deixou passar. Nunca
    # dar acerto por omissão: isso concluiria a estação sem o aluno acertar.
    logger.error("Formato de exercício sem correção: %r", formato)
    return False, "incorreto"


def feedback_da_tentativa(bloco: dict, chave: str, acertou: bool, tentativa: int) -> dict:
    """A escada didática: o servidor decide QUANTO revelar, e quando.

    * acertou → o comentário da resposta certa e a resolução completa, que
      agora é reforço e não gabarito entregue.
    * 1º erro → só a dica. O aluno ainda tem o que pensar.
    * 2º erro → o comentário específico do que ele escolheu (é aqui que mora
      o "por que a sua conta deu isso"), se o conteúdo tiver escrito um.
    * 3º erro em diante → a resolução. Insistir além disso não ensina mais
      nada e transforma a estação num muro.

    `tentativa` é a contagem JÁ INCLUINDO esta.
    """
    resposta: dict[str, Any] = {"acertou": acertou, "tentativa": tentativa}
    feedback = bloco.get("feedback") or {}

    if acertou:
        if feedback.get(chave):
            resposta["comentario"] = feedback[chave]
        if bloco.get("solucao"):
            resposta["solucao"] = bloco["solucao"]
        return resposta

    if tentativa <= 1:
        if bloco.get("dica"):
            resposta["dica"] = bloco["dica"]
        elif feedback.get(chave):
            resposta["comentario"] = feedback[chave]
        return resposta

    if feedback.get(chave):
        resposta["comentario"] = feedback[chave]
    elif feedback.get("incorreto"):
        resposta["comentario"] = feedback["incorreto"]
    if bloco.get("dica"):
        resposta["dica"] = bloco["dica"]
    if tentativa >= 3 and bloco.get("solucao"):
        resposta["solucao"] = bloco["solucao"]
    return resposta


# ---------------------------------------------------------------------------
# Inventário — a tela de quem PRODUZ o conteúdo
# ---------------------------------------------------------------------------


def inventario(bib: Biblioteca | None = None, *, catalogo: Iterable[str] | None = None) -> dict:
    """O estado da produção de conteúdo, por curso.

    Responde as perguntas que a equipe de conteúdo faz toda semana: quantas
    estações já existem, quantos exercícios por nível (é isso que mostra se a
    progressão é real ou se o curso inteiro está no nível 2), quantos vídeos
    faltam gravar e quais cursos do catálogo ainda não têm nada.
    """
    bib = bib or biblioteca()
    if catalogo is None:
        import cursos as _catalogo_de_produto
        catalogo = [c.curso_id for c in _catalogo_de_produto.CURSOS]

    por_curso = []
    for curso_id in catalogo:
        curso = bib.curso(curso_id)
        problemas = [p for p in bib.problemas if p.curso_id == curso_id]
        if curso is None:
            por_curso.append({
                "curso_id": curso_id,
                "publicado": False,
                "estacoes": 0,
                "problemas": [{"arquivo": p.arquivo, "mensagem": p.mensagem} for p in problemas],
            })
            continue

        niveis: dict[int, int] = {}
        exercicios = desafios = videos = videos_pendentes = 0
        habilidades: set[str] = set()
        minutos = 0
        for est in curso.estacoes.values():
            minutos += est.duracao_minutos or 0
            habilidades |= set(est.habilidades)
            for b in est.blocos:
                if b["tipo"] == "exercicio":
                    exercicios += 1
                    niveis[b["nivel"]] = niveis.get(b["nivel"], 0) + 1
                elif b["tipo"] == "desafio":
                    desafios += 1
                elif b["tipo"] == "video":
                    videos += 1
                    if not b.get("ref"):
                        videos_pendentes += 1

        por_curso.append({
            "curso_id": curso_id,
            "publicado": True,
            "versao": curso.versao,
            "trilhas": [
                {"trilha_id": t.trilha_id, "titulo": t.titulo, "estacoes": len(t.estacoes)}
                for t in curso.trilhas
            ],
            "estacoes": len(curso.estacoes),
            "exercicios": exercicios,
            "desafios": desafios,
            "exercicios_por_nivel": {str(n): niveis.get(n, 0) for n in range(NIVEL_MIN, NIVEL_MAX + 1)},
            "videos": videos,
            "videos_pendentes": videos_pendentes,
            "habilidades": sorted(habilidades),
            "duracao_minutos": minutos,
            "problemas": [],
        })

    # Pastas que não correspondem a curso nenhum do catálogo aparecem também:
    # são conteúdo escrito que não tem como chegar a aluno nenhum.
    conhecidos = set(catalogo)
    orfaos = sorted({p.curso_id for p in bib.problemas if p.curso_id not in conhecidos})
    for curso_id in orfaos:
        por_curso.append({
            "curso_id": curso_id,
            "publicado": False,
            "estacoes": 0,
            "problemas": [
                {"arquivo": p.arquivo, "mensagem": p.mensagem}
                for p in bib.problemas if p.curso_id == curso_id
            ],
        })

    return {
        "raiz": bib.raiz,
        "schema_version": SCHEMA_VERSION,
        "cursos": por_curso,
        "problemas_totais": len(bib.problemas),
    }
