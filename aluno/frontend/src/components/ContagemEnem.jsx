import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarDays, Radio, ArrowRight } from "lucide-react";
import { proximaProva, tempoRestante, quintasAteAProva } from "../lib/enem";

/**
 * A contagem regressiva para o ENEM.
 *
 * É a peça mais insistente do produto, e de propósito: é também a única que
 * não precisa exagerar para pressionar. A data é real (a mesma de
 * `backend/engajamento.py`), o relógio é real, e o número que fecha o
 * argumento — **quantas quintas-feiras ainda cabem antes da prova** — é
 * aritmética, não retórica. Cada quinta que passa é uma aula ao vivo que não
 * volta, e isso é literalmente verdade.
 *
 * Por isso NÃO existe aqui nenhum contador de "restam 3 vagas", nenhuma
 * oferta que "acaba em 10 minutos" e nenhum desconto que reaparece amanhã.
 * Urgência inventada dura uma semana e queima a confiança de quem já pagou;
 * o calendário do INEP não precisa de ajuda.
 *
 * Some sozinha quando os dois domingos passam (ver `lib/enem.js`).
 *
 * `variante`:
 *   - "faixa"   — a barra larga das telas de venda (cursos, mentoria, landing);
 *   - "medida"  — um azulejo da tira de progresso do Painel;
 *   - "linha"   — uma linha discreta, para o rodapé de outra seção.
 *
 * A "medida" entrou em 2026-09-16, quando a faixa saiu do TOPO do Painel. A
 * faixa é uma peça de venda — três CTAs e dois parágrafos — e ela abria a
 * tela do aluno antes de qualquer coisa que ele pudesse FAZER. O relógio
 * continua sendo a primeira dobra; o que mudou é que ali ele é um dado ao
 * lado da ofensiva e do nível, e o argumento completo vive onde a compra
 * acontece. O número é o mesmo nos dois lugares: o mesmo `tempoRestante`.
 */

function Bloco({ valor, rotulo, grande }) {
  return (
    <div
      className={`rounded-2xl border border-white/12 bg-black/35 text-center ${
        grande ? "min-w-[4.25rem] px-3.5 py-2.5" : "min-w-[3rem] px-2.5 py-1.5"
      }`}
    >
      <div
        className={`font-display font-extrabold tabular-nums tracking-tighter text-white ${
          grande ? "text-3xl md:text-4xl" : "text-lg"
        }`}
      >
        {String(valor).padStart(2, "0")}
      </div>
      <div className="font-mono-alt text-[9px] uppercase tracking-[0.2em] text-white/35">{rotulo}</div>
    </div>
  );
}

