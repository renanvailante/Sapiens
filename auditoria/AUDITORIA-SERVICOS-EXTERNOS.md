# Auditoria de serviços externos — Sapiens

**Registrado em:** 2026-08-21
**Escopo:** os três apps (`aluno`, `professor`, `pipeline`), depois da remoção completa da Emergent.
**Método:** rastreamento funcional a partir do código — todo import de SDK, todo host externo e toda variável de ambiente que aponte para fora do processo. Não é lista de intenções: cada linha abaixo corresponde a uma chamada que existe.

**Natureza deste documento:** registro (`auditoria/`), não norma. Sob GOV-1.0 §1.1 nada aqui vincula.

---

## 1. Superfície externa real, depois da remoção

Inventário exaustivo de SDKs de serviço e hosts externos referenciados em código de aplicação:

| SDK / host | Onde | Serviço |
|---|---|---|
| `google.genai` | `pipeline/backend/cognitive_engine.py`, `aluno/backend/ai_service.py` | **Gemini API** |
| `firebase_admin` (`firestore`) | `aluno/backend/firestore_service.py`, `pipeline/backend/firestore_sync.py` | **Firestore** |
| `firebase_admin` (`storage`) | `pipeline/backend/storage.py` (modo opcional) | **Firebase Storage** |
| `motor` / `pymongo` | os três backends | **MongoDB** — infraestrutura própria, não SaaS |
| `axios` → `http://localhost` | os três frontends | backend do próprio app |

**Nenhum outro host externo aparece no código dos três apps.** Confirmado por varredura de `https?://` em 236 arquivos de aplicação: o único literal restante é `http://localhost`.

---

## 2. Capacidades, uma a uma

Para cada capacidade em uso: o que ela faz, quem a executa hoje e o que **poderia** executá-la. A coluna de veredito responde a pergunta que motivou esta auditoria — se Gemini + Firestore bastam.

### 2.1 Cobertas por **Gemini API**

| Capacidade | Onde | Situação |
|---|---|---|
| Anotação cognitiva multimodal de questão (PDF/imagem → Schema 2.2) | `cognitive_engine.run_cognitive_pipeline` | Já era Gemini direto. Inalterada. |
| Manifesto de caderno (enumerar questões de um PDF) | `cognitive_engine.run_book_manifest` | Já era Gemini direto. Inalterada. |
| Importação de ontologia a partir de PDF/DOCX/MD | `cognitive_engine.parse_ontology_with_gemini` | Já era Gemini direto. Inalterada. |
| **OCR de cartão-resposta** | `ai_service.ocr_answer_sheet` → `exam_routes` | **Migrada.** Já era Gemini Vision, mas atravessando o proxy da Emergent. Agora é chamada direta. |
| **Narrativa diagnóstica do simulado** | `ai_service.diagnose` → `exam_routes` | **Migrada.** Era Claude Sonnet 4.5 via proxy; virou Gemini com `response_mime_type="application/json"`. É geração de texto com saída estruturada — nada no prompt dependia de capacidade exclusiva do Claude. |

### 2.2 Cobertas por **Firestore / Firebase**

| Capacidade | Onde | Situação |
|---|---|---|
| Espelho dos itens anotados | `pipeline/backend/firestore_sync.py` | Inalterada. |
| Eventos de resposta do aluno (behavior 1.1) | `aluno/backend/firestore_service.py` | Inalterada. |
| Perfil do estudante (`students/{uid}`) | idem | Inalterada. |
| **Artefatos binários** (PDF original, extração, anotação) | `pipeline/backend/storage.py` | **Migrada.** Era Object Storage da Emergent. Agora `STORAGE_MODE=local` (disco, padrão) ou `STORAGE_MODE=firebase` (bucket do GCS, mesma credencial de serviço do Firestore). |

### 2.3 Implementadas **localmente** — não exigem serviço nenhum

| Capacidade | Onde | Observação |
|---|---|---|
| Autenticação e-mail/senha, sessão em cookie | `aluno/backend/auth.py` (`bcrypt`) | Autossuficiente. Nunca dependeu da Emergent. |
| Autenticação do professor (JWT) | `professor/backend/server.py` (`bcrypt` + `jwt`) | Autossuficiente. |
| RBAC professor↔turma; admin por `ADMIN_EMAILS` | `professor/backend/server.py`, `aluno/backend/auth.py` | Autossuficiente. |
| Validação de contratos (Schema 2.2, Error Trace) | `pipeline/backend/ontology_validator.py` | Puro Python sobre o catálogo em disco. |
| Derivação de domínios/competências | `ontology_validator.derivar_estrutura` | Determinística. |
| Feedback qualitativo por templates | `aluno/backend/feedback_templates.py` | Sem IA, por decisão de projeto — lookup no catálogo. |
| Extração determinística de PDF do ENEM | `pipeline/backend/enem_service.py` (pacote `enem` 1.0.4) | Biblioteca local, sem rede. |
| Persistência operacional | MongoDB | Infraestrutura própria, autohospedável. |

### 2.4 Capacidades que **não** são cobertas por Gemini + Firestore

Esta é a resposta direta à pergunta central da auditoria. São **três**, e nenhuma bloqueia a operação atual:

