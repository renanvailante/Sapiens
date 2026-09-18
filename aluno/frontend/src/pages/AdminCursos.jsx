import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  AlertTriangle, MessageCircleMore, Copy, Check, Users,
  Zap, Bell, ArrowRight, BookOpen, RefreshCw, FilePlus2, Wand2, Trash2,
  Loader2, X,
} from "lucide-react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import PublicarLinkDaLive from "../components/PublicarLinkDaLive";

/**
 * Admin · Aula ao vivo e cursos.
 *
 * A tela existe para UMA tarefa recorrente de quinta-feira: publicar o link
 * do Meet da edição e falar com quem pagou por ela. Por isso o link fica em
 * cima, o aviso de "tem gente paga e nenhum link publicado" é vermelho, e
 * cada inscrito traz o botão que abre a conversa no WhatsApp — a informação
 * não serve para ser consultada, serve para ser usada.
 *
 * Embaixo ficam os cursos em pré-venda, e ali o número que importa é quem já
 * PAGOU por um curso que ainda não existe: é a dívida assumida com aluno. A
 * fila de quem só quer ser avisado vem ao lado, como evidência de qual dos
 * quatro construir primeiro.
 */

function LinhaDeContato({ pessoa, testid }) {
  return (
    <div
      className="flex flex-wrap items-center gap-3 rounded-xl border border-zinc-100 px-3 py-2.5"
      data-testid={testid}
    >
      <div className="min-w-[9rem] flex-1">
        <div className="truncate text-sm font-medium text-zinc-900">{pessoa.nome || pessoa.user_id}</div>
        <div className="truncate text-xs text-zinc-500">{pessoa.email}</div>
      </div>
      {pessoa.whatsapp_link ? (
        <a
          href={pessoa.whatsapp_link}
          target="_blank"
          rel="noopener noreferrer"
          className="pill inline-flex shrink-0 items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 font-mono-alt text-xs text-emerald-700 hover:bg-emerald-100"
          data-testid={`${testid}-whatsapp`}
        >
          <MessageCircleMore className="h-3.5 w-3.5" /> {pessoa.whatsapp}
        </a>
      ) : (
        <span className="shrink-0 font-mono-alt text-xs text-zinc-300" title="Este aluno não informou WhatsApp">
          sem WhatsApp
        </span>
      )}
    </div>
  );
}

/**
 * O PAINEL DE QUEM PRODUZ O CONTEÚDO.
 *
 * Responde três perguntas que a equipe de conteúdo faz toda semana, e que
 * nenhum outro lugar do produto responde:
 *
 * 1. **O que já está publicado?** Estações, exercícios, vídeos.
 * 2. **A progressão existe de verdade?** A distribuição por nível é o número
 *    que denuncia um curso inteiro escrito no nível 2 — que passa em todas as
 *    outras validações e não ensina ninguém a subir.
 * 3. **O que quebrou?** Curso com qualquer problema de validação sai do ar
 *    inteiro, e é aqui que aparece o motivo exato, arquivo por arquivo.
 *
 * "Recarregar do disco" existe para o ciclo de produção: publicar uma estação,
 * conferir, corrigir. Sem ele, cada vírgula num JSON custaria um deploy para
 * ser conferida.
 */
/**
 * PUBLICAR UMA AULA A PARTIR DO TEXTO DELA.
 *
 * O caminho de conteúdo deste produto sempre foi por commit: escreve-se o JSON
 * do contrato, abre-se um PR, espera-se o deploy. É a resposta certa para um
 * curso inteiro (revisão, diff, rollback) e a resposta errada para uma
 * estação: quem está escrevendo aula quer ver a aula no ar hoje.
 *
 * Aqui a pessoa cola o texto — explicação, exemplos, questões com as
 * alternativas, a resposta certa e o porquê dela — e o servidor faz o resto:
 * compila em blocos, embaralha as alternativas, reparte o feedback por
 * distrator e valida contra o MESMO contrato do conteúdo em arquivo.
 *
 * **A prévia não é enfeite, é o ponto.** O compilador toma decisões visíveis
 * (a posição das alternativas muda, o feedback é fatiado, o nível é deduzido),
 * e publicar sem olhar isso é publicar no escuro. Por isso são dois botões, e
 * o de publicar só acende quando o texto compilou inteiro e nenhuma estação
 * tem problema de contrato.
 *
 * O que NÃO se faz por aqui: criar um curso novo no catálogo. Título, preço e
 * status são decisão de produto e moram em `cursos.py` — um texto colado não
 * inventa uma coisa à venda.
 */

/**
 * A ESPECIFICAÇÃO — o que este campo espera, escrita para ser COLADA em outro
 * lugar.
 *
 * Quem escreve os cursos não escreve dentro deste painel: escreve num modelo
 * de linguagem, revisa, e cola o resultado aqui. Então a documentação do
 * formato não pode ser só uma ajuda para ler — ela precisa ser um texto que
 * funcione como INSTRUÇÃO para quem vai gerar a aula. É por isso que ela está
 * ao lado do campo, e com um botão de copiar: a mesma frase que explica o
 * formato é a frase que produz o formato.
 *
 * Ela descreve o que o compilador de fato aceita (`cursos_ingestao`), e não
 * um ideal. Cada linha daqui tem uma regra correspondente lá; quando uma
 * mudar, a outra muda junto.
 */
