import { useCallback, useEffect, useState } from "react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { toast } from "sonner";
import {
  Plus, Trash2, Eye, EyeOff, Copy, Check, AlertTriangle, Wand2,
  ArrowRight, Loader2, ChevronDown, ChevronUp,
} from "lucide-react";

/**
 * Admin · Feed.
 *
 * Igual em espírito ao painel de cursos (`AdminCursos.jsx`): quem escreve o
 * feed não escreve dentro deste painel — escreve num modelo de linguagem
 * (DeepSeek, ChatGPT), revisa, e cola o resultado aqui. O servidor faz TODO
 * o resto sozinho — corta em cards, decide o tipo de cada um, embaralha
 * alternativas, reparte feedback e valida — e faz isso com um parser
 * determinístico (`feed_ingestao.py`, Python puro): NENHUMA chamada a uma IA
 * paga entra nesse caminho. O formato é um contrato que o Sapiens define e
 * confere sozinho, nunca uma interpretação de terceiro.
 *
 * Por isso a régua do formato mora do LADO do campo, pronta para ser colada
 * no gerador — é a mesma frase que explica o formato e que produz o formato.
 * Mudou uma regra em `feed_ingestao`? Muda a `ESPECIFICACAO` no mesmo commit.
 */

// ---------------------------------------------------------------------------
// A ESPECIFICAÇÃO — para ser colada no gerador, não só para ser lida aqui.
// ---------------------------------------------------------------------------

const ESPECIFICACAO = `Escreva um FEED de estudo em texto simples, com quantos cards quiser, um
atrás do outro. Cada card começa numa linha própria com o TIPO dele:

## TIPO — Título opcional

("QUESTÃO" sozinha numa linha, ou "[TIPO] Título", também funcionam — mas
"## TIPO — Título" é a forma mais confiável.)

TIPOS ACEITOS (com ou sem acento, maiúsculo ou minúsculo)
-----------------------------------------------------------
QUESTÃO              Pergunta de múltipla escolha (A, B, C, D...)
FLASHCARD            Frente e verso; o aluno diz se lembrava
VERDADEIRO OU FALSO  Uma afirmação, certa ou errada
COMPLETE A LACUNA    Como a questão, com "___" no lugar da lacuna
DESAFIO              Mais difícil — com alternativas OU resposta livre (um
                     número ou uma palavra curta, sem alternativa nenhuma)
INSIGHT              Um fato curto e curioso, só para ler
REVISÃO              Como o flashcard, para relembrar algo já visto antes
CONCEITO             Uma explicação mais longa, com subtítulos com "### "
LISTA                Vários itens curtos ("- item"), com detalhe ao tocar
ORDENE               Colocar passos na ordem certa ("- passo")
RELACIONE            Ligar duas colunas ("Termo = Definição")
ENQUETE              Pergunta de opinião, sem resposta certa

CAMPOS (cada um numa linha própria, com dois-pontos)
-----------------------------------------------------------
**Resposta:**   a letra certa (QUESTÃO/COMPLETE/V-F/DESAFIO com alternativas)
                ou o texto certo (DESAFIO sem alternativas: um número ou uma
                expressão curta, nunca uma frase)
**Feedback:**   por que a certa é certa — e comente CADA errada citando a
                letra dela ("A alternativa A soma antes de multiplicar.")
Verso:          o verso do FLASHCARD/REVISÃO
Subtítulo:      uma linha de apoio abaixo do título
Tag:            o assunto — aparece pequeno, acima do texto
Dica:           uma pista opcional
Cor:            tema visual — cinza, roxo, verde, âmbar, rosa ou azul
Imagem:         (opcional, ainda simples) uma URL de imagem já hospedada em
                algum lugar — o Sapiens ainda não recebe upload de arquivo

ALTERNATIVAS (QUESTÃO, COMPLETE, DESAFIO com alternativas)
-----------------------------------------------------------
Uma por linha, começando com a letra:

A) texto da alternativa
B) texto da alternativa

TEXTOS CURTOS E LONGOS
-----------------------------------------------------------
O enunciado pode ter uma linha ou vários parágrafos — não há limite. Um
CONCEITO longo pode ter subtítulos ("### Nome da parte") no meio; cada um
vira uma seção separada na tela.

REGRAS QUE NÃO PODEM SER QUEBRADAS
-----------------------------------------------------------
1. Toda QUESTÃO/COMPLETE/VERDADEIRO-OU-FALSO precisa de "**Resposta:**".
   Sem isso, o card fica de fora (o resto do texto continua valendo).
2. DESAFIO sem alternativas precisa de uma resposta CURTA — um número ou até
   24 caracteres. Uma resposta em frase não dá para corrigir sozinha.
3. ENQUETE nunca tem "**Resposta:**" — é opinião, não tem certo ou errado.
4. NUNCA escreva preço, custo, Sparks ou qualquer valor em dinheiro.
5. A posição certa da alternativa não importa: o Sapiens embaralha sozinho.
6. Um card com erro de formato vira AVISO e fica de fora; os outros cards
   do mesmo texto vão ao ar normalmente — colar 40 cards nunca é tudo ou
   nada.`;

