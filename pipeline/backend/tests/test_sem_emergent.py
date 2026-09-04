"""Garante que nenhuma dependência da Emergent voltou a entrar na plataforma.

A Emergent foi removida em 2026-08-21. Estes testes rodam offline e falham se
alguém reintroduzir a dependência por qualquer via — import, host, variável de
ambiente, pacote npm ou requirement.

Referências históricas em comentário são permitidas de propósito: explicar o que
foi removido e por quê é o que impede a remoção de ser desfeita por engano.
O que os testes proíbem é dependência **funcional**.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent.parent
sys.path.insert(0, str(BACKEND))

APPS = ("aluno", "pipeline", "professor")

# Linha de código (não comentário, não docstring) que mencione a Emergent.
_COMENTARIO_PY = re.compile(r"^\s*#")
_COMENTARIO_JS = re.compile(r"^\s*(//|\*|/\*)")


def _arquivos(padrao: str, *subdirs: str) -> list[Path]:
    aqui = Path(__file__).resolve()
    out: list[Path] = []
    for app in APPS:
        for sub in subdirs:
            base = ROOT / app / sub
            if base.is_dir():
                out += [
                    p for p in base.rglob(padrao)
                    if "node_modules" not in p.parts
                    and "venv" not in p.parts
                    and ".venv" not in p.parts
                    # este próprio arquivo cita os hosts para poder procurá-los
                    and p.resolve() != aqui
                ]
    return out


def _linhas_de_codigo(p: Path) -> list[tuple[int, str]]:
    comentario = _COMENTARIO_PY if p.suffix == ".py" else _COMENTARIO_JS
    dentro_docstring = False
    saida: list[tuple[int, str]] = []
    for i, linha in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if p.suffix == ".py":
            aspas = linha.count('"""') + linha.count("'''")
            if aspas % 2:
                dentro_docstring = not dentro_docstring
                continue
            if dentro_docstring:
                continue
        if comentario.match(linha):
            continue
        saida.append((i, linha))
    return saida


def test_nenhum_import_de_sdk_da_emergent():
    """`emergentintegrations` era o proxy de LLM; foi substituído por google-genai."""
    ofensores = []
    for p in _arquivos("*.py", "backend"):
        if p.name.startswith("test_") or p.name == "backend_test.py":
            continue
        for n, linha in _linhas_de_codigo(p):
            if re.search(r"^\s*(import|from)\s+emergent", linha):
                ofensores.append(f"{p.relative_to(ROOT)}:{n}")
    assert not ofensores, f"import da Emergent reintroduzido: {ofensores}"


def test_nenhum_host_da_emergent_em_codigo_executavel():
    ofensores = []
    for padrao, subdirs in (("*.py", ("backend",)), ("*.js", ("frontend/src",)), ("*.jsx", ("frontend/src",))):
        for p in _arquivos(padrao, *subdirs):
            for n, linha in _linhas_de_codigo(p):
                if "emergentagent.com" in linha or "assets.emergent.sh" in linha:
                    ofensores.append(f"{p.relative_to(ROOT)}:{n}: {linha.strip()[:80]}")
    assert not ofensores, f"host da Emergent em código executável: {ofensores}"


def test_nenhum_requirement_da_emergent():
    ofensores = []
    for app in APPS:
        req = ROOT / app / "backend" / "requirements.txt"
        if not req.is_file():
            continue
        for n, linha in enumerate(req.read_text(encoding="utf-8").splitlines(), 1):
            if linha.strip().startswith("#"):
                continue
            if "emergent" in linha.lower():
                ofensores.append(f"{app}:{n}: {linha.strip()}")
    assert not ofensores, f"requirement da Emergent: {ofensores}"


def test_nenhum_pacote_npm_da_emergent():
    ofensores = []
    for app in APPS:
        pkg = ROOT / app / "frontend" / "package.json"
        if not pkg.is_file():
            continue
        data = json.loads(pkg.read_text(encoding="utf-8"))
        for sec in ("dependencies", "devDependencies", "optionalDependencies"):
            for nome, versao in (data.get(sec) or {}).items():
                if "emergent" in nome.lower() or "emergent" in str(versao).lower():
                    ofensores.append(f"{app}/{sec}/{nome}")
    assert not ofensores, f"pacote npm da Emergent: {ofensores}"


def test_nenhuma_variavel_de_ambiente_da_emergent():
    """`EMERGENT_LLM_KEY` era a credencial única do proxy e do object storage."""
    ofensores = []
    for app in APPS:
        for sub in ("backend", "frontend"):
            env = ROOT / app / sub / ".env"
            if env.is_file() and "EMERGENT" in env.read_text(encoding="utf-8").upper():
                ofensores.append(f"{app}/{sub}/.env")
    assert not ofensores, f"variável da Emergent: {ofensores}"


