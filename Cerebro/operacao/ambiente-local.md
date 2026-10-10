---
tags: [operacao, dev, teste]
atualizado: 2026-10-10
---

# Ambiente local e testes

Duas armadilhas que falham em **silêncio** — nenhuma das duas dá erro, e o sintoma
aparece longe da causa.

## `.env.development.local` não funciona neste projeto

`aluno/frontend/craco.config.js`, linha 3, chama `require("dotenv").config()`, que
carrega o `.env` para `process.env` **antes** de o CRA ler os arquivos por
ambiente. Como o dotenv não sobrescreve variável já definida, o
`REACT_APP_BACKEND_URL` do `.env` — que aponta para **produção** — vence, e o dev
server fala com produção achando que fala com o local. O sintoma é **CORS no
console**, não um erro de configuração.

→ Passe a variável pelo **processo** (uma entrada temporária em
`.claude/launch.json` com `runtimeExecutable: "env"` e `REACT_APP_BACKEND_URL=...`
no início dos args), que vence o dotenv.

→ **Nunca edite `aluno/frontend/.env`**: é ele que o build do deploy usa, e outra
sessão publicando no meio derrubaria o frontend de produção para localhost. Ver
[[sessoes-concorrentes]].

## A suíte de testes escrevia no Mongo REAL da máquina

`import server` chama `set_db(db)` em vários módulos com um cliente de Mongo de
verdade, e esse `_db` é global de módulo — quem não for redublado pelo teste
seguinte continua ligado nele. Rodar `pytest` criava XP, contador do dia e linhas
de LIGA em nome dos usuários de fixture (`U1`, `U-cron`); a liga do desenvolvedor
aparecia com dois competidores que nunca existiram.

→ Corrigido pelas fixtures `_sem_mongo_real_no_engajamento` e `_sem_firestore_real`
em `tests/conftest.py`. **Todo módulo novo que receba `set_db` precisa entrar
nessa lista**, senão a suíte volta a escrever no banco da máquina.

## Tocar fora do repo: liberado, e o prompt que aparecia em bypass

Desde 2026-10-09 o agente pode ler e editar em **qualquer lugar da máquina** quando a
tarefa pedir — o dono revogou o veto antigo a tudo fora do repo. Só ficam as travas
de segurança (credencial, dinheiro, apagar dado de vez).

O prompt que parava o trabalho mesmo com bypass ligado vinha de
`blockReadsOutsideWorkingDirectories: true` na config global
(`~/.claude/settings.json`): qualquer leitura ou comando com caminho fora dos
diretórios de trabalho pedia aprovação. A chave foi **removida** no mesmo dia. Os
`additionalDirectories` do `.claude/settings.local.json` (memória do Claude e
`/private/tmp/claude-501`) eram o contorno e podem ficar. Se o prompt voltar, alguém
religou a chave — o dono pediu explicitamente para nunca ser interrompido assim.

## Convenções de teste

- **Backend, offline.** Chamada direta de função, `asyncio.run()` dentro de testes
  síncronos, sem `pytest-asyncio`. Fixture compartilhada `fake_db` em
  `tests/conftest.py` — um store em memória com forma de Motor
  (`find_one`/`update_one`/`insert_one`/`find`). Ele **impõe unicidade de `_id`**;
  sem isso os testes de idempotência passariam sem provar nada.
- **Frontend.** `CI=true npx craco test --watchAll=false`. O jest do CRA **não
  resolve `react-router-dom` 7** (ESM) — mocke com `{ virtual: true }`.
- **O que os testes travam de propósito** (se um quebrar, foi regra que voltou, não
  feature): `test_custo_firestore.py` (ordens de grandeza de leitura),
  `TestLinhaEtica` (ética da gamificação), `test_direitos_do_pacote.py` (a escada
  dos pacotes), `atalhos.test.js` (largura da barra), `ExplorarOSapiens.test.js`
  (ordem da primeira dobra do Painel), `Alternativas.test.js` (gabarito
  desconhecido nunca pinta verde), `test_mentis_nao_consegue_mover_bloco`.

## Coisas que só se veem abrindo o navegador

O projeto **não tem teste de componente**. Esta classe de defeito não aparece em
revisão de código nem em screenshot parado:

- cor errada no tema escuro → confira com `getComputedStyle`, não lendo classe;
- `:hover` → só passando o mouse (ver [[sistema-visual]]);
- largura de barra → meça no CSS **compilado**, não estime;
- alvo de toque e sobreposição → `elementFromPoint` em produção, porque
  `getBoundingClientRect` não enxerga área de `::before` (ver [[mobile]]).

**Login não é opção para o agente** — digitar senha é ação proibida por política,
mesmo a do próprio usuário. E o dev server local aponta para o backend de produção
e leva CORS em `/api/auth/me`, então nem haveria como. A alternativa que funciona:
no Browser pane, **sem login**, injetar por `javascript_tool` um clone do elemento
usando as classes reais do bundle, fora da tela, e medir. O CSS já está carregado
para qualquer visitante; só o **dado** exige sessão.

**Para percorrer telas LOGADAS de ponta a ponta:** `aluno/frontend/verificacao/
servidor_falso.py`. Um build com `REACT_APP_BACKEND_URL=http://localhost:8799`
(em `BUILD_PATH` fora da árvore — o `.env` não é tocado) servido pelo próprio
script, que responde às rotas com um aluno de teste na **mesma origem** (sem
CORS); o token de teste vai no `localStorage`. Instruções e cenários no
cabeçalho do arquivo. Foi como o fluxo Hoje → prática dirigida → fechamento e
o desfecho do Treino foram verificados em 2026-09-30.

**Com recarga a quente (2026-10-09):** o servidor falso responde CORS, então o
dev server pode falar com ele — `preview_start` com `aluno-verificacao` (porta
3010, `REACT_APP_BACKEND_URL` pelo processo) e o servidor rodando à parte. O
servidor **não sobe pelo `preview_start`**: o processo do painel não tem
permissão de ler `~/Documents` (macOS) e morre em "Operation not permitted";
rode-o por Bash em segundo plano. O cenário `dia_cheio` traz revisão vencida,
bloco de hoje e as três missões — a trilha do dia com todo tipo de nó.

> **Tela que quebra só ali é, primeiro, dado falso incompleto** (`ANCORA_BIOMA_SRC`
> exige id de bioma real; a liga lê `tabela`). O script loga `SEM MOCK GET …`
> para cada rota sem resposta própria — olhe ali antes de suspeitar do código.

Duas coisas mais que dá para provar sem sessão, e que valeram a pena em 18/09:

- **Os redirects.** `history.pushState` + `PopStateEvent` para cada endereço
  antigo, conferindo que nenhum cai na tela de "não encontrada". Deslogado,
  todos param em `/login`, que é a resposta certa: a rota existe e exige auth.
- **A barra, nos três viewports.** Ver a receita em [[navegacao]].

> **Armadilha do clone:** `c.querySelector("span:last-child")` devolve o
> primeiro casamento em ordem de documento, que pode ser um span aninhado
> dentro do ícone — não o rótulo. Meça o elemento pelo nome da classe.

---
Relacionado: [[deploy]] · [[sessoes-concorrentes]] · [[sistema-visual]] · [[mobile]]
