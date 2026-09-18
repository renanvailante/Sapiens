"""O contrato de conteúdo dos e-books: o que a carga aceita e o que recusa.

Irmão pequeno de `test_cursos_conteudo.py`, na mesma disciplina: o conteúdo
entra por commit, em lote, e o validador é quem garante que um arquivo com
problema fica fora do ar em vez de meio publicado. O que doeria, na ordem:

1. Preço declarado em conteúdo — decisão de produto, mora em `cursos.py`.
2. Um `ebook_id` que não existe no catálogo (`cursos.EBOOKS`).
3. Página ou bloco com id repetido — são a chave de `pagina()`/`bloco()`.
4. Um tipo de bloco que um e-book não aceita (`exercicio`, `video`...) — quem
   quer praticar vai para um curso.

Tudo offline: os e-books de exemplo são escritos em `tmp_path`. O último
teste, e só ele, valida a pasta REAL de conteúdo do produto.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import ebooks_conteudo as ec  # noqa: E402

CATALOGO = {"ebook-de-teste"}


def _pagina(pagina_id: str, **extra) -> dict:
    base = {
        "pagina_id": pagina_id,
        "titulo": "Página de teste",
        "blocos": [{"tipo": "texto", "bloco_id": "t1", "markdown": "Texto de teste."}],
    }
    base.update(extra)
    return base


def _ebook(ebook_id: str = "ebook-de-teste", **extra) -> dict:
    base = {
        "schema_version": "1.0",
        "ebook_id": ebook_id,
        "versao": "2026-09-17",
        "paginas": [_pagina("p1")],
    }
    base.update(extra)
    return base


def _escrever(raiz: Path, arquivo: str, dados: dict) -> Path:
    raiz.mkdir(parents=True, exist_ok=True)
    caminho = raiz / arquivo
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return caminho


class TestCarga:
    def test_pasta_ausente_nao_e_erro(self, tmp_path):
        bib = ec.carregar(tmp_path / "nao-existe", catalogo=CATALOGO)
        assert bib.ebooks == {}
        assert bib.problemas == ()

    def test_ebook_valido_carrega_com_paginas_e_blocos(self, tmp_path):
        _escrever(tmp_path, "ebook-de-teste.json", _ebook())
        bib = ec.carregar(tmp_path, catalogo=CATALOGO)
        assert not bib.problemas
        e = bib.ebook("ebook-de-teste")
        assert e is not None
        assert e.versao == "2026-09-17"
        assert len(e.paginas) == 1
        pagina = e.pagina("p1")
        assert pagina is not None
        assert pagina.bloco("t1")["markdown"] == "Texto de teste."
        assert bib.tem_conteudo("ebook-de-teste")

    def test_ebook_id_do_arquivo_diferente_do_nome_e_recusado(self, tmp_path):
        _escrever(tmp_path, "ebook-de-teste.json", _ebook(ebook_id="outro-id"))
        bib = ec.carregar(tmp_path, catalogo=CATALOGO | {"outro-id"})
        assert bib.ebooks == {}
        assert any("nome do arquivo" in p.mensagem for p in bib.problemas)

    def test_ebook_fora_do_catalogo_e_recusado(self, tmp_path):
        _escrever(tmp_path, "fantasma.json", _ebook(ebook_id="fantasma"))
        bib = ec.carregar(tmp_path, catalogo=CATALOGO)
        assert bib.ebooks == {}
        assert any("não existe em" in p.mensagem for p in bib.problemas)


class TestPrecoNaoMoraEmConteudo:
    def test_custo_sparks_em_qualquer_nivel_e_recusado(self, tmp_path):
        dados = _ebook()
        dados["paginas"][0]["blocos"][0]["custo_sparks"] = 50
        _escrever(tmp_path, "ebook-de-teste.json", dados)
        bib = ec.carregar(tmp_path, catalogo=CATALOGO)
        assert bib.ebooks == {}
        assert any("preço/moeda" in p.mensagem for p in bib.problemas)


class TestTiposDeBloco:
    def test_exercicio_nao_e_aceito_num_ebook(self, tmp_path):
        dados = _ebook()
        dados["paginas"][0]["blocos"] = [{
            "tipo": "exercicio", "bloco_id": "x1", "formato": "multipla_escolha",
            "enunciado": "?", "alternativas": [], "gabarito": "a",
        }]
        _escrever(tmp_path, "ebook-de-teste.json", dados)
        bib = ec.carregar(tmp_path, catalogo=CATALOGO)
        assert bib.ebooks == {}
        assert any("tipo inválido" in p.mensagem for p in bib.problemas)

    def test_tabela_e_exemplo_sao_aceitos(self, tmp_path):
        dados = _ebook()
        dados["paginas"][0]["blocos"] = [
            {"tipo": "tabela", "bloco_id": "tb1", "colunas": ["A", "B"], "linhas": [["1", "2"]]},
            {"tipo": "exemplo", "bloco_id": "ex1", "enunciado": "Resolva.",
             "passos": [{"texto": "Passo 1."}]},
        ]
        _escrever(tmp_path, "ebook-de-teste.json", dados)
        bib = ec.carregar(tmp_path, catalogo=CATALOGO)
        assert not bib.problemas
        assert bib.ebook("ebook-de-teste") is not None


class TestIdentificadoresUnicos:
    def test_pagina_id_repetida_e_recusada(self, tmp_path):
        dados = _ebook()
        dados["paginas"] = [_pagina("p1"), _pagina("p1")]
        _escrever(tmp_path, "ebook-de-teste.json", dados)
        bib = ec.carregar(tmp_path, catalogo=CATALOGO)
        assert bib.ebooks == {}
        assert any("repetido" in p.mensagem for p in bib.problemas)

    def test_bloco_id_repetido_na_mesma_pagina_e_recusado(self, tmp_path):
        dados = _ebook()
        dados["paginas"][0]["blocos"] = [
            {"tipo": "texto", "bloco_id": "t1", "markdown": "Um."},
            {"tipo": "texto", "bloco_id": "t1", "markdown": "Outro."},
        ]
        _escrever(tmp_path, "ebook-de-teste.json", dados)
        bib = ec.carregar(tmp_path, catalogo=CATALOGO)
        assert bib.ebooks == {}
        assert any("repetido na página" in p.mensagem for p in bib.problemas)


class TestPastaReal:
    def test_a_pasta_real_de_conteudo_carrega_sem_explodir(self):
        """Sem asserção de conteúdo — só que a carga da pasta de produto (hoje
        vazia, "em breve") não levanta exceção nenhuma."""
        bib = ec.recarregar()
        assert isinstance(bib.ebooks, dict)
