import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Gift, Sparkles, Snowflake } from "lucide-react";
import { tocar } from "../../lib/som";
import { chuvaDeConfete, soltarConfete } from "../../lib/confete";
import {
  BENEFICIOS_DO_PLUS, fraseDoDesafio, letraDoDia, prazoDoPlus,
} from "../../lib/celebracao";
import { ROTAS } from "../../lib/rotas";

/**
 * A TELA DA OFENSIVA — o momento mais reconhecível do Duolingo, no Sapiens.
 *
 * Aparece por cima de tudo na primeira vez do dia em que o aluno estuda (a
 * regra de "quando" mora em `lib/celebracao.js`): a chama acende, o número
 * vira, a bolinha de hoje enche na fileira da semana, e — enquanto o aluno
 * ainda não ganhou — o caminho até os 2 dias de Sapiens Plus avança um nó.
 *
 * Se o 5º dia acabou de virar o presente, a tela tem um segundo ato: a caixa
 * abre, chove confete e o aluno lê o que ganhou e até quando vale.
 *
 * **Cada número aqui veio do servidor** (`/engajamento/me`): os dias, a
 * semana, o progresso do desafio, o prazo do Plus. A tela anima a chegada do
 * número; ela não inventa nenhum.
 */

/** A chama. Duas camadas que tremulam em ritmos diferentes — o fogo do
 *  Duolingo, desenhado aqui para não carregar imagem nenhuma. */
export function Chama({ tamanho = 120, acesa = true, className = "" }) {
  return (
    <svg
      viewBox="0 0 64 80"
      width={tamanho}
      height={(tamanho * 80) / 64}
      className={`chama ${acesa ? "chama-acesa" : "chama-apagada"} ${className}`}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="chama-fora" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stopColor="#FF6A00" />
          <stop offset="0.55" stopColor="#FF9F1C" />
          <stop offset="1" stopColor="#FFD166" />
        </linearGradient>
        <linearGradient id="chama-dentro" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stopColor="#FFD166" />
          <stop offset="1" stopColor="#FFF6D5" />
        </linearGradient>
      </defs>
      <path
        className="chama-fora"
        d="M32 2c4 12 18 20 22 36 5 19-8 40-22 40S5 67 10 46c3-12 11-16 12-28 6 6 7 12 7 12S34 18 32 2z"
        fill="url(#chama-fora)"
      />
      <path
        className="chama-dentro"
        d="M33 34c3 7 11 12 11 23 0 10-6 17-12 17s-12-6-11-15c1-8 7-10 8-17 3 3 4 7 4 7s1-8 0-15z"
        fill="url(#chama-dentro)"
      />
    </svg>
  );
}

