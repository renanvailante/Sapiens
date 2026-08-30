"""Corretor de redação Enem — base local-first.

Ordem de leitura recomendada para quem for mexer aqui:
`canon.py` (dados) → `elegibilidade.py` + `heuristicas.py` (Nível 1-2, sem
rede) → `avaliador_local.py` (combina tudo via `decision_gate`) →
`escalonamento_redacao.py` (só o que sobrou indeterminado) → `pontuacao.py`
(monta o resultado final) → `service.py` (orquestra a sequência).
"""
