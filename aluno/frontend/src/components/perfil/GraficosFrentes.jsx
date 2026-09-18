import { Link } from "react-router-dom";
import {
  ResponsiveContainer, BarChart, Bar, LabelList, PieChart, Pie, Cell,
  ScatterChart, Scatter, ZAxis, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";
import {
  Layers, PieChart as PieIcon, Crosshair, LineChart as LineIcon, ArrowRight, ArrowUpDown,
} from "lucide-react";
import Grafico, { Balao, SemDado } from "./Grafico";
import { EIXO, GRADE, SERIES, TINTA, ESTADO, DIVERGENTE, pct, questoes } from "./paleta";

/**
 * AS FRENTES DA PROVA — Matemática, Biologia, Redação…
 *
 * Isto não é a ontologia do produto e não pode ser confundido com ela: é a
 * divisão pública do ENEM, a mesma que o cronograma e o Painel usam
 * (`prioridade_enem` no servidor). É por isso que aqui pode haver percentual,
 * amostra e tabela, enquanto a seção de forças continua sendo só palavras.
 *
 * A COR SEGUE A MATÉRIA, nunca a posição dela no ranking. Matemática é a
 * mesma cor no gráfico de barras, na pizza e nas linhas — se a cor mudasse
 * conforme a ordem, cada gráfico contaria uma história diferente sobre a
 * mesma semana.
 */
const COR_DA_FRENTE = {
  matematica: SERIES[0],
  biologia: SERIES[1],
  quimica: SERIES[2],
  fisica: SERIES[3],
  natureza: SERIES[4],
  humanas: SERIES[5],
  linguagens: SERIES[6],
  redacao: SERIES[7],
};
const corDa = (chave) => COR_DA_FRENTE[chave] || SERIES[0];
const CINZA = "rgba(175, 196, 224, 0.28)";

/** Frentes que o aluno já respondeu o bastante para a conta valer. Frente sem
 *  medida NÃO vira barra de 0%: "não medi" e "você errou tudo" são coisas
 *  diferentes, e desenhar as duas igual é mentira. */
const medidas = (linhas) =>
  (linhas || []).filter((l) => l.chave !== "redacao" && l.taxa_acerto != null && l.respondidas > 0);

export function AcertoPorFrente({ linhas, destacado }) {
  const dados = medidas(linhas)
    .slice()
    .sort((a, b) => (b.taxa_acerto ?? 0) - (a.taxa_acerto ?? 0));
  const semMedida = (linhas || []).filter(
    (l) => l.chave !== "redacao" && (l.taxa_acerto == null || l.respondidas === 0)
  );

  return (
    <Grafico
      id="frentes"
      destacado={destacado}
      olho={<><Layers className="h-3.5 w-3.5" /> Matéria por matéria</>}
      titulo="Onde você acerta mais"
      explicacao="Só entram as matérias em que você já respondeu o bastante para a conta significar alguma coisa. O número ao lado da barra é a amostra."
      altura={Math.max(150, dados.length * 38 + 20)}
      tabela={{
        colunas: ["Matéria", "Respondidas", "Acertos", "Taxa", "Amostra"],
        linhas: (linhas || []).map((l) => [
          l.nome,
          l.respondidas,
          l.acertos,
          l.taxa_acerto == null ? "—" : pct(l.taxa_acerto),
          { medido: "medida", amostra_curta: "curta", sem_medida: "sem medida" }[l.estado] || "—",
        ]),
      }}
    >
      {dados.length === 0 ? (
        <SemDado>
          Nenhuma matéria tem respostas suficientes ainda. Bastam três questões numa matéria para
          ela aparecer aqui.
        </SemDado>
      ) : (
        <ResponsiveContainer>
          <BarChart
            data={dados}
            layout="vertical"
            margin={{ top: 0, right: 64, left: 0, bottom: 0 }}
            barCategoryGap="34%"
          >
            <CartesianGrid stroke={GRADE} horizontal={false} />
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis
              type="category" dataKey="nome" {...EIXO}
              width={112} tick={{ fill: TINTA.media, fontSize: 11 }}
            />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
              content={
                <Balao
                  titulo={(p) => p.nome}
                  linhas={(p) => [
                    { cor: corDa(p.chave), rotulo: "Acerto", valor: pct(p.taxa_acerto) },
                    { cor: null, rotulo: "Amostra", valor: questoes(p.respondidas) },
                    p.estado === "amostra_curta"
                      ? { cor: null, rotulo: "Atenção", valor: "amostra curta" }
                      : null,
                  ]}
                />
              }
            />
            <Bar dataKey="taxa_acerto" name="Acerto" radius={[0, 4, 4, 0]} maxBarSize={18}>
              {dados.map((d) => (
                <Cell key={d.chave} fill={corDa(d.chave)} />
              ))}
              {/* Rótulo direto na ponta: o valor não pode morar só no balão,
                  que no celular não existe. */}
              <LabelList
                dataKey="taxa_acerto"
                position="right"
                formatter={(v) => pct(v)}
                fill={TINTA.forte}
                fontSize={11}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      {semMedida.length > 0 && (
        <p className="mt-2 text-[11px] leading-relaxed text-zinc-500">
          Ainda sem medida: {semMedida.map((l) => l.nome).join(", ")}. Responda algumas questões
          dessas matérias e elas entram no gráfico.
        </p>
      )}
    </Grafico>
  );
}

/**
 * O GRÁFICO DE DUAS DIMENSÕES — o que a tela toda existia sem responder:
 * **entre tudo que dá para estudar agora, o que move mais a nota?**
 *
 * Eixo horizontal: o quanto falta para o acerto pleno naquela matéria.
 * Eixo vertical: o peso da matéria na nota do ENEM (decisão de produto, a
 * mesma de `prioridade_enem`). Tamanho da bolha: quantas questões sustentam a
 * medida. Quem está em cima e à direita rende mais ponto por hora estudada.
 */
export function OndeRendeMais({ linhas, destacado }) {
  const dados = (linhas || [])
    .filter((l) => l.lacuna != null)
    .map((l, i) => ({
      ...l,
      x: Math.round((l.lacuna || 0) * 100),
      y: l.peso,
      z: Math.max(6, l.respondidas || 0),
      prioridade: i === 0,
    }));
  const topo = dados.find((d) => d.prioridade);

  return (
    <Grafico
      id="prioridade"
      destacado={destacado}
      olho={<><Crosshair className="h-3.5 w-3.5" /> Onde investir a próxima hora</>}
      titulo="Peso na prova × o quanto falta"
      explicacao="Quanto mais à direita, mais falta. Quanto mais acima, mais aquela matéria mexe na sua nota. O tamanho da bolha é a quantidade de questões que já medi."
      legenda={[
        { cor: ESTADO.atencao, rotulo: "Onde rende mais agora" },
        { cor: SERIES[0], rotulo: "Demais matérias" },
      ]}
      altura={250}
      tabela={{
        colunas: ["Matéria", "Falta", "Peso", "Amostra", "Por quê"],
        linhas: dados.map((d) => [d.nome, `${d.x}%`, d.peso.toFixed(2), d.respondidas, d.porque]),
      }}
    >
      {dados.length === 0 ? (
        <SemDado>Este gráfico aparece assim que houver matéria medida.</SemDado>
      ) : (
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 14, right: 20, left: -14, bottom: 4 }}>
            <CartesianGrid stroke={GRADE} />
            <XAxis
              type="number" dataKey="x" name="Falta" domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]} tickFormatter={(v) => `${v}%`} {...EIXO}
            />
            <YAxis
              type="number" dataKey="y" name="Peso" domain={[0.3, 1.1]}
              ticks={[0.5, 0.7, 1.0]}
              tickFormatter={(v) => ({ 0.5: "menor", 0.7: "médio", 1: "maior" }[v] || "")}
              width={62} {...EIXO}
            />
            <ZAxis type="number" dataKey="z" range={[60, 460]} />
            <Tooltip
              cursor={{ stroke: GRADE }}
              content={
                <Balao
                  titulo={(p) => p.nome}
                  linhas={(p) => [
                    { cor: p.prioridade ? ESTADO.atencao : SERIES[0], rotulo: "Falta", valor: `${p.x}%` },
                    { cor: null, rotulo: "Amostra", valor: p.respondidas ? questoes(p.respondidas) : "sem medida" },
                  ]}
                />
              }
            />
            <Scatter data={dados} name="Matérias">
              {dados.map((d) => (
                <Cell
                  key={d.chave}
                  fill={d.prioridade ? ESTADO.atencao : SERIES[0]}
                  fillOpacity={d.prioridade ? 0.9 : 0.55}
                  stroke="#0a1526"
                  strokeWidth={2}
                />
              ))}
              <LabelList
                dataKey="nome"
                position="top"
                fill={TINTA.media}
                fontSize={10}
                // Só os três primeiros ganham nome no gráfico: com sete
                // rótulos eles se sobrepõem e nenhum fica legível. Os outros
                // estão no balão e na tabela.
                content={(props) => {
                  const { x, y, index, value } = props;
                  if (index > 2) return null;
                  return (
                    <text x={x} y={y - 10} fill={TINTA.media} fontSize={10} textAnchor="middle">
                      {value}
                    </text>
                  );
                }}
              />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      )}

      {topo && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-amber-100 bg-amber-50 px-3.5 py-2.5">
          <p className="min-w-0 text-xs leading-relaxed text-amber-900">
            <strong className="font-semibold">{topo.nome}</strong> — {topo.porque}
          </p>
          <Link
            to={topo.rota || "/exams"}
            className="pill btn-sapiens inline-flex min-h-[32px] shrink-0 items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium"
            data-testid="perfil-ir-prioridade"
          >
            Praticar <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      )}
    </Grafico>
  );
}