const MODELO = `## QUESTÃO — Proporcionalidade
Se 3 xícaras de farinha fazem 12 biscoitos, quantas xícaras fazem 20?
A) 4
B) 5
C) 6
D) 7
**Resposta:** B
**Feedback:** Cada biscoito pede 0,25 xícara; 20 × 0,25 = 5. A alternativa A divide direto por 5, sem achar a proporção por biscoito.

## FLASHCARD — Trabalho de uma força
Qual é a fórmula do trabalho de uma força constante?
Verso: W = F · d · cos(θ)

## VERDADEIRO OU FALSO
A velocidade média depende da trajetória percorrida, e não só do deslocamento.
**Resposta:** Verdadeiro
**Feedback:** A velocidade média usa a distância percorrida no denominador do tempo — o deslocamento sozinho dá a velocidade vetorial.

## COMPLETE A LACUNA
A fórmula de Bhaskara resolve equações do ___ grau.
A) primeiro
B) segundo
C) terceiro
**Resposta:** B
**Feedback:** Equações do segundo grau têm expoente máximo 2, que é justamente onde Bhaskara se aplica.

## DESAFIO
Quanto é 2 elevado a 5?
**Resposta:** 32
**Feedback:** 2×2×2×2×2 = 32.

## INSIGHT
O cérebro consome cerca de 20% de toda a energia do corpo, mesmo pesando só 2% do peso total.

## REVISÃO — Lei de Ohm
Você lembra da relação entre tensão, corrente e resistência?
Verso: V = R × i

## LISTA — Fatores de risco cardiovascular
- Sedentarismo: menos de 150 minutos de atividade por semana
- Tabagismo: mesmo em pequena quantidade
- Hipertensão não controlada

## ORDENE — Método científico
- Observação
- Formulação da hipótese
- Experimentação
- Conclusão

## RELACIONE — Capitais
Brasil = Brasília
França = Paris
Japão = Tóquio

## ENQUETE
Qual matéria você mais tem dificuldade agora?
A) Matemática
B) Redação
C) Química
`;

// ---------------------------------------------------------------------------
// A régua do lado do campo
// ---------------------------------------------------------------------------

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
    <aside className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4" data-testid="admin-feed-especificacao">
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
        O que este campo espera
      </div>
      <p className="mt-2 text-[13px] leading-relaxed text-zinc-600">
        Cole um texto <strong className="font-semibold text-zinc-800">de qualquer tamanho</strong>,
        com quantos cards quiser. Cada card começa com uma linha de tipo
        (<code className="font-mono-alt">## QUESTÃO — título</code>), e dentro dele o
        Sapiens reconhece <code className="font-mono-alt">**Resposta:**</code>,{" "}
        <code className="font-mono-alt">**Feedback:**</code>,{" "}
        <code className="font-mono-alt">Verso:</code> e as alternativas
        (<code className="font-mono-alt">A) ...</code>).
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" onClick={copiar}
          className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-900 px-4 py-2 text-xs font-semibold text-zinc-900"
          data-testid="admin-feed-copiar-espec">
          {copiado ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copiado ? "Copiado" : "Copiar a especificação"}
        </button>
        <button type="button" onClick={aoUsarModelo}
          className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-4 py-2 text-xs font-medium text-zinc-500"
          data-testid="admin-feed-modelo">
          Colar um exemplo pronto
        </button>
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-zinc-400">
        A especificação é o texto que você cola no gerador (DeepSeek, ChatGPT) antes de
        pedir o feed. O que ele devolver, cole aqui ao lado. O Sapiens nunca chama uma
        IA paga para ler esse texto — o parsing é determinístico, do lado do servidor.
      </p>

      <pre className="mt-3 max-h-[26rem] overflow-auto whitespace-pre-wrap rounded-xl border border-zinc-200 bg-white p-3 font-mono-alt text-[11px] leading-relaxed text-zinc-600"
        data-testid="admin-feed-espec-corpo">
        {ESPECIFICACAO}
      </pre>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// A prévia: o card como ele ficou depois de compilado — com o gabarito à