| # | Capacidade | Estado | Por que não é coberta | Caminho |
|---|---|---|---|---|
| **1** | **Login social (Google SSO)** | **REMOVIDO.** | Dependia inteiramente de `auth.emergentagent.com` + `demobackend.emergentagent.com`. Gemini não faz auth; Firestore é banco, não provedor de identidade. | **Firebase Authentication** cobre integralmente, com a mesma credencial de serviço já em uso. É acréscimo de arquitetura, não migração — não foi implementado. O login por e-mail/senha continua funcionando e não perdeu nada. |
| **2** | **MongoDB** | **EM USO.** | É o banco operacional dos três apps (usuários, sessões, provas, gabaritos, análises, feed, imports do professor). Firestore só guarda itens e behavior. | Migrar tudo para Firestore eliminaria o Mongo, mas é reescrita de persistência, não substituição de fornecedor. Mantido: é infraestrutura própria, não um SaaS de que se dependa. |
| **3** | **Object storage de binários** | **RESOLVIDA com ressalva.** | O modo padrão (`local`) grava em disco: não sobrevive a container efêmero nem escala horizontalmente. | `STORAGE_MODE=firebase` resolve, e usa a credencial que já existe. Basta provisionar o bucket e definir `FIREBASE_STORAGE_BUCKET`. |

**Conclusão.** Fora o Google SSO — que foi removido, não quebrado — **Gemini + Firestore cobrem toda a superfície externa da plataforma**. O MongoDB permanece por decisão de persistência, não por dependência de fornecedor.

---

## 3. O que foi removido da Emergent, e o que ocupou o lugar

| Dependência removida | Função | Substituição |
|---|---|---|
| `emergentintegrations` + `litellm` (índice pip privado) | Proxy de LLM (Claude + Gemini) | `google-genai`, chamada direta |
| `integrations.emergentagent.com/objstore` | Object storage | `storage.py` — disco ou Firebase Storage |
| `auth.emergentagent.com` | Redirect de OAuth | — (removido) |
| `demobackend.emergentagent.com` | Troca de `session_id` por dados do usuário | — (removido) |
| `@emergentbase/visual-edits` (tarball `assets.emergent.sh`) | Edição visual em dev | — (removido dos 3 `craco.config.js` e `package.json`) |
| `.emergent/cron/*.sh` | Cron/webhook da plataforma | — (removido dos 3 apps) |
| `EMERGENT_LLM_KEY` | Credencial única do proxy | `GEMINI_API_KEY` |
| Hosts `*.preview.emergentagent.com` em testes | Alvo das suítes de integração | `SAPIENS_BACKEND_URL`, default `localhost` |

---

## 4. Variáveis de ambiente, estado final

| Variável | App | Obrigatória? | Para quê |
|---|---|---|---|
| `MONGO_URL`, `DB_NAME` | os três | **Sim** | Banco operacional |
| `CORS_ORIGINS` | os três | Não | Origens permitidas |
| `GEMINI_API_KEY` | pipeline, **aluno** | Sim, para IA | Anotação, OCR, diagnóstico |
| `GEMINI_MODEL`, `GEMINI_VISION_MODEL` | pipeline, aluno | Não | Escolha do modelo |
| `PIPELINE_API_KEY` | pipeline | **Sim** | Shared secret de todas as rotas |
| `GOOGLE_APPLICATION_CREDENTIALS` / `FIREBASE_SERVICE_ACCOUNT_PATH` | pipeline, aluno | Sim, para Firestore | Credencial de serviço |
| `FIREBASE_PROJECT_ID`, `FIRESTORE_MODE`, `FIRESTORE_COLLECTION` | pipeline, aluno | Não | Configuração do espelho |
| `STORAGE_MODE`, `STORAGE_ROOT`, `FIREBASE_STORAGE_BUCKET` | pipeline | Não | Backend de artefatos |
| `SAPIENS_ONTOLOGY_PATH`, `SAPIENS_CONTRACTS_PATH` | aluno | Só em deploy separado | Localiza o corpus canônico |
| `ADMIN_EMAILS` | aluno | Não | Semeia papel de admin |
| `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `FRONTEND_URL` | professor | **Sim** | Auth do professor |
| ~~`EMERGENT_LLM_KEY`~~ | — | — | **Removida** |

---

## 5. Validação de independência

Os três backends foram iniciados **sem nenhuma credencial ou host da Emergent** e responderam:

```
pipeline  (uvicorn :8801)  GET /api/                    -> 401  (exige X-API-Key — correto)
                           GET /api/ontology/summary    -> 200  ontologia 1.4.1, 128 IDs
                           GET /api/schema/summary      -> 200  Schema Sapiens 2.2
aluno     (uvicorn :8802)  GET /api/                    -> 200
                           POST /api/auth/signup        -> 200  usuário criado
                           GET  /api/auth/me            -> 200  provider "email"
                           POST /api/auth/logout        -> 200
                           POST /api/auth/emergent/session -> 404  (rota removida)
professor (uvicorn :8803)  GET /api/                    -> 200
                           POST /api/auth/login (admin) -> 200
```

Nenhum log de boot registrou erro. O catálogo foi re-semeado a partir do JSON canônico do disco depois do reset de dados, confirmando que o Mongo nunca foi fonte da ontologia.

Round-trip do storage local verificado: gravação, leitura com `content-type` preservado e remoção por prefixo.

---

## 6. Fora de escopo, deliberadamente

- **Produtor de Error Trace** — não implementado. O contrato (ETRACE-1.0) e sua validação permanecem; a produção aguarda evidência longitudinal e especificação estatística/metodológica futura. A `Especificação do Error Trace` §0.1, item 2, declara explicitamente que não define o mecanismo de produção.
- **Firebase Authentication** — caminho identificado para o SSO removido, não implementado.
- **Migração MongoDB → Firestore** — reescrita de persistência, não remoção de fornecedor.
