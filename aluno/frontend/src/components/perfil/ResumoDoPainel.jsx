import { Target, CheckCircle2, CalendarCheck, Hourglass, Flame, TrendingUp, TrendingDown } from "lucide-react";
import { SERIES, pct } from "./paleta";

/**
 * A TIRA DE MEDIDAS — cinco números que o aluno lê em um movimento de olho.
 *
 * Um número sozinho não é gráfico: uma barra só, uma pizza de duas fatias e um
 * medidor para um valor único são todos piores do que o número escrito grande.
 * O que um número grande aceita é DUAS companhias, e só duas:
 *
 *  · a **minilinha** dos últimos 14 dias, que dá forma ao número sem eixo,
 *    sem rótulo e sem balão — ela não é para ser lida, é para ser reconhecida;
 *  · a **variação**, quando existe amostra dos dois lados para compará-la. Sem
 *    amostra ela simplesmente não aparece: um "+20 pontos" feito de três
 *    questões contra duas é o tipo de número que anima hoje e desmente
 *    semana que vem.
 *
 * O número grande usa algarismos proporcionais, não tabulares: `tabular-nums`
 * serve para colunas que precisam alinhar (tabela, eixo), e num número de
 * display deixa dígito estreito com folga dos dois lados.
 */

/** A minilinha. SVG cru, 14 barras, sem eixo: em 40px de altura qualquer
 *  biblioteca de gráfico desenharia menos e pesaria mais. */
function Minilinha({ dias }) {
  const valores = (dias || []).map((d) => d.respondidas);
  const teto = Math.max(1, ...valores);
  if (valores.length === 0) return null;
  const largura = 4;
  const folga = 2;
  return (
    <svg
      viewBox={`0 0 ${valores.length * (largura + folga)} 24`}
      className="mt-1.5 h-6 w-full"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {valores.map((v, i) => {
        const altura = v === 0 ? 2 : Math.max(3, Math.round((v / teto) * 22));
        return (
          <rect
            key={i}
            x={i * (largura + folga)}
            y={24 - altura}
            width={largura}
            height={altura}
            rx={1.5}
            fill={SERIES[0]}
            fillOpacity={v === 0 ? 0.18 : 0.55 + 0.45 * (v / teto)}
          />
        );
      })}
    </svg>
  );
}

/** A variação, com ícone e texto — nunca só a cor: verde e vermelho sozinhos
 *  não dizem nada para quem não distingue os dois. */
function Variacao({ delta, sufixo = "pts" }) {
  if (delta == null || delta === 0) return null;
  const subiu = delta > 0;
  const Icone = subiu ? TrendingUp : TrendingDown;
  return (
    <span
      className={`inline-flex items-center gap-1 text-[11px] font-semibold ${
        subiu ? "text-emerald-600" : "text-rose-600"
      }`}
      data-testid="perfil-variacao"
    >
      <Icone className="h-3 w-3" />
      {subiu ? "+" : ""}{Math.round(delta)}{sufixo ? ` ${sufixo}` : ""}
    </span>
  );
}

function Medida({ icone: Icone, olho, valor, unidade, rodape, extra, cor, testid }) {
  return (
    <div className="superficie flex min-h-[6.5rem] flex-col justify-between p-3.5" data-testid={testid}>
      <div className={`secao-olho flex items-center gap-1.5 ${cor || ""}`}>
        <Icone className="h-3 w-3" /> {olho}
      </div>
      <div>
        <div className="mt-2 flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
          <span className="medida-n text-2xl md:text-3xl" style={{ fontVariantNumeric: "proportional-nums" }}>
            {valor}
          </span>
          {unidade && <span className="text-xs text-white/45">{unidade}</span>}
          {extra}
        </div>
        {rodape && <div className="medida-rotulo min-w-0 truncate">{rodape}</div>}
      </div>
    </div>
  );
}

/** `620` -> `"10h20"`. Tempo de estudo em minutos passa de quatro dígitos
 *  rápido, e "1240 min" não quer dizer nada para ninguém. */
function horas(minutos) {
  if (!minutos) return { valor: "—", unidade: null };
  if (minutos < 60) return { valor: String(minutos), unidade: "min" };
  const h = Math.floor(minutos / 60);
  const m = minutos % 60;
  return { valor: m ? `${h}h${String(m).padStart(2, "0")}` : `${h}h`, unidade: null };
}

export default function ResumoDoPainel({ resumo }) {
  const tempo = horas(resumo.tempo_total_minutos);
  const pulso = resumo.pulso || {};
  const deltaVolume =
    pulso.respondidas_7 != null && pulso.respondidas_7_anterior != null
      ? pulso.respondidas_7 - pulso.respondidas_7_anterior
      : null;

  return (
    <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-5" data-testid="perfil-resumo">
      <div className="superficie col-span-2 flex flex-col justify-between p-3.5 lg:col-span-1" data-testid="perfil-resumo-respondidas">
        <div className="secao-olho flex items-center gap-1.5">
          <Target className="h-3 w-3" /> Respondidas
        </div>
        <div>
          <div className="mt-2">
            <span className="medida-n text-2xl md:text-3xl" style={{ fontVariantNumeric: "proportional-nums" }}>
              {resumo.respondidas}
            </span>
          </div>
          <Minilinha dias={pulso.dias} />
          {/* A variação anda colada ao número de que ela fala. Ao lado do
              total de sempre, um "+43 na semana" pareceria dizer que o total
              subiu 43 — e o total não é uma medida que sobe e desce. */}
          <div className="flex items-center gap-2">
            <span className="medida-rotulo truncate">
              {pulso.respondidas_7 != null
                ? `${pulso.respondidas_7} nos últimos 7 dias`
                : "últimos 14 dias"}
            </span>
            <Variacao delta={deltaVolume} sufixo="" />
          </div>
        </div>
      </div>

      <Medida
        icone={CheckCircle2} olho="Acerto" testid="perfil-resumo-taxa"
        valor={pct(resumo.taxa)}
        rodape={
          pulso.delta_taxa != null ? (
            <span className="flex items-center gap-2">
              <span className="truncate">{pct(pulso.taxa_7)} em 7 dias</span>
              <Variacao delta={pulso.delta_taxa} />
            </span>
          ) : (
            `${resumo.acertos} questões certas`
          )
        }
      />
      <Medida
        icone={CalendarCheck} olho="Dias de estudo" testid="perfil-resumo-dias"
        valor={resumo.dias_ativos}
        unidade={resumo.dias_ativos === 1 ? "dia" : "dias"}
        rodape={`melhor sequência: ${resumo.melhor_sequencia}`}
      />
      <Medida
        icone={Flame} olho="Sequência" testid="perfil-resumo-sequencia"
        cor={resumo.sequencia > 0 ? "text-amber-300/85" : ""}
        valor={resumo.sequencia}
        unidade={resumo.sequencia === 1 ? "dia" : "dias"}
        rodape="seguidos, até hoje"
      />
      <Medida
        icone={Hourglass} olho="Tempo medido" testid="perfil-resumo-tempo"
        valor={tempo.valor} unidade={tempo.unidade}
        rodape={
          resumo.tempo_medio_segundos
            ? `${resumo.tempo_medio_segundos}s por questão`
            : "sem tempo registrado"
        }
      />
    </div>
  );
}