// mostra, porque é exatamente essa conferência que a prévia existe para
// permitir (mesma filosofia de `EstacaoCompilada` em AdminCursos.jsx).
// ---------------------------------------------------------------------------

function PreviaDeCard({ card }) {
  const tipo = card.content_type;
  const opcoes = card.answer_options || [];
  return (
    <div className="rounded-xl border border-zinc-200 p-3.5" data-testid={`admin-feed-previa-${card.content_id}`}>
      <div className="flex flex-wrap items-center gap-2 font-mono-alt text-[10px] uppercase tracking-[0.18em] text-zinc-400">
        <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-600">{card.rotulo || tipo}</span>
        <span>{card.background_theme}</span>
        {card.formato === "aberto" && <span className="text-zinc-400">· resposta livre</span>}
      </div>
      <p className="mt-1.5 text-sm font-medium text-zinc-900">{card.question_data?.prompt}</p>
      {card.question_data?.subtitle && (
        <p className="text-[12px] text-zinc-500">{card.question_data.subtitle}</p>
      )}

      {opcoes.length > 0 && (
        <ul className="mt-2 space-y-1">
          {opcoes.map((o) => (
            <li key={o.key}
              className={`flex gap-2 rounded-lg px-2 py-1 text-[13px] ${o.is_correct ? "bg-emerald-50 font-semibold text-emerald-900" : "text-zinc-600"}`}>
              <span className="font-mono-alt uppercase">{o.key})</span>
              <span className="min-w-0 flex-1">{o.label}</span>
              {o.is_correct && <Check className="h-3.5 w-3.5 shrink-0" />}
              {o.feedback && (
                <span className="hidden max-w-[45%] shrink-0 text-right text-[11px] italic text-zinc-400 md:block">{o.feedback}</span>
              )}
            </li>
          ))}
        </ul>
      )}

      {tipo === "desafio" && card.formato === "aberto" && (
        <p className="mt-2 font-mono-alt text-[11px] text-zinc-500">
          resposta esperada: <strong className="text-zinc-700">{card.metadata?.resposta_exibicao}</strong>
          {card.metadata?.numero && ` (tolerância ±${card.metadata.numero.tolerancia})`}
        </p>
      )}

      {(tipo === "flashcard" || tipo === "revisao") && (
        <p className="mt-2 rounded-lg bg-emerald-50 px-2 py-1.5 text-[13px] text-emerald-900">
          <strong className="font-semibold">Verso:</strong> {card.explanation_data?.text}
        </p>
      )}

      {tipo === "lista" && (
        <ul className="mt-2 space-y-1 text-[13px] text-zinc-600">
          {(card.metadata?.itens || []).map((it, i) => (
            <li key={i}>• {it.titulo}{it.detalhe ? ` — ${it.detalhe}` : ""}</li>
          ))}
        </ul>
      )}

      {tipo === "ordene" && (
        <ol className="mt-2 list-decimal list-inside space-y-0.5 text-[13px] text-zinc-600">
          {(card.metadata?.passos || []).map((p) => <li key={p.id}>{p.texto}</li>)}
        </ol>
      )}

      {tipo === "relacione" && (
        <ul className="mt-2 space-y-0.5 text-[13px] text-zinc-600">
          {(card.metadata?.pares || []).map((p) => <li key={p.id}>{p.esquerda} → {p.direita}</li>)}
        </ul>
      )}

      {card.explanation_data?.text && !["flashcard", "revisao"].includes(tipo) && (
        <p className="mt-2 border-t border-zinc-100 pt-2 text-[12px] text-zinc-500">
          <strong className="font-semibold text-zinc-700">Explicação:</strong> {card.explanation_data.text}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Colar texto → compilar → conferir → publicar
// ---------------------------------------------------------------------------

function PublicarPorTexto({ aoPublicar }) {
  const [texto, setTexto] = useState("");
  const [previa, setPrevia] = useState(null);
  const [ocupado, setOcupado] = useState("");

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
      const { data } = await api.post("/admin/feed/compilar", { texto });
      setPrevia(data);
      if (data.pode_publicar) {
        toast.success(`${data.cards.length} card(s) pronto(s) para publicar.`);
      } else if (!data.problemas?.length) {
        toast.error("Nenhum card válido nesse texto — veja os avisos abaixo.");
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
      const { data } = await api.post("/admin/feed/publicar", { texto });
      toast.success(`Publicado: ${data.novos} novo(s), ${data.atualizados} reafirmado(s).`);
      setTexto("");
      setPrevia(null);
      aoPublicar?.();
    } catch (e) {
      toast.error(problemasDoServidor(e));
    } finally {
      setOcupado("");
    }
  };

  return (
    <div className="card-sapiens rounded-2xl p-5">
      <h3 className="font-display text-lg font-bold tracking-tight text-zinc-950">
        Cole o feed escrito — o site monta os cards
      </h3>
      <p className="mt-1 text-[13px] leading-relaxed text-zinc-600">
        Pergunta, flashcard, verdadeiro ou falso, desafio, insight e mais — tudo num texto
        só. O servidor corta em cards, identifica o tipo de cada um, embaralha alternativas,
        reparte o feedback por distrator e valida. Fica no ar na hora, sem deploy.
      </p>

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <label className="block">
          <span className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
            O texto do feed
          </span>
          <textarea
            value={texto}
            onChange={(e) => { setTexto(e.target.value); setPrevia(null); }}
            rows={26}
            spellCheck={false}
            placeholder="Cole aqui o texto inteiro do feed (quantos cards forem, um atrás do outro)…"
            className="mt-1 h-full min-h-[24rem] w-full rounded-xl border border-zinc-200 px-3 py-2 font-mono-alt text-[12px] leading-relaxed outline-none focus:border-zinc-900"
            data-testid="admin-feed-texto"
          />
          <span className="mt-1 block text-[11px] text-zinc-400">
            {texto.trim()
              ? `${texto.trim().split(/\s+/).length.toLocaleString("pt-BR")} palavras coladas`
              : "Não há limite de tamanho: cole o feed inteiro, com quantos cards forem."}
          </span>
        </label>
        <Especificacao aoUsarModelo={() => { setTexto(MODELO); setPrevia(null); }} />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button onClick={compilar} disabled={!texto.trim() || Boolean(ocupado)}
          className="pill inline-flex items-center gap-2 rounded-full border border-zinc-900 px-5 py-2.5 text-sm font-semibold text-zinc-900 disabled:opacity-40"
          data-testid="admin-feed-compilar">
          {ocupado === "compilar" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
          Ver o que vai virar
        </button>
        <button onClick={publicar} disabled={!previa?.pode_publicar || Boolean(ocupado)}
          className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-bold disabled:opacity-40"
          data-testid="admin-feed-publicar">
          {ocupado === "publicar" ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
          Publicar no ar
        </button>
      </div>

      {previa?.problemas?.length > 0 && (
        <ul className="mt-4 space-y-1.5 rounded-2xl bg-rose-50 p-4" data-testid="admin-feed-problemas">
          {previa.problemas.map((p, i) => (
            <li key={i} className="flex gap-2 text-[13px] text-rose-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> {p}
            </li>
          ))}
        </ul>
      )}

      {previa?.avisos?.length > 0 && (
        <ul className="mt-4 space-y-1.5 rounded-2xl bg-amber-50 p-4" data-testid="admin-feed-avisos">
          {previa.avisos.map((a, i) => (
            <li key={i} className="text-[13px] text-amber-800">{a}</li>
          ))}
        </ul>
      )}

      {previa?.cards?.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-white/35">
            Prévia · {previa.cards.length} card(s)
          </div>
          {previa.cards.map((c) => <PreviaDeCard key={c.content_id} card={c} />)}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Composer manual — para um ajuste rápido, sem passar pelo texto inteiro.
// ---------------------------------------------------------------------------

const TIPOS_MANUAIS = [
  { value: "question", label: "Pergunta com alternativas" },
  { value: "verdadeiro_falso", label: "Verdadeiro ou Falso" },
  { value: "complete", label: "Complete a lacuna" },
  { value: "flashcard", label: "Flashcard" },
  { value: "revisao", label: "Revisão" },
  { value: "desafio", label: "Desafio (com alternativas)" },
  { value: "insight", label: "Insight" },
  { value: "explanation", label: "Conceito" },
];
const THEMES = ["slate", "violet", "emerald", "amber", "rose", "ocean"];

const EMPTY_DRAFT = {
  content_type: "question",
  sequence_order: 0,
  question_data: { prompt: "", subject_hint: "" },
  answer_options: [
    { key: "A", label: "", is_correct: false },
    { key: "B", label: "", is_correct: false },
    { key: "C", label: "", is_correct: false },
    { key: "D", label: "", is_correct: false },
  ],
  explanation_data: { text: "" },
  multimedia_assets: [],
  metadata: {},
  cognitive_mapping_reference: "",
  difficulty_reference: "",
  learning_objectives: [],
  background_theme: "slate",
  published: true,
};

const TIPOS_COM_ALTERNATIVAS = new Set(["question", "verdadeiro_falso", "complete", "desafio"]);

function ComposerManual({ onCriado }) {
  const [aberto, setAberto] = useState(false);
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [busy, setBusy] = useState(false);

  const updateOption = (idx, patch) => {
    setDraft((d) => ({
      ...d,
      answer_options: d.answer_options.map((o, i) => (i === idx ? { ...o, ...patch } : o)),
    }));
  };

  const criar = async () => {
    if (!draft.question_data.prompt.trim()) return toast.error("Adicione um prompt.");
    setBusy(true);
    try {
      await api.post("/admin/feed-items", draft);
      toast.success("Card criado.");
      setDraft(EMPTY_DRAFT);
      onCriado?.();
    } catch (e) {
      toast.error(errMsg(e, "Erro ao criar."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-6">
      <button onClick={() => setAberto((a) => !a)}
        className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-4 py-2 text-xs font-medium text-zinc-500"
        data-testid="admin-feed-avancado">
        {aberto ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        Avançado: criar 1 card à mão
      </button>

      {aberto && (
        <div className="mt-4 card-sapiens rounded-2xl p-6" data-testid="admin-feed-composer-manual">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <label className="text-xs">
              <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Tipo</div>
              <select value={draft.content_type}
                onChange={(e) => setDraft((d) => ({ ...d, content_type: e.target.value }))}
                className="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm bg-white outline-none focus:border-zinc-900"
                data-testid="feed-admin-type">
                {TIPOS_MANUAIS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </label>
            <label className="text-xs">
              <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Tema visual</div>
              <select value={draft.background_theme}
                onChange={(e) => setDraft((d) => ({ ...d, background_theme: e.target.value }))}
                className="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm bg-white outline-none focus:border-zinc-900"
                data-testid="feed-admin-theme">
                {THEMES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            <label className="text-xs">
              <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Ordem (0 = automática)</div>
              <input type="number" value={draft.sequence_order}
                onChange={(e) => setDraft((d) => ({ ...d, sequence_order: Number(e.target.value) }))}
                className="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900"
                data-testid="feed-admin-order" />
            </label>
          </div>

          <label className="block mt-4 text-xs">
            <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">Prompt principal</div>
            <textarea rows={2} value={draft.question_data.prompt}
              onChange={(e) => setDraft((d) => ({ ...d, question_data: { ...d.question_data, prompt: e.target.value } }))}
              className="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900"
              placeholder="Escreva o enunciado ou conceito..."
              data-testid="feed-admin-prompt" />
          </label>

          {TIPOS_COM_ALTERNATIVAS.has(draft.content_type) && (
            <div className="mt-4 space-y-2">
              <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 text-xs mb-1">Alternativas</div>
              {draft.answer_options.map((o, i) => (
                <div key={o.key} className="flex items-center gap-2" data-testid={`feed-admin-opt-${o.key}`}>
                  <div className="w-8 text-center text-xs font-mono-alt text-zinc-500">{o.key}</div>
                  <input value={o.label} onChange={(e) => updateOption(i, { label: e.target.value })}
                    className="flex-1 border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900"
                    placeholder={`Alternativa ${o.key}`} />
                  <label className="flex items-center gap-1 text-xs text-zinc-600">
                    <input type="radio" name="correct" checked={o.is_correct}
                      onChange={() => setDraft((d) => ({
                        ...d,
                        answer_options: d.answer_options.map((oo, ii) => ({ ...oo, is_correct: ii === i })),
                      }))}
                      data-testid={`feed-admin-opt-correct-${o.key}`} /> correta
                  </label>
                </div>
              ))}
            </div>
          )}

          <label className="block mt-4 text-xs">
            <div className="font-mono-alt uppercase tracking-[0.2em] text-zinc-500 mb-1">
              {TIPOS_COM_ALTERNATIVAS.has(draft.content_type) ? "Explicação (após responder)" : "Verso / resposta"}
            </div>
            <textarea rows={3} value={draft.explanation_data.text}
              onChange={(e) => setDraft((d) => ({ ...d, explanation_data: { ...d.explanation_data, text: e.target.value } }))}
              className="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900"
              data-testid="feed-admin-explanation" />
          </label>

          <button disabled={busy} onClick={criar}
            className="pill mt-6 inline-flex items-center gap-2 btn-sapiens disabled:opacity-60 text-white px-6 py-3 rounded-full text-sm font-medium"
            data-testid="feed-admin-create">
            <Plus className="w-4 h-4" /> {busy ? "Criando..." : "Criar card"}
          </button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

export default function AdminFeed() {
  const [items, setItems] = useState([]);

  const load = useCallback(() => api.get("/admin/feed-items").then(({ data }) => setItems(data)), []);
  useEffect(() => { load(); }, [load]);

  const togglePublish = async (it) => {
    await api.patch(`/admin/feed-items/${it.content_id}`, { published: !it.published });
    load();
  };
  const remove = async (it) => {
    if (!window.confirm("Excluir este card do feed?")) return;
    await api.delete(`/admin/feed-items/${it.content_id}`);
    toast.success("Card excluído.");
    load();
  };
  const patchOrder = async (it, newOrder) => {
    await api.patch(`/admin/feed-items/${it.content_id}`, { sequence_order: Number(newOrder) });
    load();
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-5xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="secao-olho">Admin · Feed</div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-white" data-testid="feed-admin-title">
          Gerenciar o feed
        </h1>
        <p className="mt-3 text-white/60 max-w-2xl">
          Cada card aparece como uma tela cheia no feed vertical do aluno — pergunta, flashcard,
          desafio, insight e outros tipos, um por vez, como um Reels de estudo. Cole o texto
          gerado fora do Sapiens e o servidor monta os cards sozinho, de forma determinística.
        </p>

        <div className="mt-8">
          <PublicarPorTexto aoPublicar={load} />
        </div>

        <ComposerManual onCriado={load} />

        {/* Lista */}
        <div className="mt-10">
          <div className="font-display font-bold text-xl tracking-tight text-zinc-950 mb-4">
            Cards no ar ({items.length})
          </div>
          <div className="space-y-2">
            {items.map((it) => (
              <div key={it.content_id} className="card-sapiens rounded-2xl p-4 flex items-center gap-4" data-testid={`feed-admin-row-${it.content_id}`}>
                <input type="number" defaultValue={it.sequence_order}
                  onBlur={(e) => { if (Number(e.target.value) !== it.sequence_order) patchOrder(it, e.target.value); }}
                  className="w-16 text-center border border-zinc-200 rounded-lg px-2 py-1 text-sm font-mono-alt"
                  data-testid={`feed-admin-order-${it.content_id}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-zinc-500">
                    {it.rotulo || it.content_type} · {it.background_theme}
                  </div>
                  <div className="mt-1 font-display font-semibold text-base text-zinc-900 truncate">
                    {it.question_data?.prompt || "(sem prompt)"}
                  </div>
                </div>
                <button onClick={() => togglePublish(it)}
                  className="p-2 rounded-full hover:bg-zinc-100" title={it.published ? "Publicado" : "Rascunho"}
                  data-testid={`feed-admin-toggle-${it.content_id}`}>
                  {it.published ? <Eye className="w-4 h-4 text-emerald-500" /> : <EyeOff className="w-4 h-4 text-zinc-400" />}
                </button>
                <button onClick={() => remove(it)}
                  className="p-2 rounded-full hover:bg-rose-50 text-rose-600"
                  data-testid={`feed-admin-delete-${it.content_id}`}>
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            {items.length === 0 && (
              <div className="text-sm text-white/40 py-6 text-center">
                Nenhum card ainda. Cole um texto acima para começar.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
