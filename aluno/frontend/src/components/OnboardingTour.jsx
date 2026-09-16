import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";
import BrandMark from "./BrandMark";
import Mentis from "./Mentis";
import { ArrowRight, X } from "lucide-react";

// Tour guiado da Mentis: uma sequência de balões que aponta pras peças reais
// da UI (via `data-tour="..."` nos elementos-alvo, espalhados por
// Dashboard.jsx, PainelDeProgresso.jsx, Nav.jsx e MentisWidget.jsx). Nunca
// bloqueia a página por baixo — é dispensável a qualquer momento.
//
// QUANDO ABRE (revisto em 2026-09-15): uma vez por SESSÃO do navegador, não
// uma vez na vida. Quem entra na plataforma vê o guia; quem recarrega a página
// no meio do estudo, não. Quem quiser rever fora disso tem o botão "Guia" no
// topo do Painel e o "Rever o guia" no lançador de ferramentas — os dois
// abrem esta mesma sequência (ver `Dashboard.jsx`, `?guia=1`).
//
// O QUE ENTRA: TUDO o que o aluno pode usar. A régua antiga era "as nove
// ferramentas principais"; ela deixava de fora justamente o que ninguém
// descobre sozinho — provas do ENEM, revisões, cronograma, liga, ofensiva,
// comunidade, instalar o app, falar com a equipe. Uma ferramenta que só existe
// atrás de um ícone de grade não existe para quem não sabe que ela existe.
//
// Uma frase por passo, sempre. Completo não quer dizer longo de ler: são
// vinte e um passos de uma linha, não cinco parágrafos de filosofia do
// produto. Alvo que pode não estar na tela (seção que só aparece com dado)
// simplesmente centraliza o balão, sem quebrar a sequência.
const STEPS = [
  {
    target: null,
    mascote: true,
    title: "Oi, eu sou a Mentis",
    text: "Eu acompanho você até a prova. Em um minuto eu te mostro tudo o que existe aqui dentro.",
  },
  // O MAPA PRIMEIRO. É a peça de maior impacto visual do Sapiens e a que
  // comunica o valor do produto sem um parágrafo — começar por ela é decisão
  // de produto, não ordem de tela.
  {
    target: "dash-mapa",
    title: "Mapa de Treino",
    text: "56 pontos. Cada um é uma missão curta. Domine um e o território ao redor se revela.",
  },
  {
    target: "dash-provas",
    title: "Provas do ENEM",
    text: "As provas inteiras, questão por questão, do jeito que caíram — e cada resposta alimenta o resto.",
  },
  {
    target: "dash-mastery",
    title: "Seu domínio",
    text: "Seis frentes. Cada uma sobe com ACERTO: 40 acertos numa frente é o que vale um \u201cDominado\u201d.",
  },
  {
    target: "tour-ofensiva",
    title: "Ofensiva",
    text: "Dias seguidos estudando. Se faltar um, o congelador salva a sequência.",
  },
  {
    target: "tour-liga",
    title: "Liga da semana",
    text: "Seu XP te coloca numa tabela com outros alunos. Zera toda segunda.",
  },
  {
    target: "tour-missoes",
    title: "Missões de hoje",
    text: "Três por dia, trocam à meia-noite. Concluir rende Sparks e XP.",
  },
  {
    target: "dash-conquistas",
    title: "Conquistas",
    text: "Clique em qualquer uma: ela abre com o seu progresso, o que falta e onde conseguir.",
  },
  {
    target: "dash-foco",
    title: "Onde focar",
    text: "Suas dificuldades, com destino. Todo card leva à missão que trata aquilo — ou a mim.",
    // Some quando o aluno ainda não tem medida nenhuma: apontar para uma
    // seção que não está na tela centralizaria um balão falando do nada.
  },
  {
    target: "dash-hoje",
    title: "Hoje",
    text: "Seu cronograma da semana e as revisões que venceram — o que tem hora marcada aparece aqui.",
  },
  {
    target: "dash-mentis",
    mascote: true,
    title: "Eu leio o seu histórico",
    text: "Antes da primeira palavra eu já sei onde você escorrega. Te levar a qualquer tela daqui é de graça.",
  },
  {
    target: "dash-redacao",
    title: "Redação",
    text: "Escreva no padrão ENEM e receba a nota nas cinco competências.",
  },
  {
    target: "dash-gerar",
    title: "Questões feitas para você",
    text: "Eu gero questões novas sobre a sua lacuna exata. 5 Sparks cada uma, sempre com o preço à vista.",
  },
  {
    target: "dash-desempenho",
    title: "Meu desempenho",
    text: "Não é quanto você errou. É por quê — o padrão que se repete nos seus erros.",
  },
  {
    target: "dash-sparks",
    title: "Sparks",
    text: "A moeda do que usa IA. Você ganha estudando e pode comprar. Nada com IA roda sem o preço aparecer antes.",
  },
  {
    target: "dash-comunidade",
    title: "Comunidade",
    text: "Mural de dúvidas: perguntar é de graça e responder bem rende Sparks.",
  },
  {
    target: "dash-aulas",
    title: "Aula com gente de verdade",
    text: "Quando o problema é maior que uma questão: aula particular com alunos de Medicina da USP.",
  },
  {
    target: "dash-extras",
    title: "App e contato",
    text: "Instale o Sapiens no aparelho e fale com a equipe quando achar um erro ou tiver uma ideia.",
  },
  {
    target: "nav-more",
    title: "Tudo o que existe",
    text: "Este botão abre o produto inteiro em grade: liga, histórico, feed, lixeira e todas as telas.",
    mobile: { target: "nav-mobile-trigger" },
  },
  {
    target: "mentis-widget",
    mascote: true,
    title: "Estou em toda tela",
    text: "Este ícone me chama de qualquer lugar do Sapiens, sem você perder o que estava fazendo.",
  },
  {
    target: null,
    mascote: true,
    title: "É isso",
    text: "Comece abrindo o mapa. Para rever este guia, o botão \u201cGuia\u201d fica no topo do Painel.",
  },
];