def test_nenhum_diretorio_de_bootstrap_da_emergent():
    """`.emergent/cron/*.sh` eram scripts de cron/webhook da plataforma."""
    assert not [app for app in APPS if (ROOT / app / ".emergent").exists()]


def test_craco_nao_carrega_plugin_de_edicao_visual():
    ofensores = [
        app for app in APPS
        if (ROOT / app / "frontend" / "craco.config.js").is_file()
        and "emergentbase" in (ROOT / app / "frontend" / "craco.config.js").read_text(encoding="utf-8")
    ]
    assert not ofensores, f"craco ainda referencia @emergentbase: {ofensores}"


# ---------------------------------------------------------------- storage
def test_storage_local_faz_round_trip_sem_rede(tmp_path, monkeypatch):
    """O modo padrão grava em disco: o pipeline roda sem credencial nenhuma."""
    import storage

    monkeypatch.setattr(storage, "STORAGE_MODE", "local")
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path)
    caminho = storage.build_path("original", "q-1", "prova.pdf")
    storage.put_object(caminho, b"%PDF-1.7 conteudo", "application/pdf")
    data, content_type = storage.get_object(caminho)
    assert data == b"%PDF-1.7 conteudo"
    # o content-type precisa sobreviver: o download do artefato o devolve ao cliente
    assert content_type == "application/pdf"


def test_storage_local_recusa_caminho_que_escapa_da_raiz(tmp_path, monkeypatch):
    """`build_path` compõe nomes de arquivo enviados pelo usuário."""
    import storage

    monkeypatch.setattr(storage, "STORAGE_MODE", "local")
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path)
    with pytest.raises(ValueError, match="fora da raiz"):
        storage.put_object("../../etc/senha", b"x", "text/plain")


def test_storage_delete_prefix_remove_a_arvore(tmp_path, monkeypatch):
    import storage

    monkeypatch.setattr(storage, "STORAGE_MODE", "local")
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path)
    for kind in ("original", "extraction", "pipeline"):
        storage.put_object(storage.build_path(kind, "q-9", f"{kind}.bin"), b"x", "application/octet-stream")
    assert storage.delete_prefix(f"{storage.APP_NAME}/questions/q-9") == 3
    assert storage.delete_prefix(f"{storage.APP_NAME}/questions/q-9") == 0


def test_storage_get_de_objeto_ausente_falha_explicitamente(tmp_path, monkeypatch):
    import storage

    monkeypatch.setattr(storage, "STORAGE_MODE", "local")
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path)
    with pytest.raises(FileNotFoundError):
        storage.get_object(storage.build_path("original", "inexistente", "x.pdf"))


def test_storage_put_object_deduped_grava_uma_vez_por_conteudo(tmp_path, monkeypatch):
    """Mesmo conteúdo (mesmo caderno reprocessado por questão, ou mesmo
    arquivo reenfileirado) deve cair no mesmo objeto, não numa cópia nova —
    é a correção da duplicação de 90x medida na auditoria de custo de imagem."""
    import storage

    monkeypatch.setattr(storage, "STORAGE_MODE", "local")
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path)

    conteudo = b"%PDF-1.7 caderno inteiro"
    r1 = storage.put_object_deduped(conteudo, "application/pdf", "caderno.pdf")
    assert r1["deduped"] is False

    r2 = storage.put_object_deduped(conteudo, "application/pdf", "caderno.pdf")
    assert r2["deduped"] is True
    assert r2["path"] == r1["path"]

    # só existe um arquivo de fato no disco para as duas "gravações"
    arquivos = [
        p for p in (tmp_path / storage.APP_NAME / "blobs").rglob("*")
        if p.is_file() and not p.name.endswith(storage._CONTENT_TYPE_SIDECAR)
    ]
    assert len(arquivos) == 1

    data, content_type = storage.get_object(r1["path"])
    assert data == conteudo
    assert content_type == "application/pdf"


def test_storage_put_object_deduped_conteudo_diferente_grava_objetos_distintos(tmp_path, monkeypatch):
    import storage

    monkeypatch.setattr(storage, "STORAGE_MODE", "local")
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path)

    r1 = storage.put_object_deduped(b"conteudo A", "application/pdf", "a.pdf")
    r2 = storage.put_object_deduped(b"conteudo B", "application/pdf", "b.pdf")
    assert r1["path"] != r2["path"]
