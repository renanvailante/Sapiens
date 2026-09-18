import { Link } from "react-router-dom";
import {
  ResponsiveContainer, AreaChart, Area, RadarChart, Radar, PolarGrid, PolarAngleAxis,
  XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, LabelList,
} from "recharts";
import { PenLine, Compass, ArrowRight } from "lucide-react";
import Grafico, { Balao, SemDado } from "./Grafico";
import { EIXO, GRADE, SERIES, TINTA } from "./paleta";

/**
 * A REDAÇÃO — mil pontos num componente só, e o painel passava por ela em
 * silêncio.
 *
 * O produto já guarda cada correção com nota total E nota por competência
 * (`redacao_avaliacoes`, escrito pelo corretor em `redacao_routes`). Era o
 * maior conjunto de dado real do aluno que nenhuma tela desenhava.
 *
 * Duas perguntas, dois gráficos, e nenhum deles inventa nada:
 *
 *  · **a nota ao longo das correções** — a série é a nota que o corretor deu,
 *    na ordem em que saiu. O eixo vai de 0 a 1000 sempre: cortar o eixo em
 *    volta das notas do aluno faria 40 pontos parecerem uma virada;
 *  · **as cinco competências** — média de todas as correções contra a última.
 *    É o radar, porque as cinco competências são um conjunto fechado e do
 *    mesmo tamanho (200 pontos cada), que é exatamente quando um radar diz
 *    algo que cinco barras não dizem: a FORMA do texto do aluno.
 */

const COR_NOTA = SERIES[0];
const COR_MEDIA = SERIES[6];

function Vazio({ id, titulo, destacado }) {
  return (
    <Grafico
      id={id}
      destacado={destacado}
      olho={<><PenLine className="h-3.5 w-3.5" /> Redação</>}
      titulo={titulo}
      explicacao="A redação vale 1000 pontos sozinha — é o único componente da prova que não depende de acertar questão nenhuma."
      altura={150}
    >
      <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
        <p className="max-w-sm text-xs leading-relaxed text-zinc-500">
          Você ainda não corrigiu nenhuma redação por aqui. A primeira já desenha o gráfico — e a
          partir da terceira dá para ver a sua curva.
        </p>
        <Link
          to="/redacao"
          className="pill btn-sapiens inline-flex min-h-[34px] items-center gap-1.5 rounded-full px-4 py-2 text-xs font-medium"
          data-testid="perfil-ir-redacao"
        >
          Corrigir uma redação <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </Grafico>
  );
}