const ESPECIFICACAO = `Escreva uma ESTAÇÃO de curso (uma aula fechada, de 10 a 20 minutos) em texto
markdown, exatamente no formato abaixo. Não escreva mais nada fora dele.

# Título da estação

## Objetivo
Uma frase: o que o aluno sai sabendo FAZER.

## Conteúdo
A explicação, do zero. Pode ter vários parágrafos e subtítulos em "### ".
Pode usar tabelas de markdown e \`código\` entre crases. Escreva à vontade —
texto longo é bem-vindo, e cada "### " vira um bloco separado na tela.

## Exemplos resolvidos
**Exemplo 1.** O enunciado do exemplo
- primeiro passo
- segundo passo
Uma linha final com o que se generaliza dele.

## Erros comuns
O que costuma dar errado. (Outras seções também podem existir: "Estratégias",
"Dicas", "Pegadinhas", ou qualquer título seu — todas viram blocos de leitura.)

## Exercícios

### Questão 1
O enunciado da questão de múltipla escolha.
A) alternativa
B) alternativa
C) alternativa
D) alternativa
**Resposta:** B
**Feedback:** Explique a resposta certa. Depois comente CADA alternativa errada
citando a letra ("A alternativa A soma antes de multiplicar. C ignora o sinal.").
dificuldade: básico

### Questão 2
O enunciado de uma questão DISSERTATIVA — o aluno responde escrevendo.
Tipo: dissertativa
**Critérios:**
- o que a resposta precisa conter
- outro ponto que a resposta precisa conter
**Resposta esperada:** a resposta que o autor espera (o aluno nunca vê).
dificuldade: intermediário

## Desafio final
Uma questão mais difícil, de resposta ÚNICA.
**Resposta:** 44
**Resolução:**
- como se chega lá

REGRAS QUE NÃO PODEM SER QUEBRADAS
1. Toda questão de alternativas precisa das linhas \`**Resposta:**\` e
   \`**Feedback:**\`. Os dois-pontos são obrigatórios.
2. Toda questão dissertativa precisa de \`**Critérios:**\` com pelo menos um
   item em "- ". Sem critério, ela não pode ser corrigida e fica de fora.
3. A resposta certa pode ficar em qualquer letra: as alternativas são
   embaralhadas na publicação.
4. \`dificuldade:\` embaixo de cada questão (básico, intermediário, avançado)
   é o que dá progressão à estação. Do mais fácil para o mais difícil.
5. A resposta do desafio final tem de ser um número ou uma expressão curta
   (até 24 caracteres). Nada de resposta em prosa.
6. NUNCA escreva preço, custo, Sparks, XP ou qualquer valor em dinheiro.
7. De 6 a 10 exercícios por estação, sendo 1 ou 2 dissertativos.

Para várias estações de uma vez, escreva uma depois da outra, cada uma
começando com sua linha "# ".`;

const MODELO = `---
station_id: 07
title: "Potenciação"
---
# Estação 07 — Potenciação

## Objetivo

Ao final desta estação, você saberá resolver potências e usar as propriedades
que mais aparecem na prova.

## Conteúdo

Potência é multiplicação repetida: \`2³ = 2 × 2 × 2 = 8\`.

### Expoente zero

Todo número diferente de zero elevado a zero é \`1\`.

## Exemplos resolvidos

**Exemplo 1.** \`2³ × 2²\`
- Mesma base: somam-se os expoentes, \`2⁵\`
- \`2⁵ = 32\`

## Exercícios

### Questão 1
Calcule \`3²\`.
A) 9
B) 6
C) 5
D) 8
**Resposta:** A
**Feedback:** \`3² = 3 × 3 = 9\`. A alternativa B multiplica a base pelo expoente. C soma os dois. D chuta um valor próximo.

dificuldade: básico

### Questão 2
Calcule \`2³ × 2²\`.
A) 32
B) 64
C) 16
D) 12
**Resposta:** A
**Feedback:** Mesma base: somam-se os expoentes, \`2⁵ = 32\`. B multiplica os expoentes em vez de somar. C para no \`2⁴\`.

dificuldade: intermediário

### Questão 3
Explique, com suas palavras, por que \`2³ × 2²\` não dá \`2⁶\`.
Tipo: dissertativa
**Critérios:**
- Diz que os expoentes se SOMAM, e não se multiplicam
- Mostra ou descreve a expansão \`2 × 2 × 2 × 2 × 2\`
**Resposta esperada:** São cinco fatores 2 ao todo, então o expoente é 3 + 2 = 5.

dificuldade: avançado
`;

/** A régua do lado do campo: o que colar, e o texto pronto para pedir isso a
 *  quem escreve — pessoa ou modelo. */
