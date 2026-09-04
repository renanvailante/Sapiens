# Log de correções P0 — Sapiens

Contexto: auditoria completa em 2026-08-16 (ver histórico da sessão). Esta sessão resolve
os P0 identificados, em ordem arquitetural, sem tocar em P1/P2/P3.

Ordem planejada (2026-08-16T23:42Z):
1. pipeline: auth em todas as rotas mutáveis
2. professor: RBAC turma↔professor
3. professor: remover credenciais admin da tela de login
4. professor: seed_admin não deve sobrescrever senha existente
5. aluno: feed não deve expor is_correct antes da resposta
6. aluno: is_correct/acertou recalculado no backend (feed + response events)
7. aluno: fix crash de frontend em erro 422
8. pipeline+aluno: alinhar coleção Firestore (pipelines vs itens)
9. pipeline: não perder resultado do Gemini se object storage falhar
10. aluno: validar payload de behavior (Firestore) em vez de dict livre
11. 3 frontends: remover script emergent.sh + posthog do index.html

Status de cada item registrado abaixo conforme execução.

## [2026-08-16T23:44Z] 1/11 — Auth no pipeline ✅
- Adicionado `PIPELINE_API_KEY` (shared secret) via header `X-API-Key`, checado em
  `Depends(require_api_key)` aplicado a TODO o `api_router` (server.py).
- Chave gerada e colocada em `pipeline/backend/.env` (PIPELINE_API_KEY) e
  `pipeline/frontend/.env` (REACT_APP_PIPELINE_API_KEY).
- `pipeline/frontend/src/lib/api.js` agora manda o header em toda requisição.
- Testado: sem header → 401; com header → 200; rota destrutiva (`/ontology/reset`)
  sem header → 401. Frontend recarregado e dashboard carregando normal com a chave.
- Nota: é auth mínima (API key única), não RBAC por usuário — suficiente pra fechar
  o P0 de "zero auth", mas não substitui um sistema de usuários se isso vier a ser
  necessário depois (fora de escopo P0).

## [2026-08-16T23:47Z] 2/11 — RBAC professor↔turma ✅
- Novo `scope_query(user)` em professor/server.py: admin vê tudo; teacher só vê
  imports com `_ingested_by == seu email` ou `turma in user.turmas_autorizadas`.
