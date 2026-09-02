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

## O que falta: entrega do e-mail

Não há provedor de e-mail configurado neste backend, e inventar um seria
inventar infraestrutura. Enquanto isso, `auth._entregar_link_de_reset` registra
o link no log em nível WARNING:

```
fly logs -a sapiens-aluno | grep "RESET DE SENHA"
```

Isso mantém o fluxo completo e auditável, e permite destravar um aluno
manualmente, mas **não é aceitável como estado permanente de um beta público**:
depende de alguém ler o log e enviar o link à mão.

### Para ligar o envio de verdade

Só o corpo de `_entregar_link_de_reset` muda — nada mais no fluxo. Com Resend,
por exemplo:

```python
async def _entregar_link_de_reset(email: str, token: str) -> None:
    base = (settings.CORS_ORIGINS or ["http://localhost:3000"])[0].rstrip("/")
    link = f"{base}/redefinir-senha?token={token}"
    async with httpx.AsyncClient(timeout=10) as cliente:
        await cliente.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={
                "from": "Sapiens <nao-responda@seudominio.com.br>",
                "to": [email],
                "subject": "Redefinir sua senha do Sapiens",
                "html": f'<p>Para criar uma senha nova, <a href="{link}">clique aqui</a>. '
                        f'O link vale por {PASSWORD_RESET_TTL_MINUTOS} minutos.</p>'
                        f'<p>Se não foi você que pediu, ignore este e-mail.</p>',
            },
        )
```

Depois: declarar `RESEND_API_KEY` em `settings.py` (mesmo padrão das outras) e
publicar com `fly secrets set`. O domínio remetente precisa estar verificado no
provedor, senão o e-mail cai em spam.

## Alternativa para abrir o beta antes disso

Induzir o login com Google — que já funciona e não tem senha para esquecer — e
deixar o cadastro por senha em segundo plano. A tela de login já traz o botão
do Google em primeiro lugar.
