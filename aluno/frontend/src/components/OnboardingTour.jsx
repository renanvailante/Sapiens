import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import BrandMark from "./BrandMark";
import { ArrowRight, X } from "lucide-react";

// Tour guiado do primeiro login: uma sequência de balões que aponta pras
// peças reais da UI (via `data-tour="..."` nos elementos-alvo, espalhados
// por Dashboard.jsx, Nav.jsx e MentisWidget.jsx). Nunca bloqueia a página
// por baixo — é dispensável a qualquer momento, e não repete depois que
// `flags.onboarded` vira `true` no perfil do aluno (Firestore). O botão
// "Rever o guia", no topo do Painel, reabre esta mesma sequência.
//
// A régua do que entra aqui (2026-09-09): o guia tem de cobrir TUDO o que o
// aluno precisa saber para usar o produto sozinho — as quatro abas da barra,
// de onde saem as questões, o que custa Sparks e por quê, e o fato de que
// todo card de dificuldade é clicável. Um passo por ideia; alvo que pode não
// existir na tela (uma seção que só aparece com dado) simplesmente centraliza
// o balão, sem quebrar a sequência.
const STEPS = [
  {
    target: null,
    title: "Bem-vindo(a) ao Sapiens",
    text: "Um minuto e você sabe usar tudo por aqui. Pode pular quando quiser — o guia volta pelo botão \u201cRever o guia\u201d.",
  },
  {
    target: "nav-primarios",
    title: "Suas quatro abas",
    text: "Painel, Treino, Redação e Mentis. Nesta ordem: onde você se orienta, onde treina, onde escreve e com quem conversa.",
  },
  {
    target: "dash-hero",
    title: "Tudo começa nas provas",
    text: "O botão principal abre todas as provas do ENEM. Você responde questão a questão, e a cada dez o Sapiens fecha uma rodada com o seu padrão de erro.",
  },
  {
    target: "dash-stats",
    title: "Seus números do dia",
    text: "Sequência de dias, a semana, quantas questões você já respondeu e o seu saldo de Sparks. Consistência vale mais que maratona.",
  },
  {
    target: "nav-sparks",
    title: "Sparks",
    text: "A moeda dos recursos com IA. Você ganha respondendo questões e pode comprar mais. Nada com IA acontece sem o preço aparecer antes.",
  },
  {
    target: "dash-foco",
    title: "Todo card de erro é clicável",
    text: "Cada dificuldade aqui leva a algum lugar: a missão do Treino que trata aquilo, ou um pedido pronto à Mentis sobre aquele ponto.",
  },
  {
    target: "dash-foco",
    title: "E nada é enviado sozinho",
    text: "Ao pedir à Mentis, a mensagem já vem escrita, mas parada. Você escolhe abrir o chat, ou enviar se ele já estiver aberto — vendo o custo antes.",
  },
  {
    target: "dash-treino",
    title: "Treino",
    text: "Um mapa de missões curtas. Dominar um ponto revela o território ao redor — e é para cá que os cards de dificuldade te mandam.",
  },
  {
    target: "dash-redacao",
    title: "Redação",
    text: "Escreva no padrão ENEM e receba a nota nas cinco competências. Se quiser entender a nota, a Mentis lê a sua redação e explica.",
  },
  {
    target: "dash-mentis",
    title: "Mentis",
    text: "Ela lê o seu histórico inteiro antes da primeira palavra: onde você erra, com que amostra, e qual padrão está por trás. Depois é conversa.",
  },
  {
    target: "mentis-widget",
    title: "Ela vai com você",
    text: "Este ícone abre a mesma conversa em qualquer tela — e ela sabe em qual você está quando você pergunta.",
  },
  {
    target: "nav-more",
    title: "O resto fica aqui",
    text: "Provas por área, seu perfil cognitivo, as questões que você gerou, histórico, feed e o canal de reclamações e sugestões: tudo neste menu.",
  },
  {
    target: "dash-aulas",
    title: "Aula com gente de verdade",
    text: "Quando o problema é maior que uma questão, dá para pedir aula particular com a nossa equipe por aqui.",
  },
  {
    target: "dash-achievements",
    title: "Conquistas",
    text: "Poucas, e só as que realmente importam. Todas contadas do que você fez de fato — nada de medalha de participação.",
  },
  {
    target: null,
    title: "Pronto!",
    text: "É isso. Comece pelas provas do ENEM no botão principal do Painel — o resto aparece a partir do que você responder.",
  },
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

          <div className="mt-4 flex items-center justify-between gap-2">
            <div className="flex items-center gap-3">
              <button onClick={finish} className="text-xs text-zinc-400 hover:text-zinc-600" data-testid="onboarding-skip">
                Pular tour
              </button>
              {stepIndex > 0 && (
                <button
                  onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
                  className="text-xs text-zinc-400 hover:text-zinc-600"
                  data-testid="onboarding-back"
                >
                  Voltar
                </button>
              )}
            </div>
            <button onClick={next} className="pill btn-sapiens inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-medium" data-testid="onboarding-next">
              {stepIndex === STEPS.length - 1 ? "Começar" : "Próximo"} <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
