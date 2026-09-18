import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import TextoRico from "../components/curso/TextoRico";
import {
  ChevronUp, Check, X, RotateCw, ArrowLeft, ThumbsUp, ThumbsDown,
  GripVertical, Undo2, Lightbulb,
} from "lucide-react";

// Card visual themes — kept solid (dark palette) to avoid muddy gradients.
// A TARJA (o nome do tipo) não mora mais aqui: o servidor já manda
// `item.rotulo` (ver `feed_conteudo.para_a_tela`), então o mesmo nome que
// aparece no painel do admin aparece aqui, sem duplicar o vocabulário dos
// tipos em dois lugares que podem divergir.
const THEMES = {
  slate:   { bg: "#0b0f19", accent: "#818cf8" },
  violet:  { bg: "#1e1b4b", accent: "#a78bfa" },
  emerald: { bg: "#022c22", accent: "#34d399" },
  amber:   { bg: "#1c1917", accent: "#fbbf24" },
  rose:    { bg: "#1f0a13", accent: "#fb7185" },
  ocean:   { bg: "#082032", accent: "#38bdf8" },
};

const PAGE_SIZE = 6;
const PRELOAD_THRESHOLD = 3;

/** Os blocos de leitura do servidor (`{tipo: "texto"|"subtitulo"|"topicos"}`)
 *  viram uma string markdown, e quem desenha essa string é `TextoRico` — o
 *  MESMO renderizador inline (negrito, itálico, código, fórmula) que os
 *  cursos já usam. Um segundo renderizador de markdown aqui divergiria do
 *  primeiro na primeira fórmula com asterisco. */
function corpoParaMarkdown(corpo) {
  return (corpo || [])
    .map((b) => {
      if (b.tipo === "subtitulo") return `## ${b.texto}`;
      if (b.tipo === "topicos") return (b.itens || []).map((i) => `- ${i}`).join("\n");
      return b.texto || "";
    })
    .filter(Boolean)
    .join("\n\n");
}