const TYPE_MS = 14; // ms por caractere — digitação rápida, de propósito.
const BUBBLE_MAX = 340;
const MARGIN = 14;
const ESTIMATED_HEIGHT = 220; // só o palpite inicial; ver `bubbleH` abaixo.

/** Largura que cabe de verdade nesta tela. Era 340 cravado, e o clamp de
 *  posição usava `innerWidth - 340 - MARGIN` como TETO: abaixo de 354px de
 *  largura esse teto fica negativo e vence o piso, então num aparelho de
 *  320px o balão nascia em `left: -34` — com o selo e o começo do texto
 *  cortados fora da tela. */
const larguraBalao = () => Math.min(BUBBLE_MAX, window.innerWidth - MARGIN * 2);

/** Resolve a sequência para a largura atual: cada passo pode trazer um
 *  `mobile` com alvo e texto próprios, ou `mobile: null` para sumir no
 *  celular. Nada disso é enfeite — abaixo de `lg` metade dos alvos do tour
 *  (`nav-primarios`, `nav-more`) simplesmente não está na página. */
function passosPara(estreito) {
  if (!estreito) return STEPS.map(({ mobile, ...passo }) => passo);
  return STEPS.map(({ mobile, ...passo }) => (mobile === undefined ? passo : mobile && { ...passo, ...mobile }))
    .filter(Boolean);
}