/** O número que vira — o antigo sai por cima, o novo entra por baixo. */
function NumeroQueVira({ de, para }) {
  const [valor, setValor] = useState(de);
  useEffect(() => {
    const t = setTimeout(() => setValor(para), 650);
    return () => clearTimeout(t);
  }, [para]);
  return (
    <span className="relative inline-flex h-[1em] overflow-hidden align-bottom leading-none">
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={valor}
          initial={{ y: "100%", opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: "-100%", opacity: 0 }}
          transition={{ type: "spring", stiffness: 420, damping: 26 }}
          className="inline-block tabular-nums"
        >
          {valor}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}

/** A fileira da semana: bolinhas que acendem em sequência, hoje por último. */
function Semana({ semana = [] }) {
  return (
    <div className="mt-6 flex items-end justify-center gap-2 sm:gap-3" data-testid="ofensiva-semana">
      {semana.map((d, i) => (
        <div key={d.dia} className="flex flex-col items-center gap-1.5">
          <span className={`text-[11px] font-bold ${d.hoje ? "text-amber-200" : "text-white/40"}`}>
            {letraDoDia(d.dia)}
          </span>
          <span
            className={[
              "bolinha-semana",
              d.ativo ? "bolinha-ativa" : d.congelado ? "bolinha-congelada" : "",
              d.hoje ? "bolinha-hoje" : "",
            ].join(" ")}
            style={{ animationDelay: d.hoje ? "900ms" : `${120 + i * 60}ms` }}
          >
            {d.ativo ? <Check className="h-3.5 w-3.5" strokeWidth={3.5} /> : d.congelado ? <Snowflake className="h-3 w-3" /> : null}
          </span>
        </div>
      ))}
    </div>
  );
}

/** O caminho até o presente: cinco chamas e a caixa no fim. */
export function CaminhoDoPlus({ plus, compacto = false, acendendoHoje = false }) {
  if (!plus) return null;
  const nos = Array.from({ length: plus.meta_dias }, (_, i) => i + 1);
  return (
    <div className={`caminho-plus ${compacto ? "caminho-plus-compacto" : ""}`} data-testid="caminho-plus">
      {nos.map((n) => {
        const aceso = n <= plus.progresso;
        const recemAceso = acendendoHoje && n === plus.progresso;
        return (
          <span key={n} className="caminho-plus-trecho">
            <span
              className={`no-plus ${aceso ? "no-plus-aceso" : ""} ${recemAceso ? "no-plus-novo" : ""}`}
              title={`Dia ${n}`}
            >
              {aceso ? <Chama tamanho={compacto ? 14 : 18} /> : <span className="no-plus-n">{n}</span>}
            </span>
            {n < plus.meta_dias && <span className={`elo-plus ${n < plus.progresso ? "elo-plus-aceso" : ""}`} />}
          </span>
        );
      })}
      <span className="elo-plus" />
      <span className={`presente-plus ${plus.faltam === 1 ? "presente-quase" : ""}`} title={`${plus.presente_dias} dias de Sapiens Plus`}>
        <Gift className={compacto ? "h-4 w-4" : "h-5 w-5"} />
      </span>
    </div>
  );
}

function AtoDaOfensiva({ engajamento, aoContinuar, temPresente }) {
  const { ofensiva, plus } = engajamento;
  const botao = useRef(null);
  useEffect(() => {
    tocar("ofensiva");
    const t = setTimeout(() => soltarConfete({ quantidade: 60, forca: 10, y: window.innerHeight * 0.32 }), 700);
    botao.current?.focus();
    return () => clearTimeout(t);
  }, []);
  // No dia do presente o caminho continua na tela, cheio: é a 5ª chama
  // acendendo que dá sentido ao botão "Abrir meu presente".
  const mostrarCaminho = plus && (!plus.conquistado || temPresente);
  const frase = temPresente ? "Cinco dias seguidos. Seu presente chegou!" : fraseDoDesafio(plus);
  const recorde = ofensiva.dias > 1 && ofensiva.dias >= ofensiva.recorde;

  return (
    <motion.div
      key="ofensiva"
      initial={{ opacity: 0, scale: 0.92 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, x: -40 }}
      transition={{ type: "spring", stiffness: 260, damping: 22 }}
      className="flex w-full max-w-md flex-col items-center text-center"
    >
      <motion.div
        initial={{ scale: 0.2, rotate: -12 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 12, delay: 0.1 }}
        className="relative"
      >
        <span className="chama-aura" aria-hidden="true" />
        <Chama tamanho={128} />
      </motion.div>

      <div className="mt-2 font-display text-[64px] font-black leading-none tracking-tight text-amber-300 drop-shadow-[0_0_28px_rgba(255,170,40,0.55)] sm:text-[80px]">
        <NumeroQueVira de={Math.max(0, ofensiva.dias - 1)} para={ofensiva.dias} />
      </div>
      <h2 id="tela-ofensiva-titulo" className="mt-1 font-display text-2xl font-extrabold tracking-tight text-white">
        {ofensiva.dias === 1 ? "Sua ofensiva começou!" : `${ofensiva.dias} dias de ofensiva!`}
      </h2>
      <p className="mt-2 max-w-xs text-sm text-white/60">
        {recorde
          ? "É o seu recorde. Cada dia daqui para a frente é território novo."
          : ofensiva.dias === 1
          ? "Volte amanhã para a chama crescer."
          : "Hoje já conta. Amanhã, uma questão mantém a chama acesa."}
      </p>

      <Semana semana={ofensiva.semana} />

      {mostrarCaminho && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.1 }}
          className="mt-7 w-full rounded-2xl border border-amber-300/25 bg-amber-400/[0.07] p-4"
          data-testid="ofensiva-desafio-plus"
        >
          <div className="secao-olho text-amber-200/90">Desafio dos {plus.meta_dias} dias</div>
          <CaminhoDoPlus plus={plus} acendendoHoje />
          {frase && <p className="mt-2 text-sm font-semibold text-amber-100">{frase}</p>}
        </motion.div>
      )}

      <button
        ref={botao}
        onClick={aoContinuar}
        className="pill btn-sapiens mt-8 w-full rounded-2xl px-6 py-4 text-base font-extrabold uppercase tracking-wide"
        data-testid="ofensiva-continuar"
      >
        {temPresente ? "Abrir meu presente" : "Continuar"}
      </button>
    </motion.div>
  );
}