- Aplicado em fetch_imports (todas as /views/*), list_imports, get_filters,
  taxonomia e delete_import.
- Testado: teacher sem vínculo agora recebe 404/listas vazias (antes vazava nome+nota
  de 8 alunos); admin continua vendo tudo.
- PENDENTE (fora de P0): não há UI para conceder `turmas_autorizadas` a um professor.
  Hoje só admin ou quem importou enxerga dados.

## [2026-08-16T23:48Z] 3/11 + 4/11 — Credenciais admin ✅
- Removido bloco "Conta de demonstração: admin@sapiens.edu / admin123" de LoginPage.jsx.
- seed_admin() não sobrescreve mais a senha de um admin existente; e não tem mais
  fallback hardcoded (se ADMIN_EMAIL/ADMIN_PASSWORD não estiverem no .env, pula o seed).
- Testado: troquei o hash da senha no Mongo, reiniciei, e a senha do .env NÃO foi
  re-imposta (login com admin123 deu 401). Depois restaurei admin123 para uso local.

## [2026-08-16T23:52Z] 5/11 + 6/11 + 7/11 — Confiança de dados no aluno ✅
- /feed não devolve mais `is_correct` nas alternativas (strip no backend).
- /feed/interactions recalcula certo/errado a partir do gabarito no banco e ignora
  o `is_correct` do cliente; só revela `correct_key` DEPOIS de o aluno responder.
- Feed.jsx agora revela com base na resposta do servidor, não em gabarito local.
- events_routes.py: `acertou` recalculado via novo helper `_grade()` (single + bulk);
  valor do cliente só é usado se o item não existir localmente (import histórico).
- Novo helper `errMsg()` em lib/api.js extrai string de erro do FastAPI (detail pode
  ser array em 422) — aplicado nos 6 pontos que crashavam o React.
- Testado: cliente enviou `is_correct:true` numa alternativa errada → servidor
  persistiu `false` e respondeu `correct_key:"B"`. Nenhum `is_correct` no /feed.
- Testado no browser: cadastro com email inválido agora mostra toast de erro em vez
  de derrubar o app com tela branca.

## [2026-08-16T23:52Z] 8/11 — Colecao Firestore alinhada ✅
- Firestore real (projeto sapiens-dataset) JÁ TEM a coleção `itens` com 18 docs;
  `pipelines` não existia. Portanto o pipeline é que estava apontando pro lugar errado.
- `FIRESTORE_COLLECTION=itens` no .env do pipeline + default do código trocado
  de "pipelines" para "itens" (aluno lê de `itens` em annotation_service.py:57).
- RISCO ENCONTRADO NO CAMINHO: `sync_all_questions` deleta do Firestore tudo que não
  existe no Mongo do pipeline. Com o Mongo local vazio, um clique em "sincronizar tudo"
  apagaria os 18 itens reais. Adicionada guarda: aborta se o conjunto interno for vazio.
- Testado: /firestore/sync-all com Mongo vazio → 500 + log "Refusing full sync";
  os 18 itens continuam intactos (mirrored_count = 18).

## [2026-08-16T23:54Z] 9/11 — Resultado do Gemini não se perde mais ✅
- generate_pipeline agora grava o registro no Mongo ANTES de subir artefatos ao
  object storage; falha de storage vira campo `artifacts_error` no doc, não 500.
- Testado com storage mockado como offline: requisição retornou OK, `pipeline`
  (resultado do Gemini) preservado no Mongo, erro registrado. Antes: 500 + perda total.

## [2026-08-16T23:57Z] 10/11 — Behavior payload validado ✅
- BehaviorPayload deixou de ser `dict[str, Any]` livre: agora só aceita `profile`
  e `flags` (com extra="forbid"). stats/events/identidade não são mais graváveis
  pelo cliente. Endpoint não é usado pelo frontend hoje.
- Testado: `{"stats":{"total_correct":9999},"is_admin":true}` → 422 extra_forbidden;
  `{"flags":{"onboarded":true}}` → 200.

## [2026-08-16T23:58Z] 11/11 — Emergent removida do runtime dos 3 frontends ✅
- Removidos de aluno/pipeline/professor `frontend/public/index.html`:
  - `<script src="https://assets.emergent.sh/scripts/emergent-main.js">` (supply chain:
    JS remoto e mutável, controlado por terceiro, em todo carregamento de página)
  - bloco PostHog completo, incluindo `session_recording` (gravação de sessão de
    alunos enviada a terceiro sem consentimento)
  - title "Emergent | Fullstack App" e meta description "A product of emergent.sh"
- Testado no browser: `window.posthog` = undefined, zero scripts de emergent/posthog
  no DOM, apps funcionando normalmente.

---

# Estado final (2026-08-16T23:59Z)

Todos os 11 P0 resolvidos e testados. P1/P2/P3 intocados, conforme pedido.

## Credenciais/config criadas nesta sessão (ambiente local)
- `PIPELINE_API_KEY` = ver pipeline/backend/.env (mesma chave em pipeline/frontend/.env)
- professor admin local: admin@sapiens.edu / admin123 (restaurado após teste)
- Mongo local: mongodb://127.0.0.1:27017 (bancos sapiens_aluno, sapiens_pipeline,
  sapiens_professor); dados em Sapiens/.mongodb-data
- Portas: aluno 3000/8001, pipeline 3001/8002, professor 3002/8003

## Pendências conhecidas (NÃO são P0, ficam pro futuro)
1. Não existe UI para conceder `turmas_autorizadas` a um professor — hoje só admin
   ou quem importou vê dados. Se um professor real precisar de acesso, é preciso
   editar o doc do usuário no Mongo à mão.
2. A auth do pipeline é uma API key única compartilhada, não usuários individuais.
   A chave fica exposta no bundle do frontend (é inevitável com CRA) — serve contra
   acesso anônimo externo, não contra um usuário do próprio app.
3. Lock-in remanescente da Emergent (P1, fora de escopo desta rodada):
   - aluno/backend/ai_service.py → todo diagnóstico Claude + OCR Gemini via proxy
   - pipeline/backend/storage.py → todos os binários no object storage deles
   - login com Google do aluno → depende de auth.emergentagent.com
   - emergentintegrations/litellm exigem índice pip privado da Emergent
   - craco plugin @emergentbase/visual-edits ainda injeta overlay + tailwind CDN
     em modo dev dentro de iframe (não afeta build de produção)