/** Onde o seu tempo foi parar. Parte-do-todo com poucas fatias, que é a única
 *  coisa que uma pizza faz bem: comparar valores próximos nela é impossível,
 *  e para isso existe o gráfico de barras logo acima. */
export function DistribuicaoDoEsforco({ linhas, destacado }) {
  const todas = medidas(linhas)
    .slice()
    .sort((a, b) => b.respondidas - a.respondidas);
  const principais = todas.slice(0, 5);
  const resto = todas.slice(5);
  const dados = [
    ...principais.map((l) => ({ nome: l.nome, chave: l.chave, valor: l.respondidas, cor: corDa(l.chave) })),
    ...(resto.length
      ? [{
          nome: "Outras matérias",
          chave: "outras",
          valor: resto.reduce((s, l) => s + l.respondidas, 0),
          cor: CINZA,
        }]
      : []),
  ];
  const total = dados.reduce((s, d) => s + d.valor, 0);

  return (
    <Grafico
      id="esforco"
      destacado={destacado}
      olho={<><PieIcon className="h-3.5 w-3.5" /> Divisão do esforço</>}
      titulo="De onde vieram as suas questões"
      explicacao="A fatia é o volume respondido, não o acerto. Serve para ver se o seu tempo está indo para onde a sua nota precisa."
      legenda={dados.map((d) => ({ cor: d.cor, rotulo: d.nome }))}
      altura={230}
      tabela={{
        colunas: ["Matéria", "Questões", "Fatia"],
        linhas: dados.map((d) => [d.nome, d.valor, total ? `${Math.round((100 * d.valor) / total)}%` : "—"]),
      }}
    >
      {total === 0 ? (
        <SemDado>A divisão aparece quando houver matéria medida.</SemDado>
      ) : (
        <ResponsiveContainer>
          <PieChart>
            <Tooltip
              content={
                <Balao
                  titulo={(p) => p.nome}
                  linhas={(p) => [
                    { cor: p.cor, rotulo: "Questões", valor: String(p.valor) },
                    { cor: null, rotulo: "Do total", valor: `${Math.round((100 * p.valor) / total)}%` },
                  ]}
                />
              }
            />
            <Pie
              data={dados}
              dataKey="valor"
              nameKey="nome"
              innerRadius="56%"
              outerRadius="82%"
              // A folga de 2px entre fatias é feita com a cor do fundo: quem
              // separa é o vazio, nunca um contorno desenhado em volta.
              paddingAngle={2}
              stroke="#0a1526"
              strokeWidth={2}
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

/** A mesma pergunta da curva geral, agora por matéria: você melhorou em quê?
 *  Teto de quatro linhas — a quinta em diante o olho não separa, e a resposta
 *  certa para "séries demais" nunca é inventar mais uma cor. */
export function EvolucaoPorFrente({ porFrente, destacado }) {
  const series = (porFrente?.series || []).slice(0, 4);
  const linhas = porFrente?.linhas || [];
  const util = linhas.filter((l) => series.some((s) => l[s.chave] != null));

  return (
    <Grafico
      id="evolucao-frente"
      destacado={destacado}
      olho={<><LineIcon className="h-3.5 w-3.5" /> Semana a semana</>}
      titulo="A sua evolução em cada matéria"
      explicacao="Cada ponto é uma semana em que você respondeu aquela matéria. Semana sem resposta não vira ponto — a linha atravessa, porque não houve queda, houve folga."
      legenda={series.map((s) => ({ cor: corDa(s.chave), rotulo: s.nome }))}
      altura={240}
      tabela={{
        colunas: ["Semana de", ...series.map((s) => s.nome)],
        linhas: util.slice().reverse().map((l) => [
          l.rotulo,
          ...series.map((s) => (l[s.chave] == null ? "—" : `${pct(l[s.chave])} (${l[`${s.chave}__n`]}q)`)),
        ]),
      }}
    >
      {series.length === 0 || util.length < 2 ? (
        <SemDado>
          Duas semanas respondendo a mesma matéria e a linha dela começa aqui — é assim que dá
          para ver se o estudo pegou.
        </SemDado>
      ) : (
        <ResponsiveContainer>
          <LineChart data={util} margin={{ top: 10, right: 12, left: -18, bottom: 0 }}>
            <CartesianGrid stroke={GRADE} vertical={false} />
            <XAxis dataKey="rotulo" {...EIXO} minTickGap={24} />
            <YAxis
              {...EIXO} domain={[0, 100]} ticks={[0, 50, 100]}
              tickFormatter={(v) => `${v}%`} width={46}
            />
            <Tooltip
              cursor={{ stroke: GRADE }}
              content={
                <Balao
                  titulo={(p) => `Semana de ${p.rotulo}`}
                  linhas={(p) =>
                    series
                      .filter((s) => p[s.chave] != null)
                      .map((s) => ({
                        cor: corDa(s.chave),
                        rotulo: s.nome,
                        valor: `${pct(p[s.chave])} · ${p[`${s.chave}__n`]}q`,
                      }))
                  }
                />
              }
            />
            {series.map((s) => (
              <Line
                key={s.chave}
                type="monotone"
                dataKey={s.chave}
                name={s.nome}
                stroke={corDa(s.chave)}
                strokeWidth={2}
                connectNulls
                dot={{ r: 3, strokeWidth: 2, stroke: "#0a1526" }}
                activeDot={{ r: 5, strokeWidth: 2, stroke: "#0a1526" }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </Grafico>
  );
}

/**
 * O QUE SUBIU E O QUE CAIU — o único gráfico da tela que encoda POLARIDADE.
 *
 * Por isso a cor aqui não é a da matéria: azul para quem subiu, vermelho para
 * quem caiu, o zero no meio. Nas outras telas a cor responde "qual matéria";
 * nesta ela responde "para que lado", e misturar as duas perguntas num
 * gráfico só é como se lê a coisa errada com confiança.
 *
 * Só entra matéria com amostra dos DOIS lados da comparação — o servidor já
 * corta (`perfil_painel._tendencia_por_frente`). Sem esse corte, uma matéria
 * com três questões no mês passado e vinte neste apareceria como "queda de 30
 * pontos" que é só o tamanho da amostra mudando.
 */
export function TendenciaPorFrente({ tendencia, semanas = 4, destacado }) {
  const dados = tendencia || [];
  const extremo = Math.max(10, ...dados.map((t) => Math.abs(t.delta)));

  return (
    <Grafico
      id="tendencia"
      destacado={destacado}
      olho={<><ArrowUpDown className="h-3.5 w-3.5" /> Movimento</>}
      titulo="O que subiu e o que caiu"
      explicacao={`Diferença em pontos de acerto entre as suas últimas ${semanas} semanas e as ${semanas} anteriores, matéria por matéria.`}
      legenda={[
        { cor: DIVERGENTE.positivo, rotulo: "Subiu" },
        { cor: DIVERGENTE.negativo, rotulo: "Caiu" },
      ]}
      altura={Math.max(150, dados.length * 40 + 24)}
      tabela={{
        colunas: ["Matéria", "Antes", "Agora", "Diferença"],
        linhas: dados.map((t) => [
          t.nome,
          `${pct(t.antes.taxa)} (${t.antes.respondidas}q)`,
          `${pct(t.agora.taxa)} (${t.agora.respondidas}q)`,
          `${t.delta > 0 ? "+" : ""}${Math.round(t.delta)} pts`,
        ]),
      }}
    >
      {dados.length === 0 ? (
        <SemDado>
          Para comparar dois meses eu preciso de pelo menos cinco questões da mesma matéria em
          cada um deles. Continue praticando e a comparação aparece sozinha.
        </SemDado>
      ) : (
        <ResponsiveContainer>
          <BarChart
            data={dados}
            layout="vertical"
            margin={{ top: 0, right: 40, left: 0, bottom: 0 }}
            barCategoryGap="34%"
          >
            <CartesianGrid stroke={GRADE} horizontal={false} />
            <XAxis type="number" domain={[-extremo, extremo]} hide />
            <YAxis
              type="category" dataKey="nome" {...EIXO}
              width={112} tick={{ fill: TINTA.media, fontSize: 11 }}
            />
            {/* O zero é o eixo real deste gráfico: sem a linha, "subiu 2" e
                "caiu 2" viram duas barrinhas indistinguíveis. */}
            <ReferenceLine x={0} stroke={DIVERGENTE.meio} />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
              content={
                <Balao
                  titulo={(p) => p.nome}
                  linhas={(p) => [
                    { cor: null, rotulo: `${semanas} semanas atrás`, valor: `${pct(p.antes.taxa)} · ${p.antes.respondidas}q` },
                    { cor: null, rotulo: "Agora", valor: `${pct(p.agora.taxa)} · ${p.agora.respondidas}q` },
                    {
                      cor: p.delta > 0 ? DIVERGENTE.positivo : DIVERGENTE.negativo,
                      rotulo: "Diferença",
                      valor: `${p.delta > 0 ? "+" : ""}${Math.round(p.delta)} pts`,
                    },
                  ]}
                />
              }
            />
            <Bar dataKey="delta" name="Diferença" radius={[3, 3, 3, 3]} maxBarSize={18}>
              {dados.map((t) => (
                <Cell key={t.chave} fill={t.delta >= 0 ? DIVERGENTE.positivo : DIVERGENTE.negativo} />
              ))}
              <LabelList
                dataKey="delta"
                position="right"
                formatter={(v) => `${v > 0 ? "+" : ""}${Math.round(v)}`}
                fill={TINTA.forte}
                fontSize={11}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Grafico>
  );
}