export default function ContagemEnem({ variante = "faixa", comCta = true, testid = "contagem-enem" }) {
  const [prova, setProva] = useState(() => proximaProva());
  const [tempo, setTempo] = useState(() => {
    const p = proximaProva();
    return p ? tempoRestante(p.inicio) : null;
  });

  useEffect(() => {
    const tick = () => {
      const p = proximaProva();
      setProva(p);
      setTempo(p ? tempoRestante(p.inicio) : null);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  if (!prova || !tempo) return null;

  const quintas = quintasAteAProva();
  const dia = prova.fase === 1 ? "primeiro" : "segundo";
  const dataFmt = prova.inicio.toLocaleDateString("pt-BR", { day: "2-digit", month: "long" });

  if (variante === "medida") {
    return (
      <Link
        to="/aula-ao-vivo"
        className="superficie lift flex flex-col justify-between p-4"
        data-testid={`${testid}-medida`}
        title={`${dia} dia do ENEM · ${dataFmt}`}
      >
        <div className="secao-olho flex items-center gap-1.5 text-amber-300/85">
          <CalendarDays className="h-3 w-3" /> ENEM
        </div>
        <div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="medida-n text-3xl text-amber-100">{tempo.dias}</span>
            <span className="text-sm text-white/45">{tempo.dias === 1 ? "dia" : "dias"}</span>
          </div>
          {/* O relógio vivo em letra pequena: é ele que faz a contagem parecer
              um relógio e não um número que alguém digitou. */}
          <div className="font-mono-alt text-[11px] tabular-nums text-white/35">
            {String(tempo.horas).padStart(2, "0")}:{String(tempo.minutos).padStart(2, "0")}
            :{String(tempo.segundos).padStart(2, "0")}
          </div>
        </div>
        <div className="medida-rotulo text-amber-200/70">
          {quintas === 0
            ? "sem aula antes da prova"
            : quintas === 1
            ? "1 aula ao vivo até lá"
            : `${quintas} aulas ao vivo até lá`}
        </div>
      </Link>
    );
  }

  if (variante === "linha") {
    return (
      <div
        className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-white/50"
        data-testid={`${testid}-linha`}
      >
        <CalendarDays className="h-3.5 w-3.5 text-amber-300" />
        <strong className="font-semibold text-white/85 tabular-nums">{tempo.dias} dias</strong>
        para o {dia} dia do ENEM
        <span className="text-white/25">·</span>
        <strong className="font-semibold text-amber-200 tabular-nums">{quintas}</strong>
        {quintas === 1 ? " aula ao vivo" : " aulas ao vivo"} até lá
      </div>
    );
  }

  return (
    <section
      className="relative overflow-hidden rounded-3xl border border-amber-300/25 p-5 md:p-6"
      style={{
        background:
          "radial-gradient(60% 120% at 12% 0%, rgba(242,169,59,0.16), transparent 70%)," +
          "linear-gradient(120deg, rgba(30,16,4,0.85) 0%, rgba(8,16,30,0.92) 60%)",
      }}
      data-testid={testid}
    >
      <div className="flex flex-wrap items-center gap-x-6 gap-y-4">
        <div className="min-w-[13rem] flex-1">
          <div className="flex items-center gap-2 font-mono-alt text-[10px] uppercase tracking-[0.28em] text-amber-300/90">
            <CalendarDays className="h-3.5 w-3.5" /> {dia} dia do ENEM · {dataFmt}
          </div>
          <h2 className="mt-2 font-display text-2xl font-extrabold leading-[1.05] tracking-tighter text-white md:text-3xl">
            O relógio não para.{" "}
            <span className="text-amber-200">
              {quintas === 0
                ? "Não há mais quinta antes da prova."
                : quintas === 1
                ? "Resta 1 aula ao vivo antes da prova."
                : `Restam ${quintas} aulas ao vivo antes da prova.`}
            </span>
          </h2>
          <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-white/55">
            {quintas > 0 ? (
              <>
                Toda quinta que passa é uma aula com o 1º colocado de Medicina da USP que você
                não assiste — e ela não volta. A data da prova é a mesma para todo mundo; o que
                muda é quantas dessas quintas você aproveita.
              </>
            ) : (
              <>
                A prova é agora. Use o que você já comprou: reveja seus cursos, converse com a
                Mentis e durma cedo.
              </>
            )}
          </p>
        </div>

        <div className="flex shrink-0 gap-2" aria-label="Tempo restante para o ENEM">
          <Bloco valor={tempo.dias} rotulo="dias" grande />
          <Bloco valor={tempo.horas} rotulo="horas" grande />
          <Bloco valor={tempo.minutos} rotulo="min" grande />
          <Bloco valor={tempo.segundos} rotulo="seg" grande />
        </div>
      </div>

      {comCta && quintas > 0 && (
        <div className="mt-5 flex flex-wrap items-center gap-2.5 border-t border-white/10 pt-4">
          <Link
            to="/aula-ao-vivo"
            className="pill btn-calor inline-flex items-center gap-2 rounded-full px-5 py-3 text-xs"
            data-testid={`${testid}-cta-live`}
          >
            <Radio className="h-3.5 w-3.5" /> Garantir a aula desta quinta
          </Link>
          <Link
            to="/cursos"
            className="pill btn-vidro inline-flex items-center gap-1.5 rounded-full px-4 py-2.5 text-xs"
            data-testid={`${testid}-cta-cursos`}
          >
            Ver os cursos <ArrowRight className="h-3 w-3" />
          </Link>
          <Link
            to="/mentoria"
            className="pill inline-flex items-center gap-1.5 rounded-full border border-white/12 px-4 py-2.5 text-xs text-white/60 hover:text-white"
            data-testid={`${testid}-cta-mentoria`}
          >
            Entrar na lista da mentoria
          </Link>
        </div>
      )}
    </section>
  );
}
