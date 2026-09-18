"""Dublês mínimos de Mongo (Motor) para testes offline do corretor de
redação — sem banco real, síncronos por baixo mas com a mesma interface
`async def` que o código de produção espera."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
from pymongo.errors import DuplicateKeyError

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def _chave_ordenavel(valor):
    """Ordena mesmo com `None` no meio (campo ausente em parte dos documentos).

    Comparar `None` com `str` ou `int` levanta `TypeError` em Python, e é
    exatamente o que acontece quando se ordena por um campo opcional —
    `destacada_ate` só existe em dúvida destacada. O Mongo põe ausente/nulo
    ANTES de tudo na ordem crescente; a tupla `(0, "")` reproduz isso.
    """
    if valor is None:
        return (0, "")
    if isinstance(valor, bool):
        return (1, int(valor))
    if isinstance(valor, (int, float)):
        return (1, valor)
    return (2, str(valor))


def _avaliar_expr(expr, doc: dict):
    """Avalia a expressão de agregação do `$addFields` usada pelo mural:
    referência de campo (`"$campo"`), `$cond`, `$gt`. Nada além disso — um
    operador novo deve falhar alto aqui, não devolver `None` calado."""
    if isinstance(expr, str) and expr.startswith("$"):
        return doc.get(expr[1:])
    if isinstance(expr, dict):
        if "$cond" in expr:
            teste, entao, senao = expr["$cond"]
            return entao if _avaliar_expr(teste, doc) else senao
        if "$gt" in expr:
            a, b = (_avaliar_expr(x, doc) for x in expr["$gt"])
            return a is not None and b is not None and a > b
        raise NotImplementedError(f"expressão {list(expr)} não suportada pelo dublê")
    return expr


class FakeCursor:
    """`sort` e `limit` ORDENAM e CORTAM de verdade.

    Eram no-ops que devolviam `self`. Um teste de ranking (quem está em 1º na
    liga) ou de "a resposta marcada como melhor aparece primeiro" passava sem
    provar nada: a ordem que ele observava era a de inserção, não a que o Mongo
    real produziria. Um dublê que aceita a chamada e ignora o efeito é pior que
    um que não a suporta — o segundo quebra, o primeiro mente.
    """

    def __init__(self, docs: list[dict]):
        self._docs = docs
        self._i = 0

    def sort(self, campo_ou_lista, direcao: int = 1):
        pares = (
            list(campo_ou_lista)
            if isinstance(campo_ou_lista, (list, tuple))
            else [(campo_ou_lista, direcao)]
        )
        for campo, dir_ in reversed(pares):
            self._docs.sort(key=lambda d: _chave_ordenavel(d.get(campo)), reverse=dir_ < 0)
        return self

    def limit(self, n: int):
        if n:
            self._docs = self._docs[:n]
        return self

    def skip(self, n: int):
        if n:
            self._docs = self._docs[n:]
        return self

    async def to_list(self, length=None):
        return list(self._docs)

    def __aiter__(self):
        self._i = 0
        return self

    async def __anext__(self):
        if self._i >= len(self._docs):
            raise StopAsyncIteration
        doc = self._docs[self._i]
        self._i += 1
        return doc


class FakeUpdateResult:
    """`UpdateResult` do PyMongo expõe `matched_count` E `modified_count`; o
    dublê só tinha o primeiro. A distinção importa para quem conta o que de
    fato mudou (a exclusão de conta reporta quantos pagamentos anonimizou).
    Aqui os dois são iguais porque o dublê sempre aplica o update que casou."""

    def __init__(self, matched_count: int, upserted_id=None, modified_count: int | None = None):
        self.matched_count = matched_count
        # Por padrão, casou = modificou (o que basta para a maioria dos
        # chamadores). `update_one` passa o valor de verdade, comparando o
        # documento antes e depois — ver o comentário lá.
        self.modified_count = matched_count if modified_count is None else modified_count
        # `UpdateResult.upserted_id` é como se distingue "criei o documento
        # agora" de "já existia e nada mudou" — os dois chegam com
        # `modified_count == 0`. A guarda de chave única do motor de
        # engajamento (`registrar_acao(chave_unica=...)`) depende dessa
        # diferença para não pagar XP duas vezes pelo mesmo bloco.
        self.upserted_id = upserted_id


class FakeDeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


class FakeCollection:
    """Suporte mínimo: find_one/update_one(upsert)/insert_one/find. Consultas
    são casamento exato de campo — suficiente para os testes deste módulo,
    que nunca fazem filtro composto complexo."""

    def __init__(self):
        self.docs: list[dict] = []

    def _ne(atual, alvo) -> bool:
        # Mongo real: `$ne` sobre um campo-array testa se o valor NÃO é um
        # elemento do array, não igualdade de lista inteira contra escalar.
        if isinstance(atual, list):
            return alvo not in atual
        return atual != alvo

    _OPS = {
        "$in": lambda atual, alvo: atual in alvo,
        "$gt": lambda atual, alvo: atual is not None and atual > alvo,
        "$gte": lambda atual, alvo: atual is not None and atual >= alvo,
        "$lt": lambda atual, alvo: atual is not None and atual < alvo,
        "$lte": lambda atual, alvo: atual is not None and atual <= alvo,
        "$ne": _ne,
        # Usado pela exclusão de conta para alcançar documentos cujo `_id` é
        # composto (`"{uid}|{chave}"`), em `mentis_intervencoes_abertas`.
        "$regex": lambda atual, alvo: bool(
            isinstance(atual, str) and __import__("re").search(alvo, atual)
        ),
    }

    @staticmethod
    def _caminho(doc: dict, caminho: str):
        """Resolve `"a.b"` e também `"lista.0"` — índice numérico dentro de
        array, que é como o Mongo pergunta "esta lista tem pelo menos um
        elemento?" (`{"reportada_por.0": {"$exists": true}}`, a consulta da
        fila de moderação)."""
        alvo = doc
        for parte in caminho.split("."):
            if isinstance(alvo, list):
                if not parte.isdigit() or int(parte) >= len(alvo):
                    return None
                alvo = alvo[int(parte)]
            elif isinstance(alvo, dict):
                alvo = alvo.get(parte)
            else:
                return None
        return alvo

    def _bate(self, doc: dict, query: dict) -> bool:
        for k, v in query.items():
            # `$or` é operador de nível de consulta, não nome de campo.
            if k == "$or":
                if not any(self._bate(doc, sub) for sub in v):
                    return False
                continue
            if isinstance(v, dict) and "$exists" in v:
                if (self._caminho(doc, k) is not None) != bool(v["$exists"]):
                    return False
                continue
            atual = self._caminho(doc, k) if "." in k else doc.get(k)
            if isinstance(v, dict) and any(op in v for op in self._OPS):
                for op, esperado in v.items():
                    if not self._OPS[op](atual, esperado):
                        return False
            elif isinstance(atual, list) and not isinstance(v, list):
                # Mongo real: igualdade direta contra um campo-array testa se
                # o valor é um ELEMENTO do array (ex.: `{"mostrada_para": uid}`).
                if v not in atual:
                    return False
            elif atual != v:
                return False
        return True

    @staticmethod
    def _projetar(doc: dict, projection: dict | None) -> dict:
        """Aplica a projeção como o Mongo real: `{"campo": 0}` exclui,
        `{"campo": 1}` inclui só o que foi pedido, e `_id` é o único campo que
        pode ser excluído no meio de uma projeção de inclusão.

        O dublê ignorava a projeção e devolvia o documento inteiro. Isso não é
        só imprecisão: `admin_routes.list_users` depende de
        `{"password_hash": 0}` para o hash de senha de todo aluno não sair na
        resposta de uma tela de admin, e nenhum teste conseguia provar isso —
        o dublê devolvia o hash e o servidor não.
        """
        if not projection:
            return dict(doc)
        incluir = {k for k, v in projection.items() if v and k != "_id"}
        if incluir:
            saida = {k: doc[k] for k in incluir if k in doc}
            if projection.get("_id") and "_id" in doc:
                saida["_id"] = doc["_id"]
            return saida
        excluir = {k for k, v in projection.items() if not v}
        return {k: v for k, v in doc.items() if k not in excluir}

    async def find_one(self, query: dict, projection: dict | None = None, sort=None):
        candidatos = [d for d in self.docs if self._bate(d, query)]
        if sort:
            for campo, direcao in reversed(list(sort)):
                candidatos.sort(key=lambda d: d.get(campo) or "", reverse=direcao < 0)
        return self._projetar(candidatos[0], projection) if candidatos else None

    @staticmethod
    def _set_dotted(doc: dict, caminho: str, valor) -> None:
        """`$set` do Mongo real interpreta `"a.b"` como campo aninhado, não
        como uma chave plana `"a.b"` — precisa disso para `respostas.{uid}`."""
        partes = caminho.split(".")
        alvo = doc
        for p in partes[:-1]:
            alvo = alvo.setdefault(p, {})
        alvo[partes[-1]] = valor

    @staticmethod
    def _get_dotted(doc: dict, caminho: str):
        alvo = doc
        for p in caminho.split("."):
            if not isinstance(alvo, dict):
                return None
            alvo = alvo.get(p)
        return alvo

    def _aplicar_update(self, doc: dict, update: dict, *, inserindo: bool = False) -> None:
        # `$setOnInsert` só vale quando o upsert de fato CRIOU o documento —
        # era ignorado sempre, e com isso todo documento nascido de upsert no
        # dublê vinha sem os campos de nascimento (o `liga_id` da liga, a
        # identificação do progresso de uma estação). O teste via um documento
        # que o Mongo real nunca produziria.
        if inserindo:
            for campo, valor in (update.get("$setOnInsert") or {}).items():
                self._set_dotted(doc, campo, valor)
        for campo, valor in (update.get("$set") or {}).items():
            self._set_dotted(doc, campo, valor)
        # `$inc` cria o campo com o incremento quando ele não existe, igual ao
        # Mongo real — é disso que dependem os contadores por par do
        # microdiagnóstico, que nunca são pré-criados.
        for campo, valor in (update.get("$inc") or {}).items():
            atual = self._get_dotted(doc, campo) or 0
            self._set_dotted(doc, campo, atual + valor)
        for campo, valor in (update.get("$push") or {}).items():
            lista = doc.setdefault(campo, [])
            lista.extend(valor["$each"] if isinstance(valor, dict) and "$each" in valor else [valor])
        # `$pull` com valor escalar remove TODAS as ocorrências dele da lista.
        # A exclusão de conta usa isto para desvincular o aluno de uma questão
        # gerada por IA sem apagar a questão, que é conteúdo e não dado pessoal.
        for campo, valor in (update.get("$pull") or {}).items():
            lista = doc.get(campo)
            if isinstance(lista, list):
                doc[campo] = [x for x in lista if x != valor]
        for campo, valor in (update.get("$addToSet") or {}).items():
            lista = doc.setdefault(campo, [])
            itens = valor["$each"] if isinstance(valor, dict) and "$each" in valor else [valor]
            for item in itens:
                if item not in lista:
                    lista.append(item)

    async def insert_one(self, doc: dict):
        """Aplica a unicidade de `_id` do Mongo real. Sem isto, o dublê
        aceitaria duas reivindicações com a mesma chave e os testes de
        idempotência de `redacao_routes` passariam sem provar nada — a
        garantia inteira depende de `DuplicateKeyError` acontecer."""
        _id = doc.get("_id")
        if _id is not None and any(d.get("_id") == _id for d in self.docs):
            raise DuplicateKeyError(f"E11000 duplicate key error: _id {_id!r}")
        self.docs.append(dict(doc))

    async def insert_many(self, docs: list[dict]):
        for doc in docs:
            await self.insert_one(doc)

    async def find_one_and_update(self, query: dict, update: dict, return_document=True, **kwargs):
        for doc in self.docs:
            if self._bate(doc, query):
                self._aplicar_update(doc, update)
                return dict(doc)
        return None

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        for doc in self.docs:
            if self._bate(doc, query):
                # `modified_count` é 0 quando o update CASOU mas não mudou
                # nada — `$addToSet` de um elemento que já está na lista, ou
                # `$set` do mesmo valor. O dublê devolvia 1 nesses casos, e com
                # isso toda guarda do tipo "só passa se eu fui quem inseriu"
                # (a chave única do motor de engajamento) parecia funcionar no
                # teste e não funcionava no Mongo. Comparar antes/depois é a
                # única forma de o dublê contar a mesma coisa que o banco.
                antes = copy.deepcopy(doc)
                self._aplicar_update(doc, update)
                return FakeUpdateResult(matched_count=1, modified_count=int(antes != doc))
        if upsert:
            # `$ne`/`$gt` e afins no filtro são CONDIÇÃO de busca, não valor
            # inicial: o Mongo não cria um campo com `{"$ne": "x"}` dentro.
            novo = {k: v for k, v in query.items() if not isinstance(v, dict)}
            self._aplicar_update(novo, update, inserindo=True)
            self.docs.append(novo)
            return FakeUpdateResult(matched_count=0, upserted_id=novo.get("_id", True))
        return FakeUpdateResult(matched_count=0)

    async def update_many(self, query: dict, update: dict):
        n = 0
        for doc in self.docs:
            if self._bate(doc, query):
                self._aplicar_update(doc, update)
                n += 1
        return FakeUpdateResult(matched_count=n)

    async def delete_many(self, query: dict):
        antes = len(self.docs)
        self.docs = [d for d in self.docs if not self._bate(d, query)]
        return FakeDeleteResult(antes - len(self.docs))

    async def delete_one(self, query: dict):
        for i, d in enumerate(self.docs):
            if self._bate(d, query):
                del self.docs[i]
                return FakeDeleteResult(1)
        return FakeDeleteResult(0)

    def find(self, query: dict | None = None, projection: dict | None = None):
        query = query or {}
        return FakeCursor(
            [self._projetar(d, projection) for d in self.docs if self._bate(d, query)]
        )

    async def count_documents(self, query: dict | None = None):
        return len([d for d in self.docs if self._bate(d, query or {})])

    def aggregate(self, pipeline: list[dict]):
        """Suporte a `$match`, `$addFields`, `$sort`, `$skip`, `$limit` e
        `$project` — os estágios que o mural de dúvidas usa.

        O mural precisa de agregação por um motivo real: "destaque comprado
        sobe ao topo ENQUANTO vale" é uma ordenação por um campo que não está
        guardado (a comparação de `destacada_ate` com o instante de agora).
        Sem `$addFields`, um destaque VENCIDO continuaria ordenando acima de
        todo mundo — o aluno teria comprado 24h e levado para sempre.
        """
        docs = [dict(d) for d in self.docs]
        for estagio in pipeline:
            (op, arg), = estagio.items()
            if op == "$match":
                docs = [d for d in docs if self._bate(d, arg)]
            elif op == "$addFields":
                for d in docs:
                    for campo, expr in arg.items():
                        d[campo] = _avaliar_expr(expr, d)
            elif op == "$sort":
                for campo, direcao in reversed(list(arg.items())):
                    docs.sort(key=lambda d: _chave_ordenavel(d.get(campo)), reverse=direcao < 0)
            elif op == "$skip":
                docs = docs[arg:]
            elif op == "$limit":
                docs = docs[:arg]
            elif op == "$project":
                docs = [self._projetar(d, arg) for d in docs]
            else:  # pragma: no cover - estágio novo precisa entrar aqui de propósito
                raise NotImplementedError(f"estágio {op} não suportado pelo dublê")
        return FakeCursor(docs)


class FakeDB:
    def __init__(self):
        self._colecoes: dict[str, FakeCollection] = {}

    def __getitem__(self, nome: str) -> FakeCollection:
        # Motor real aceita `db["colecao"]` além de `db.colecao`. Quem monta o
        # nome da coleção a partir de uma lista (a exclusão de conta percorre
        # um inventário) precisa desta forma.
        return getattr(self, nome)

    def __getattr__(self, nome: str) -> FakeCollection:
        return self._colecoes.setdefault(nome, FakeCollection())


@pytest.fixture
def fake_db() -> FakeDB:
    return FakeDB()


# ---------------------------------------------------------------------------
# Isolamento dos caches de processo entre testes
# ---------------------------------------------------------------------------
#
# Vários módulos do backend guardam cache em variável de PROCESSO, de propósito:
# é o que impede uma requisição custar O(eventos) no Firestore (ver
# `project_aluno_disciplina_leitura_firestore`). Em produção isso é a feature;
# entre testes, é estado de um teste vazando para o seguinte — e o sintoma
# nunca aponta para o culpado, porque a vítima está noutro arquivo.
#
# O ciclo adaptativo acrescentou três caches desse tipo (`revisao_service._MEMO`,
# `curadoria._DOCS`, `microdiagnostico._MEMO`), e esta fixture existe para que
# eles nasçam isolados em vez de virarem a próxima falha de ordem. Os caches
# que já existiam entram na mesma limpeza.
#
# NÃO resolve a falha de ordem conhecida de
# `test_diagnostico_real.py::test_padrao_associado_so_aparece_para_processo_fraco_e_inequivoco`,
# que é anterior a este trabalho (reproduz em HEAD limpo, sem nenhum módulo
# novo) e vem do dublê de Mongo que sobra em `annotation_service._db` depois de
# outros arquivos — `_agregado_com_cache` passa então pelo caminho de cache em
# vez do atalho de `_db is None`. Corrigir exige decidir quem é dono de `_db`
# nos testes, o que é mudança nos testes alheios e merece ser feita de
# propósito, não de raspão.


@pytest.fixture(autouse=True)
def _caches_de_processo_limpos():
    """Zera os caches de processo antes e depois de CADA teste."""

    def _limpar():
        import annotation_service

        annotation_service._ITEM_INDEX = None
        for modulo, atributo, vazio in (
            ("motor_cognitivo", "_CACHE", {}),
            ("motor_cognitivo", "_HISTORICO_MEMO", {}),
            ("portao_crenca", "_cache", None),
            ("curadoria", "_DOCS", None),
            ("microdiagnostico", "_MEMO", {}),
            ("revisao_service", "_MEMO", {}),
            # A biblioteca de conteúdo dos cursos é carregada uma vez por
            # processo de propósito (abrir uma trilha não pode custar I/O).
            # Entre testes, é o conteúdo de mentira de um vazando para o
            # seguinte — e quem falha é sempre outro arquivo.
            ("cursos_conteudo", "_BIBLIOTECA", None),
            ("cursos_conteudo", "_MESCLADA", None),
            ("cursos_conteudo", "_PUBLICADOS", {}),
        ):
            try:
                mod = __import__(modulo)
            except Exception:  # noqa: BLE001
                continue
            atual = getattr(mod, atributo, None)
            if isinstance(atual, dict) and isinstance(vazio, dict):
                atual.clear()
            else:
                setattr(mod, atributo, vazio)

    _limpar()
    yield
    _limpar()


@pytest.fixture(autouse=True)
def _sem_firestore_real(monkeypatch):
    """Nenhum teste alcança o Firestore de VERDADE.

    Não era assim. `tests/test_resumo_sessao.py` faz `import server` dentro de
    um teste, e `server` chama `set_db` em vários módulos — entre eles
    `annotation_service`. Esse `_db` é global de módulo e fica ligado pelo
    resto do processo, então TODOS os testes seguintes deixavam de usar o
    caminho offline e passavam a falar com a infraestrutura real: o Mongo da
    máquina e o projeto Firestore de PRODUÇÃO (`sapiens-dataset`, o mesmo que
    atende aluno). Consequências medidas:

    * `test_diagnostico_real.py::test_padrao_associado_...` passava sozinho e
      falhava na suíte, porque `_agregado_com_cache` servia um documento de
      cache que sobrara no Mongo local em vez de chamar o leitor dublado;
    * rodar `pytest` queimava cota de leitura do projeto que já saiu do ar por
      estouro de cota em 04/09.

    Bloquear aqui resolve os dois de uma vez e torna a falha BARULHENTA: quem
    escrever um teste que dependa do Firestore real vê esta mensagem em vez de
    um resultado que muda conforme a máquina de quem roda.

    Quem precisa de Firestore no teste substitui `get_firestore` pelo próprio
    dublê — `monkeypatch` do teste roda depois desta fixture e vence.
    """
    import firestore_service

    monkeypatch.setattr(firestore_service, "get_firestore", lambda *a, **k: _ClienteSemRede())


@pytest.fixture(autouse=True)
def _sem_mongo_real_no_engajamento():
    """A outra metade do vazamento descrito acima: o MONGO da máquina.

    `_sem_firestore_real` fecha o Firestore, mas o `_db` que `import server`
    espalha é um cliente de Mongo REAL, e ele continuava ligado nos módulos que
    ninguém redublava. O motor de engajamento tornou isso visível: as rotas de
    responder questão, concluir bloco e corrigir redação agora chamam
    `registrar_acao`, então rodar a suíte escrevia XP, contador do dia e linha
    de LIGA no banco local, em nome dos usuários de fixture (`U1`, `U-cron`).

    O sintoma foi bizarro e instrutivo: a liga do desenvolvedor aparecia com
    dois competidores que nunca existiram — a suíte de testes fabricando
    exatamente os adversários fantasmas que `engajamento.py` promete não criar.

    Com `_db = None`, `registrar_acao` sai pelo atalho de "sem Mongo" e não
    escreve nada. Quem precisa do banco no teste põe o próprio dublê, que roda
    depois desta fixture e vence (é o que `test_engajamento.py` faz).
    """
    import comunidade
    import cursos_routes
    import engajamento_service
    import mentoria_routes
    import onboarding_routes

    # TODO MÓDULO NOVO QUE RECEBA `set_db` PRECISA ENTRAR AQUI. Sem isso a
    # suíte volta a escrever no Mongo da máquina, e o sintoma aparece longe da
    # causa (dados fantasma no banco, nenhum erro).
    modulos = (engajamento_service, comunidade, onboarding_routes, cursos_routes,
               mentoria_routes)
    for modulo in modulos:
        modulo.set_db(None)
    yield
    for modulo in modulos:
        modulo.set_db(None)


class _TransacaoFalsa:
    """Transação do Firestore com a única propriedade que importa aqui: as
    escritas só valem no commit, e na ORDEM em que foram enfileiradas.

    É o que deixa os testes de idempotência de Sparks exercitarem o commit
    atômico de verdade — se o `create` do comprovante falhar com
    `AlreadyExists`, o `update` do saldo nunca chega a rodar, exatamente como
    no servidor. Um dublê que aplicasse as escritas na hora esconderia
    justamente a falha que a transação existe para impedir.

    Os membros abaixo são o contrato que `firestore.transactional` consome
    (ver `firestore_v1/transaction.py`): `_read_only`, `_max_attempts`, `_id`,
    `_clean_up`, `_begin`, `_commit` e `_rollback`.
    """

    _read_only = False
    _max_attempts = 1
    _id = b"transacao-falsa"

    def __init__(self):
        self._pendentes: list[tuple[str, object, dict]] = []

    def _clean_up(self):
        self._pendentes = []

    def _begin(self, retry_id=None):
        self._pendentes = []

    def _rollback(self):
        self._pendentes = []

    def create(self, reference, document_data):
        self._pendentes.append(("create", reference, document_data))

    def update(self, reference, field_updates, option=None):
        self._pendentes.append(("update", reference, field_updates))

    def _commit(self):
        for operacao, ref, dados in self._pendentes:
            getattr(ref, operacao)(dados)
        self._pendentes = []
        return []


class _ClienteSemRede:
    """Cliente de Firestore que só sabe abrir transação.

    `transaction()` funciona porque o código de concessão de Sparks precisa
    dela e os testes substituem as referências de documento por dublês.
    Qualquer OUTRO uso — `collection()`, `document()` — estoura com a mensagem
    abaixo, que é o ponto: nenhum teste pode falar com o projeto de produção.
    """

    def transaction(self, **_kwargs):
        return _TransacaoFalsa()

    def __getattr__(self, nome):
        raise RuntimeError(
            f"Teste tentou usar o Firestore REAL (`get_firestore().{nome}`). "
            "Nenhum teste pode depender da infraestrutura de produção: o "
            "resultado passa a variar com a máquina de quem roda, e a execução "
            "gasta cota de leitura do projeto que atende aluno. Substitua o "
            "que você precisa por um dublê no próprio teste."
        )
