import { useNavigate } from "react-router-dom";
import CardDeMelhora from "./CardDeMelhora";
import { CalendarClock, Repeat, TrendingDown, Shuffle, CircleAlert, Sprout } from "lucide-react";

/**
 * A fila de revisões de hoje — o que a Fase 1 entrega ao aluno.
 *
 * A diferença em relação ao plano antigo (`/plan/:analysisId`) não é visual: é
 * de natureza. Aquele era um snapshot preso a uma análise — lia `study_plan` de
 * um documento velho e o desenhava, sem reagir ao que o aluno demonstrou ontem
 * e sem nenhuma noção de tempo. Esta fila é uma CONSEQUÊNCIA: ela existe porque
 * o aluno respondeu alguma coisa, e muda quando ele responde outra.
 *
 * Anki e Quizlet resolvem espaçamento sem saber POR QUE o aluno errou. Aqui a
 * causa raiz é o que agenda — e é ela que decide o que aparece primeiro.
 *
 * Nada nesta tela mostra ID de catálogo (`ERR-*`, `PROC-*`, `MEC-*`): o aluno
 * lê o nome da habilidade e a linguagem cotidiana da intervenção, nunca a
 * ontologia.
 */

const ESTADOS = {
  em_consolidacao: {
    icone: Sprout,
    rotulo: "Em consolidação",
    explicacao: "Você já trabalhou isto. A revisão de hoje serve para fixar.",
  },
  erro_recorrente: {
    icone: Repeat,
    rotulo: "Erro recorrente",
    explicacao: "Isto voltou a acontecer em dias diferentes — não foi um deslize isolado.",
  },
  em_deterioracao: {
    icone: TrendingDown,
    rotulo: "Em deterioração",
    explicacao: "Você vinha acertando isto e o acerto caiu na sequência mais recente.",
  },
};

function Linha({ icone: Icone, texto, testid }) {
  return (
    <div className="flex items-center gap-2 text-sm text-zinc-600" data-testid={testid}>
      <Icone className="w-3.5 h-3.5 shrink-0 text-sapiens-accentDeep" />
      {texto}
    </div>
  );
}

/** O cabeçalho fechado e curto: "Revisões de hoje · 8 questões" e a composição. */
export function ResumoDaFila({ resumo }) {
  if (!resumo?.questoes) return null;
  const linhas = [
    resumo.em_consolidacao && {
      icone: Sprout,
      texto: `${resumo.em_consolidacao} ${resumo.em_consolidacao === 1 ? "habilidade" : "habilidades"} em consolidação`,
      testid: "fila-resumo-consolidacao",
    },
    resumo.erros_recorrentes && {
      icone: Repeat,
      texto: `${resumo.erros_recorrentes} ${resumo.erros_recorrentes === 1 ? "erro recorrente" : "erros recorrentes"}`,
      testid: "fila-resumo-recorrentes",
    },
    resumo.em_deterioracao && {
      icone: TrendingDown,
      texto: `${resumo.em_deterioracao} ${resumo.em_deterioracao === 1 ? "conceito" : "conceitos"} em deterioração`,
      testid: "fila-resumo-deterioracao",
    },
    resumo.transferencias && {
      icone: Shuffle,
      texto: `${resumo.transferencias} ${resumo.transferencias === 1 ? "transferência recomendada" : "transferências recomendadas"}`,
      testid: "fila-resumo-transferencias",
    },
  ].filter(Boolean);

  return (
    <div className="card-sapiens rounded-2xl p-5" data-testid="fila-resumo">
      <div className="flex items-center gap-2">
        <CalendarClock className="w-4 h-4 text-sapiens-accentDeep" />
        <span className="font-display text-lg font-bold tracking-tight text-zinc-950">
          Revisões de hoje · {resumo.questoes} {resumo.questoes === 1 ? "questão" : "questões"}
        </span>
      </div>
      <div className="mt-3 space-y-1.5">
        {linhas.map((l) => (
          <Linha key={l.testid} {...l} />
        ))}
      </div>
    </div>
  );
}

/** Leva às questões que exercitam ESTE processo, não ao cardápio genérico. */
function hrefDaRevisao(item) {
  const ids = (item.praticar || []).map((p) => p.item_id).filter(Boolean);
  return ids.length ? `/exams?item_ids=${encodeURIComponent(ids.join(","))}` : "/exams";
}

