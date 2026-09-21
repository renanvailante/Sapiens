---
tags: [regra, produto, etica]
atualizado: 2026-09-18
---

# Regras invioláveis

Regras declaradas pelo dono do produto ou pagas com incidente. Cada uma é a
primeira coisa a sumir quando alguém tiver pressa. **Nenhuma delas se revoga
sozinha no meio de uma tarefa** — se uma atrapalhar o que foi pedido, pergunte.

## Produto

**Nenhum aluno baixa nada do ecossistema Sapiens.** Só admin. Declarada em
2026-09-17 ("nunca permita nenhum aluno, fora os admin, baixar nenhum tipo de
coisa do ecossistema Sapiens"), sem escopo — vale para o produto inteiro, não só
para o e-book que a disparou. Antes de escrever qualquer `download`, exportação ou
`target="_blank"` para arquivo numa tela de aluno, construa o leitor in-app. Foi
o que transformou o e-book de link de PDF em `pages/EbookLeitor.jsx`.
Duas exceções, de categoria diferente: exportar os **próprios dados pessoais**
(`MeusDadosLGPD.jsx`, direito legal de portabilidade) e instalar o PWA.

**Os nomes reais da ontologia nunca aparecem para o aluno.** São a IP do produto.
O mapa de habilidades é um hexágono **cosmético** com rótulos inventados (o
endpoint é `GET /cognitive-profile`; a tela que o desenha é `/progresso`). O único elo entre o dado real e a camada cosmética é
`HUB_DOMAIN_MAP` (11 `DOM-*` reais → 6 hubs, muitos-para-um) e ele serve só para
derivar percentual — **nunca** para inferência ou relatório pedagógico.

**O produto nunca afirma que o aluno estudou o que ele pulou.** Quem passa na
sondagem de domínio fica `pulada_em` com a evidência gravada, e **nunca**
`concluida_em`.

**Nunca se promete o conteúdo da aula ao vivo** (ninguém sabe qual é). O convite é
sempre "leve esta pergunta". Há teste que falha se aparecer "vai ensinar" / "aula
sobre".

**Nunca pintar de verde uma alternativa sem saber o gabarito.**
`GET /treino/questoes-geradas` não devolve gabarito; a tela pintava de verde a
resposta *errada* do aluno ao reabrir. `Alternativas.test.js` trava isso.

## Ética da gamificação

A linha está no cabeçalho de `engajamento.py` e tem teste (`TestLinhaEtica`).
Nasceu do pedido "o mais próximo possível de dark patterns, mas de forma ética" —
a leitura adotada foi **pressão real e honesta sim, engano não**:

- sem urgência, escassez ou prova social falsas;
- sem bots na liga;
- XP não se compra;
- recompensa fixa e anunciada;
- preço que não reage ao desespero.

A régua ao mexer em gamificação: *"isto seria verdade se o aluno visse o código?"*

O mesmo vale para a venda personalizada (`lib/venda.js`): toda frase é aritmética
sobre dado que o próprio aluno gerou; sem número, sem frase. Não se vende a alguém
o que ele já tem. Ver [[engajamento]].

**Nenhuma escassez inventada.** A contagem regressiva do ENEM conta *quintas que
ainda cabem antes da prova*, que é aritmética. O `PainelDeProgresso` perdeu a
linha "faltam X dias" porque dois contadores da mesma data divergiam em um dia.

## Dados e privacidade

**Coletar não é inferir (GL-3).** O bloco `desempenho` do evento é coletado e
**não forma crença** sobre o aluno. Descrever ("você responde mais à noite") é
permitido; inferir a partir disso, não. `compute_diagnostico_real` não lê a chave
da telemetria descritiva. Não misture os dois caminhos.

**Toda coleção por usuário entra em `dados_pessoais.COLECOES_POR_USUARIO`.** Sai
com a conta. O teste de inventário LGPD pega quem esquecer.

**Menor de idade autodeclarado** revela nome + WhatsApp do responsável,
obrigatórios no cadastro por e-mail (LGPD art. 14). Quem se declara maior **nunca**
guarda campo de responsável, nem mandando um.

**Credencial de banco nunca é escrita em arquivo do repo nem salva em memória** —
só `fly secrets set`. Pedido explícito do dono para o Mongo Atlas do app professor.

## Dinheiro

**O Mercado Pago decide, não nós.** Só credita se `GET /v1/payments/{id}` responder
`approved` — nunca o corpo do webhook, nunca o navegador, nunca o status guardado
no nosso Mongo. Sem isso, a rede de segurança vira máquina de dar Spark de graça
para quem só abriu o QR Code. Ver [[pagamentos]].

**Nunca propor aprovação manual de pagamento.** Pedido explícito: "a aprovação dos
Sparks tem que ser imediata ao entrar o dinheiro, eu não quero ficar aprovando
toda hora".

**Direito concedido não se revoga por mudança de catálogo.** Quem comprou o pacote
de 1.500 antes de 16/09 continua entrando de graça na live: a flag está gravada em
`students/{uid}` e nenhuma migração a tirou. Tirar do catálogo para de prometer, não
desfaz a promessa. Revogar, se um dia for preciso, é varredura no Firestore — nunca
uma linha de catálogo.

**`mentis_ilimitada` tem prazo de 30 dias — exceção explícita à regra acima,
pedida pelo dono em 2026-09-21.** Reverte a regra que valia entre 20/09 e
21/09 ("não afirme que um direito expira" — chegou a divergir na vitrine
antes disso também, "por um mês" entre 16/09 e 20/09, então este campo já
mudou de direção duas vezes; ver o histórico completo em [[catalogo]]). A
migração dá a quem já tinha o direito permanente uma janela nova de 30 dias
a partir de **hoje**, nunca a partir da compra original — ninguém perde
acesso no instante em que a migração roda, decisão também explícita do
dono. **Os outros três direitos do pacote de R$119,90
(`cursos_inclusos`/`lives_inclusas`/`comunidade_vip`) continuam cobertos
pela regra "direito concedido não se revoga" acima, sem prazo nenhum** —
esta exceção é só da Mentis, não abra precedente para generalizar sem nova
decisão explícita.

## Custo de infraestrutura

**Nenhuma requisição pode custar O(eventos do aluno) em leituras do Firestore.**
Regra nascida de um apagão. Ver [[custo-de-leitura]].

---
Relacionado: [[decisoes-do-dono]] · [[engajamento]] · [[pagamentos]] · [[custo-de-leitura]]
