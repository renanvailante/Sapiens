import { useEffect, useRef } from "react";
import { Flame } from "lucide-react";
import Grafico, { SemDado } from "./Grafico";
import { RAMPA, VAZIO, pct, questoes } from "./paleta";

/**
 * O CALENDÁRIO DE CONSTÂNCIA — dezessete semanas de estudo num só olhar.
 *
 * Não é um gráfico do recharts porque não precisa ser: é uma grade de
 * quadrados, e uma grade de quadrados em CSS é mais leve, mais nítida e mais
 * fácil de tornar acessível do que qualquer biblioteca faria.
 *
 * A escala é ORDINAL: um tom só, do fundo para o claro, quatro degraus fixos
 * (1-4, 5-9, 10-19, 20+ questões). Fixos, e não relativos ao próprio aluno,
 * de propósito — uma escala que se reajusta sozinha faria três questões numa
 * semana fraca acenderem igual a trinta numa semana cheia, e o aluno leria
 * como constância o que foi só ausência de comparação.
 */

const NIVEIS = [VAZIO, ...RAMPA];
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

function titulo(d) {
  const [ano, mes, dia] = d.dia.split("-");
  const data = `${dia}/${mes}/${ano}`;
  if (!d.respondidas) return `${data} — sem estudo`;
  return `${data} — ${questoes(d.respondidas)}, ${pct(d.taxa)} de acerto`;
}

export default function Calendario({ constancia, destacado }) {
  const rolagem = useRef(null);
  const dias = constancia?.calendario || [];

  // A semana de hoje é a que importa; num celular a grade não cabe inteira,
  // então ela abre já no fim, não no começo de quatro meses atrás.
  useEffect(() => {
    const el = rolagem.current;
    if (el) el.scrollLeft = el.scrollWidth;
  }, [dias.length]);

  const semanas = dias.length ? Math.max(...dias.map((d) => d.semana)) + 1 : 0;
  // Um rótulo de mês por coluna em que o mês vira.
  const rotulos = [];
  let ultimoMes = null;
  for (let s = 0; s < semanas; s++) {
    const primeiro = dias.find((d) => d.semana === s);
    const mes = primeiro ? Number(primeiro.dia.slice(5, 7)) - 1 : null;
    rotulos.push(mes != null && mes !== ultimoMes ? MESES[mes] : "");
    if (mes != null) ultimoMes = mes;
  }

  return (
    <Grafico
      id="constancia"
      destacado={destacado}
      olho={<><Flame className="h-3.5 w-3.5" /> Constância</>}
      titulo="Os seus últimos quatro meses"
      explicacao="Cada quadrado é um dia. Quanto mais claro, mais questões. Quadrado apagado é dia sem resposta — e dia sem resposta não é fracasso, é informação."
      altura="auto"
      tabela={{
        colunas: ["Dia", "Respondidas", "Acertos", "Taxa"],
        linhas: dias
          .filter((d) => d.respondidas > 0)
          .slice()
          .reverse()
          .slice(0, 40)
          .map((d) => [d.dia.split("-").reverse().join("/"), d.respondidas, d.acertos, pct(d.taxa)]),
      }}
    >
      {dias.length === 0 ? (
        <SemDado>O calendário começa no seu primeiro dia de estudo.</SemDado>
      ) : (
        <>
          <div ref={rolagem} className="no-scrollbar overflow-x-auto pb-1">
            <div className="inline-flex gap-[3px]">
              {/* Coluna dos dias da semana: só três rótulos, senão a grade
                  vira um bloco de texto. */}
              <div className="mr-1 flex flex-col gap-[3px] pt-[14px]">
                {["", "Ter", "", "Qui", "", "Sáb", ""].map((r, i) => (
                  <div key={i} className="h-[11px] text-[9px] leading-[11px] text-zinc-500">{r}</div>
                ))}
              </div>
              {Array.from({ length: semanas }).map((_, s) => (
                <div key={s} className="flex flex-col gap-[3px]">
                  <div className="h-[11px] text-[9px] leading-[11px] text-zinc-500">{rotulos[s]}</div>
                  {Array.from({ length: 7 }).map((__, w) => {
                    const d = dias.find((x) => x.semana === s && x.dia_semana === w);
                    if (!d) return <div key={w} className="h-[11px] w-[11px]" />;
                    return (
                      <div
                        key={w}
                        className="h-[11px] w-[11px] rounded-[3px]"
                        style={{ background: NIVEIS[d.nivel] }}
                        title={titulo(d)}
                        data-testid={d.respondidas > 0 ? "calendario-dia-ativo" : undefined}
                      />
                    );
                  })}
                </div>
              ))}
            </div>
          </div>

          {/* O medidor de constância. Um valor contra um limite não é gráfico
              de barras nem pizza: é um medidor — oito casas, uma por semana.
              E ele mede PRESENÇA, não volume: quem faz vinte questões toda
              semana aprende mais que quem faz cento e sessenta num domingo e
              some por dois meses. */}
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2" data-testid="perfil-consistencia">
            <div className="flex items-center gap-1">
              {Array.from({ length: constancia.semanas_na_janela || 8 }).map((_, i) => (
                <span
                  key={i}
                  className="h-1.5 w-5 rounded-full"
                  style={{
                    background:
                      i < (constancia.semanas_com_estudo || 0) ? RAMPA[2] : "rgba(255,255,255,0.08)",
                  }}
                />
              ))}
            </div>
            <span className="text-[11px] text-zinc-400">
              presente em{" "}
              <strong className="font-mono-alt text-zinc-200">{constancia.semanas_com_estudo || 0}</strong>{" "}
              das últimas {constancia.semanas_na_janela || 8} semanas
            </span>
          </div>

          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1.5 text-[10px] text-zinc-500">
              menos
              {NIVEIS.map((cor, i) => (
                <span key={i} className="h-[11px] w-[11px] rounded-[3px]" style={{ background: cor }} />
              ))}
              mais
            </div>
            <div className="flex flex-wrap items-center gap-4 text-[11px] text-zinc-400">
              <span>
                <strong className="font-mono-alt text-zinc-200">{constancia.dias_ativos_30}</strong> dos últimos 30 dias
              </span>
              <span>
                melhor sequência:{" "}
                <strong className="font-mono-alt text-zinc-200">{constancia.melhor_sequencia}</strong>
              </span>
            </div>
          </div>
        </>
      )}
    </Grafico>
  );
}