function evidenciaDe(item) {
  if (item.estado === "em_deterioracao" && item.deterioracao) {
    return `de ${item.deterioracao.antes}% para ${item.deterioracao.agora}% de acerto`;
  }
  if (item.recorrencia) {
    return `${item.recorrencia.ocorrencias} vezes, em ${item.recorrencia.dias} dias diferentes`;
  }
  if (item.proximo_reteste) {
    return item.vencido ? "revisão marcada para hoje" : "revisão já marcada";
  }
  return undefined;
}

export default function FilaDeRevisao({ fila, onSaldo }) {
  const nav = useNavigate();
  const itens = fila?.itens || [];

  if (fila?.indisponivel) {
    return (
      <div className="card-sapiens rounded-2xl p-6" data-testid="fila-indisponivel">
        <div className="flex items-start gap-3">
          <CircleAlert className="w-5 h-5 shrink-0 text-amber-600" />
          <p className="text-sm leading-relaxed text-zinc-600">{fila.aviso}</p>
        </div>
      </div>
    );
  }

  if (itens.length === 0) {
    return (
      <div className="card-sapiens rounded-2xl p-6" data-testid="fila-vazia">
        <div className="font-display text-lg font-bold tracking-tight text-zinc-950">
          Nada marcado para hoje.
        </div>
        <p className="mt-2 text-sm leading-relaxed text-zinc-600">
          As revisões nascem do que você erra: quando o Sapiens identifica a causa de um erro, ele
          marca quando voltar a cobrar aquilo. Responda algumas questões e esta fila se monta sozinha.
        </p>
        <button
          onClick={() => nav("/exams")}
          className="pill btn-sapiens mt-4 inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium"
          data-testid="fila-vazia-praticar"
        >
          Praticar questões
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="fila-revisao">
      <ResumoDaFila resumo={fila.resumo} />

      {fila.aviso && (
        // Rótulo de hipótese não é copy — é requisito. Enquanto a anotação das
        // questões não passar por revisão humana, o que esta fila mostra é
        // onde olhar primeiro, não um veredito.
        <div
          className="rounded-2xl border border-amber-100 bg-amber-50 p-4 text-sm leading-relaxed text-amber-800"
          data-testid="fila-aviso-provisorio"
        >
          {fila.aviso}
        </div>
      )}

      <div className="space-y-3">
        {itens.map((item) => {
          const est = ESTADOS[item.estado] || ESTADOS.em_consolidacao;
          const transferencia = item.transferencia;
          return (
            <CardDeMelhora
              key={item.processo_id}
              testid={`fila-item-${item.processo_id}`}
              rotuloTopo={est.rotulo}
              titulo={item.processo_nome}
              descricao={est.explicacao}
              medida={item.vencido ? "hoje" : null}
              medidaLabel={item.vencido ? "revisar" : null}
              assunto={item.processo_nome}
              evidencia={evidenciaDe(item)}
              // O destino principal do card é sempre a prática — a fila só faz
              // sentido se levar a responder questão. Quando o acervo tem
              // questão exata pra este processo, o link já vai carregado
              // com ela; sem isso, cai no cardápio geral.
              treino={{ href: hrefDaRevisao(item), rotulo: "Fazer a revisão" }}
              onSaldo={onSaldo}
            >
              <div className="space-y-3">
                {item.intervencao?.objetivo && (
                  <p className="text-sm leading-relaxed text-zinc-600">{item.intervencao.objetivo}</p>
                )}
                {transferencia && (
                  // Só aparece quando o acervo TEM item do mesmo processo em
                  // outro contexto. Sem isso a linha some — nunca se degrada
                  // para "mais um item igual", que mediria memória do item.
                  <div
                    className="flex items-start gap-2 rounded-xl border border-zinc-200 bg-white/70 p-3"
                    data-testid={`fila-transferencia-${item.processo_id}`}
                  >
                    <Shuffle className="mt-0.5 w-3.5 h-3.5 shrink-0 text-sapiens-accentDeep" />
                    <div className="min-w-0 text-xs leading-relaxed text-zinc-600">
                      <span className="font-semibold text-zinc-700">Transferência: </span>
                      a mesma habilidade cobrada noutro contexto
                      {transferencia.tema ? ` (${transferencia.tema})` : ""} — é o teste que mede a
                      habilidade, e não a memória daquela questão.
                    </div>
                  </div>
                )}
                {item.provisorio && (
                  <div className="font-mono-alt text-[10px] uppercase tracking-wide text-amber-700">
                    leitura provisória
                  </div>
                )}
              </div>
            </CardDeMelhora>
          );
        })}
      </div>
    </div>
  );
}
