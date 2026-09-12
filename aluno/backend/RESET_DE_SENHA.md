# Recuperação de senha — estado e o que falta

## O que já funciona

O fluxo inteiro está implementado e testado (`tests/test_auth_seguranca.py`):

1. `POST /api/auth/password/forgot` gera um token de 256 bits, guarda **só o
   hash** (`password_resets.token_hash`), com validade de 30 minutos e índice
   TTL que apaga o registro sozinho.
2. A resposta é **idêntica** exista ou não a conta — dizer "e-mail não
   encontrado" transformaria a rota num verificador de quem estuda aqui, isto
   é, numa lista de menores de idade para quem quisesse coletá-la.
3. `POST /api/auth/password/reset` consome o token (uso único), troca a senha,
   marca a conta como verificada e **apaga todas as sessões abertas** — se a
   conta estava tomada, é aí que o acesso do invasor termina.
4. As telas são `/esqueci-senha` e `/redefinir-senha`.

## Entrega do e-mail

`auth._entregar_link_de_reset` envia pelo [Resend](https://resend.com) quando
as duas variáveis estão configuradas, e cai no log quando não estão:

| `RESEND_API_KEY` | `RESEND_FROM` | O que acontece |
| --- | --- | --- |
| ausente | qualquer | link em `WARNING` no log — ninguém recebe e-mail |
| presente | ausente | idem (as duas são exigidas juntas) |
| presente | presente | e-mail enviado; se o envio falhar, o link vai para o log em `ERROR` |

Confira o estado em produção sem abrir o painel do Fly:

```bash
curl -s https://sapiens-aluno.fly.dev/ready | python3 -m json.tool | grep -A 2 '"email"'
```

`"configurado": false` significa que o link está indo só para o log.

### Para ligar o envio

```bash
flyctl secrets set RESEND_API_KEY=re_xxx "RESEND_FROM=Sapiens <nao-responda@seudominio.com.br>" -a sapiens-aluno
```

O domínio do remetente precisa estar **verificado no Resend** (registros SPF e
DKIM no DNS), senão o provedor recusa o envio ou o e-mail cai em spam. Enquanto
não estiver, o comportamento é o mesmo de antes: link só no log.

`FRONTEND_URL` é opcional e só muda o endereço que vai dentro do link. Sem ela,
o link usa a primeira origem de `CORS_ORIGINS` — defina-a se essa lista tiver
mais de uma origem e a primeira não for a canônica.

### Por que a falha de envio não vira erro na resposta

`/password/forgot` devolve a mesma coisa exista ou não a conta, de propósito
(ver item 2 acima). Se uma exceção de envio escapasse, a rota passaria a
responder 500 **só para e-mails cadastrados** — reconstruindo exatamente o
oráculo que o resto do fluxo evita. Por isso `_entregar_link_de_reset` absorve
qualquer falha e registra no log.

## Alternativa para abrir o beta antes disso

Induzir o login com Google — que já funciona e não tem senha para esquecer — e
deixar o cadastro por senha em segundo plano. A tela de login já traz o botão
do Google em primeiro lugar.
