---
tags: [produto, catalogo, venda]
atualizado: 2026-09-18
---

# Catálogo — cursos, e-books, live, mentoria e direitos

Preços em [[economia-de-sparks]]. Aqui está **como cada produto se comporta**.

## Aula ao vivo — toda quinta, 20h de Brasília, 60 min, Google Meet

Cobrada **por edição**. A edição é identificada pela data da quinta (`AAAA-MM-DD`),
e `proxima_live()` é o **único** lugar que calcula qual está sendo vendida: durante
a aula (e 30 min antes) a edição corrente continua sendo a de hoje — senão quem
paga às 20h30 compraria a da semana seguinte.

- **O link do Meet só sai para quem pagou** (`_montar_live` devolve `link: None`
  para os demais). É publicado por edição pelo admin: um documento `cursos_config`
  por **data**, nunca um "link atual" sobrescrito. Só aceita
  `https://meet.google.com/...`.
- **Comprar antes de o link existir é permitido de propósito** — o aluno compra a
  **vaga**. O painel do admin mostra aviso vermelho quando existe gente paga numa
  edição sem link publicado; é o que impede a promessa de ser esquecida.
- **A live INSCREVE** quem tem o direito, na leitura do `GET /cursos` — é de
  `cursos_live_acessos` que sai a lista de quem recebe o link no WhatsApp.
- Tela própria: `/aula-ao-vivo` (`/live` redireciona). `LIVE_DURACAO_MINUTOS` tem
  espelho em `frontend/src/lib/live.js`; os dois contam a **mesma** hora de fim, que
  é o que decide quando a edição vira a da semana seguinte.

## Cursos — pré-venda vitalícia

Compra única, acesso vitalício. Quem não quer comprar tem o botão grátis "só me
avise" ao lado. O sistema pedagógico por trás está em [[cursos-conteudo]].

**O curso NÃO cria documento de compra** quando vem por direito. O direito é o
registro, e vale para curso que ainda entrar no catálogo. Um doc de 0 Spark
poluiria o número de "compradores" da pré-venda, que é a **dívida em dinheiro
real**.

Capa = duas cores + um glifo (`cursos.Capa`, `curso/CapaDoCurso.jsx`), não um JPEG
por curso.

## Mentoria — lista de espera

`/mentoria`, `mentoria_routes.py`. **Substituiu a "aula particular"**: é uma lista
de espera com o mesmo mentor, devolve a posição na fila, e **reenviar o formulário
corrige o pedido sem criar um segundo nem perder o lugar**. Nome/e-mail/WhatsApp
são checados **antes** do débito, e o índice `aulas_particulares.user_id` é único.

A coleção do Mongo continua se chamando `aulas_particulares` para não perder o
histórico — **o nome da coleção não é o nome do produto.**

## Pacotes de Sparks concedem DIREITOS

Até 2026-09-15 todo pacote vendia a mesma coisa em quantidades diferentes: saldo.
Hoje o de **4.000 Sparks (R$119,90)** vende direitos.

- `sparks_store.SparksPackage.direitos` — tupla de chaves de uma **lista fechada**
  (`sparks_store.DIREITOS`). `beneficios` é o texto que a loja escreve, um por
  direito. **Anunciar e conceder leem a mesma fonte** — é todo o desenho.
- `sparks_payments_service` concede no **mesmo ponto** do crédito de Sparks (só
  webhook, só pagamento aprovado).
- `fs.ler_direitos(uid)` faz **uma** leitura e devolve todos. Falha → tudo `False`
  (ver [[custo-de-leitura]]).

**A escada:** pacote mais caro nunca concede menos direito que um mais barato — há
teste que quebra o build. Ver [[decisoes-do-dono]].

### Os direitos

`sparks_store.DIREITOS` (lista fechada): `cursos_inclusos`, `lives_inclusas`,
`mentis_ilimitada`, `comunidade_vip`.

- **`mentis_ilimitada`** — o atalho vive no ponto único de cobrança
  (`mentis_routes._cobrar`), **antes** do débito. Ver a divergência aberta abaixo.
- **`comunidade_vip`** — permanente. É uma **sala** do mural (`?sala=vip`), não uma
  coleção nova: voto, melhor resposta, moderação e exclusão por LGPD continuam
  valendo sem segunda implementação. A porta (`_exigir_vip`, **403 e não 404**) está
  em três lugares: listagem, link direto de uma dúvida (que circula no WhatsApp) e
  resposta. Admin entra sem comprar, porque modera.
- **`lives_inclusas`** e **`cursos_inclusos`** — hoje só no pacote de 4.000.

### Divergência aberta: "por um mês" é só a vitrine

> [!warning] A loja anuncia prazo; o backend concede permanente.
> `beneficios` diz **"Mentis ILIMITADA por um mês"**, mas `conceder_direitos` grava
> só `{direito}: True` + `{direito}_em` (quando foi concedido) — **não existe
> `_ate`, nem `PRAZO_DOS_DIREITOS_DIAS`, nem checagem de vencimento em lugar
> nenhum.** Verificado no código em 2026-09-18.
>
> Hoje **entregamos mais do que anunciamos** — o lado seguro da divergência, mas
> ainda uma divergência. Fechá-la exige guardar o vencimento por aluno e checá-lo em
> `mentis_routes`.
>
> **Enquanto isso não existir, não escreva em lugar nenhum que o direito expira de
> fato.** A instrução está no próprio `sparks_store.py`, junto do pacote.

`conceder_direitos` é idempotente por natureza (escrever `True` duas vezes não muda
nada), então o reenvio de webhook não precisa de guarda extra.

## Grandfathering já concedido

Quem comprou o pacote de 1.500 **antes de 16/09** continua entrando de graça na
live: a flag está gravada em `students/{uid}` e não foi revogada. Tirar do catálogo
para de prometer, não desfaz a promessa. Se um dia for preciso revogar, é varredura
no Firestore, não uma linha de catálogo.

## A contagem regressiva do ENEM

`components/ContagemEnem.jsx` + `lib/enem.js`. O número que vende não é "dias": é
**quantas quintas ainda cabem antes da prova**. Foi **desacoplada** da aula ao vivo
em 17/09 — não volte a citar quinta-feira ali.

---
Relacionado: [[economia-de-sparks]] · [[pagamentos]] · [[cursos-conteudo]] · [[marca]]
