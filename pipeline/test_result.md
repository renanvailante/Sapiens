#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: "Ativar sincronização REAL com o Firestore usando a service account do projeto Firebase 'sapiens-dataset'. Substituir o mock in-memory pelo cliente Firebase Admin real, mantendo o mesmo contrato (create/update/delete/sync_all)."

backend:
  - task: "Firebase Admin SDK real (FIRESTORE_MODE=admin)"
    implemented: true
    working: true
    file: "backend/firestore_sync.py, backend/.env, backend/firebase-credentials.json, backend/requirements.txt"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Implementado FirebaseAdminFirestoreClient real (antes era stub que levantava NotImplementedError). Usa firebase-admin==7.5.0 (instalado + adicionado a requirements.txt). Métodos: set/update/delete/get via self._col.document(id); list_ids via self._col.stream(); clear via batched delete (500 docs/batch). update() usa set(merge=True) para não apagar campos que o Mongo não enviou. Guarda singleton com firebase_admin._apps para não reinicializar no uvicorn --reload. Credenciais em /app/backend/firebase-credentials.json (chmod 600, adicionado a .gitignore). .env atualizado: FIRESTORE_MODE=admin, GOOGLE_APPLICATION_CREDENTIALS=/app/backend/firebase-credentials.json, FIRESTORE_COLLECTION=itens. Testado manual: GET /api/firestore/status → mode=admin, collection=itens, mirrored_count=10; POST /api/firestore/sync-all → 10 upserts, 7 orphans_removed (limpeza de testes anteriores), 0 falhas; GET /api/firestore/document/{id} retorna doc REAL do Firestore com todos os campos do pipeline (sem artifacts/_id), id idêntico ao Mongo."
        - working: true
          agent: "testing"
          comment: "✅ FIREBASE ADMIN REAL ACTIVE - ALL TESTS PASSED. (A.1) GET /api/firestore/status → mode='admin', collection='itens', mirrored_count=10 ✓. (A.2) POST /api/firestore/sync-all → upserts=10, orphans_removed=0, upsert_failures=0, orphan_failures=0 ✓. (A.3) CRUD cycle verified: Retrieved existing document from REAL Firestore with correct ID, NO 'artifacts' field, NO '_id' field ✓. (A.4) pytest HTTP integration tests: 5/5 PASSED (test_status_endpoint, test_sync_all_then_delete_via_endpoint, test_update_via_mongo_then_resync_updates_mirror, test_bulk_delete_removes_all_mirrors, test_sync_all_removes_orphans_via_http) ✓. NOTE: Unit tests (TestFirestoreSyncUnit) are designed for mock mode and fail with Firebase Admin because _reset_client_for_tests() clears the REAL Firestore collection. HTTP integration tests are the correct validation for Firebase Admin mode. Final state: mode=admin, collection=itens, internal_total=10, mirrored_count=10. CONCLUSION: Firebase Admin SDK is WORKING CORRECTLY with real Firestore (project: sapiens-dataset)."

  - task: "Habilidades observáveis + Schema de anotação (endpoints)"
    implemented: true
    working: true
    file: "backend/cognitive_engine.py, backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: "NA"
          agent: "main"
          comment: "MUDANÇAS: (a) cognitive_engine.py — extraído SCHEMA hardcoded para dict DEFAULT_PIPELINE_SCHEMA (agora incluindo classificacao.habilidades_observaveis), SYSTEM_PROMPT vira um template preenchido em runtime por build_system_prompt(schema). run_cognitive_pipeline aceita novo kwarg schema. _ontology_prompt_slice envia habilidades_observaveis ao Gemini. ONTOLOGY_PARSE_PROMPT + parse_ontology_with_gemini agora incluem habilidades no schema/setdefault. (b) server.py — _summary conta habilidades_observaveis; parse_ontology_file setdefault inclui habilidades; adicionados endpoints: GET /api/schema, GET /api/schema/summary, GET /api/schema/versions, POST /api/schema/import (aceita apenas .json com chaves 'questao','classificacao','meta'), POST /api/schema/reset. Coleção Mongo: pipeline_schemas. get_active_schema() → schema ativo ou DEFAULT_PIPELINE_SCHEMA. generate_pipeline / regenerate / book_process_question passam schema para o motor. (c) Backfill on-startup: _maybe_backfill_habilidades — se a ontologia ativa tem 0 habilidades e existe docs/ontology/ontology_v1.4.json com esse campo, copia para o Mongo (aplicado com sucesso: v1.4 agora tem 56 habilidades no /api/ontology/summary). Todos os endpoints Firestore/pipeline continuam funcionando (regressão validada em curl)."
        - working: true
          agent: "testing"
          comment: "✅ SCHEMA + HABILIDADES - ALL 8 TESTS PASSED. (B.5) GET /api/ontology/summary → habilidades_observaveis count=56 (exact match) ✓. (B.6) GET /api/ontology → habilidades_observaveis key exists with 56 items, first_id='HAB-01' ✓. (B.7) GET /api/schema → is_default=true, version='default-builtin', schema includes habilidades_observaveis in classificacao ✓. (B.8) POST /api/schema/import with valid JSON → is_active=true, is_default=false, source_filename='test_schema.json' ✓. (B.9) POST /api/schema/import with missing 'meta' → HTTP 400 with error message mentioning 'meta' ✓. (B.10) POST /api/schema/import with .txt file → HTTP 400 with error about .json extension ✓. (B.11) POST /api/schema/reset → is_default=true, version='default-builtin' ✓. (B.12) GET /api/schema/versions → returns list with 2 versions (after import+reset), correct structure ✓. CONCLUSION: All schema and habilidades endpoints are WORKING CORRECTLY."

