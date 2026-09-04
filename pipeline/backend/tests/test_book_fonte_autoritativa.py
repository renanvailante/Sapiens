"""`banca`/`ano`/`prova` do caderno são fonte autoritativa, nunca inferida.

Cobre a exigência: os metadados fornecidos pelo usuário no upload do caderno
(`/api/book/upload`) têm que sobrepor qualquer coisa que o modelo produza em
`fonte`, e `numero` continua vindo da questão dentro do caderno. Não depende
de rede, Mongo nem Gemini — importa `server` diretamente (mesmo padrão de
`test_contratos_canonicos.py`, mais o carregamento do módulo do servidor, que
não abre conexão de verdade na importação).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from server import _book_fonte_conhecida  # noqa: E402


class TestBookFonteConhecida:
    def test_reune_banca_ano_prova_do_caderno_e_numero_da_questao(self):
        book = {"banca": "ENEM", "ano": 2023, "prova": "Azul"}
        assert _book_fonte_conhecida(book, "137") == {
            "numero": 137, "banca": "ENEM", "ano": 2023, "prova": "Azul",
        }

    def test_numero_nao_numerico_e_preservado_como_string(self):
        book = {"banca": "ENEM", "ano": 2023, "prova": "Azul"}
        assert _book_fonte_conhecida(book, "23-bis")["numero"] == "23-bis"

    def test_caderno_antigo_sem_metadados_nao_forca_campos_ausentes(self):
        """Cadernos criados antes desta exigência não têm banca/ano/prova
        gravados — omitir em vez de forçar `None` evita apagar uma inferência
        do modelo com um valor pior do que ela (nenhuma informação)."""
        book = {}
        assert _book_fonte_conhecida(book, "5") == {"numero": 5}


class TestUploadBookValidacao:
    """Exercita só a validação de `/api/book/upload`, sem rede: chama a
    função da rota diretamente com um FastAPI UploadFile fake."""

    @staticmethod
    def _run(coro):
        import asyncio
        return asyncio.new_event_loop().run_until_complete(coro)

    def test_banca_com_variacao_de_caixa_e_recusada_para_enem(self):
        import server
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            self._run(server.upload_book(files=[], banca="Enem", ano=2023, prova="Azul"))
        assert exc_info.value.status_code == 400
        assert "ENEM" in exc_info.value.detail

    def test_banca_vazia_e_recusada(self):
        import server
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            self._run(server.upload_book(files=[], banca="   ", ano=2023, prova="Azul"))
        assert exc_info.value.status_code == 400

    def test_prova_vazia_e_recusada(self):
        import server
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            self._run(server.upload_book(files=[], banca="ENEM", ano=2023, prova="  "))
        assert exc_info.value.status_code == 400

    def test_ano_fora_do_intervalo_plausivel_e_recusado(self):
        import server
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            self._run(server.upload_book(files=[], banca="ENEM", ano=1500, prova="Azul"))
        assert exc_info.value.status_code == 400
