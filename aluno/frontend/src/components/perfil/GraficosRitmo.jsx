import {
  ResponsiveContainer, BarChart, Bar, Cell, LabelList,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  PieChart, Pie, XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";
import { Clock, Timer, CalendarDays, Repeat2, Compass } from "lucide-react";
import Grafico, { Balao, SemDado } from "./Grafico";
import { EIXO, GRADE, SERIES, RAMPA, TINTA, pct, questoes } from "./paleta";

/**
 * RITMO E HÁBITO — o que o aluno FAZ, nunca o que ele é.
 *
 * Tudo aqui é descrição: "você acerta mais à noite" é um fato sobre as suas
 * respostas. "Você rende mais à noite" seria uma afirmação sobre você, que
 * este produto não faz a partir de tempo de resposta (o contrato de behavior
 * declara esses campos como coletados e não usados para formar crença sobre o
 * estado cognitivo do estudante). A diferença mora nos textos, e ela é
 * deliberada — não mexa neles sem entender essa linha.
 */

const CINZA = "rgba(175, 196, 224, 0.28)";

export function QuandoVoceEstuda({ porHora, destacado }) {
  const dados = porHora || [];
  const total = dados.reduce((s, h) => s + h.respondidas, 0);
  const pico = dados.reduce((a, b) => (b.respondidas > (a?.respondidas || 0) ? b : a), null);

  return (
    <Grafico
      id="ritmo"
      destacado={destacado}
      olho={<><Clock className="h-3.5 w-3.5" /> O seu relógio</>}
      titulo="A que horas você estuda"
      explicacao="Cada coluna é uma hora do dia, no horário de Brasília. É o seu volume, não o seu acerto — o acerto por período está logo ao lado."
      altura={190}
      tabela={{
        colunas: ["Hora", "Respondidas", "Acertos", "Taxa"],
        linhas: dados.filter((h) => h.respondidas > 0).map((h) => [h.rotulo, h.respondidas, h.acertos, pct(h.taxa)]),
      }}
    >
      {total === 0 ? (
        <SemDado>Ainda não há respostas com horário registrado.</SemDado>
      ) : (
        <ResponsiveContainer>
          <BarChart data={dados} margin={{ top: 8, right: 8, left: -26, bottom: 0 }} barCategoryGap="18%">
            <CartesianGrid stroke={GRADE} vertical={false} />
            <XAxis
              dataKey="hora" {...EIXO}
              ticks={[0, 3, 6, 9, 12, 15, 18, 21]}
              tickFormatter={(h) => `${h}h`}
            />
            <YAxis {...EIXO} allowDecimals={false} width={40} />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
              content={
                <Balao
                  titulo={(p) => `Entre ${p.rotulo} e ${String((p.hora + 1) % 24).padStart(2, "0")}h`}
                  linhas={(p) => [
                    { cor: SERIES[0], rotulo: "Respondidas", valor: String(p.respondidas) },
                    p.respondidas ? { cor: null, rotulo: "Acerto", valor: pct(p.taxa) } : null,
                  ]}
                />
              }
            />
            <Bar dataKey="respondidas" name="Questões" radius={[3, 3, 0, 0]} maxBarSize={14} fill={SERIES[0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
      {pico?.respondidas > 0 && (
        <p className="mt-2 text-[11px] text-zinc-500">
          O seu horário mais frequente é por volta das {pico.rotulo} — {questoes(pico.respondidas)}.
        </p>
      )}
    </Grafico>
  );
}

export function AcertoPorPeriodo({ blocos, destacado }) {
  const dados = (blocos || []).filter((b) => b.respondidas > 0);

  return (
    <Grafico
      id="periodo"
      destacado={destacado}
      olho={<><Compass className="h-3.5 w-3.5" /> Manhã, tarde ou noite</>}
      titulo="Em que período você acerta mais"
      explicacao="Período com menos de 10 questões aparece apagado: ainda é pouco para eu afirmar qualquer coisa sobre ele."
      altura={190}
      tabela={{
        colunas: ["Período", "Faixa", "Respondidas", "Acertos", "Taxa"],
        linhas: (blocos || []).map((b) => [b.rotulo, b.faixa, b.respondidas, b.acertos, pct(b.taxa)]),
      }}
    >
      {dados.length === 0 ? (
        <SemDado>Ainda não há respostas suficientes para separar por período do dia.</SemDado>
      ) : (
        <ResponsiveContainer>
          <BarChart data={dados} margin={{ top: 18, right: 8, left: -26, bottom: 0 }} barCategoryGap="34%">
            <CartesianGrid stroke={GRADE} vertical={false} />
            <XAxis dataKey="rotulo" {...EIXO} />
            <YAxis {...EIXO} domain={[0, 100]} ticks={[0, 50, 100]} tickFormatter={(v) => `${v}%`} width={40} />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
              content={
                <Balao
                  titulo={(p) => `${p.rotulo} · ${p.faixa}`}
                  linhas={(p) => [
                    { cor: SERIES[0], rotulo: "Acerto", valor: pct(p.taxa) },
                    { cor: null, rotulo: "Amostra", valor: questoes(p.respondidas) },
                    p.confiavel ? null : { cor: null, rotulo: "Atenção", valor: "amostra curta" },
                  ]}
                />
              }
            />
            <Bar dataKey="taxa" name="Acerto" radius={[4, 4, 0, 0]} maxBarSize={44}>
              {dados.map((b) => (
                <Cell key={b.chave} fill={SERIES[0]} fillOpacity={b.confiavel ? 1 : 0.35} />
              ))}
              <LabelList dataKey="taxa" position="top" formatter={(v) => pct(v)} fill={TINTA.forte} fontSize={11} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Grafico>
  );
}

export function SuaSemana({ porDiaSemana, destacado }) {
  const dados = porDiaSemana || [];
  const total = dados.reduce((s, d) => s + d.respondidas, 0);

  return (
    <Grafico
      id="semana"
      destacado={destacado}
      olho={<><CalendarDays className="h-3.5 w-3.5" /> A forma da sua semana</>}
      titulo="Em que dias você estuda"
      explicacao="Quanto mais longe do centro, mais questões naquele dia da semana. Um desenho torto para um lado é um dia que está carregando os outros."
      altura={230}
      tabela={{
        colunas: ["Dia", "Respondidas", "Acertos", "Taxa"],
        linhas: dados.map((d) => [d.rotulo, d.respondidas, d.acertos, pct(d.taxa)]),
      }}
    >
      {total === 0 ? (
        <SemDado>O desenho da sua semana aparece com as primeiras respostas.</SemDado>
      ) : (
        <ResponsiveContainer>
          <RadarChart data={dados} outerRadius="72%">
            <PolarGrid stroke={GRADE} />
            <PolarAngleAxis dataKey="rotulo" tick={{ fill: TINTA.fraca, fontSize: 11 }} />
            <Tooltip
              content={
                <Balao
                  titulo={(p) => p.rotulo}
                  linhas={(p) => [
                    { cor: SERIES[0], rotulo: "Respondidas", valor: String(p.respondidas) },
                    p.respondidas ? { cor: null, rotulo: "Acerto", valor: pct(p.taxa) } : null,
                  ]}
                />
              }
            />
            <Radar
              dataKey="respondidas" name="Questões"
              stroke={SERIES[0]} strokeWidth={2} fill={SERIES[0]} fillOpacity={0.16}
              dot={{ r: 3, fill: SERIES[0], stroke: "#0a1526", strokeWidth: 2 }}
            />
          </RadarChart>
        </ResponsiveContainer>
      )}
    </Grafico>
  );
}

/** Faixa de tempo é uma escala ORDENADA (rápido → devagar), então a cor é uma
 *  rampa de um tom só, do fundo para o claro: a ordem aparece na cor. */
export function RitmoDeResposta({ faixas, destacado }) {
  const dados = (faixas || []).filter((f) => f.respondidas > 0);

  return (
    <Grafico
      id="tempo"
      destacado={destacado}
      olho={<><Timer className="h-3.5 w-3.5" /> Pressa</>}
      titulo="Você acerta mais rápido ou com calma?"
      explicacao="O tempo é medido da abertura da questão até o envio, e só conta quando foi registrado. Barra apagada tem amostra pequena demais."
      altura={190}
      tabela={{
        colunas: ["Ritmo", "Quando", "Respondidas", "Acertos", "Taxa"],
        linhas: (faixas || []).map((f) => [f.rotulo, f.descricao, f.respondidas, f.acertos, pct(f.taxa)]),
      }}
    >
      {dados.length === 0 ? (
        <SemDado>
          Nenhuma resposta com tempo registrado ainda. Ele começa a ser gravado quando você
          responde pelo app, na tela de prática.
        </SemDado>
      ) : (
        <ResponsiveContainer>
          <BarChart data={dados} margin={{ top: 18, right: 8, left: -26, bottom: 0 }} barCategoryGap="34%">
            <CartesianGrid stroke={GRADE} vertical={false} />
            <XAxis dataKey="rotulo" {...EIXO} />
            <YAxis {...EIXO} domain={[0, 100]} ticks={[0, 50, 100]} tickFormatter={(v) => `${v}%`} width={40} />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
              content={
                <Balao
                  titulo={(p) => `${p.rotulo} · ${p.descricao}`}
                  linhas={(p) => [
                    { cor: null, rotulo: "Acerto", valor: pct(p.taxa) },
                    { cor: null, rotulo: "Amostra", valor: questoes(p.respondidas) },
                  ]}
                />
              }
            />
            <Bar dataKey="taxa" name="Acerto" radius={[4, 4, 0, 0]} maxBarSize={48}>
              {dados.map((f, i) => (
                <Cell key={f.chave} fill={RAMPA[i + 1] || RAMPA[3]} fillOpacity={f.confiavel ? 1 : 0.35} />
              ))}
              <LabelList dataKey="taxa" position="top" formatter={(v) => pct(v)} fill={TINTA.forte} fontSize={11} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Grafico>
  );
}

export function MudarDeResposta({ decisao, destacado }) {
  const dados = (decisao || []).filter((d) => d.respondidas > 0);

  return (
    <Grafico
      id="habitos"
      destacado={destacado}
      olho={<><Repeat2 className="h-3.5 w-3.5" /> Primeira ideia</>}
      titulo="Vale a pena mudar de resposta?"
      explicacao="Isto é o SEU histórico, não uma regra sobre provas. Só conta questão em que o app registrou se você trocou a alternativa antes de enviar."
      altura={170}
      tabela={{
        colunas: ["Decisão", "Respondidas", "Acertos", "Taxa"],
        linhas: (decisao || []).map((d) => [d.rotulo, d.respondidas, d.acertos, pct(d.taxa)]),
      }}
    >
      {dados.length < 2 ? (
        <SemDado>
          Ainda faltam respostas registradas dos dois jeitos — mantendo e trocando a alternativa.
        </SemDado>
      ) : (
        <ResponsiveContainer>
          <BarChart
            data={dados} layout="vertical"
            margin={{ top: 0, right: 58, left: 0, bottom: 0 }} barCategoryGap="36%"
          >
            <CartesianGrid stroke={GRADE} horizontal={false} />
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis
              type="category" dataKey="rotulo" {...EIXO}
              width={150} tick={{ fill: TINTA.media, fontSize: 11 }}
            />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
              content={
                <Balao
                  titulo={(p) => p.rotulo}
                  linhas={(p) => [
                    { cor: null, rotulo: "Acerto", valor: pct(p.taxa) },
                    { cor: null, rotulo: "Amostra", valor: questoes(p.respondidas) },
                  ]}
                />
              }
            />
            <Bar dataKey="taxa" name="Acerto" radius={[0, 4, 4, 0]} maxBarSize={18}>
              {dados.map((d) => (
                <Cell key={d.chave} fill={SERIES[0]} fillOpacity={d.confiavel ? 1 : 0.35} />
              ))}
              <LabelList dataKey="taxa" position="right" formatter={(v) => pct(v)} fill={TINTA.forte} fontSize={11} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Grafico>
  );
}

export function DeOndeVemSuasRespostas({ origem, destacado }) {
  const todas = origem || [];
  const principais = todas.slice(0, 5);
  const resto = todas.slice(5);
  const dados = [
    ...principais.map((o, i) => ({ ...o, cor: SERIES[i] })),
    ...(resto.length
      ? [{
          chave: "outras", rotulo: "Outras",
          respondidas: resto.reduce((s, o) => s + o.respondidas, 0),
          acertos: resto.reduce((s, o) => s + o.acertos, 0),
          taxa: null, cor: CINZA,
        }]
      : []),
  ];
  const total = dados.reduce((s, d) => s + d.respondidas, 0);

  return (
    <Grafico
      id="origem"
      destacado={destacado}
      olho={<><Compass className="h-3.5 w-3.5" /> De onde vêm</>}
      titulo="Onde você responde questão"
      explicacao="Prática, treino, aulas e questões feitas pela Mentis contam juntas no seu histórico — todas alimentam este painel."
      legenda={dados.map((d) => ({ cor: d.cor, rotulo: d.rotulo }))}
      altura={210}
      tabela={{
        colunas: ["Origem", "Questões", "Acerto"],
        linhas: dados.map((d) => [d.rotulo, d.respondidas, pct(d.taxa)]),
      }}
    >
      {total === 0 ? (
        <SemDado>Nada respondido ainda.</SemDado>
      ) : (
        <ResponsiveContainer>
          <PieChart>
            <Tooltip
              content={
                <Balao
                  titulo={(p) => p.rotulo}
                  linhas={(p) => [
                    { cor: p.cor, rotulo: "Questões", valor: String(p.respondidas) },
                    { cor: null, rotulo: "Do total", valor: `${Math.round((100 * p.respondidas) / total)}%` },
                  ]}
                />
              }
            />
            <Pie
              data={dados} dataKey="respondidas" nameKey="rotulo"
              innerRadius="54%" outerRadius="80%"
              paddingAngle={2} stroke="#0a1526" strokeWidth={2}
            >
              {dados.map((d) => (
                <Cell key={d.chave} fill={d.cor} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      )}
    </Grafico>
  );
}