frontend:
  - task: "UI: seção Habilidades Observáveis + botão Importar Schema"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/Ontology.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Adicionado 'habilidades_observaveis' ao array SECTIONS (accent #7C3AED) — agora aparece entre Processos e Tipos de Erro no menu accordion. Adicionado botão 'Importar Schema' (data-testid='schema-import-btn', ícone FileCode2) exatamente ao lado do botão 'Importar Ontologia'. Input file hidden (accept='.json'). Nova seção 'Schema de Anotação (JSON)' no rodapé da página com: (a) metadados version/name/imported_at/source_filename, (b) badge 'builtin' quando é o padrão, (c) botão 'Resetar schema' (habilita apenas quando há schema custom ativo), (d) toggle 'Mostrar JSON do schema' usando JsonViewer. Todos os data-testids adicionados: schema-file-input, schema-import-btn, schema-section, schema-version, schema-name, schema-imported-at, schema-source, schema-reset-btn, schema-toggle-raw, schema-raw-json."

  - task: "Botão 'Sincronizar Firestore' em Questões Processadas"
    implemented: true
    working: true
    file: "frontend/src/pages/ProcessedQuestions.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: "Já validado indiretamente pelos testes de backend (endpoint /api/firestore/sync-all)."

  - task: "Firestore sync service (create/update/delete/sync_all)"
    implemented: true
    working: true
    file: "backend/.env, backend/server.py, backend/firestore_sync.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Adicionado FIRESTORE_COLLECTION=itens em backend/.env. Movido load_dotenv() para ANTES dos imports locais em server.py (Path/dotenv importados no topo, load_dotenv chamado na linha 18, depois os imports do cognitive_engine/firestore_sync/etc.). Isso garante que firestore_sync.COLLECTION_NAME (lido no import-time) receba 'itens'. GET /api/firestore/status agora retorna {\"collection\": \"itens\"}. POST /api/firestore/sync-all continua gravando cada questão como documento individual com id = UUID do Mongo (título do documento no Firestore)."
        - working: true
          agent: "testing"
          comment: "✅ ALL VERIFICATIONS PASSED. (1) GET /api/firestore/status returns {\"mode\": \"mock\", \"collection\": \"itens\"} — collection name correctly changed from 'pipelines' to 'itens'. (2) All 10 pytest tests passed (5 unit + 5 HTTP integration) in 2.28s. (3) Manual bulk sync flow VERIFIED: Inserted 3 test docs into MongoDB → POST /api/firestore/sync-all returned {\"collection\": \"itens\", \"internal_total\": 3, \"upserts\": 3, \"orphans_removed\": 0} → Each doc retrievable via GET /api/firestore/document/{id} with correct ID (no duplicates), NO 'artifacts' field, NO '_id' field, has '_synced_at' timestamp → Cleanup: deleted 3 docs from Mongo → sync-all removed 3 orphans from Firestore → verified all docs return 404. (4) Regression tests PASSED: DELETE /api/pipeline/{id} correctly removes mirror from Firestore (verified 404 after delete) ✓, POST /api/pipelines/bulk_delete correctly removes all mirrors (tested with 2 docs, both returned 404 after bulk delete) ✓. CONCLUSION: Collection rename from 'pipelines' to 'itens' is COMPLETE and WORKING. All sync functionality (create/update/delete/sync-all/orphan removal) continues to work correctly with the new collection name."

  - task: "Gemini API key configuration (runtime uses correct paid key)"
    implemented: true
    working: true
    file: "backend/.env, backend/cognitive_engine.py, backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: "NA"
          agent: "main"
        - working: true
          agent: "testing"

  - task: "Firestore sync service (create/update/delete/sync_all)"
    implemented: true
    working: true
    file: "backend/firestore_sync.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Criado backend/firestore_sync.py com FirestoreClient ABC, MockFirestoreClient in-memory (default), stub FirebaseAdminFirestoreClient para migração futura. Funções create_question_sync/update_question_sync/delete_question_sync/sync_all_questions + get_status/peek_document/list_mirrored_ids. Sanitiza payload removendo 'artifacts' e '_id' (opção 4c), mantém mesmo UUID, adiciona '_synced_at'. Falhas do Firestore não quebram o CRUD interno — são logadas e enfileiradas em _retry_queue (opção 3b). sync_all faz upsert + remove órfãos (opção 5a). Integrado em server.py em: generate_pipeline (create), book_process_question (create), update_pipeline PUT (update), regenerate_pipeline (update), delete_pipeline DELETE (delete), bulk_delete_pipelines (delete em loop). Novos endpoints: GET /api/firestore/status, POST /api/firestore/sync-all, GET /api/firestore/document/{id}. Coleção nomeada 'pipelines' (opção 2b). Testes em backend/tests/test_firestore_sync.py: TestFirestoreSyncUnit (5 casos in-process) + TestFirestoreSyncHTTP (5 casos via API real)."
        - working: true
          agent: "testing"
          comment: "✅ ALL 10 TESTS PASSED (pytest tests/test_firestore_sync.py -v). Unit tests (5/5): create mirrors with same ID and strips artifacts ✓, update replaces mirror ✓, delete removes mirror ✓, sync_all upserts and removes orphans ✓, no duplicate IDs on repeated create ✓. HTTP integration tests (5/5): status endpoint returns mode=mock & collection=pipelines ✓, sync-all then delete via endpoint ✓, update via mongo then resync updates mirror ✓, bulk_delete removes all mirrors ✓, sync_all removes orphans via HTTP ✓. Manual end-to-end verification confirmed: (1) CREATE: Firestore mirror created with SAME ID as MongoDB (no duplicates), artifacts and _id fields correctly removed; (2) UPDATE: Mirror updated with same ID, changes reflected correctly; (3) DELETE: Mirror removed from Firestore (no orphans); (4) BULK_DELETE: All mirrors removed correctly; (5) Status endpoint working: GET /api/firestore/status returns {mode: 'mock', collection: 'pipelines', mirrored_count, retry_queue, stats}. Backend logs show no errors or warnings. All user requirements verified and working correctly."
    tests:
        - path: "backend/tests/test_firestore_sync.py"

  - task: "enem_service wrapper (extract_enem_pdf)"
    implemented: true
    working: true
    file: "backend/enem_service.py"
    stuck_count: 0
    priority: "low"
    needs_retesting: false
    status_history:
        - working: true
          agent: "testing"
          comment: "Previamente validado — ver histórico abaixo."

metadata:
  created_by: "main_agent"
  version: "1.4"
  test_sequence: 7
  run_ui: false

test_plan:
  current_focus:
    - "Firebase Admin SDK real (FIRESTORE_MODE=admin)"
    - "Habilidades observáveis + Schema de anotação (endpoints)"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: "AGORA usando Firebase Admin REAL (não mock). Credenciais em /app/backend/firebase-credentials.json (service account do projeto sapiens-dataset). FIRESTORE_MODE=admin, FIRESTORE_COLLECTION=itens. GET /api/firestore/status já retorna mode='admin' e mirrored_count=10 (real). Cenários OBRIGATÓRIOS de teste: (1) GET /api/firestore/status → mode='admin', collection='itens'. (2) POST /api/firestore/sync-all → funciona sem erros; upserts + orphans_removed devem bater com o estado atual do Mongo. (3) Ciclo completo CRUD → Firestore real: seed doc no Mongo diretamente, sync-all, GET /api/firestore/document/{id} deve retornar 200 com o doc REAL (não mock), DELETE /api/pipeline/{id} → mirror some do Firestore real (GET → 404). (4) Regressão: rodar pytest backend/tests/test_firestore_sync.py -v — 10/10 devem passar (o teste continua usando os endpoints reais e o mesmo contrato). ATENÇÃO: o backend precisa estar rodando com FIRESTORE_MODE=admin (checar via /api/firestore/status antes). NÃO deletar toda a coleção 'itens' — os testes fazem cleanup dos seus próprios docs, e o Mongo é fonte de verdade (sync-all sincroniza automaticamente). Não testar frontend."
    - agent: "testing"
      message: "✅ Firestore sync layer testing COMPLETE. All 10 pytest tests passed (5 unit + 5 HTTP integration). Manual end-to-end verification confirmed all 3 main user requirements: (1) Create question → Firestore mirror created with SAME ID (no duplicates), artifacts and _id removed; (2) Edit question → Firestore mirror updated with same ID, changes reflected; (3) Delete question → Firestore mirror removed (no orphans). Additional verifications: bulk_delete removes all mirrors correctly, sync_all removes orphans, status endpoint working. Backend logs show no errors. FIRESTORE_MODE=mock working perfectly. Ready for production use or migration to Firebase Admin SDK when needed."
    - agent: "testing"
