# Sapiens - Anotador Cognitivo (PRD)

## Arquitetura do ecossistema (contexto)
Este projeto é o **Aplicativo 2 — Pipeline Generator / Banco de Itens** do ecossistema Sapiens.
Ele produz o **Item Annotation JSON canônico** de cada questão de vestibular.

Ecossistema completo:
- **App 1 — Plataforma do Aluno**: consome o Banco de Itens (não modifica); grava Student Response Events.
- **App 2 (ESTE) — Pipeline Generator / Banco de Itens**: única fonte de verdade dos Item Annotations e assets.
- **App 3 — Dashboard**: apenas leitura; faz JOIN entre App 1 (eventos) e App 2 (itens).

Cada questão gera **exatamente 1 Item Annotation** independente; assets nunca são embutidos no JSON — apenas referenciados por resource_uri.

## Personas
- Autores/coordenadores de banco de itens (usam App 2 = este).
- App 1 (Plataforma do Aluno) consome via API.
- App 3 (Dashboard) consome via API.

## Core requirements
- Ontologia = única fonte autorizada (motor nunca inventa IDs).
- Leitura multimodal (texto + figuras + tabelas + fórmulas).
- 3 artefatos por item: original, extração estruturada, pipeline final.
- Cada asset com asset_id único, referenciado, nunca duplicado.

## Stack
- Backend: FastAPI + MongoDB + Emergent Object Storage.
- Motor cognitivo: **Google Gemini API direto** (google-genai SDK).
  - Chave: `GEMINI_API_KEY` em `/app/backend/.env`.
  - Modelo default: `gemini-3-flash-preview` (multimodal, disponível no free tier).
  - Configurável via `GEMINI_MODEL` env var (ex: `gemini-3.1-pro-preview` se billing habilitado).
- Frontend: React + Shadcn/UI + Tailwind (Swiss/High-Contrast theme).

## Implementado (Fev/2026)
- Sidebar, Dashboard, Ontology (view+import+reset), Pipeline Generator (3 modos), Processed Questions.
- Modos do Gerador: `Uma questão`, `Lote` (paralelismo 3), `Caderno` (manifest + processamento individual paralelo).
- Ontologia semente (8 dom + 16 comp + 28 proc + 13 erro + 7 int) reimportável (JSON/YAML/MD/DOCX/PDF via Gemini) + botão Resetar.
- Ações em massa: checkbox por questão, Selecionar todos, Copiar/Exportar/Excluir em lote.
- 3 artefatos por questão persistidos em Emergent Object Storage.
- Migração para Gemini API direto (bypass do Emergent proxy esgotado).

## Backlog
- P1: exportar XLSX/CSV consolidado por caderno.
- P1: página /cadernos listando books com % de conclusão.
- P1: endpoints públicos de leitura (para App 1 e App 3 consumirem sem duplicar dados).
- P2: relatório comparativo entre cadernos (dashboard).
- P2: schema Item Annotation Sapiens oficial (asset_id, resource_uri) — hoje o schema é próximo mas precisa alinhamento formal.
