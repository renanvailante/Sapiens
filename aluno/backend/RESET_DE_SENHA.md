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
curl -s https://sapiens-aluno.fly.dev/ready | python3 -m json.tool | grep -A 4 '"email"'
```

`"configurado": false` significa que o link está indo só para o log.

> [!danger] `configurado: true` NÃO quer dizer que o e-mail chega
> Esse booleano só diz que as duas variáveis existem no processo. Em
> **23/09/2026** ele valia `true` enquanto o Resend recusava **todo** envio com
> `401 Unauthorized` — chave inválida ou revogada. A tela prometia o link ao
> aluno, nada chegava, e `/ready` concordava que estava tudo bem. O defeito
> existia só dentro de um `logger.exception`, e o dono do produto ficou sem
> conseguir entrar na própria plataforma.
>
> Por isso o bloco traz também `ultimo_envio` — o resultado da última tentativa
> REAL (`ok`, `FALHOU` com o status HTTP, ou `sem provedor configurado`). É a
> única coisa ali que distingue configurado de funcionando.
>
> Os dois status que aparecem na prática pedem ações opostas:
> **401** = chave inválida ou revogada → gere outra e troque o secret;
> **403** = conta do Resend ainda em modo de teste → ela só entrega para o
> e-mail do dono da conta, e é preciso verificar um domínio para sair disso.
>
> `ultimo_envio` é memória do processo: zera a cada deploy, vale por instância,
> e `verificado_em` existe para ninguém ler um `ok` antigo como notícia de
> agora. Um `desconhecido` só quer dizer que este processo ainda não teve
> nenhum pedido para entregar.

### Enquanto o envio está quebrado, ninguém precisa ficar trancado

O link completo vai para o log em `ERROR`, e vale 30 minutos:

```bash
flyctl logs --config aluno/backend/fly.toml --no-tail > /tmp/fly.log 2>&1
grep -o "https://sapiens-aluno.pages.dev/redefinir-senha?token=[A-Za-z0-9_-]*" /tmp/fly.log | tail -1
```

Peça a redefinição pela tela primeiro — é ela que gera o token — e só então leia
o log. Um pedido novo **invalida** os anteriores, então use o último.

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