function Especificacao({ aoUsarModelo }) {
  const [copiado, setCopiado] = useState(false);

  const copiar = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(ESPECIFICACAO);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2500);
      toast.success("Especificação copiada. Cole no gerador de texto.");
    } catch {
      toast.error("Não deu para copiar. Selecione o texto e copie à mão.");
    }
  }, []);

  return (
    <aside className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4" data-testid="admin-texto-especificacao">
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
        O que este campo espera
      </div>
      <p className="mt-2 text-[13px] leading-relaxed text-zinc-600">
        O compilador aceita <strong className="font-semibold text-zinc-800">texto de verdade</strong> —
        aula longa, subtítulos, tabelas, exemplos, questões de alternativa e questões
        dissertativas que a Mentis corrige. O que ele precisa é de três marcas:{" "}
        <code className="font-mono-alt">## Objetivo</code>,{" "}
        <code className="font-mono-alt">### Questão N</code> e, em cada questão,{" "}
        <code className="font-mono-alt">**Resposta:**</code> (alternativas) ou{" "}
        <code className="font-mono-alt">**Critérios:**</code> (dissertativa).
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={copiar}
          className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-900 px-4 py-2 text-xs font-semibold text-zinc-900"
          data-testid="admin-texto-copiar-espec"
        >
          {copiado ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copiado ? "Copiado" : "Copiar a especificação"}
        </button>
        <button
          type="button"
          onClick={aoUsarModelo}
          className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-4 py-2 text-xs font-medium text-zinc-500"
          data-testid="admin-texto-modelo"
        >
          Colar um exemplo pronto
        </button>
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-zinc-400">
        A especificação é o texto que você cola no gerador (DeepSeek, ChatGPT) antes de
        pedir a aula. O que ele devolver, cole aqui ao lado.
      </p>

      <pre
        className="mt-3 max-h-[26rem] overflow-auto whitespace-pre-wrap rounded-xl border border-zinc-200 bg-white p-3 font-mono-alt text-[11px] leading-relaxed text-zinc-600"
        data-testid="admin-texto-espec-corpo"
      >
        {ESPECIFICACAO}
      </pre>

      <ul className="mt-3 space-y-1.5 text-[12px] leading-relaxed text-zinc-500">
        <li>
          <strong className="font-semibold text-zinc-700">O que é tolerado:</strong> seção
          numerada (<code className="font-mono-alt">## 2. Conteúdo</code>), título de questão
          sem marcação, alternativa com traço ou negrito, <code className="font-mono-alt">Gabarito:</code>{" "}
          no lugar de <code className="font-mono-alt">Resposta:</code>, seção com nome que o
          compilador não conhece (vira leitura, com o título dela), e texto sem{" "}
          <code className="font-mono-alt">## Objetivo</code> (entra com aviso).
        </li>
        <li>
          <strong className="font-semibold text-zinc-700">O que faz uma questão ficar de
          fora:</strong> gabarito que não é nenhuma das alternativas, questão de alternativa
          sem <code className="font-mono-alt">**Resposta:**</code> e dissertativa sem
          critério. Ela sai nos avisos, nominalmente — o resto da aula vai ao ar.
        </li>
        <li>
          <strong className="font-semibold text-zinc-700">Dissertativa:</strong> a Mentis
          corrige critério por critério e cobra Sparks do aluno; o veredito é do servidor
          (70% dos critérios). Os critérios aparecem para o aluno ANTES de ele escrever; a
          resposta esperada, nunca.
        </li>
      </ul>
    </aside>
  );
}

/** Um exercício como ele ficou depois de compilado — com o gabarito à mostra,
 *  que é justamente o que precisa ser conferido antes de ir para o aluno. */
function ExercicioCompilado({ bloco }) {
  return (
    <div className="rounded-xl border border-zinc-200 p-3" data-testid={`previa-${bloco.bloco_id}`}>
      <div className="flex items-center gap-2 font-mono-alt text-[10px] uppercase tracking-[0.18em] text-zinc-400">
        {bloco.tipo === "desafio" ? "Desafio" : `Nível ${bloco.nivel}`}
        <span className="text-zinc-300">·</span>
        <span className="normal-case tracking-normal">{bloco.bloco_id}</span>
      </div>
      <p className="mt-1.5 text-sm font-medium text-zinc-900">{bloco.enunciado}</p>
      <ul className="mt-2 space-y-1">
        {(bloco.alternativas || []).map((alt) => {
          const certa = alt.id === bloco.gabarito;
          return (
            <li
              key={alt.id}
              className={`flex gap-2 rounded-lg px-2 py-1 text-[13px] ${
                certa ? "bg-emerald-50 font-semibold text-emerald-900" : "text-zinc-600"
              }`}
            >
              <span className="font-mono-alt uppercase">{alt.id})</span>
              <span className="min-w-0 flex-1">{alt.texto}</span>
              {certa && <Check className="h-3.5 w-3.5 shrink-0" />}
              {bloco.feedback?.[alt.id] && (
                <span className="hidden max-w-[45%] shrink-0 text-right text-[11px] italic text-zinc-400 md:block">
                  {bloco.feedback[alt.id]}
                </span>
              )}
            </li>
          );
        })}
      </ul>
      {bloco.formato && bloco.formato !== "multipla_escolha" && (
        <p className="mt-2 font-mono-alt text-[11px] text-zinc-500">
          resposta {bloco.formato === "numerico" ? "numérica" : "em texto curto"}:{" "}
          {JSON.stringify(bloco.gabarito)}
        </p>
      )}
      {bloco.solucao && (
        <p className="mt-2 border-t border-zinc-100 pt-2 text-[12px] text-zinc-500">
          <strong className="font-semibold text-zinc-700">Como se resolve:</strong> {bloco.solucao}
        </p>
      )}
    </div>
  );
}

