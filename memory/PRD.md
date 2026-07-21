# Sapiens Dashboard — PRD

## Problem statement (original)
Construa "Sapiens Dashboard" — uma plataforma de OBSERVABILIDADE PEDAGÓGICA para
professores e coordenadores. É uma camada de visualização de dados já processados por
sistemas externos de análise cognitiva do ecossistema Sapiens. NÃO classifica, NÃO
infere, NÃO gera diagnósticos — só visualiza. Sempre exibir a versão da taxonomia
usada em cada dado. Nunca comparar turmas de versões diferentes sem aviso.
Restrições: sem invenção/estimativa/completar dados ausentes ("Sem dado"), sem IA
generativa, sem edição de dados importados. Agregações permitidas: soma, contagem,
média simples, percentual, ordenação, filtro — sempre rotuladas como "Calculado
pelo Dashboard". 5 telas MVP: Turma, Processo cognitivo, Aluno, Evolução temporal,
Exploração da taxonomia. Filtros globais: turma, período, disciplina, ano escolar,
banca, prova.

## Architecture
- Backend: FastAPI + Motor (MongoDB async), bcrypt + PyJWT auth with httpOnly cookies
  (SameSite=None; Secure) for cross-origin preview URL.
- Frontend: React 19 + React Router 7 + Tailwind + shadcn/ui (Swiss/brutalist override:
  no rounding, no shadows). Recharts for graphs. Fonts: Chivo (headings) + IBM Plex
  Sans (body) + IBM Plex Mono (numbers/IDs).
- DB: `sapiens_dashboard`, collections: `users`, `imports`.

## Personas
- Professor(a): visualiza turma, aluno individual, evolução ao longo dos períodos.
- Coordenador(a): visão consolidada, exportação CSV, gerenciamento de imports.

## Core requirements (static)
- Nunca inventar dados. Campo ausente → "Sem dado".
- Sempre exibir versão da taxonomia do snapshot atual.
- Alertar em comparações que atravessam versões diferentes.
- Rotular agregações como "Calculado pelo Dashboard".
- Auth simples (email/senha JWT).

## Implemented (2026-02)
- [x] Auth JWT + cookies httpOnly + admin seed (admin@sapiens.edu / admin123).
- [x] Ingestão de snapshot (POST /api/imports) — JSON upload + endpoint.
- [x] Seed com 2 turmas × 3 períodos × 8 alunos × 7 nós (Matemática/Português/Ciências),
  atravessando duas versões de taxonomia (v0.8 e v0.9) para exercitar avisos.
- [x] GET /api/filters — descoberta de opções.
- [x] Visão da turma — matriz aluno×nó com heatmap 5 níveis + "Sem dado" hatched.
- [x] Visão por processo cognitivo — média + distribuição em bins + lista alunos.
- [x] Visão por aluno — comparação com média simples da turma + coluna Δ.
- [x] Evolução temporal — série de períodos + aviso quando versões diferentes.
- [x] Exploração da taxonomia — árvore navegável por disciplina + detalhes.
- [x] Filtros globais (turma/período/disciplina/ano/banca/prova).
- [x] Exportação CSV da matriz da turma.
- [x] Badge de versão da taxonomia no header, sincronizado com o snapshot exibido.

## Backlog / Next
- [P1] Exportar CSV também de Processo, Aluno e Evolução.
- [P1] Cache/paginação em imports muito grandes.
- [P1] Rota /api/imports/upload multipart para arquivos grandes.
- [P2] Filtro por versão da taxonomia (comparar apenas dentro da mesma versão).
- [P2] Comparação lado-a-lado de dois períodos (com aviso de versão).
- [P2] Papel de "coordenador" com permissão de deletar imports; teachers read-only.
- [P2] Auditoria de imports (quem ingeriu, quando, tamanho).
- [P3] Suporte a taxonomia hierárquica (pais/filhos de nó) quando o formato de entrada
  passar a fornecer hierarquia.