export default function OnboardingTour({ onDone }) {
  // `lg` do Tailwind (1024px) é a mesma fronteira onde a barra de links dá
  // lugar ao menu deslizante em Nav.jsx — o tour tem de contar a mesma
  // história que a tela está mostrando.
  const [estreito, setEstreito] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(max-width: 1023px)").matches,
  );
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1023px)");
    const ouvir = (e) => setEstreito(e.matches);
    mq.addEventListener("change", ouvir);
    return () => mq.removeEventListener("change", ouvir);
  }, []);
  const passos = useMemo(() => passosPara(estreito), [estreito]);

  const [stepIndex, setStepIndex] = useState(0);
  const [revealed, setRevealed] = useState(0);
  const [rect, setRect] = useState(null);
  // Altura REAL do balão. O valor fixo de 220px subestimava o balão a 340px de
  // largura (o texto quebra em cinco ou seis linhas), e como ele é `fixed` o
  // rodapé com "Próximo"/"Pular tour" podia cair abaixo da dobra sem que
  // houvesse como rolar até lá — o aluno ficava preso no guia.
  const [bubbleH, setBubbleH] = useState(ESTIMATED_HEIGHT);
  const bubbleRef = useRef(null);
  const spotlightRef = useRef(null);
  const typeTimerRef = useRef(null);

  const step = passos[Math.min(stepIndex, passos.length - 1)];

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

  // Mede a altura real do balão e reposiciona a partir dela. Um
  // `ResizeObserver` e não uma medição única porque a altura muda enquanto o
  // texto é digitado e a cada passo — e é a altura que decide se o rodapé com
  // os botões cabe na tela.
  useLayoutEffect(() => {
    const el = bubbleRef.current;
    if (!el) return;
    const medir = () => setBubbleH(el.getBoundingClientRect().height || ESTIMATED_HEIGHT);
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    return () => ro.disconnect();
  }, [stepIndex]);

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
    if (stepIndex >= passos.length - 1) finish();
    else setStepIndex((i) => i + 1);
  };

  const anchored = Boolean(step.target && rect);
  const bubbleStyle = anchored
    ? (() => {
        const largura = larguraBalao();
        // Abaixo do alvo se couber; senão acima; e se não couber de nenhum dos
        // dois lados, encostado na borda de baixo — nunca fora dela. Os três
        // casos usam a altura medida, não um palpite.
        let top = rect.bottom + MARGIN;
        if (top + bubbleH > window.innerHeight) top = rect.top - bubbleH - MARGIN;
        top = Math.min(Math.max(top, MARGIN), Math.max(MARGIN, window.innerHeight - bubbleH - MARGIN));

        let left = rect.left + rect.width / 2 - largura / 2;
        // Piso DEPOIS do teto: invertido, o piso perdia para um teto negativo
        // em telas estreitas e jogava o balão para fora pela esquerda.
        left = Math.max(MARGIN, Math.min(left, window.innerWidth - largura - MARGIN));
        return { position: "fixed", top, left, width: largura };
      })()
    : { position: "fixed", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", padding: MARGIN };

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 100, pointerEvents: "none" }} data-testid="onboarding-tour">
      <div style={bubbleStyle}>
        <div
          ref={bubbleRef}
          className="tour-bubble pointer-events-auto rounded-2xl p-6 relative reveal"
          // Centralizado eram 360px cravados, sem teto: num aparelho de 320px
          // o balão era mais largo que a tela. E é justamente no modo
          // centralizado que o celular cai com mais frequência, porque o alvo
          // `nav-primarios` não existe abaixo de `lg`.
          style={{ width: anchored ? "100%" : "min(360px, 100%)" }}
          data-testid={`onboarding-step-${stepIndex}`}
        >
          {/* Nos passos em que a Mentis fala na primeira pessoa, é a cara
              dela no selo — não a marca. O guia É ela. */}
          {step.mascote ? (
            <Mentis className="absolute left-2.5 top-2.5 h-7 w-7 shrink-0" variante="icone" />
          ) : (
            <div className="absolute left-3 top-3 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sapiens-navy">
              <BrandMark className="h-3.5 w-3.5" tone="light" />
            </div>
          )}
          <button onClick={finish} className="absolute top-3 right-3 text-zinc-300 hover:text-zinc-600" data-testid="onboarding-close" aria-label="Pular tour">
            <X className="w-4 h-4" />
          </button>

          <div className="pt-7">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-sapiens-accentDeep mb-1">
              {stepIndex + 1}/{passos.length}
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
              {stepIndex >= passos.length - 1 ? "Começar" : "Próximo"} <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
