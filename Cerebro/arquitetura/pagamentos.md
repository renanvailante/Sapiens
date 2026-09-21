---
tags: [arquitetura, dinheiro, mercadopago]
atualizado: 2026-09-18
---

# Pagamentos — Mercado Pago, Pix e crédito

## O crédito NÃO depende do webhook

Há **dois caminhos**, e o webhook é só o rápido:

1. `POST /api/sparks/webhook` — caminho rápido.
2. `_sparks_reconciliacao_loop` em `server.py`, a cada **60s** — a garantia.
3. `GET /sparks/purchases/{id}`, a consulta que a tela de pagamento já fazia,
   também repergunta ao MP enquanto o pagamento estiver em aberto — é ela que dá o
   crédito em segundos com o aluno olhando o QR Code.

Nasceu do incidente de 2026-09-07 ([[incidentes]]). **Nunca volte a tratar o
webhook como fonte única, e nunca proponha aprovação manual.**

### As duas travas que tornam o repergunta-sempre seguro

1. **A decisão é do Mercado Pago.** Credita só se `GET /v1/payments/{id}`
   responder `approved` — nunca o corpo do webhook, nunca o navegador, nunca o
   status guardado no nosso Mongo
   (`test_status_aprovado_so_no_nosso_banco_nao_basta`). Sem isso, a rede de
   segurança vira máquina de dar Spark de graça para quem só abriu o QR Code.
2. **Idempotência atômica por `mp_payment_id` no Firestore**
   (`grant_purchase_sparks`) — é o que permite reprocessar à vontade.

## Comprar é Pix em um clique

`POST /sparks/purchases {package_id, payment_method_id: "pix"}`, **sem nenhum dado
de pagador**, e a tela mostra QR Code + copia-e-cola + "abrir no app do banco". O
Payment Brick do MP ficou só para cartão, atrás do link "Prefiro pagar com cartão".

O pedido que gerou isso: *"quando vou comprar sparks, aparece um email para eu
confirmar antes de comprar. eu quero que já apareça um QR code"* — o Brick pedia
e-mail e CPF antes de mostrar qualquer coisa, um formulário inteiro entre a vontade
de comprar e o meio de pagar, pedindo um e-mail que a conta já tem.

Três fatos caros de redescobrir, todos em `sparks_payments_service.py`:

1. **O MP aceita Pix só com `payer.email`.** CPF é opcional — verificado contra a
   API real em produção (16/09, pagamento 178357857077, payload sem
   `identification`). Se mexer no payload, `identification` tem de ficar
   **ausente** quando não informado, nunca `null`.
2. **Clicar de novo no mesmo pacote devolve o MESMO código** (`_pix_em_aberto`,
   janela `PIX_REAPROVEITAR_MINUTOS = 25`). Dois QR Codes válidos do mesmo produto
   é um jeito de o aluno pagar duas vezes.
3. **O QR Code vale 1h** (`PIX_VALIDADE_MINUTOS`), não as 24h padrão do MP:
   cobrança que nasce de um clique é abandonada com frequência, e cada pendente
   fica sendo reperguntado ao MP até expirar. O prazo é **economia nossa**, não
   produto. `_criar_pagamento` refaz a compra sem prazo se o MP recusar a data —
   só em HTTP 400, a única recusa que garante que nada foi criado do lado de lá.

## Provar mudança nesse caminho

Nada offline prova que o MP aceita o formato. O pacote `spark_test_15`
("[teste inte.........rno] R$ 1,00 → 15 Sparks", link discreto no fim da loja) existe para
isso: dá para montar o payload e chamar o MP de dentro da máquina com
`fly ssh console -a sapiens-aluno -C "python ..."` sem tocar no Mongo.

## Diagnóstico

`GET /api/admin/sparks/pendentes` (admin, abre direto na barra de endereço) devolve
o que está preso **e** as últimas notificações recebidas (`webhook_recebimentos`,
gravadas mesmo quando a assinatura é recusada).

- `items` cheio + `webhooks_recebidos` vazio → a notificação nunca chegou.
- `assinatura_valida: false` → `MERCADOPAGO_WEBHOOK_SECRET` não bate com o painel.

## Acessórios do crédito

O prêmio de indicação mora **dentro** de `process_payment_webhook`, depois de
`grant_purchase_sparks`, com `try/except` que só loga — **falhar o bônus nunca pode
derrubar a compra de quem pagou**. Mesmo princípio: a inscrição na live é só
registro, o direito é a autorização; se a escrita falhar, o acesso sai do mesmo
jeito.

## Indicação de amigo

Cada aluno tem `users.referral_code`, criado **preguiçosamente** ao abrir a tela —
não por migração. Quem se cadastra com ele ganha `users.indicado_por` + um
documento em `indicacoes` (`_id = indicado_id`). Na **primeira compra** do
indicado, o indicador recebe `sparks_do_pacote // 2`.

**Um campo só no cadastro** para cupom e indicação: `auth._bonus_de_cadastro`
resolve cupom primeiro (o catálogo do admin vence) e só então indicação — quem
recebe um código por WhatsApp não sabe de que tipo ele é. Por isso
`indicacoes._codigo_livre` também recusa sortear um código igual a um cupom.

O cupom é registrado por `auth._registrar_cupom` **logo depois** do `insert_one`,
nunca antes: `validar_e_registrar_uso` incrementa `usos`, e fazer isso antes da
conta existir gastaria um uso de um cadastro que falhou.

---
Relacionado: [[economia-de-sparks]] · [[catalogo]] · [[dados]] · [[incidentes]]
