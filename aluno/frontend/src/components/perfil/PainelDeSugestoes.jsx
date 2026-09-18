import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ChevronRight, ChevronLeft, Radio, RotateCw, Target, PenLine, Flame, ArrowRight,
} from "lucide-react";
import Mentis from "../Mentis";
import { montarSugestoes } from "../../lib/sugestoes";

/**
 * O BALÃO DE SUGESTÕES — o que fazer com o que o painel acabou de mostrar.
 *
 * O PROBLEMA QUE ELE RESOLVE. O painel de desempenho é a tela mais densa do
 * Sapiens: dezessete gráficos que descrevem o aluno com honestidade. E
 * descrever é onde ele parava. O aluno lia "você acerta 48% em Química",
 * concordava, fechava a aba — e a informação não virava nenhuma mudança de
 * comportamento. Diagnóstico sem prescrição é só um espelho melhor.
 *
 * Este balão é a prescrição, e ele não inventa nada: cada item sai de um
 * número que já está desenhado num gráfico atrás dele (ver `lib/sugestoes.js`,
 * onde moram as regras e a razão de cada uma). Nenhuma requisição nova — o
 * payload de `/perfil/painel` já traz tudo.
 *
 * POR QUE ELE RECOLHE. A tela tem um dono, e o dono é o painel. Um balão fixo
 * e permanente por cima de gráficos é a definição de elemento que domina a
 * página sem ter sido convidado — e o aluno que quer comparar duas curvas
 * precisa do canto direito. A aba de reabrir tem 34px e fica encostada na
 * borda: some do caminho sem sumir do produto.
 *
 * O ESTADO FICA NO NAVEGADOR (`localStorage`), e é a escolha certa para este
 * caso: é conveniência de quem está olhando, não dado do aluno. Quem recolheu
 * o balão numa visita não quer encontrá-lo aberto na próxima; e se o
 * armazenamento falhar (aba anônima, cookies bloqueados), o pior que acontece
 * é ele nascer aberto, que é o padrão de qualquer forma.
 *
 * NO CELULAR ELE NASCE RECOLHIDO. Um painel de 340px sobre uma tela de 375px
 * é uma tela nova, não um balão: ali ele precisa ser convidado. No notebook
 * nasce aberto, porque há canto sobrando e porque é onde a leitura demorada
 * dos gráficos acontece.
 */

const CHAVE = "sapiens_sugestoes_aberto";

// Do nome que `lib/sugestoes.js` devolve para o desenho. A biblioteca não
// importa ícone nenhum de propósito: ela é regra pura e é testada sem React.
const ICONES = {
  radio: Radio,
  rotate: RotateCw,
  alvo: Target,
  caneta: PenLine,
  chama: Flame,
};

function leituraInicial() {
  try {
    const guardado = localStorage.getItem(CHAVE);
    if (guardado === "0") return false;
    if (guardado === "1") return true;
  } catch {
    // Aba anônima, cookies bloqueados, storage cheio: cai no padrão abaixo.
  }
  // Sem preferência guardada: aberto no notebook, recolhido no telefone.
  return typeof window !== "undefined" ? window.innerWidth >= 1024 : true;
}

export default function PainelDeSugestoes({ painel }) {
  const [aberto, setAberto] = useState(leituraInicial);

  useEffect(() => {
    try {
      localStorage.setItem(CHAVE, aberto ? "1" : "0");
    } catch {
      // Ver `leituraInicial`: não poder lembrar não pode quebrar a tela.
    }
  }, [aberto]);

  const sugestoes = montarSugestoes(painel);

  // Sem sugestão, sem balão — nem a aba. Um aluno novo, com o painel ainda
  // em amostra insuficiente, não tem o que ser sugerido, e uma aba que abre
  // um balão vazio é pior do que aba nenhuma.
  if (sugestoes.length === 0) return null;

  return (
    <aside
      className="balao-sugestoes"
      data-aberto={aberto}
      aria-label="Sugestões para você"
      data-testid="painel-sugestoes"
    >
      {/* A ABA. Fica FORA do corpo, encostada na borda esquerda dele, e é o
          que sobra na tela quando o balão recolhe. */}
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        className="balao-aba"
        aria-expanded={aberto}
        aria-controls="balao-sugestoes-corpo"
        data-testid="painel-sugestoes-alternar"
      >
        {aberto ? (
          <ChevronRight className="h-4 w-4" />
        ) : (
          <>
            <ChevronLeft className="h-4 w-4" />
            <span className="balao-aba-contagem">{sugestoes.length}</span>
          </>
        )}
        <span className="sr-only">
          {aberto ? "Recolher sugestões" : `Abrir ${sugestoes.length} sugestões`}
        </span>
      </button>

      <div className="balao-corpo" id="balao-sugestoes-corpo">
        <div className="balao-cabeca">
          <Mentis className="h-6 w-6 shrink-0" variante="icone" animada={false} />
          <div className="min-w-0">
            <div className="secao-olho">Para você</div>
            <div className="balao-titulo">O que fazer com isto</div>
          </div>
        </div>

        <ul className="balao-lista">
          {sugestoes.map((s) => {
            const Icone = ICONES[s.icone];
            return (
              <li key={s.id}>
                <Link
                  to={s.rota}
                  className="balao-item"
                  data-tom={s.tom}
                  data-testid={`sugestao-${s.id}`}
                >
                  <span className="balao-item-icone">
                    {Icone ? (
                      <Icone className="h-4 w-4" strokeWidth={1.9} />
                    ) : (
                      <Mentis className="h-4 w-4" variante="icone" animada={false} />
                    )}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="balao-item-olho">{s.olho}</span>
                    <span className="balao-item-titulo">{s.titulo}</span>
                    <span className="balao-item-porque">{s.porque}</span>
                    <span className="balao-item-cta">
                      {s.cta} <ArrowRight className="h-3 w-3" />
                    </span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}