export function EvolucaoDaRedacao({ redacao, destacado }) {
  const serie = redacao?.serie || [];
  if (!redacao?.corrigidas) {
    return <Vazio id="redacao" titulo="A sua nota de redação" destacado={destacado} />;
  }

  return (
    <Grafico
      id="redacao"
      destacado={destacado}
      olho={<><PenLine className="h-3.5 w-3.5" /> Redação</>}
      titulo="A sua nota, correção a correção"
      explicacao="Cada ponto é uma redação corrigida, na ordem em que você enviou. A linha fina atravessada é a sua média."
      altura={230}
      acaoTopo={
        <div className="text-right">
          <div className="font-display text-2xl font-extrabold leading-none text-zinc-950">
            {redacao.melhor}
          </div>
          <div className="text-[10px] uppercase tracking-wide text-zinc-500">melhor nota</div>
        </div>
      }
      tabela={{
        colunas: ["Quando", "Nota", "Pontos estimados"],
        linhas: serie.slice().reverse().map((s) => [
          s.rotulo, s.nota, s.estimados ? `${s.estimados} de ${s.nota}` : "—",
        ]),
      }}
    >
      {serie.length < 2 ? (
        <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
          <div className="font-display text-5xl font-extrabold text-zinc-950">{redacao.ultima}</div>
          <div className="text-xs text-zinc-500">
            de 1000, na sua primeira correção. A segunda redação já vira linha.
          </div>
          <Link
            to="/redacao"
            className="pill btn-sapiens mt-1 inline-flex min-h-[34px] items-center gap-1.5 rounded-full px-4 py-2 text-xs font-medium"
          >
            Escrever outra <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      ) : (
        <ResponsiveContainer>
          <AreaChart data={serie} margin={{ top: 14, right: 14, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="grad-redacao" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={COR_NOTA} stopOpacity={0.22} />
                <stop offset="100%" stopColor={COR_NOTA} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={GRADE} vertical={false} />
            <XAxis dataKey="rotulo" {...EIXO} minTickGap={20} />
            {/* 0 a 1000 sempre: um eixo apertado em volta das notas do aluno
                transformaria 40 pontos de variação numa montanha. */}
            <YAxis {...EIXO} domain={[0, 1000]} ticks={[0, 250, 500, 750, 1000]} width={48} />
            <ReferenceLine y={redacao.media} stroke={COR_MEDIA} strokeWidth={1.5} />
            <Tooltip
              cursor={{ stroke: GRADE }}
              content={
                <Balao
                  titulo={(p) => `Correção de ${p.rotulo}`}
                  linhas={(p) => [
                    { cor: COR_NOTA, rotulo: "Nota", valor: `${p.nota} / 1000` },
                    p.estimados
                      ? { cor: null, rotulo: "Ainda estimados", valor: `${p.estimados} pts` }
                      : null,
                  ]}
                />
              }
            />
            <Area
              type="monotone" dataKey="nota" name="Nota"
              stroke={COR_NOTA} strokeWidth={2} fill="url(#grad-redacao)"
              dot={{ r: 3, fill: COR_NOTA, stroke: "#0a1526", strokeWidth: 2 }}
              activeDot={{ r: 5, stroke: "#0a1526", strokeWidth: 2 }}
            >
              {/* Um rótulo só, na última nota: um número em cima de cada ponto
                  é ruído, e a tabela já carrega todos. */}
              <LabelList
                dataKey="nota"
                content={(props) => {
                  const { x, y, index, value } = props;
                  if (index !== serie.length - 1) return null;
                  return (
                    <text x={x} y={y - 10} fill={TINTA.forte} fontSize={12} textAnchor="middle">
                      {value}
                    </text>
                  );
                }}
              />
            </Area>
          </AreaChart>
        </ResponsiveContainer>
      )}
    </Grafico>
  );
}

export function CompetenciasDaRedacao({ redacao, destacado }) {
  const comps = redacao?.competencias || [];
  if (!redacao?.corrigidas || comps.length === 0) {
    return <Vazio id="competencias" titulo="As cinco competências" destacado={destacado} />;
  }
  const dados = comps.map((c) => ({ ...c, curto: c.rotulo }));
  const pior = comps.reduce((a, b) => (b.media < a.media ? b : a), comps[0]);

  return (
    <Grafico
      id="competencias"
      destacado={destacado}
      olho={<><Compass className="h-3.5 w-3.5" /> Redação por competência</>}
      titulo="A forma da sua redação"
      explicacao="Cada eixo vale 200 pontos. Quanto mais perto da borda, melhor — e o recorte para dentro é onde a sua nota está sendo perdida."
      legenda={[
        { cor: COR_MEDIA, rotulo: "Média das suas correções" },
        { cor: COR_NOTA, rotulo: "Última correção" },
      ]}
      altura={250}
      rodape={
        <p className="mt-2 text-[11px] leading-relaxed text-zinc-500">
          A que mais segura a sua nota é{" "}
          <strong className="text-zinc-300">{pior.rotulo.toLowerCase()}</strong> ({pior.media} de{" "}
          {pior.maxima} em média, {pior.amostra} correção{pior.amostra === 1 ? "" : "ões"}) —{" "}
          {pior.descricao.toLowerCase()}.
        </p>
      }
      tabela={{
        colunas: ["Competência", "O que mede", "Média", "Última", "Melhor", "Correções"],
        linhas: comps.map((c) => [
          c.rotulo, c.descricao, `${c.media}/200`, `${c.ultima}/200`, `${c.melhor}/200`, c.amostra,
        ]),
      }}
    >
      <ResponsiveContainer>
        <RadarChart data={dados} outerRadius="68%">
          <PolarGrid stroke={GRADE} />
          <PolarAngleAxis dataKey="curto" tick={{ fill: TINTA.fraca, fontSize: 10 }} />
          <Tooltip
            content={
              <Balao
                titulo={(p) => p.rotulo}
                linhas={(p) => [
                  { cor: COR_MEDIA, rotulo: "Média", valor: `${p.media} / 200` },
                  { cor: COR_NOTA, rotulo: "Última", valor: `${p.ultima} / 200` },
                  { cor: null, rotulo: "Correções", valor: String(p.amostra) },
                ]}
              />
            }
          />
          <Radar
            dataKey="media" name="Média"
            stroke={COR_MEDIA} strokeWidth={1.5} fill={COR_MEDIA} fillOpacity={0.14}
          />
          <Radar
            dataKey="ultima" name="Última"
            stroke={COR_NOTA} strokeWidth={2} fill={COR_NOTA} fillOpacity={0.1}
            dot={{ r: 3, fill: COR_NOTA, stroke: "#0a1526", strokeWidth: 2 }}
          />
        </RadarChart>
      </ResponsiveContainer>

    </Grafico>
  );
}