function EstacaoCompilada({ estacao }) {
  const contagem = estacao.contagem || {};
  const exercicios = (estacao.blocos || []).filter(
    (b) => b.tipo === "exercicio" || b.tipo === "desafio",
  );
  return (
    <div className="card-sapiens rounded-2xl p-4" data-testid={`previa-estacao-${estacao.estacao_id}`}>
      <div className="flex flex-wrap items-baseline gap-2">
        <span className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
          Estação {String(estacao.numero ?? "").padStart(2, "0")}
        </span>
        <h4 className="font-display text-lg font-bold tracking-tight text-zinc-950">{estacao.titulo}</h4>
        <span className="font-mono-alt text-[10px] text-zinc-400">{estacao.estacao_id}</span>
      </div>
      <p className="mt-1 text-[13px] leading-relaxed text-zinc-600">{estacao.objetivo}</p>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono-alt text-[10px] uppercase tracking-[0.16em] text-zinc-400">
        <span>{estacao.duracao_minutos} min</span>
        <span>{contagem.texto || 0} leitura</span>
        <span>{contagem.exemplo || 0} exemplos</span>
        <span>{contagem.tabela || 0} tabelas</span>
        <span>{contagem.exercicio || 0} exercícios</span>
        <span>{contagem.desafio || 0} desafio</span>
        <span className="text-zinc-500">
          conclui com {estacao.conclusao?.minimo ?? contagem.exercicio} acertos
        </span>
      </div>

      {estacao.problemas?.length > 0 && (
        <ul className="mt-3 space-y-1 rounded-xl bg-rose-50 p-3">
          {estacao.problemas.map((p, i) => (
            <li key={i} className="flex gap-2 text-[12px] text-rose-700">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {p}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 space-y-2">
        {exercicios.map((b) => <ExercicioCompilado key={b.bloco_id} bloco={b} />)}
      </div>
    </div>
  );
}

function PublicarPorTexto({ cursos, aoPublicar }) {
  const [aberto, setAberto] = useState(false);
  const [cursoId, setCursoId] = useState("");
  const [trilha, setTrilha] = useState("");
  const [texto, setTexto] = useState("");
  const [previa, setPrevia] = useState(null);
  const [ocupado, setOcupado] = useState("");
  const [publicados, setPublicados] = useState([]);

  const carregarPublicados = useCallback(() => {
    api
      .get("/admin/cursos/conteudo/publicados")
      .then(({ data }) => setPublicados(data.cursos || []))
      .catch(() => {});
  }, []);

  useEffect(() => { if (aberto) carregarPublicados(); }, [aberto, carregarPublicados]);

  const corpo = {
    curso_id: cursoId,
    texto,
    trilha_titulo: trilha,
  };

  const problemasDoServidor = (e) => {
    const detalhe = e?.response?.data?.detail;
    if (detalhe?.problemas?.length) {
      setPrevia((p) => ({ ...(p || {}), problemas: detalhe.problemas, pode_publicar: false }));
      return detalhe.mensagem || "O texto não passou na validação.";
    }
    return errMsg(e, "Não foi possível processar o texto.");
  };

  const compilar = async () => {
    setOcupado("compilar");
    try {
      const { data } = await api.post("/admin/cursos/conteudo/compilar", corpo);
      setPrevia(data);
      if (data.pode_publicar) {
        toast.success(`${data.estacoes.length} estação(ões) prontas para publicar.`);
      }
    } catch (e) {
      toast.error(problemasDoServidor(e));
    } finally {
      setOcupado("");
    }
  };

  const publicar = async () => {
    setOcupado("publicar");
    try {
      const { data } = await api.post("/admin/cursos/conteudo/publicar", corpo);
      toast.success(`Publicado: ${data.publicado.estacoes.length} estação(ões) no ar.`);
      setTexto("");
      setPrevia(null);
      carregarPublicados();
      aoPublicar?.(data.inventario);
    } catch (e) {
      toast.error(problemasDoServidor(e));
    } finally {
      setOcupado("");
    }
  };

  const tirarDoAr = async (curso) => {
    if (!window.confirm(
      `Tirar do ar as ${curso.estacoes.length} estação(ões) publicadas por texto em ${curso.curso_id}?\n\n`
      + "O conteúdo que veio de arquivo continua no ar — ele nunca foi apagado.",
    )) return;
    try {
      const { data } = await api.delete(`/admin/cursos/conteudo/publicados/${curso.curso_id}`);
      toast.success("Publicação removida.");
      carregarPublicados();
      aoPublicar?.(data.inventario);
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível remover."));
    }
  };

  return (
    <div className="mt-4">
      <button
        onClick={() => setAberto((a) => !a)}
        className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-bold"
        data-testid="admin-abrir-texto"
      >
        {aberto ? <X className="h-4 w-4" /> : <FilePlus2 className="h-4 w-4" />}
        {aberto ? "Fechar" : "Criar conteúdo a partir de texto"}
      </button>

      {!aberto ? null : (
        <div className="mt-4 space-y-4" data-testid="admin-publicar-texto">
          <div className="card-sapiens rounded-2xl p-5">
            <h3 className="font-display text-lg font-bold tracking-tight text-zinc-950">
              Cole a aula escrita — o site monta a estação
            </h3>
            <p className="mt-1 text-[13px] leading-relaxed text-zinc-600">
              Explicação, exemplos, questões, gabarito e o porquê de cada erro. O servidor
              compila em blocos, embaralha as alternativas, reparte o feedback por alternativa e
              valida pelo mesmo contrato do conteúdo que entra por commit. Fica no ar na hora —
              sem deploy.
            </p>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <label className="block">
                <span className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
                  Curso de destino
                </span>
                <select
                  value={cursoId}
                  onChange={(e) => { setCursoId(e.target.value); setPrevia(null); }}
                  className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-900"
                  data-testid="admin-texto-curso"
                >
                  <option value="">Escolha um curso do catálogo…</option>
                  {cursos.map((c) => (
                    <option key={c.curso_id} value={c.curso_id}>
                      {c.curso_id}{c.publicado ? ` · ${c.estacoes} estações` : " · sem conteúdo ainda"}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
                  Parte do curso (trilha)
                </span>
                <input
                  value={trilha}
                  onChange={(e) => setTrilha(e.target.value)}
                  placeholder="Ex.: Números e operações"
                  className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-900"
                  data-testid="admin-texto-trilha"
                />
                <span className="mt-1 block text-[11px] text-zinc-400">
                  Se o curso já tiver uma parte com esse nome, as estações entram no fim dela.
                </span>
              </label>
            </div>

            {/* O campo e a régua LADO A LADO. A especificação embaixo do campo
                (ou escondida num "como escrever") é lida depois de colar, que
                é tarde: ela existe para ser lida ANTES, e copiada para o
                lugar onde o texto é escrito. */}
            <div className="mt-3 grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
              <label className="block">
                <span className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
                  O texto da aula
                </span>
                <textarea
                  value={texto}
                  onChange={(e) => { setTexto(e.target.value); setPrevia(null); }}
                  rows={26}
                  spellCheck={false}
                  placeholder="Cole aqui o texto inteiro da estação (ou de várias, uma depois da outra)…"
                  className="mt-1 h-full min-h-[24rem] w-full rounded-xl border border-zinc-200 px-3 py-2 font-mono-alt text-[12px] leading-relaxed outline-none focus:border-zinc-900"
                  data-testid="admin-texto-corpo"
                />
                <span className="mt-1 block text-[11px] text-zinc-400">
                  {texto.trim()
                    ? `${texto.trim().split(/\s+/).length.toLocaleString("pt-BR")} palavras coladas`
                    : "Não há limite de tamanho: cole a aula inteira, com quantas estações forem."}
                </span>
              </label>
              <Especificacao aoUsarModelo={() => { setTexto(MODELO); setPrevia(null); }} />
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                onClick={compilar}
                disabled={!cursoId || !texto.trim() || Boolean(ocupado)}
                className="pill inline-flex items-center gap-2 rounded-full border border-zinc-900 px-5 py-2.5 text-sm font-semibold text-zinc-900 disabled:opacity-40"
                data-testid="admin-texto-compilar"
              >
                {ocupado === "compilar" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                Ver o que vai virar
              </button>
              <button
                onClick={publicar}
                disabled={!previa?.pode_publicar || Boolean(ocupado)}
                className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-bold disabled:opacity-40"
                data-testid="admin-texto-publicar"
              >
                {ocupado === "publicar" ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                Publicar no ar
              </button>
            </div>

          </div>

          {previa?.problemas?.length > 0 && (
            <ul className="space-y-1.5 rounded-2xl bg-rose-50 p-4" data-testid="admin-texto-problemas">
              {previa.problemas.map((p, i) => (
                <li key={i} className="flex gap-2 text-[13px] text-rose-700">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> {p}
                </li>
              ))}
            </ul>
          )}

          {previa?.avisos?.length > 0 && (
            <ul className="space-y-1.5 rounded-2xl bg-amber-50 p-4" data-testid="admin-texto-avisos">
              {previa.avisos.map((a, i) => (
                <li key={i} className="text-[13px] text-amber-800">{a}</li>
              ))}
            </ul>
          )}

          {previa?.estacoes?.length > 0 && (
            <div className="space-y-3">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-white/35">
                Prévia · {previa.estacoes.length} estação(ões) em “{previa.trilha?.titulo}”
              </div>
              {previa.estacoes.map((e) => (
                <EstacaoCompilada key={e.estacao_id} estacao={e} />
              ))}
            </div>
          )}

          {publicados.length > 0 && (
            <div className="card-sapiens rounded-2xl p-4" data-testid="admin-texto-publicados">
              <h4 className="font-display font-bold tracking-tight text-zinc-950">
                No ar por publicação de painel
              </h4>
              <p className="mt-0.5 text-[12px] text-zinc-500">
                O que veio de arquivo continua valendo por baixo — tirar do ar aqui devolve o
                curso ao que o repositório diz.
              </p>
              <ul className="mt-3 space-y-2">
                {publicados.map((c) => (
                  <li key={c.curso_id} className="flex flex-wrap items-center gap-3 rounded-xl border border-zinc-100 px-3 py-2">
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-semibold text-zinc-900">{c.curso_id}</div>
                      <div className="font-mono-alt text-[10px] uppercase tracking-[0.18em] text-zinc-400">
                        {c.estacoes.length} estação(ões) · versão {c.versao} · por {c.publicado_por}
                      </div>
                    </div>
                    <button
                      onClick={() => tirarDoAr(c)}
                      className="pill inline-flex items-center gap-1.5 rounded-full border border-rose-200 px-3 py-1.5 text-xs text-rose-600 hover:bg-rose-50"
                      data-testid={`admin-texto-remover-${c.curso_id}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" /> Tirar do ar
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PainelDeConteudo() {
  const [inventario, setInventario] = useState(null);
  const [recarregando, setRecarregando] = useState(false);

  const carregar = useCallback(() => {
    api
      .get("/admin/cursos/conteudo")
      .then(({ data }) => setInventario(data))
      .catch((e) => toast.error(errMsg(e, "Não foi possível ler o inventário de conteúdo.")));
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const recarregar = async () => {
    setRecarregando(true);
    try {
      const { data } = await api.post("/admin/cursos/conteudo/recarregar");
      setInventario(data);
      toast.success(
        data.problemas_totais
          ? `Recarregado com ${data.problemas_totais} problema(s).`
          : "Conteúdo recarregado do disco.",
      );
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível recarregar."));
    } finally {
      setRecarregando(false);
    }
  };

  if (!inventario) return null;

  return (
    <section className="mt-10" data-testid="admin-cursos-conteudo">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 font-display text-xl font-bold tracking-tight text-white">
            <BookOpen className="h-4 w-4 text-[#7FD8FF]" /> Conteúdo publicado
          </h2>
          <p className="mt-1 font-mono-alt text-[10px] uppercase tracking-[0.2em] text-white/30">
            schema {inventario.schema_version} · {inventario.raiz}
          </p>
        </div>
        <button
          onClick={recarregar}
          disabled={recarregando}
          className="pill inline-flex items-center gap-1.5 rounded-full border border-white/15 px-4 py-2.5 text-xs font-medium text-white/70 hover:text-white disabled:opacity-50"
          data-testid="admin-cursos-recarregar"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${recarregando ? "animate-spin" : ""}`} />
          Recarregar do disco
        </button>
      </div>

      <PublicarPorTexto cursos={inventario.cursos} aoPublicar={setInventario} />

      <div className="mt-6 space-y-2">
        {inventario.cursos.map((c) => (
          <div key={c.curso_id} className="card-sapiens rounded-2xl p-4" data-testid={`conteudo-${c.curso_id}`}>
            <div className="flex flex-wrap items-center gap-3">
              <div className="min-w-0 flex-1">
                <div className="truncate font-display font-semibold text-zinc-900">{c.curso_id}</div>
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
                  {c.publicado ? `versão ${c.versao} · ${c.trilhas?.length || 0} trilha(s)` : "sem conteúdo"}
                </div>
              </div>
              {c.publicado ? (
                <>
                  <Medida n={c.estacoes} rotulo="estações" />
                  <Medida n={c.exercicios} rotulo="exercícios" />
                  <Medida n={c.desafios} rotulo="desafios" />
                  {c.videos_pendentes > 0 && (
                    <Medida n={c.videos_pendentes} rotulo="vídeos a gravar" alerta />
                  )}
                </>
              ) : (
                <span className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-amber-600">
                  {c.problemas?.length ? "fora do ar" : "em produção"}
                </span>
              )}
            </div>

            {/* A progressão, em barras. Um curso todo num nível só salta aos
                olhos aqui e em nenhum outro lugar. */}
            {c.publicado && c.exercicios > 0 && (
              <div className="mt-3 flex items-end gap-1.5" title="Exercícios por nível">
                {Object.entries(c.exercicios_por_nivel).map(([nivel, quantos]) => (
                  <div key={nivel} className="flex-1 text-center">
                    <div
                      className="mx-auto w-full rounded-t bg-gradient-to-t from-sky-400 to-violet-400"
                      style={{ height: `${Math.max(3, (quantos / c.exercicios) * 46)}px` }}
                    />
                    <div className="mt-1 font-mono-alt text-[9px] text-zinc-400">
                      N{nivel} · {quantos}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {c.problemas?.length > 0 && (
              <ul className="mt-3 space-y-1.5 border-t border-rose-200 pt-3" data-testid={`problemas-${c.curso_id}`}>
                {c.problemas.map((p, i) => (
                  <li key={i} className="flex gap-2 text-xs text-rose-700">
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span>
                      <code className="font-mono-alt text-rose-900">{p.arquivo}</code> — {p.mensagem}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function Medida({ n, rotulo, alerta = false }) {
  return (
    <div className="shrink-0 text-right">
      <div
        className={`font-display text-xl font-extrabold leading-none tracking-tighter ${
          alerta ? "text-amber-600" : "text-zinc-950"
        }`}
      >
        {n}
      </div>
      <div className="font-mono-alt text-[9px] uppercase tracking-[0.2em] text-zinc-400">{rotulo}</div>
    </div>
  );
}

export default function AdminCursos() {
  const [dados, setDados] = useState(null);
  const [copiado, setCopiado] = useState(false);
  const [aberto, setAberto] = useState(null);

  const carregar = useCallback(() => {
    api
      .get("/admin/cursos")
      .then(({ data }) => setDados(data))
      .catch((e) => toast.error(errMsg(e, "Não foi possível carregar o painel de cursos.")));
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const live = dados?.live || {};
  const inscritos = dados?.inscritos || [];

  /** Todos os números da edição, um por linha — para colar numa lista de
   *  transmissão sem catar um a um. */
  const copiarNumeros = async () => {
    const numeros = inscritos.map((i) => i.whatsapp_e164).filter(Boolean);
    if (numeros.length === 0) {
      toast.error("Nenhum inscrito desta edição informou WhatsApp.");
      return;
    }
    try {
      await navigator.clipboard.writeText(numeros.join("\n"));
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
      toast.success(`${numeros.length} número(s) copiado(s).`);
    } catch {
      toast.error("O navegador bloqueou a cópia.");
    }
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-5xl px-5 py-7 md:px-10 md:py-10">
        <div className="mb-3 font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50">
          Admin · Cursos e live
        </div>
        <h1
          className="font-display text-4xl font-extrabold tracking-tighter text-white"
          data-testid="admin-cursos-title"
        >
          Aula ao vivo de quinta
        </h1>
        <p className="mt-3 max-w-2xl text-white/60">
          Publique o link do Meet e o tema da edição, e fale com quem já pagou. O link só
          chega ao navegador de quem comprou o acesso.
        </p>
        {/* A regra de cobrança escrita onde ela é executada: quem publica o
            link é quem responde ao aluno que perguntar por que pagou de novo. */}
        <p className="mt-2 max-w-2xl text-sm text-white/40">
          A aula custa 200 Sparks <strong className="font-semibold text-white/60">por
          edição</strong> — toda quinta de novo. A única exceção é quem comprou o pacote de
          4.000 Sparks: esses entram em todas sem pagar, e aparecem na lista abaixo com 0
          Sparks.
        </p>

        {/* Estado da edição */}
        <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="card-sapiens rounded-2xl p-4">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Edição</div>
            <div className="mt-1 font-display text-xl font-extrabold tracking-tighter text-zinc-950">
              {live.edicao || "—"}
            </div>
          </div>
          <div className="card-sapiens rounded-2xl p-4">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Inscritos</div>
            <div className="mt-1 font-display text-xl font-extrabold tracking-tighter text-zinc-950">
              {dados?.inscritos_count ?? "—"}
            </div>
          </div>
          <div className="card-sapiens rounded-2xl p-4">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Sparks</div>
            <div className="mt-1 font-display text-xl font-extrabold tracking-tighter text-zinc-950">
              {dados?.receita_sparks ?? "—"}
            </div>
          </div>
          <div className="card-sapiens rounded-2xl p-4">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Link</div>
            <div
              className={`mt-1 font-display text-xl font-extrabold tracking-tighter ${
                live.link_publicado ? "text-emerald-600" : "text-amber-600"
              }`}
            >
              {live.link_publicado ? "publicado" : "pendente"}
            </div>
          </div>
        </div>

        {/* O campo do link, o mesmo componente que abre a primeira tela do
            admin. Duas cópias do mesmo formulário divergiriam na validação, e
            o aviso de "tem gente paga sem link" só vale se for o mesmo nos
            dois lugares. Publicar aqui recarrega o painel abaixo. */}
        <div className="mt-6">
          <PublicarLinkDaLive testid="admin-cursos-form" />
        </div>

        {/* Inscritos da edição */}
        <section className="mt-8" data-testid="admin-cursos-inscritos">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 font-display text-xl font-bold tracking-tight text-white">
              <Users className="h-4 w-4 text-[#7FD8FF]" /> Quem pagou esta edição
            </h2>
            <button
              onClick={copiarNumeros}
              className="pill inline-flex items-center gap-1.5 rounded-full border border-white/15 px-4 py-2 text-xs font-medium text-white/70 hover:text-white"
              data-testid="admin-cursos-copiar-numeros"
            >
              {copiado ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              Copiar os números
            </button>
          </div>

          <div className="card-sapiens rounded-2xl p-4">
            {inscritos.length === 0 ? (
              <div className="py-6 text-center text-sm text-zinc-500">
                Ninguém comprou o acesso desta edição ainda.
              </div>
            ) : (
              <div className="space-y-1.5">
                {inscritos.map((i) => (
                  <LinhaDeContato
                    key={i.user_id}
                    pessoa={i}
                    testid={`admin-cursos-inscrito-${i.user_id}`}
                  />
                ))}
              </div>
            )}
          </div>

          {dados?.historico?.length > 1 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {dados.historico.map((h) => (
                <span
                  key={h.edicao}
                  className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 font-mono-alt text-[11px] text-white/50"
                >
                  <Zap className="h-3 w-3 text-amber-400" /> {h.edicao}: {h.inscritos}
                </span>
              ))}
            </div>
          )}
        </section>

        <PainelDeConteudo />

        {/* Pré-venda dos cursos: quem já pagou, e quem só quer ser avisado */}
        <section className="mt-10" data-testid="admin-cursos-interesse">
          <h2 className="mb-1 flex items-center gap-2 font-display text-xl font-bold tracking-tight text-white">
            <Bell className="h-4 w-4 text-[#7FD8FF]" /> Pré-venda e fila de espera
          </h2>
          <p className="mb-3 max-w-2xl text-sm text-white/50">
            O número em destaque é quem <strong className="font-semibold text-white/80">já
            pagou</strong> por um curso que ainda não existe — é a dívida assumida com
            aluno, não uma métrica. Clique para ver nome e WhatsApp de cada um.
          </p>
          <div className="space-y-2">
            {(dados?.cursos || []).map((c) => {
              const fila = dados?.interessados_por_curso?.[c.curso_id] || [];
              const pagantes = dados?.compradores_por_curso?.[c.curso_id] || [];
              const expandido = aberto === c.curso_id;
              return (
                <div key={c.curso_id} className="card-sapiens rounded-2xl p-4">
                  <button
                    onClick={() => setAberto(expandido ? null : c.curso_id)}
                    className="flex w-full items-center gap-3 text-left"
                    data-testid={`admin-cursos-curso-${c.curso_id}`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-display font-semibold text-zinc-900">{c.titulo}</div>
                      <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-amber-600">
                        {c.status === "em_breve" ? "em breve" : c.status} · {c.custo_sparks} Sparks
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="font-display text-2xl font-extrabold leading-none tracking-tighter text-emerald-700">
                        {c.compradores}
                      </div>
                      <div className="font-mono-alt text-[9px] uppercase tracking-[0.2em] text-zinc-400">
                        pagaram
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="font-display text-2xl font-extrabold leading-none tracking-tighter text-zinc-950">
                        {c.interessados}
                      </div>
                      <div className="font-mono-alt text-[9px] uppercase tracking-[0.2em] text-zinc-400">
                        na fila
                      </div>
                    </div>
                    <ArrowRight
                      className={`h-4 w-4 shrink-0 text-zinc-400 transition-transform ${expandido ? "rotate-90" : ""}`}
                    />
                  </button>
                  {expandido && (
                    <div className="mt-3 space-y-3 border-t border-zinc-100 pt-3">
                      <div>
                        <div className="mb-1.5 font-mono-alt text-[10px] uppercase tracking-[0.25em] text-emerald-700">
                          Já pagaram · {c.sparks_arrecadados} Sparks
                        </div>
                        {pagantes.length === 0 ? (
                          <div className="py-2 text-sm text-zinc-500">Ninguém comprou ainda.</div>
                        ) : (
                          <div className="space-y-1.5">
                            {pagantes.map((p) => (
                              <LinhaDeContato
                                key={p.user_id}
                                pessoa={p}
                                testid={`admin-cursos-comprador-${p.user_id}`}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                      <div>
                        <div className="mb-1.5 font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">
                          Só querem ser avisados
                        </div>
                        {fila.length === 0 ? (
                          <div className="py-2 text-sm text-zinc-500">Ninguém na fila ainda.</div>
                        ) : (
                          <div className="space-y-1.5">
                            {fila.map((p) => (
                              <LinhaDeContato
                                key={p.user_id}
                                pessoa={p}
                                testid={`admin-cursos-interessado-${p.user_id}`}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        <Link
          to="/admin/users"
          className="pill mt-8 inline-flex items-center gap-1.5 rounded-full border border-white/15 px-4 py-2.5 text-xs font-medium text-white/70 hover:text-white"
        >
          Ver todos os alunos e WhatsApps <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
}
