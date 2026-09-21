"""O 500 genérico precisa CHEGAR ao navegador — e não só ser enviado.

Um handler de `Exception` é servido pelo `ServerErrorMiddleware`, que no
Starlette é a camada mais externa de todas: a resposta dele nasce FORA do
`CORSMiddleware` e sai sem `Access-Control-Allow-Origin`. O navegador bloqueia
a leitura, o axios levanta um erro sem `response`, e o `errMsg` do frontend cai
no texto genérico ("Não foi possível entrar.").

Foi assim que o cadastro quebrado (2026-09-21) chegou como mistério: o servidor
respondia qual era o incidente e ninguém do outro lado conseguia ler.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import server  # noqa: E402


class _URL:
    path = "/api/auth/signup"


class _Request:
    method = "POST"
    url = _URL()

    def __init__(self, origem=None):
        self.headers = {"origin": origem} if origem else {}


def _responder(origem):
    return asyncio.run(server._erro_nao_tratado(_Request(origem), RuntimeError("falha qualquer")))


def test_erro_interno_nao_vaza_detalhe_interno():
    resposta = _responder("https://sapiens-aluno.pages.dev")
    corpo = json.loads(resposta.body)
    assert resposta.status_code == 500
    assert corpo["detail"] == "Erro interno."
    assert "falha qualquer" not in resposta.body.decode()
    assert corpo["incidente"]  # o identificador que liga a tela ao traceback


def test_origem_permitida_recebe_cors_e_consegue_ler_o_erro():
    resposta = _responder(server._origens_permitidas()[0])
    assert resposta.headers["access-control-allow-origin"] == server._origens_permitidas()[0]
    assert resposta.headers["access-control-allow-credentials"] == "true"


def test_origem_desconhecida_nao_ganha_cors():
    """O handler não é uma porta lateral para liberar origem que o middleware
    recusaria."""
    resposta = _responder("https://site-de-terceiro.exemplo")
    assert "access-control-allow-origin" not in resposta.headers


def test_sem_origem_nenhuma_continua_respondendo():
    """Chamada sem `Origin` (curl, servidor a servidor) não é caso de CORS e
    não pode virar erro no handler de erro."""
    resposta = _responder(None)
    assert resposta.status_code == 500
    assert "access-control-allow-origin" not in resposta.headers
