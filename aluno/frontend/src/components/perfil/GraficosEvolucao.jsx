import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";
import { TrendingUp, CalendarRange, MoveRight } from "lucide-react";
import Grafico, { Balao, SemDado } from "./Grafico";
import { EIXO, GRADE, SERIES, TINTA, pct, questoes } from "./paleta";

/**
 * A EVOLUÇÃO — a parte da tela que justifica a tela.
 *
 * Duas medidas convivem aqui e elas NÃO podem dividir o mesmo gráfico: taxa de
 * acerto é percentual, volume é contagem. Um gráfico com dois eixos verticais
 * é o erro mais comum que existe em visualização — o leitor não tem como saber
 * qual linha lê em qual escala, e qualquer cruzamento entre as duas é acidente
 * do desenho, não fato sobre o aluno. Por isso são dois gráficos empilhados,
 * com o mesmo eixo de tempo embaixo.
 */

const CORTE_MOVEL = SERIES[0];
const CORTE_ACUMULADA = SERIES[6];

/** Quantos dias mostrar. A janela chega com 90 do servidor; no celular a
 *  leitura fica melhor com o mês corrente. */
function recortar(diaria, dias) {
  return dias ? diaria.slice(-dias) : diaria;
}

export function CurvaDeAcerto({ diaria, destacado }) {
  const pontos = recortar(diaria || [], 90).filter((d) => d.movel != null || d.acumulada != null);

  return (
    <Grafico
      id="evolucao"
      destacado={destacado}
      olho={<><TrendingUp className="h-3.5 w-3.5" /> Sua curva</>}
      titulo="Taxa de acerto ao longo do tempo"
      explicacao="A linha grossa é a média dos últimos 7 dias — ela ignora o dia isolado em que tudo deu errado. A fina é a média de tudo o que você já respondeu."
      legenda={[
        { cor: CORTE_MOVEL, rotulo: "Últimos 7 dias" },
        { cor: CORTE_ACUMULADA, rotulo: "Desde o começo" },
      ]}
      altura={230}
      tabela={{
        colunas: ["Dia", "Respondidas", "Acertos", "No dia", "7 dias"],
        linhas: pontos
          .filter((p) => p.respondidas > 0)
          .slice(-40)
          .reverse()
          .map((p) => [p.rotulo, p.respondidas, p.acertos, pct(p.taxa), pct(p.movel)]),
      }}
    >
      {pontos.length < 2 ? (
        <SemDado>
          A curva aparece quando você tiver respondido em dias diferentes — é a comparação entre
          eles que mostra a mudança.
        </SemDado>
      ) : (
        <ResponsiveContainer>
          <LineChart data={pontos} margin={{ top: 8, right: 10, left: -18, bottom: 0 }}>
            <CartesianGrid stroke={GRADE} vertical={false} />
            <XAxis dataKey="rotulo" {...EIXO} minTickGap={36} />
            <YAxis
              {...EIXO}
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              tickFormatter={(v) => `${v}%`}
              width={46}
            />
            {/* A régua de 50%: não é meta, é referência. Sem ela, uma curva
                que sobe de 30 para 40 parece a mesma coisa que uma que sobe de
                70 para 80. */}
            <ReferenceLine y={50} stroke={GRADE} />
            <Tooltip
              content={
                <Balao
                  titulo={(p) => p.rotulo}
                  linhas={(p) => [
                    p.respondidas
                      ? { cor: null, rotulo: "No dia", valor: `${questoes(p.respondidas)} · ${pct(p.taxa)}` }
                      : { cor: null, rotulo: "No dia", valor: "dia de folga" },
                    { cor: CORTE_MOVEL, rotulo: "Últimos 7 dias", valor: pct(p.movel) },
                    { cor: CORTE_ACUMULADA, rotulo: "Desde o começo", valor: pct(p.acumulada) },
                  ]}
                />
              }
              cursor={{ stroke: GRADE }}
            />
            <Line
              type="monotone" dataKey="acumulada" name="Desde o começo"
              stroke={CORTE_ACUMULADA} strokeWidth={1.5} dot={false} connectNulls
            />
            <Line
              type="monotone" dataKey="movel" name="Últimos 7 dias"
              stroke={CORTE_MOVEL} strokeWidth={2} dot={false} connectNulls
              activeDot={{ r: 4, stroke: "#0a1526", strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Grafico>
  );
}

export function VolumePorSemana({ semanal, destacado }) {
  const dados = (semanal || []).slice(-16);
  const tem = dados.some((s) => s.respondidas > 0);

  return (
    <Grafico
      id="volume"
      destacado={destacado}
      olho={<><CalendarRange className="h-3.5 w-3.5" /> Seu esforço</>}
      titulo="Quantas questões por semana"
      explicacao="Cada barra é uma semana de segunda a domingo. A última é a semana em curso — ela ainda vai crescer."
      legenda={[
        { cor: SERIES[0], rotulo: "Semanas fechadas" },
        { cor: "rgba(31,159,196,0.45)", rotulo: "Semana em curso" },
      ]}
      altura={200}
      tabela={{
        colunas: ["Semana de", "Respondidas", "Acertos", "Taxa"],
        linhas: dados.slice().reverse().map((s) => [s.rotulo, s.respondidas, s.acertos, pct(s.taxa)]),
      }}
    >
      {!tem ? (
        <SemDado>Responda algumas questões e a sua primeira barra aparece aqui.</SemDado>
      ) : (
        <ResponsiveContainer>
          <BarChart data={dados} margin={{ top: 8, right: 10, left: -22, bottom: 0 }} barCategoryGap="28%">
            <CartesianGrid stroke={GRADE} vertical={false} />
            <XAxis dataKey="rotulo" {...EIXO} minTickGap={18} />
            <YAxis {...EIXO} allowDecimals={false} width={44} />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
              content={
                <Balao
                  titulo={(p) => `Semana de ${p.rotulo}`}
                  linhas={(p) => [
                    { cor: SERIES[0], rotulo: "Respondidas", valor: String(p.respondidas) },
                    { cor: null, rotulo: "Acertos", valor: `${p.acertos} · ${pct(p.taxa)}` },
                  ]}
                />
              }
            />
            <Bar dataKey="respondidas" name="Questões" radius={[4, 4, 0, 0]} maxBarSize={24}>
              {dados.map((s) => (
                <Cell
                  key={s.semana}
                  fill={SERIES[0]}
                  // A semana em curso é outra COISA, não um valor menor: ela
                  // ainda não terminou. Meia opacidade + legenda dizem isso;
                  // outra cor faria parecer outra categoria.
                  fillOpacity={s.corrente ? 0.45 : 1}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Grafico>
  );
}

/**
 * COMEÇO → AGORA. Uma comparação de dois valores de UM item: a forma certa
 * não é gráfico de barras nem pizza, é o haltere — dois pontos na mesma régua,
 * ligados. O olho lê a distância, que é justamente o que importa.
 */
export function ComecoEAgora({ comparativo, destacado }) {
  if (!comparativo?.suficiente) {
    return (
      <Grafico
        id="comparativo"
        destacado={destacado}
        olho={<><MoveRight className="h-3.5 w-3.5" /> Começo × agora</>}
        titulo="Quanto você mudou"
        explicacao={`Preciso de pelo menos ${comparativo?.minimo ?? 20} respostas para comparar o seu começo com o seu agora sem que a conta vire sorte.`}
        altura={120}
      >
        <SemDado>
          Você tem {questoes(comparativo?.respondidas ?? 0)} respondidas. Faltam{" "}
          {Math.max(0, (comparativo?.minimo ?? 20) - (comparativo?.respondidas ?? 0))} para eu
          conseguir medir a sua mudança.
        </SemDado>
      </Grafico>
    );
  }

  const { inicio, agora, delta } = comparativo;
  const subiu = delta > 0;
  const corInicio = "rgba(31,159,196,0.55)";
  const corAgora = SERIES[0];
  const x = (v) => `${Math.max(0, Math.min(100, v))}%`;

  return (
    <Grafico
      id="comparativo"
      destacado={destacado}
      olho={<><MoveRight className="h-3.5 w-3.5" /> Começo × agora</>}
      titulo="Quanto você mudou"
      explicacao="O corte é na metade das suas respostas, não na metade do tempo — assim os dois lados têm o mesmo tamanho de amostra."
      altura={132}
      tabela={{
        colunas: ["Fase", "Respondidas", "Acertos", "Taxa"],
        linhas: [
          ["Primeira metade", inicio.respondidas, inicio.acertos, pct(inicio.taxa)],
          ["Metade mais recente", agora.respondidas, agora.acertos, pct(agora.taxa)],
        ],
      }}
    >
      <div className="flex h-full flex-col justify-center gap-5 px-1">
        <div className="relative h-11">
          {/* A régua de 0 a 100: sem ela, dois pontos soltos não dizem nada. */}
          <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2" style={{ background: GRADE }} />
          <div
            className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full"
            style={{
              left: x(Math.min(inicio.taxa, agora.taxa)),
              width: x(Math.abs(agora.taxa - inicio.taxa)),
              background: `linear-gradient(90deg, ${corInicio}, ${corAgora})`,
            }}
          />
          {[
            { valor: inicio.taxa, cor: corInicio, rotulo: "Começo", n: inicio.respondidas },
            { valor: agora.taxa, cor: corAgora, rotulo: "Agora", n: agora.respondidas },
          ].map((p) => (
            <div
              key={p.rotulo}
              className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 text-center"
              style={{ left: x(p.valor) }}
            >
              <div
                className="mx-auto h-3.5 w-3.5 rounded-full"
                style={{ background: p.cor, boxShadow: "0 0 0 3px #0a1526" }}
                title={`${p.rotulo}: ${pct(p.valor)} em ${questoes(p.n)}`}
              />
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-wide text-zinc-500">Primeiras {inicio.respondidas}</div>
            <div className="font-display text-xl font-bold text-zinc-300">{pct(inicio.taxa)}</div>
          </div>
          <div className="text-center">
            <div
              className="font-display text-3xl font-extrabold leading-none"
              style={{ color: subiu ? "#5FE9BC" : delta < 0 ? "#FF93A8" : TINTA.media }}
            >
              {subiu ? "+" : ""}{Math.round(delta)}
            </div>
            <div className="text-[10px] uppercase tracking-wide text-zinc-500">
              pontos {subiu ? "a mais" : delta < 0 ? "a menos" : "de diferença"}
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wide text-zinc-500">Últimas {agora.respondidas}</div>
            <div className="font-display text-xl font-bold" style={{ color: TINTA.forte }}>{pct(agora.taxa)}</div>
          </div>
        </div>
      </div>
    </Grafico>
  );
}
