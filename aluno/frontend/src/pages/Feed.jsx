import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { ChevronUp, Check, X, RotateCw, ArrowLeft } from "lucide-react";

// Card visual themes — kept solid (dark palette) to avoid muddy gradients
const THEMES = {
  slate:   { bg: "#0b0f19", accent: "#818cf8", tag: "Introdução" },
  violet:  { bg: "#1e1b4b", accent: "#a78bfa", tag: "Prática" },
  emerald: { bg: "#022c22", accent: "#34d399", tag: "Conceito" },
  amber:   { bg: "#1c1917", accent: "#fbbf24", tag: "Revisão" },
  rose:    { bg: "#1f0a13", accent: "#fb7185", tag: "Desafio" },
  ocean:   { bg: "#082032", accent: "#38bdf8", tag: "Idioma" },
};

const PAGE_SIZE = 6;
const PRELOAD_THRESHOLD = 3;

function FeedCard({ item, index, onView, onAnswer, isActive }) {
  const theme = THEMES[item.background_theme] || THEMES.slate;
  const [selected, setSelected] = useState(null);
  const [revealed, setRevealed] = useState(false);
  const [flipped, setFlipped] = useState(false);
  const cardRef = useRef(null);
  const enteredAt = useRef(null);

  // Track visibility time
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

  const correctKey = useMemo(
    () => item.answer_options?.find(o => o.is_correct)?.key,
    [item.answer_options]
  );

  const handleSelect = (k) => {
    if (revealed) return;
    setSelected(k);
    setRevealed(true);
    const isCorrect = k === correctKey;
    onAnswer?.(item, k, isCorrect);
  };

  const renderQuestion = () => (
    <>
      <div className="text-white font-display text-3xl md:text-4xl font-bold tracking-tight leading-tight">
        {item.question_data?.prompt}
      </div>
      {item.question_data?.subject_hint && (
        <div className="mt-3 text-white/50 text-sm font-mono-alt uppercase tracking-[0.25em]">
          {item.question_data.subject_hint}
        </div>
      )}
      <div className="mt-8 space-y-2.5" data-testid={`feed-options-${item.content_id}`}>
        {item.answer_options?.map(opt => {
          const isChosen = selected === opt.key;
          const isCorrect = opt.key === correctKey;
          const showCorrect = revealed && isCorrect;
          const showWrong = revealed && isChosen && !isCorrect;
          return (
            <button
              key={opt.key}
              onClick={() => handleSelect(opt.key)}
              disabled={revealed}
              className={`pill w-full text-left flex items-center gap-3 px-5 py-4 rounded-2xl border transition-colors
                ${showCorrect ? "bg-emerald-500/20 border-emerald-400 text-white"
                  : showWrong ? "bg-rose-500/20 border-rose-400 text-white"
                  : "bg-white/5 border-white/10 hover:bg-white/10 text-white"}`}
              data-testid={`feed-option-${item.content_id}-${opt.key}`}
            >
              <span className="w-8 h-8 rounded-full flex items-center justify-center font-mono-alt text-xs bg-white/10">
                {opt.key}
              </span>
              <span className="flex-1 text-base">{opt.label}</span>
              {showCorrect && <Check className="w-5 h-5 text-emerald-400" />}
              {showWrong && <X className="w-5 h-5 text-rose-400" />}
            </button>
          );
        })}
      </div>
      {revealed && item.explanation_data?.text && (
        <div className="reveal mt-6 rounded-2xl bg-white/5 border border-white/10 p-5">
          <div className="text-xs font-mono-alt uppercase tracking-[0.25em]" style={{ color: theme.accent }}>Explicação</div>
          <div className="mt-2 text-white/90 text-sm leading-relaxed">{item.explanation_data.text}</div>
        </div>
      )}
    </>
  );

  const renderFlashcard = () => (
    <div className="flex flex-col justify-center h-full">
      <div className="text-white/50 text-xs font-mono-alt uppercase tracking-[0.35em]">Flashcard</div>
      <div className="mt-6 text-white font-display text-4xl md:text-5xl font-bold tracking-tight leading-tight">
        {item.question_data?.prompt}
      </div>
      {!flipped ? (
        <button
          onClick={() => { setFlipped(true); onAnswer?.(item, "flipped", null); }}
          className="pill mt-10 inline-flex self-start items-center gap-2 px-5 py-3 rounded-full text-sm font-medium border border-white/20 hover:bg-white/10 text-white"
          data-testid={`feed-flashcard-flip-${item.content_id}`}
        >
          <RotateCw className="w-4 h-4" /> Revelar resposta
        </button>
      ) : (
        <div className="reveal mt-10 rounded-2xl bg-white/5 border border-white/10 p-6">
          <div className="text-white text-xl leading-relaxed">{item.explanation_data?.text}</div>
          {item.explanation_data?.subtitle && (
            <div className="mt-3 text-white/60 text-sm">{item.explanation_data.subtitle}</div>
          )}
        </div>
      )}
    </div>
  );

  const renderExplanation = () => (
    <div className="flex flex-col justify-center h-full">
      <div className="text-white/50 text-xs font-mono-alt uppercase tracking-[0.35em]">Conceito</div>
      <div className="mt-6 text-white font-display text-4xl md:text-6xl font-bold tracking-tighter leading-[0.95]">
        {item.question_data?.prompt}
      </div>
      {item.question_data?.subtitle && (
        <div className="mt-4 text-white/70 text-lg">{item.question_data.subtitle}</div>
      )}
      {item.explanation_data?.text && (
        <div className="mt-8 text-white/85 text-base md:text-lg leading-relaxed max-w-md">
          {item.explanation_data.text}
        </div>
      )}
    </div>
  );

  const renderDiagram = () => (
    <div className="flex flex-col justify-center h-full">
      <div className="text-white/50 text-xs font-mono-alt uppercase tracking-[0.35em]">Diagrama</div>
      <div className="mt-4 text-white font-display text-3xl font-bold tracking-tight">
        {item.question_data?.prompt}
      </div>
      <div className="mt-6 aspect-video rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
        {item.multimedia_assets?.[0]?.url ? (
          <img src={item.multimedia_assets[0].url} alt="" className="max-h-full rounded-2xl" />
        ) : (
          <div className="text-white/80 font-mono-alt text-lg">
            {item.multimedia_assets?.[0]?.caption || "◇◇◇"}
          </div>
        )}
      </div>
      {item.explanation_data?.text && (
        <div className="mt-6 text-white/80 text-sm leading-relaxed">{item.explanation_data.text}</div>
      )}
    </div>
  );

  let content = null;
  if (item.content_type === "question") content = renderQuestion();
  else if (item.content_type === "flashcard") content = renderFlashcard();
  else if (item.content_type === "diagram") content = renderDiagram();
  else content = renderExplanation();

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
            {theme.tag}
          </span>
          <span className="text-[10px] font-mono-alt uppercase tracking-[0.3em] text-white/40">
            #{item.sequence_order}
          </span>
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

  const onAnswer = useCallback(async (item, response, isCorrect) => {
    api.post("/feed/interactions", {
      content_id: item.content_id,
      completed: true,
      user_response: { selected: response },
      is_correct: isCorrect,
      event: { event: "answered", response },
    }).catch(() => {});
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
            index={i}
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