function PillButton({ children, className = "", ...props }) {
  return (
    <button
      className={`pill inline-flex items-center gap-2 px-5 py-3 rounded-full text-sm font-medium border border-white/20 hover:bg-white/10 text-white disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Um tipo por renderizador. Cada um recebe o card, o estado de "já
// respondeu" e `responder(userResponse)` — que envia ao servidor, corrige e
// devolve a revelação (gabarito, comentário, explicação: tudo que
// `feed_conteudo.para_a_tela` escondeu até agora).
// ---------------------------------------------------------------------------

function CardEscolha({ item, theme, responder }) {
  const [selecionada, setSelecionada] = useState(null);
  const [revelado, setRevelado] = useState(false);
  const [revelacao, setRevelacao] = useState(null);

  const escolher = async (key) => {
    if (revelado) return;
    setSelecionada(key);
    setRevelado(true);
    const r = await responder({ selected: key });
    setRevelacao(r);
  };

  const emLacuna = item.content_type === "complete";
  const prompt = emLacuna
    ? item.question_data?.prompt?.split(/(___)/g)
    : null;

  return (
    <>
      <div className="text-white font-display text-3xl md:text-4xl font-bold tracking-tight leading-tight">
        {emLacuna
          ? prompt.map((parte, i) => parte === "___"
              ? <span key={i} className="inline-block mx-1 px-2 rounded-lg bg-white/10 font-mono-alt" style={{ color: theme.accent }}>____</span>
              : <span key={i}>{parte}</span>)
          : item.question_data?.prompt}
      </div>
      {item.question_data?.subject_hint && (
        <div className="mt-3 text-white/50 text-sm font-mono-alt uppercase tracking-[0.25em]">
          {item.question_data.subject_hint}
        </div>
      )}
      <div className="mt-8 space-y-2.5" data-testid={`feed-options-${item.content_id}`}>
        {item.answer_options?.map((opt) => {
          const isChosen = selecionada === opt.key;
          const isCorrect = revelado && opt.key === revelacao?.correct_key;
          const showWrong = revelado && isChosen && !isCorrect;
          return (
            <button
              key={opt.key}
              onClick={() => escolher(opt.key)}
              disabled={revelado}
              className={`pill w-full text-left flex items-center gap-3 px-5 py-4 rounded-2xl border transition-colors
                ${isCorrect ? "bg-emerald-500/20 border-emerald-400 text-white"
                  : showWrong ? "bg-rose-500/20 border-rose-400 text-white"
                  : "bg-white/5 border-white/10 hover:bg-white/10 text-white"}`}
              data-testid={`feed-option-${item.content_id}-${opt.key}`}
            >
              <span className="w-8 h-8 rounded-full flex items-center justify-center font-mono-alt text-xs bg-white/10 shrink-0">
                {opt.key.toUpperCase()}
              </span>
              <span className="flex-1 text-base">{opt.label}</span>
              {isCorrect && <Check className="w-5 h-5 text-emerald-400 shrink-0" />}
              {showWrong && <X className="w-5 h-5 text-rose-400 shrink-0" />}
            </button>
          );
        })}
      </div>
      {revelado && isChosenWrongFeedback(revelacao) && (
        <div className="reveal mt-4 rounded-2xl bg-rose-500/10 border border-rose-400/30 p-4 text-rose-100 text-sm">
          {revelacao.feedback}
        </div>
      )}
      {revelado && revelacao?.explicacao && (
        <div className="reveal mt-3 rounded-2xl bg-white/5 border border-white/10 p-5">
          <div className="text-xs font-mono-alt uppercase tracking-[0.25em]" style={{ color: theme.accent }}>Explicação</div>
          <div className="mt-2 text-white/90 text-sm leading-relaxed">{revelacao.explicacao}</div>
        </div>
      )}
    </>
  );
}
function isChosenWrongFeedback(revelacao) {
  return revelacao?.feedback && revelacao.feedback.trim().length > 0;
}

function CardDesafioAberto({ item, theme, responder }) {
  const [valor, setValor] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [revelacao, setRevelacao] = useState(null);
  const [acertou, setAcertou] = useState(null);

  const enviar = async () => {
    if (!valor.trim() || enviado) return;
    setEnviado(true);
    const r = await responder({ texto: valor.trim() });
    setAcertou(r?.is_correct ?? null);
    setRevelacao(r);
  };

  return (
    <>
      <div className="inline-flex items-center gap-1.5 text-[10px] font-mono-alt uppercase tracking-[0.3em] px-2.5 py-1 rounded-full border border-white/15" style={{ color: theme.accent }}>
        Resposta livre
      </div>
      <div className="mt-4 text-white font-display text-3xl md:text-4xl font-bold tracking-tight leading-tight">
        {item.question_data?.prompt}
      </div>
      <div className="mt-8 flex items-center gap-2">
        <input
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && enviar()}
          disabled={enviado}
          placeholder="Digite sua resposta..."
          className="flex-1 bg-white/5 border border-white/15 rounded-2xl px-4 py-3.5 text-white text-lg outline-none focus:border-white/40 disabled:opacity-70"
          data-testid={`feed-desafio-input-${item.content_id}`}
        />
        {!enviado && (
          <PillButton onClick={enviar} className="btn-sapiens border-0 shrink-0" data-testid={`feed-desafio-enviar-${item.content_id}`}>
            Responder
          </PillButton>
        )}
      </div>
      {enviado && (
        <div className={`reveal mt-6 rounded-2xl border p-5 ${acertou ? "bg-emerald-500/10 border-emerald-400/30" : "bg-rose-500/10 border-rose-400/30"}`}>
          <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: acertou ? "#34d399" : "#fb7185" }}>
            {acertou ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
            {acertou ? "Você acertou" : `A resposta era ${revelacao?.resposta_certa ?? "—"}`}
          </div>
          {revelacao?.explicacao && (
            <div className="mt-2 text-white/85 text-sm leading-relaxed">{revelacao.explicacao}</div>
          )}
        </div>
      )}
    </>
  );
}

function CardMemoria({ item, theme, responder }) {
  const [flipped, setFlipped] = useState(false);
  const [avaliado, setAvaliado] = useState(null);
  const rotulo = item.rotulo || "Flashcard";

  const avaliar = async (lembrou) => {
    if (avaliado !== null) return;
    setAvaliado(lembrou);
    await responder({ lembrou });
  };

  return (
    <div className="flex flex-col justify-center h-full">
      <div className="text-white/50 text-xs font-mono-alt uppercase tracking-[0.35em]">{rotulo}</div>
      <div className="mt-6 text-white font-display text-4xl md:text-5xl font-bold tracking-tight leading-tight">
        {item.question_data?.prompt}
      </div>
      {!flipped ? (
        <PillButton onClick={() => setFlipped(true)} className="mt-10 self-start" data-testid={`feed-flashcard-flip-${item.content_id}`}>
          <RotateCw className="w-4 h-4" /> Revelar resposta
        </PillButton>
      ) : (
        <div className="reveal mt-10">
          <div className="rounded-2xl bg-white/5 border border-white/10 p-6">
            <div className="text-white text-xl leading-relaxed">{item.explanation_data?.text}</div>
            {item.explanation_data?.subtitle && (
              <div className="mt-3 text-white/60 text-sm">{item.explanation_data.subtitle}</div>
            )}
          </div>
          <div className="mt-4 flex items-center gap-3">
            <span className="text-white/50 text-xs font-mono-alt uppercase tracking-[0.2em]">Você lembrava?</span>
            <button
              onClick={() => avaliar(true)}
              disabled={avaliado !== null}
              className={`pill w-11 h-11 rounded-full flex items-center justify-center border transition-colors
                ${avaliado === true ? "bg-emerald-500/25 border-emerald-400 text-emerald-300" : "border-white/20 text-white/70 hover:bg-white/10"}`}
              data-testid={`feed-lembrou-sim-${item.content_id}`}
            >
              <ThumbsUp className="w-4 h-4" />
            </button>
            <button
              onClick={() => avaliar(false)}
              disabled={avaliado !== null}
              className={`pill w-11 h-11 rounded-full flex items-center justify-center border transition-colors
                ${avaliado === false ? "bg-rose-500/25 border-rose-400 text-rose-300" : "border-white/20 text-white/70 hover:bg-white/10"}`}
              data-testid={`feed-lembrou-nao-${item.content_id}`}
            >
              <ThumbsDown className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function CardLeitura({ item }) {
  return (
    <div className="flex flex-col justify-center h-full">
      <div className="text-white/50 text-xs font-mono-alt uppercase tracking-[0.35em]">{item.rotulo}</div>
      <div className="mt-6 text-white font-display text-4xl md:text-6xl font-bold tracking-tighter leading-[0.95]">
        {item.question_data?.prompt}
      </div>
      {item.question_data?.subtitle && (
        <div className="mt-4 text-white/70 text-lg">{item.question_data.subtitle}</div>
      )}
      {(item.question_data?.corpo?.length > 0 || item.explanation_data?.text) && (
        <div className="mt-8 text-white/85 text-base md:text-lg max-w-md">
          {item.question_data?.corpo?.length > 0
            ? <TextoRico markdown={corpoParaMarkdown(item.question_data.corpo)} />
            : <p className="leading-relaxed">{item.explanation_data.text}</p>}
        </div>
      )}
    </div>
  );
}

function CardLista({ item }) {
  const itens = item.metadata?.itens || [];
  const [abertos, setAbertos] = useState(() => new Set());
  const alternar = (i) => setAbertos((s) => {
    const novo = new Set(s);
    novo.has(i) ? novo.delete(i) : novo.add(i);
    return novo;
  });
  return (
    <div className="flex flex-col justify-center h-full">
      <div className="text-white/50 text-xs font-mono-alt uppercase tracking-[0.35em]">{item.rotulo}</div>
      <div className="mt-4 text-white font-display text-3xl font-bold tracking-tight">
        {item.question_data?.prompt}
      </div>
      <div className="mt-6 space-y-2">
        {itens.map((it, i) => (
          <button
            key={i}
            onClick={() => it.detalhe && alternar(i)}
            className="pill w-full text-left rounded-2xl bg-white/5 border border-white/10 px-4 py-3.5 hover:bg-white/10"
            data-testid={`feed-lista-item-${item.content_id}-${i}`}
          >
            <div className="flex items-center gap-3">
              <span className="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center font-mono-alt text-xs text-white/70 shrink-0">
                {i + 1}
              </span>
              <span className="flex-1 text-white font-medium">{it.titulo}</span>
            </div>
            {it.detalhe && abertos.has(i) && (
              <div className="reveal mt-2 pl-10 text-white/70 text-sm leading-relaxed">{it.detalhe}</div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function CardOrdene({ item, theme, responder }) {
  const passos = item.metadata?.passos || [];
  const [restantes, setRestantes] = useState(passos);
  const [ordemMontada, setOrdemMontada] = useState([]);
  const [enviado, setEnviado] = useState(false);
  const [revelacao, setRevelacao] = useState(null);
  const [acertou, setAcertou] = useState(null);

  const tocar = (passo) => {
    if (enviado) return;
    setRestantes((r) => r.filter((p) => p.id !== passo.id));
    setOrdemMontada((o) => [...o, passo]);
  };
  const desfazer = () => {
    if (enviado || !ordemMontada.length) return;
    const ultimo = ordemMontada[ordemMontada.length - 1];
    setOrdemMontada((o) => o.slice(0, -1));
    setRestantes((r) => [...r, ultimo]);
  };
  const confirmar = async () => {
    if (restantes.length || enviado) return;
    setEnviado(true);
    const r = await responder({ ordem: ordemMontada.map((p) => p.id) });
    setAcertou(r?.is_correct ?? null);
    setRevelacao(r);
  };

  return (
    <>
      <div className="text-white font-display text-3xl font-bold tracking-tight leading-tight">
        {item.question_data?.prompt}
      </div>
      <div className="mt-2 text-white/50 text-xs font-mono-alt uppercase tracking-[0.25em]">
        Toque na ordem certa
      </div>

      <div className="mt-6 min-h-[3.5rem] rounded-2xl border border-dashed border-white/20 p-2 flex flex-wrap gap-2">
        {ordemMontada.map((p, i) => (
          <span key={p.id} className="pill inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/10 text-white text-sm">
            <span className="font-mono-alt text-white/50">{i + 1}.</span> {p.texto}
          </span>
        ))}
        {!ordemMontada.length && <span className="text-white/30 text-sm px-2 py-2">Sua ordem aparece aqui</span>}
      </div>

      {!enviado && (
        <div className="mt-4 flex flex-wrap gap-2">
          {restantes.map((p) => (
            <button key={p.id} onClick={() => tocar(p)}
              className="pill inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-white/5 border border-white/15 hover:bg-white/10 text-white text-sm"
              data-testid={`feed-ordene-passo-${item.content_id}-${p.id}`}>
              <GripVertical className="w-3.5 h-3.5 text-white/40" /> {p.texto}
            </button>
          ))}
        </div>
      )}

      {!enviado && (
        <div className="mt-6 flex items-center gap-2">
          <button onClick={desfazer} disabled={!ordemMontada.length}
            className="pill p-3 rounded-full border border-white/15 text-white/70 hover:bg-white/10 disabled:opacity-30">
            <Undo2 className="w-4 h-4" />
          </button>
          <PillButton onClick={confirmar} disabled={restantes.length > 0} className="btn-sapiens border-0"
            data-testid={`feed-ordene-confirmar-${item.content_id}`}>
            Confirmar ordem
          </PillButton>
        </div>
      )}

      {enviado && (
        <div className={`reveal mt-6 rounded-2xl border p-5 ${acertou ? "bg-emerald-500/10 border-emerald-400/30" : "bg-rose-500/10 border-rose-400/30"}`}>
          <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: acertou ? "#34d399" : "#fb7185" }}>
            {acertou ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />} {acertou ? "Ordem certa!" : "Quase — a ordem certa era:"}
          </div>
          {!acertou && (
            <ol className="mt-2 space-y-1 text-white/85 text-sm list-decimal list-inside">
              {(revelacao?.passos_certos || []).map((p) => <li key={p.id}>{p.texto}</li>)}
            </ol>
          )}
          {revelacao?.explicacao && <div className="mt-2 text-white/70 text-sm leading-relaxed">{revelacao.explicacao}</div>}
        </div>
      )}
    </>
  );
}

function CardRelacione({ item, theme, responder }) {
  const esquerda = item.metadata?.esquerda || [];
  const direita = item.metadata?.direita || [];
  const [pares, setPares] = useState({});          // { esquerdaId: direitaId }
  const [selecionada, setSelecionada] = useState(null);
  const [enviado, setEnviado] = useState(false);
  const [revelacao, setRevelacao] = useState(null);
  const [acertou, setAcertou] = useState(null);

  const direitaUsada = new Set(Object.values(pares));
  const cores = ["#34d399", "#a78bfa", "#fbbf24", "#38bdf8", "#fb7185", "#f472b6"];
  const corDe = (id) => {
    const ids = Object.keys(pares);
    const i = ids.indexOf(id);
    return i >= 0 ? cores[i % cores.length] : theme.accent;
  };

  const tocarEsquerda = (id) => {
    if (enviado || pares[id]) return;
    setSelecionada(id);
  };
  const tocarDireita = (id) => {
    if (enviado || !selecionada || direitaUsada.has(id)) return;
    setPares((p) => ({ ...p, [selecionada]: id }));
    setSelecionada(null);
  };
  const confirmar = async () => {
    if (Object.keys(pares).length !== esquerda.length || enviado) return;
    setEnviado(true);
    const r = await responder({ pares });
    setAcertou(r?.is_correct ?? null);
    setRevelacao(r);
  };

  return (
    <>
      <div className="text-white font-display text-3xl font-bold tracking-tight leading-tight">
        {item.question_data?.prompt}
      </div>
      <div className="mt-2 text-white/50 text-xs font-mono-alt uppercase tracking-[0.25em]">
        Toque um de cada lado para ligar
      </div>
      <div className="mt-6 grid grid-cols-2 gap-3">
        <div className="space-y-2">
          {esquerda.map((e) => (
            <button key={e.id} onClick={() => tocarEsquerda(e.id)} disabled={enviado || !!pares[e.id]}
              className="pill w-full text-left px-3.5 py-3 rounded-xl border text-sm text-white transition-colors"
              style={{
                borderColor: pares[e.id] ? corDe(e.id) : selecionada === e.id ? theme.accent : "rgba(255,255,255,0.15)",
                background: pares[e.id] ? `${corDe(e.id)}22` : selecionada === e.id ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,0.05)",
              }}
              data-testid={`feed-relacione-esq-${item.content_id}-${e.id}`}>
              {e.texto}
            </button>
          ))}
        </div>
        <div className="space-y-2">
          {direita.map((d) => (
            <button key={d.id} onClick={() => tocarDireita(d.id)} disabled={enviado || direitaUsada.has(d.id)}
              className="pill w-full text-left px-3.5 py-3 rounded-xl border text-sm text-white transition-colors disabled:opacity-60"
              style={{
                borderColor: direitaUsada.has(d.id) ? corDe(Object.keys(pares).find((k) => pares[k] === d.id)) : "rgba(255,255,255,0.15)",
                background: direitaUsada.has(d.id) ? `${corDe(Object.keys(pares).find((k) => pares[k] === d.id))}22` : "rgba(255,255,255,0.05)",
              }}
              data-testid={`feed-relacione-dir-${item.content_id}-${d.id}`}>
              {d.texto}
            </button>
          ))}
        </div>
      </div>

      {!enviado && (
        <PillButton onClick={confirmar} disabled={Object.keys(pares).length !== esquerda.length}
          className="btn-sapiens border-0 mt-6" data-testid={`feed-relacione-confirmar-${item.content_id}`}>
          Confirmar
        </PillButton>
      )}

      {enviado && (
        <div className={`reveal mt-6 rounded-2xl border p-5 ${acertou ? "bg-emerald-500/10 border-emerald-400/30" : "bg-rose-500/10 border-rose-400/30"}`}>
          <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: acertou ? "#34d399" : "#fb7185" }}>
            {acertou ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />} {acertou ? "Tudo certo!" : "Alguns pares não bateram."}
          </div>
          {revelacao?.explicacao && <div className="mt-2 text-white/70 text-sm leading-relaxed">{revelacao.explicacao}</div>}
        </div>
      )}
    </>
  );
}

function CardEnquete({ item, theme, responder }) {
  const [votada, setVotada] = useState(null);
  const [revelacao, setRevelacao] = useState(null);

  const votar = async (key) => {
    if (votada) return;
    setVotada(key);
    const r = await responder({ selected: key });
    setRevelacao(r);
  };

  return (
    <>
      <div className="inline-flex items-center gap-1.5 text-[10px] font-mono-alt uppercase tracking-[0.3em] px-2.5 py-1 rounded-full border border-white/15" style={{ color: theme.accent }}>
        Sem resposta certa — é opinião
      </div>
      <div className="mt-4 text-white font-display text-3xl md:text-4xl font-bold tracking-tight leading-tight">
        {item.question_data?.prompt}
      </div>
      <div className="mt-8 space-y-2.5">
        {item.answer_options?.map((opt) => (
          <button key={opt.key} onClick={() => votar(opt.key)} disabled={!!votada}
            className={`pill w-full text-left flex items-center gap-3 px-5 py-4 rounded-2xl border transition-colors
              ${votada === opt.key ? "bg-white/15 border-white/40 text-white" : "bg-white/5 border-white/10 hover:bg-white/10 text-white"}`}
            data-testid={`feed-enquete-opcao-${item.content_id}-${opt.key}`}>
            <span className="w-8 h-8 rounded-full flex items-center justify-center font-mono-alt text-xs bg-white/10 shrink-0">
              {opt.key.toUpperCase()}
            </span>
            <span className="flex-1 text-base">{opt.label}</span>
            {votada === opt.key && <Check className="w-5 h-5 shrink-0" style={{ color: theme.accent }} />}
          </button>
        ))}
      </div>
      {votada && revelacao?.fecho && (
        <div className="reveal mt-4 rounded-2xl bg-white/5 border border-white/10 p-5 text-white/85 text-sm leading-relaxed">
          {revelacao.fecho}
        </div>
      )}
    </>
  );
}

function FeedCard({ item, onView, onAnswer, isActive }) {
  const theme = THEMES[item.background_theme] || THEMES.slate;
  const cardRef = useRef(null);
  const enteredAt = useRef(null);

  useEffect(() => {
    if (isActive) {
      enteredAt.current = performance.now();
      onView?.(item, "enter");
      return () => {
        if (enteredAt.current) {
          const spent = Math.round(performance.now() - enteredAt.current);
          onView?.(item, "leave", spent);
        }
      };
    }
  }, [isActive, item, onView]);

  const responder = useCallback((userResponse) => onAnswer(item, userResponse), [item, onAnswer]);

  let content;
  if (item.content_type === "question" || item.content_type === "complete"
      || (item.content_type === "desafio" && item.formato !== "aberto")
      || item.content_type === "verdadeiro_falso") {
    content = <CardEscolha item={item} theme={theme} responder={responder} />;
  } else if (item.content_type === "desafio") {
    content = <CardDesafioAberto item={item} theme={theme} responder={responder} />;
  } else if (item.content_type === "flashcard" || item.content_type === "revisao") {
    content = <CardMemoria item={item} theme={theme} responder={responder} />;
  } else if (item.content_type === "lista") {
    content = <CardLista item={item} />;
  } else if (item.content_type === "ordene") {
    content = <CardOrdene item={item} theme={theme} responder={responder} />;
  } else if (item.content_type === "relacione") {
    content = <CardRelacione item={item} theme={theme} responder={responder} />;
  } else if (item.content_type === "enquete") {
    content = <CardEnquete item={item} theme={theme} responder={responder} />;
  } else if (item.content_type === "diagram") {
    content = (
      <div className="flex flex-col justify-center h-full">
        <div className="text-white/50 text-xs font-mono-alt uppercase tracking-[0.35em]">{item.rotulo}</div>
        <div className="mt-4 text-white font-display text-3xl font-bold tracking-tight">{item.question_data?.prompt}</div>
        <div className="mt-6 aspect-video rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
          {item.multimedia_assets?.[0]?.url
            ? <img src={item.multimedia_assets[0].url} alt="" className="max-h-full rounded-2xl" />
            : <div className="text-white/80 font-mono-alt text-lg">{item.multimedia_assets?.[0]?.caption || "◇◇◇"}</div>}
        </div>
        {item.explanation_data?.text && <div className="mt-6 text-white/80 text-sm leading-relaxed">{item.explanation_data.text}</div>}
      </div>
    );
  } else {
    content = <CardLeitura item={item} />;
  }

  return (
    <section
      ref={cardRef}
      className="feed-card snap-start relative w-full flex-shrink-0"
      style={{ height: "100dvh", background: theme.bg }}
      data-testid={`feed-card-${item.content_id}`}
    >
      <div className="absolute inset-0 opacity-[0.06] pointer-events-none"
           style={{ backgroundImage: "radial-gradient(circle at 1px 1px, #fff 1px, transparent 0)", backgroundSize: "6px 6px" }} />

      <div className="relative h-full max-w-xl mx-auto px-6 md:px-8 pt-14 pb-24 flex flex-col">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono-alt uppercase tracking-[0.3em] px-2.5 py-1 rounded-full border border-white/15" style={{ color: theme.accent }}>
            {item.rotulo || item.content_type}
          </span>
          <span className="text-[10px] font-mono-alt uppercase tracking-[0.3em] text-white/40">
            #{item.sequence_order}
          </span>
          {item.metadata?.tem_dica && (
            <span className="ml-auto inline-flex items-center gap-1 text-[10px] font-mono-alt uppercase tracking-[0.2em] text-white/40">
              <Lightbulb className="w-3 h-3" /> dica
            </span>
          )}
        </div>
        <div className="mt-6 flex-1 overflow-auto no-scrollbar">
          {content}
        </div>
      </div>

      {/* Swipe hint */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 text-white/40 pointer-events-none">
        <ChevronUp className="w-4 h-4 animate-bounce" />
        <span className="text-[10px] font-mono-alt uppercase tracking-[0.3em]">Deslize</span>
      </div>
    </section>
  );
}

export default function Feed() {
  const [items, setItems] = useState([]);
  const [cursor, setCursor] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const containerRef = useRef(null);
  const sentinelRef = useRef(null);
  const nav = useNavigate();

  // Load next page
  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    setLoading(true);
    try {
      const { data } = await api.get("/feed", { params: { cursor, limit: PAGE_SIZE } });
      setItems(prev => {
        const seen = new Set(prev.map(p => p.content_id));
        return [...prev, ...data.items.filter(i => !seen.has(i.content_id))];
      });
      setCursor(data.next_cursor);
      setHasMore(data.has_more);
    } finally { setLoading(false); }
  }, [cursor, hasMore, loading]);

  // Initial load + restore progress
  useEffect(() => {
    (async () => {
      let restoreCursor = 0;
      let restoreContentId = null;
      try {
        const { data } = await api.get("/feed/progress");
        restoreCursor = Math.max(0, (data.last_position || 1) - 1);
        restoreContentId = data.last_content_id || null;
      } catch {}
      setLoading(true);
      try {
        const { data } = await api.get("/feed", { params: { cursor: 0, limit: PAGE_SIZE + Math.max(0, restoreCursor) } });
        setItems(data.items);
        setCursor(data.next_cursor);
        setHasMore(data.has_more);
        // Scroll to last seen item (mount effect below handles it)
        setTimeout(() => {
          if (!containerRef.current) return;
          const target = restoreContentId
            ? containerRef.current.querySelector(`[data-testid="feed-card-${restoreContentId}"]`)
            : null;
          if (target) target.scrollIntoView({ behavior: "instant", block: "start" });
        }, 50);
      } finally { setLoading(false); }
    })();
  }, []);

  // Track active card via IntersectionObserver
  useEffect(() => {
    if (!containerRef.current) return;
    const cards = containerRef.current.querySelectorAll(".feed-card");
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting && e.intersectionRatio > 0.6) {
          const idx = Array.from(cards).indexOf(e.target);
          if (idx >= 0) {
            setActiveIdx(idx);
            const item = items[idx];
            if (item) {
              // Save progress
              api.post("/feed/progress", { last_position: item.sequence_order, last_content_id: item.content_id })
                .catch(() => {});
            }
          }
        }
      });
    }, { root: containerRef.current, threshold: [0.6] });
    cards.forEach(c => io.observe(c));
    return () => io.disconnect();
  }, [items]);

  // Preload trigger (sentinel near end)
  useEffect(() => {
    if (!sentinelRef.current || !containerRef.current) return;
    const io = new IntersectionObserver((entries) => {
      if (entries.some(e => e.isIntersecting)) loadMore();
    }, { root: containerRef.current, threshold: 0.1 });
    io.observe(sentinelRef.current);
    return () => io.disconnect();
  }, [loadMore, items.length]);

  // Also trigger loadMore proactively when near the end
  useEffect(() => {
    if (items.length && activeIdx >= items.length - PRELOAD_THRESHOLD && hasMore) {
      loadMore();
    }
  }, [activeIdx, items.length, hasMore, loadMore]);

  const onView = useCallback(async (item, phase, spent) => {
    if (phase === "leave" && spent > 250) {
      api.post("/feed/interactions", {
        content_id: item.content_id,
        time_spent_ms: spent,
        event: { event: "view", ms: spent },
      }).catch(() => {});
    }
  }, []);

  // `userResponse` já chega no formato que `feed_conteudo.corrigir` espera
  // para o tipo do card ({selected} | {texto} | {ordem} | {pares} |
  // {lembrou}) — cada `Card*` monta o seu. Esta função só entrega ao
  // servidor e devolve a revelação (gabarito, comentário, explicação),
  // que ANTES da resposta nunca esteve no navegador.
  const onAnswer = useCallback(async (item, userResponse) => {
    try {
      const { data } = await api.post("/feed/interactions", {
        content_id: item.content_id,
        completed: true,
        user_response: userResponse,
        event: { event: "answered", response: userResponse },
      });
      return data;
    } catch {
      return null;
    }
  }, []);

  return (
    <div className="fixed inset-0 bg-black" data-testid="feed-root">
      {/* Header overlay */}
      <div className="absolute top-0 inset-x-0 z-20 flex items-center justify-between px-5 pt-4">
        <button onClick={() => nav("/dashboard")}
          className="pill inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur text-white text-xs font-medium hover:bg-white/20"
          data-testid="feed-back">
          <ArrowLeft className="w-4 h-4" /> Voltar
        </button>
        <div className="font-display text-white text-lg font-extrabold tracking-tighter">
          Sapiens<span className="text-emerald-400">.</span>
        </div>
        <div className="text-white/60 text-xs font-mono-alt" data-testid="feed-position">
          {items.length ? `${activeIdx + 1} / ${items.length}${hasMore ? "+" : ""}` : "—"}
        </div>
      </div>

      {/* Scroll container */}
      <div
        ref={containerRef}
        className="h-full overflow-y-auto snap-y snap-mandatory no-scrollbar"
        style={{ scrollBehavior: "smooth" }}
      >
        {items.map((it, i) => (
          <FeedCard
            key={it.content_id}
            item={it}
            isActive={i === activeIdx}
            onView={onView}
            onAnswer={onAnswer}
          />
        ))}
        <div ref={sentinelRef} className="h-32 flex items-center justify-center text-white/40 text-xs" data-testid="feed-sentinel">
          {loading ? "Carregando..." : hasMore ? "Preparando próximos..." : "Você chegou ao fim."}
        </div>
      </div>
    </div>
  );
}
