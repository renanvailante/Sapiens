import { useEffect, useRef, useState } from "react";
import { Volume2, VolumeX } from "lucide-react";
import Mentis from "../Mentis";
import { EVENTO_VOZ, calar, definirVoz, falar, vozDisponivel, vozLigada } from "../../lib/vozDaMentis";

/**
 * A MENTIS FALANDO — o balão do Duolingo, com a guia do Sapiens.
 *
 * No Duolingo, quem diz o que fazer é um personagem com um balão, não um
 * rótulo de seção. A diferença é de leitura: "Seu primeiro passo" num olho de
 * seção é metadado e o olho pula; uma frase dita por alguém, com o nome do
 * aluno, é lida. É por isso que a trilha do dia abre por aqui.
 *
 * O texto entra digitado (rápido — 2 letras a cada 16ms) e a Mentis fica no
 * estado "falando" enquanto ele entra ou enquanto a voz fala. Tocar no balão
 * mostra tudo de uma vez: ninguém espera animação para ler.
 *
 * A voz é opcional e do aparelho (`lib/vozDaMentis.js`). O botão liga e já
 * fala a frase atual — o toque É o gesto que o navegador exige para falar.
 */

function movimentoReduzido() {
  try {
    return window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
  } catch {
    return false;
  }
}

export default function BalaoDaMentis({
  titulo,
  texto,
  children,
  comemorando = false,
  olhar = 0.5,
  tamanho = "g",
  testid = "balao-mentis",
}) {
  const completo = `${titulo ? `${titulo} ` : ""}${texto || ""}`;
  const [mostrado, setMostrado] = useState(() => (movimentoReduzido() ? (texto || "").length : 0));
  const [falandoVoz, setFalandoVoz] = useState(false);
  const [voz, setVoz] = useState(vozLigada);
  const relogio = useRef(null);
  const total = (texto || "").length;
  const digitando = mostrado < total;

  // Digitação: recomeça sempre que o texto muda (um passo novo é uma fala nova).
  useEffect(() => {
    clearInterval(relogio.current);
    if (movimentoReduzido()) {
      setMostrado(total);
      return undefined;
    }
    setMostrado(0);
    relogio.current = setInterval(() => {
      setMostrado((n) => {
        if (n >= total) {
          clearInterval(relogio.current);
          return n;
        }
        return n + 2;
      });
    }, 16);
    return () => clearInterval(relogio.current);
  }, [texto, total]);

  // A voz fala a frase nova sozinha — se o aluno já a ligou um dia.
  useEffect(() => {
    if (!vozLigada()) return undefined;
    const t = setTimeout(() => {
      falar(completo, { aoComecar: () => setFalandoVoz(true), aoTerminar: () => setFalandoVoz(false) });
    }, 250);
    return () => clearTimeout(t);
  }, [completo]);

  // Sair da tela cala a Mentis: uma frase do Hoje continuando a ser falada
  // por cima da questão seguinte seria a guia atrapalhando.
  useEffect(() => () => calar(), []);

  useEffect(() => {
    const ouvir = (e) => setVoz(Boolean(e.detail));
    window.addEventListener(EVENTO_VOZ, ouvir);
    return () => window.removeEventListener(EVENTO_VOZ, ouvir);
  }, []);

  const alternarVoz = (e) => {
    e.stopPropagation();
    const nova = !voz;
    definirVoz(nova);
    setVoz(nova);
    if (nova) {
      falar(completo, { forcar: true, aoComecar: () => setFalandoVoz(true), aoTerminar: () => setFalandoVoz(false) });
    } else {
      setFalandoVoz(false);
    }
  };

  const estado = comemorando ? "feliz" : digitando || falandoVoz ? "falando" : "neutra";
  // No celular ela encolhe: a 320px uma Mentis de 80px deixava 182px para a
  // fala, e o balão virava uma coluna de 280px de altura.
  const medida = tamanho === "p" ? "h-14 w-14" : "h-14 w-14 min-[400px]:h-20 min-[400px]:w-20 sm:h-24 sm:w-24";

  return (
    <div className="balao-guia" data-testid={testid}>
      <div className="balao-guia-mentis shrink-0" aria-hidden="true">
        <Mentis className={medida} estado={estado} olhar={olhar} flutuar title={undefined} />
      </div>

      <div className="min-w-0 flex-1">
        <div
          className="balao-guia-fala"
          onClick={() => setMostrado(total)}
          data-testid={`${testid}-fala`}
        >
          {titulo && (
            <p className="font-display text-lg font-extrabold leading-snug tracking-tight text-white sm:text-xl" data-testid={`${testid}-titulo`}>
              {titulo}
            </p>
          )}
          {/* O texto inteiro existe desde o primeiro quadro (leitor de tela e
              teste leem tudo); a digitação só ESCONDE o que ainda não entrou. */}
          {texto ? <p className="mt-1 text-[15px] leading-relaxed text-white/80" data-testid={`${testid}-texto`}>
            <span className="sr-only">{texto}</span>
            {/* O resto ocupa o lugar desde já (invisível): o balão nasce do
                tamanho final e nada embaixo dele pula enquanto ela "fala". */}
            <span aria-hidden="true">
              {(texto || "").slice(0, mostrado)}
              <span className="balao-guia-resto">{(texto || "").slice(mostrado)}</span>
            </span>
          </p> : null}

          {vozDisponivel() && (
            <button
              type="button"
              onClick={alternarVoz}
              className="balao-guia-voz"
              aria-pressed={voz}
              aria-label={voz ? "Silenciar a voz da Mentis" : "Ouvir a Mentis em voz alta"}
              title={voz ? "Silenciar a voz" : "Ouvir em voz alta"}
              data-testid={`${testid}-voz`}
            >
              {voz ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
            </button>
          )}
        </div>

        {children && <div className="mt-3.5">{children}</div>}
      </div>
    </div>
  );
}
