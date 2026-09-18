"""O conteúdo de um e-book: páginas de leitura, nada mais.

Irmão pequeno de `cursos_conteudo`, e deliberadamente mais simples. Um curso
tem trilha, estação, pré-requisito, progressão de nível e exercício corrigido;
um e-book é só um material para LER — a estrutura aqui é achatada em
`paginas`, e cada página é uma lista de blocos dos mesmos três tipos de
leitura que um curso usa (`texto`, `tabela`, `exemplo`). Não existe
`exercicio`, `desafio` nem `video`: quem quer praticar vai para um curso.

Por que arquivo e não banco, e por que preço não mora aqui: as mesmas duas
razões de `cursos_conteudo` — revisão por commit, custo zero de leitura em
produção (a biblioteca inteira carrega uma vez no boot), e preço é decisão de
produto que mora em `cursos.EBOOK_CUSTO_SPARKS`, nunca em conteúdo.

**Nenhum aluno baixa nada daqui.** O e-book se lê dentro do app, página por
página — não existe link de PDF na experiência do aluno. Baixar é operação de
admin, em outra tela, e não deste módulo.

Um e-book sem pasta de conteúdo (ou sem `paginas`) não é erro: é o estado
"em breve", o mesmo que um curso sem estação publicada. A prateleira continua
vendendo a pré-venda e a tela de leitura simplesmente não abre.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("sapiens.ebooks.conteudo")

SCHEMA_VERSION = "1.0"

_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TIPOS_DE_BLOCO = ("texto", "tabela", "exemplo")
VARIANTES_DE_TEXTO = ("padrao", "destaque", "atencao")

# Mesma regra 1 de `cursos_conteudo`: preço é decisão de produto e mora em
# `cursos.py`, nunca em arquivo de conteúdo.
CHAVES_PROIBIDAS = ("custo", "custo_sparks", "preco", "preço", "sparks", "valor_sparks", "desconto")


class ConteudoInvalido(ValueError):
    """Um arquivo de e-book não obedece ao contrato — sempre com a lista
    completa de problemas."""


@dataclass(frozen=True)
class PaginaDeEbook:
    pagina_id: str
    ebook_id: str
    titulo: str
    blocos: tuple[dict, ...]
    ordem: int = 0

    def bloco(self, bloco_id: str) -> dict | None:
        for b in self.blocos:
            if b.get("bloco_id") == bloco_id:
                return b
        return None


@dataclass(frozen=True)
class EbookConteudo:
    ebook_id: str
    versao: str
    paginas: tuple[PaginaDeEbook, ...]

    def pagina(self, pagina_id: str) -> PaginaDeEbook | None:
        for p in self.paginas:
            if p.pagina_id == pagina_id:
                return p
        return None


@dataclass(frozen=True)
class Problema:
    ebook_id: str
    arquivo: str
    mensagem: str

    def __str__(self) -> str:  # pragma: no cover - conveniência de log
        return f"[{self.ebook_id}] {self.arquivo}: {self.mensagem}"


@dataclass(frozen=True)
class Biblioteca:
    ebooks: dict[str, EbookConteudo]
    problemas: tuple[Problema, ...]
    raiz: str

    def ebook(self, ebook_id: str) -> EbookConteudo | None:
        return self.ebooks.get(ebook_id)

    def tem_conteudo(self, ebook_id: str) -> bool:
        e = self.ebooks.get(ebook_id)
        return bool(e and e.paginas)


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------


def _texto(valor: Any) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


def _chaves_proibidas(dados: Any, caminho: str = "") -> list[str]:
    achados: list[str] = []
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            onde = f"{caminho}.{chave}" if caminho else str(chave)
            if str(chave).lower() in CHAVES_PROIBIDAS:
                achados.append(
                    f"`{onde}` declara preço/moeda em arquivo de conteúdo. "
                    "Preço é decisão de produto e mora em `cursos.py`."
                )
            achados += _chaves_proibidas(valor, onde)
    elif isinstance(dados, list):
        for i, item in enumerate(dados):
            achados += _chaves_proibidas(item, f"{caminho}[{i}]")
    return achados


def _validar_bloco(bloco: Any, onde: str) -> list[str]:
    if not isinstance(bloco, dict):
        return [f"{onde} não é um objeto"]

    problemas: list[str] = []
    bloco_id = bloco.get("bloco_id", "")
    if not _texto(bloco_id) or not _ID.match(bloco_id):
        problemas.append(f"{onde}.bloco_id ausente ou fora do formato slug")

    tipo = bloco.get("tipo")
    if tipo not in TIPOS_DE_BLOCO:
        problemas.append(
            f"{onde}.tipo inválido: {tipo!r} (aceitos num e-book: {', '.join(TIPOS_DE_BLOCO)})"
        )
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
                    f"{onde}.linhas[{j}] tem número de células diferente do cabeçalho"
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

    return problemas


def validar_ebook(dados: dict, catalogo: set[str]) -> list[str]:
    """Um arquivo de e-book inteiro. Devolve todos os problemas de uma vez."""
    problemas = _chaves_proibidas(dados)

    versao_schema = dados.get("schema_version")
    if versao_schema is not None and str(versao_schema) != SCHEMA_VERSION:
        problemas.append(
            f"`schema_version` {versao_schema!r} não é a suportada ({SCHEMA_VERSION})"
        )

    ebook_id = dados.get("ebook_id", "")
    if not _texto(ebook_id) or not _ID.match(ebook_id):
        problemas.append("`ebook_id` ausente ou fora do formato slug")
    elif ebook_id not in catalogo:
        problemas.append(
            f"`{ebook_id}` não existe em `cursos.EBOOKS` — conteúdo só entra em e-book "
            "que já está no catálogo"
        )

    if not _texto(str(dados.get("versao", ""))):
        problemas.append("`versao` ausente")

    paginas = dados.get("paginas")
    if not isinstance(paginas, list) or not paginas:
        problemas.append("`paginas` precisa ter pelo menos uma página")
        return problemas

    ids_vistos: set[str] = set()
    for i, pagina in enumerate(paginas):
        onde = f"paginas[{i}]"
        if not isinstance(pagina, dict):
            problemas.append(f"{onde} não é um objeto")
            continue
        pid = pagina.get("pagina_id", "")
        if not _texto(pid) or not _ID.match(pid):
            problemas.append(f"{onde}.pagina_id ausente ou fora do formato slug")
        elif pid in ids_vistos:
            problemas.append(f"{onde}.pagina_id `{pid}` repetido — cada página precisa de um id único")
        else:
            ids_vistos.add(pid)
        if not _texto(pagina.get("titulo")):
            problemas.append(f"{onde}.titulo ausente")

        blocos = pagina.get("blocos")
        if not isinstance(blocos, list) or not blocos:
            problemas.append(f"{onde}.blocos precisa ter pelo menos um bloco")
            continue
        ids_de_bloco: set[str] = set()
        for j, bloco in enumerate(blocos):
            problemas += _validar_bloco(bloco, f"{onde}.blocos[{j}]")
            bid = bloco.get("bloco_id") if isinstance(bloco, dict) else None
            if bid:
                if bid in ids_de_bloco:
                    problemas.append(f"{onde}.blocos[{j}].bloco_id `{bid}` repetido na página")
                ids_de_bloco.add(bid)

    return problemas


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------


def raiz_do_conteudo() -> Path:
    override = os.environ.get("EBOOKS_CONTEUDO_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / "conteudo" / "ebooks"


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


def _montar(ebook_id: str, dados: dict) -> EbookConteudo:
    paginas = tuple(
        PaginaDeEbook(
            pagina_id=p["pagina_id"],
            ebook_id=ebook_id,
            titulo=p["titulo"],
            blocos=tuple(p["blocos"]),
            ordem=i,
        )
        for i, p in enumerate(dados["paginas"])
    )
    return EbookConteudo(ebook_id=ebook_id, versao=str(dados["versao"]), paginas=paginas)


def carregar(raiz: Path | str | None = None, *, catalogo: set[str] | None = None) -> Biblioteca:
    if catalogo is None:
        import cursos as _catalogo_de_produto
        catalogo = {e.ebook_id for e in _catalogo_de_produto.EBOOKS}

    base = Path(raiz) if raiz else raiz_do_conteudo()
    ebooks_ok: dict[str, EbookConteudo] = {}
    problemas: list[Problema] = []

    if not base.is_dir():
        logger.info("Sem pasta de conteúdo de e-books em %s — nada a carregar.", base)
        return Biblioteca(ebooks={}, problemas=(), raiz=str(base))

    for arquivo in sorted(base.glob("*.json")):
        ebook_id = arquivo.stem
        dados, erro = _ler_json(arquivo)
        if erro:
            problemas.append(Problema(ebook_id, arquivo.name, erro))
            continue

        erros = validar_ebook(dados, catalogo)
        if dados.get("ebook_id") and dados["ebook_id"] != ebook_id:
            erros.append(
                f"`ebook_id` do arquivo (`{dados['ebook_id']}`) é diferente do nome do "
                f"arquivo (`{ebook_id}.json`) — o nome do arquivo é o endereço"
            )
        if erros:
            problemas += [Problema(ebook_id, arquivo.name, m) for m in erros]
            logger.warning("E-book `%s` fora do ar: %d problema(s) de conteúdo.", ebook_id, len(erros))
            continue

        ebooks_ok[ebook_id] = _montar(ebook_id, dados)

    logger.info("Conteúdo de e-books carregado: %d de %s.", len(ebooks_ok), base)
    return Biblioteca(ebooks=ebooks_ok, problemas=tuple(problemas), raiz=str(base))


_BIBLIOTECA: Biblioteca | None = None


def biblioteca() -> Biblioteca:
    global _BIBLIOTECA
    if _BIBLIOTECA is None:
        _BIBLIOTECA = carregar()
    return _BIBLIOTECA


def recarregar(raiz: Path | str | None = None) -> Biblioteca:
    global _BIBLIOTECA
    _BIBLIOTECA = carregar(raiz)
    return _BIBLIOTECA


def inventario(bib: Biblioteca | None = None) -> dict:
    bib = bib or biblioteca()
    return {
        "raiz": bib.raiz,
        "ebooks": {
            eid: {"paginas": len(e.paginas)}
            for eid, e in bib.ebooks.items()
        },
        "problemas": [
            {"ebook_id": p.ebook_id, "arquivo": p.arquivo, "mensagem": p.mensagem}
            for p in bib.problemas
        ],
    }
