# Sapiens — PRD

## Original problem statement
Sistema de inteligência educacional que identifica padrões cognitivos de aprendizagem, padrões de erro, competências dominadas e deficientes a partir da análise de provas do ENEM. Não é corretor. Responde: "Por que eu erro?", "Quais habilidades me faltam?", "Quais conteúdos geram maior aumento de nota?", "Como devo estudar?". Inspirado em Apple/Notion/Duolingo/Stripe.

## Architecture
- Frontend: React 19 + Tailwind + Shadcn UI + Recharts + Sonner (PWA-ready).
- Backend: FastAPI + Motor (Mongo). All routes prefixed `/api`.
- AI: Claude Sonnet 4.5 (diagnostic + tagging) + Gemini 2.5 Flash (Vision OCR) via Emergent Universal Key.
- Auth: JWT email/password + Emergent Google OAuth (parallel).

## Personas
- Aluno de vestibular (ENEM) que quer entender POR QUE erra.
- Admin pedagógico que importa novas provas oficiais.

## Implemented (2026-02-08)
- Landing minimalista com hero "Sapiens · Descubra por que você erra." + CTA.
- Login (Google + email/password) com painel-manifesto lateral.
- Seleção de prova ENEM (2022/2023/2024 · Azul + Amarela) — 6 cadernos seed.
- Entrada de respostas: manual + fotografia com Vision OCR (Gemini).
- Diagnóstico em duas fases: insight primeiro, números depois.
- Painel: mapa de competências, radar do perfil cognitivo, evolução, forças/fraquezas.
- Plano de estudos ordenado por retorno esperado (+pts, horas, "por que").
- Mapa de aprendizagem (SVG interativo com nós/arestas e causas-raiz).
- Histórico com comparação.
- Admin panel: importar prova via JSON (auto-tagging com Claude quando ausente).
- Modelos escaláveis: provider (ENEM/FUVEST/...), year, color, area — extensíveis.

## Backlog
- P0: TRI (nota calibrada por dificuldade) — modelos já preveem `difficulty`.
- P1: PDF export dos relatórios; comparação lado a lado no histórico.
- P1: Sincronização com o crawler oficial INEP (importação automática por URL).
- P2: Monetização Premium R$4,99/mês (Stripe) — desligado no MVP a pedido.
- P2: Publicação Android/iOS via Capacitor a partir do PWA.
- P2: Grafo mais rico via `react-force-graph-2d` (biblioteca opcional).

## Next tasks
- Rodar testing agent end-to-end (auth, seleção, análise, diagnóstico, mapa).
- Polir mobile na tela de resposta (grade de bolhas).
