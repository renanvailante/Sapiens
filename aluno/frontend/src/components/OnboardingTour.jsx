import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import BrandMark from "./BrandMark";
import { ArrowRight, X } from "lucide-react";

// Tour guiado do primeiro login: uma sequência de balões que aponta pras
// peças reais da UI (via `data-tour="..."` nos elementos-alvo, espalhados
// por Dashboard.jsx e Nav.jsx). Nunca bloqueia a página por baixo — é
// dispensável a qualquer momento, e não repete depois que `flags.onboarded`
// vira `true` no perfil do aluno (Firestore).
const STEPS = [
  { target: null, title: "Bem-vindo(a) ao Sapiens", text: "Sou seu guia rápido. Em poucos passos te mostro onde tudo fica — vamos lá?" },
  { target: "dash-continue", title: "Continue de onde parou", text: "Aqui você sempre retoma exatamente a atividade anterior — nunca perde o fio." },
  { target: "dash-stats", title: "Sequência e semana", text: "Sua sequência de dias estudando e o progresso da semana. Consistência importa mais que maratona." },
  { target: "dash-mastery", title: "Domínio estimado", text: "Não é só taxa de acerto — é o que o Sapiens entende sobre como você pensa em cada frente." },
  { target: "dash-recommendation", title: "Próxima ação", text: "Sempre que encontramos uma lacuna no seu domínio, avisamos aqui — com um atalho direto pra treinar." },
  { target: "dash-achievements", title: "Conquistas", text: "Poucas, e só as que realmente importam. Nada de coleção de medalhas." },
  { target: "nav-sparks", title: "Sparks", text: "O combustível dos recursos com IA. Você ganha praticando, e pode comprar mais quando quiser." },
  { target: "nav-cognitive", title: "Mapa Cognitivo", text: "Uma visão clara de como você está evoluindo, frente por frente." },
  { target: null, title: "Pronto!", text: "Isso é tudo por agora. Bora estudar?" },
];

const TYPE_MS = 14; // ms por caractere — digitação rápida, de propósito.
const BUBBLE_WIDTH = 340;
const MARGIN = 14;
const ESTIMATED_HEIGHT = 220;

export default function OnboardingTour({ onDone }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [revealed, setRevealed] = useState(0);
  const [rect, setRect] = useState(null);
  const spotlightRef = useRef(null);
  const typeTimerRef = useRef(null);

  const step = STEPS[stepIndex];

  const clearSpotlight = useCallback(() => {
    spotlightRef.current?.classList.remove("tour-spotlight");
    spotlightRef.current = null;
  }, []);

  // Localiza e realça o alvo real do passo atual; recalcula a posição do
  // balão em resize/scroll enquanto ele está na tela.
  useEffect(() => {
    clearSpotlight();
    if (!step.target) {
      setRect(null);
      return;
    }
    const el = document.querySelector(`[data-tour="${step.target}"]`);
    if (!el) {
      setRect(null);
      return;
    }
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    const medir = () => {
      const r = el.getBoundingClientRect();
      // Elemento escondido (ex.: link de nav só-desktop numa tela estreita)
      // vira "sem alvo" — o balão cai pro modo centralizado em vez de
      // apontar pra um retângulo de tamanho zero.
      setRect(r.width > 0 && r.height > 0 ? r : null);
    };
    const t = setTimeout(() => {
      el.classList.add("tour-spotlight");
      spotlightRef.current = el;
      medir();
    }, 380);
    window.addEventListener("resize", medir);
    window.addEventListener("scroll", medir, true);
    return () => {
      clearTimeout(t);
      window.removeEventListener("resize", medir);
      window.removeEventListener("scroll", medir, true);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stepIndex]);

  useEffect(() => clearSpotlight, [clearSpotlight]);

  // Efeito de digitação — sem IA, só um contador revelando `step.text` rápido.
  useEffect(() => {
    setRevealed(0);
    clearInterval(typeTimerRef.current);
    typeTimerRef.current = setInterval(() => {
      setRevealed((n) => {
        if (n >= step.text.length) {
          clearInterval(typeTimerRef.current);
          return n;
        }
        return n + 1;
      });
    }, TYPE_MS);
    return () => clearInterval(typeTimerRef.current);
  }, [stepIndex, step.text]);

  const finish = useCallback(() => {
    clearSpotlight();
    api.put("/firestore/students/me/behavior", { flags: { onboarded: true } }).catch(() => {});
    onDone?.();
  }, [clearSpotlight, onDone]);

  const next = () => {
    if (revealed < step.text.length) {
      setRevealed(step.text.length); // clique durante a digitação: revela tudo de uma vez
      return;
    }
    if (stepIndex === STEPS.length - 1) finish();
    else setStepIndex((i) => i + 1);
  };

  const anchored = Boolean(step.target && rect);
  const bubbleStyle = anchored
    ? (() => {
        let top = rect.bottom + MARGIN;
        if (top + ESTIMATED_HEIGHT > window.innerHeight) top = Math.max(MARGIN, rect.top - ESTIMATED_HEIGHT - MARGIN);
        let left = rect.left + rect.width / 2 - BUBBLE_WIDTH / 2;
        left = Math.min(Math.max(left, MARGIN), window.innerWidth - BUBBLE_WIDTH - MARGIN);
        return { position: "fixed", top, left, width: BUBBLE_WIDTH };
      })()
    : { position: "fixed", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" };

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 100, pointerEvents: "none" }} data-testid="onboarding-tour">
      <div style={bubbleStyle}>
        <div
          className="tour-bubble pointer-events-auto rounded-2xl p-6 relative reveal"
          style={{ width: anchored ? BUBBLE_WIDTH : 360 }}
          data-testid={`onboarding-step-${stepIndex}`}
        >
          <div className="absolute top-3 left-3 w-6 h-6 rounded-full bg-sapiens-navy flex items-center justify-center shrink-0">
            <BrandMark className="w-3.5 h-3.5" tone="light" />
          </div>
          <button onClick={finish} className="absolute top-3 right-3 text-zinc-300 hover:text-zinc-600" data-testid="onboarding-close" aria-label="Pular tour">
            <X className="w-4 h-4" />
          </button>

          <div className="pt-7">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-sapiens-accentDeep mb-1">
              {stepIndex + 1}/{STEPS.length}
            </div>
            <div className="font-display font-bold text-lg text-zinc-950">{step.title}</div>
            <p className="mt-2 text-sm text-zinc-600 leading-relaxed min-h-[3.6em]">
              {step.text.slice(0, revealed)}
              {revealed < step.text.length && <span className="tour-cursor h-4 align-middle" />}
            </p>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <button onClick={finish} className="text-xs text-zinc-400 hover:text-zinc-600" data-testid="onboarding-skip">
              Pular tour
            </button>
            <button onClick={next} className="pill btn-sapiens inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-medium" data-testid="onboarding-next">
              {stepIndex === STEPS.length - 1 ? "Começar" : "Próximo"} <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