function AtoDoPresente({ plus, aoFechar }) {
  const [aberto, setAberto] = useState(false);
  const botao = useRef(null);
  useEffect(() => {
    const t = setTimeout(() => {
      setAberto(true);
      tocar("presente");
      chuvaDeConfete();
    }, 900);
    return () => clearTimeout(t);
  }, []);
  useEffect(() => { if (aberto) botao.current?.focus(); }, [aberto]);
  const prazo = prazoDoPlus(plus.ate);

  return (
    <motion.div
      key="presente"
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 24 }}
      className="flex w-full max-w-md flex-col items-center text-center"
      data-testid="tela-presente-plus"
    >
      <div className="relative flex h-40 w-40 items-center justify-center">
        {aberto && <span className="raios-plus" aria-hidden="true" />}
        <motion.div
          className={`caixa-plus ${aberto ? "caixa-plus-aberta" : "caixa-plus-tremendo"}`}
          animate={aberto ? { scale: [1, 1.35, 1.1], y: [0, -14, 0] } : { scale: 1 }}
          transition={{ duration: 0.6 }}
        >
          {aberto ? <Sparkles className="h-14 w-14" /> : <Gift className="h-14 w-14" />}
        </motion.div>
      </div>

      <AnimatePresence>
        {aberto && (
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: "spring", stiffness: 240, damping: 22 }}
            className="w-full"
          >
            <div className="secao-olho text-amber-200">5 dias seguidos. Você conseguiu.</div>
            <h2 id="tela-ofensiva-titulo" className="mt-1 font-display text-3xl font-black tracking-tight text-white">
              Você ganhou {plus.presente_dias} dias de <span className="texto-plus">Sapiens Plus</span>!
            </h2>
            {prazo && (
              <p className="mt-2 text-sm font-semibold text-amber-100" data-testid="presente-prazo">
                Vale {prazo}.
              </p>
            )}
            <ul className="mt-5 space-y-2 text-left">
              {BENEFICIOS_DO_PLUS.map((b, i) => (
                <motion.li
                  key={b.chave}
                  initial={{ opacity: 0, x: -14 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.25 + i * 0.12 }}
                  className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3"
                >
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-400 text-[#2a1600]">
                    <Check className="h-3.5 w-3.5" strokeWidth={3.5} />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-bold text-white">{b.texto}</span>
                    <span className="block text-xs text-white/55">{b.detalhe}</span>
                  </span>
                </motion.li>
              ))}
            </ul>
            <button
              ref={botao}
              onClick={aoFechar}
              className="pill btn-sapiens mt-7 w-full rounded-2xl px-6 py-4 text-base font-extrabold uppercase tracking-wide"
              data-testid="presente-fechar"
            >
              Começar a usar
            </button>
            <Link
              to={ROTAS.MENTIS}
              onClick={aoFechar}
              className="mt-3 inline-block text-sm font-semibold text-[#7FD8FF] hover:underline"
            >
              Conversar com a Mentis sem gastar Sparks
            </Link>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function TelaDaOfensiva({ engajamento, ofensiva = true, presente = false, aoFechar }) {
  const [ato, setAto] = useState(ofensiva ? "ofensiva" : "presente");

  useEffect(() => {
    const aoTeclar = (e) => { if (e.key === "Escape") aoFechar?.(); };
    window.addEventListener("keydown", aoTeclar);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", aoTeclar);
      document.body.style.overflow = overflow;
    };
  }, [aoFechar]);

  if (!engajamento) return null;
  return (
    <div
      className="tela-comemoracao fixed inset-0 z-[90] flex items-center justify-center overflow-y-auto px-4 py-10"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tela-ofensiva-titulo"
      data-testid="tela-ofensiva"
    >
      <AnimatePresence mode="wait">
        {ato === "ofensiva" ? (
          <AtoDaOfensiva
            engajamento={engajamento}
            temPresente={presente}
            aoContinuar={() => (presente ? setAto("presente") : aoFechar?.())}
          />
        ) : (
          <AtoDoPresente plus={engajamento.plus} aoFechar={aoFechar} />
        )}
      </AnimatePresence>
    </div>
  );
}
