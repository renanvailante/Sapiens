"""`GET /sparks/packages/vitrine` — catálogo público (sem login) para a
landing anunciar preço real sem hardcode ("preço nunca é escrito à mão", ver
`Cerebro/produto/economia-de-sparks.md`). Offline: chamada direta da função
da rota, sem servidor HTTP nem Mongo.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import sparks_routes as sr  # noqa: E402
import sparks_store  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


class TestVitrinePublica:
    def test_nao_exige_nenhuma_dependencia_de_autenticacao(self):
        """A rota não declara `Depends(require_user)`/`Depends(require_admin)`
        — é o que a torna de fato acessível sem sessão para a landing."""
        import inspect

        assinatura = inspect.signature(sr.list_packages_publico)
        assert len(assinatura.parameters) == 0

    def test_devolve_o_mesmo_preco_do_catalogo_autoritativo(self):
        resultado = _run(sr.list_packages_publico())
        pacotes = {p["package_id"]: p for p in resultado["packages"]}
        catalogo = {p.package_id: p for p in sparks_store.list_packages() if not p.oculto}

        assert set(pacotes) == set(catalogo)
        for pid, pacote_publico in pacotes.items():
            real = catalogo[pid]
            assert pacote_publico["price_cents"] == real.price_cents
            assert pacote_publico["sparks_amount"] == real.sparks_amount
            assert pacote_publico["beneficios"] == list(real.beneficios)

    def test_pacote_oculto_de_teste_nunca_aparece(self):
        resultado = _run(sr.list_packages_publico())
        assert all(not p.get("oculto", False) for p in resultado["packages"])
        ids = {p["package_id"] for p in resultado["packages"]}
        ocultos_reais = {p.package_id for p in sparks_store.list_packages() if p.oculto}
        assert ids.isdisjoint(ocultos_reais)

    def test_nao_vaza_nenhum_campo_alem_do_que_a_vitrine_precisa(self):
        """Nada de `direitos` (nome interno de campo booleano) nem qualquer
        outro campo administrativo — só o que uma pessoa sem conta precisa
        pra decidir se cria uma."""
        resultado = _run(sr.list_packages_publico())
        campos_esperados = {"package_id", "label", "sparks_amount", "price_cents", "currency", "highlight", "beneficios"}
        for pacote in resultado["packages"]:
            assert set(pacote) == campos_esperados

    def test_o_pacote_de_119_90_tem_a_mensagem_de_mentis_por_30_dias(self):
        """Trava a regra comercial de 2026-09-21 na PONTA que a landing lê —
        se a copy do catálogo divergir da vitrine pública, é aqui que quebra
        primeiro, antes de virar uma promessa errada na landing."""
        resultado = _run(sr.list_packages_publico())
        pacote_4000 = next(p for p in resultado["packages"] if p["package_id"] == "spark_4000")
        texto = " ".join(pacote_4000["beneficios"]).lower()
        assert "30 dias" in texto
        assert "para sempre" not in texto
