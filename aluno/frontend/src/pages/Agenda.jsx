import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  CalendarDays, ChevronLeft, ChevronRight, ChevronDown, Sparkles, Loader2, Check,
  Info, X, RotateCw, BookmarkPlus, Radio, Plus, ArrowRight, SlidersHorizontal,
} from "lucide-react";
import { api, errMsg } from "../lib/api";
import { avisarSparksMudou } from "../components/Navegacao";
import Mentis from "../components/Mentis";
import CronogramaCompromissos from "../components/CronogramaCompromissos";
import EstadoDeErro from "../components/EstadoDeErro";
import FilaDeRevisao from "../components/FilaDeRevisao";
import ListaDeLembretes from "../components/ListaDeLembretes";
import AnelDeProgresso from "../components/AnelDeProgresso";
import SecaoDaAba, { useAncora } from "../components/SecaoDaAba";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { criarPortao } from "../lib/idempotencia";
import { ROTAS, ANCORAS } from "../lib/rotas";
import { proximaQuinta, temAcessoLocal } from "../lib/live";

/**
 * AGENDA — tudo o que tem hora, num lugar só.
 *
 * Pergunta mental: **quando?**
 *
 * ---------------------------------------------------------------------------
 * A ORDEM É A IMPORTÂNCIA (2026-10-19)
 * ---------------------------------------------------------------------------
 *
 * Pedido do dono, com prints do Duolingo: "o site está muito poluído e pouco
 * intuitivo, principalmente a aba agenda. Nessa aba eu quero que o cronograma
 * seja a primeira coisa que o aluno veja (…) tudo que é mais importante
 * precisa estar lá em cima e tudo que for menos importante embaixo". E o
 * progresso evidente no topo, não embaixo.
 *
 * Antes a aba abria com um parágrafo, depois "O seu dia", a fila de
 * revisões, os lembretes, e só na QUARTA seção a semana — numa grade de
 * horas de 760px que no celular rolava de lado, com texto de 10px. Abaixo
 * dela, mais três seções de meta-informação.
 *
 * Agora, de cima para baixo:
 *
 *   1. O CRONOGRAMA, com o progresso da semana no cabeçalho dele (anel +
 *      "N de M blocos") e o próximo bloco a um toque. A aula ao vivo entra
 *      como um item do dia dela — é um compromisso com hora, e é na agenda
 *      que compromisso com hora mora.
 *   2. As REVISÕES que venceram — ação com prazo.
 *   3. O que o aluno GUARDOU para rever.
 *   4. AJUSTAR A SEMANA, fechado: remontar, montar com a Mentis, a ordem de
 *      prioridade, o porquê da distribuição e a importação de compromissos.
 *      É o que se mexe uma vez por semana, não todo dia.
 *
 * O "O seu dia" que abria a aba saiu: era o dia de hoje do cronograma
 * repetido em cima do próprio cronograma.
 *
 * ---------------------------------------------------------------------------
 * A SEMANA COMO QUADRO, NÃO COMO GRADE DE HORAS
 * ---------------------------------------------------------------------------
 *
 * No desktop (lg+): sete colunas, uma por dia, e em cada uma os itens em
 * ordem de horário — compromisso do aluno em linha apagada, bloco de estudo
 * em cartão com o "feito" ao lado. A grade de horas desenhava a DURAÇÃO de
 * cada coisa, que ninguém consulta; o que o aluno consulta é "o que vem e
 * quando", e isso é uma lista.
 *
 * No celular e no tablet: a tira dos sete dias (com o progresso de cada um)
 * e, embaixo, a lista do dia escolhido em cartões grandes. Começa em hoje.
 *
 * Nenhum bloco morre em si mesmo: todo bloco leva à tela onde aquilo é
 * feito. Um cronograma que só informa é uma lista de tarefas; um que abre a
 * tarefa é uma rotina.
 *
 * ---------------------------------------------------------------------------
 * O QUE NÃO MUDOU
 * ---------------------------------------------------------------------------
 *
 * A fila de revisão é INFERIDA (nasceu de um erro que o motor explicou) e os
 * lembretes são DECLARADOS (o aluno marcou) — continuam em seções separadas,
 * porque juntas a segunda lê como uma versão pior da primeira.
 *
 * A ordem das áreas vem de `/api/prioridades` (peso da frente no ENEM x
 * lacuna medida). A faixa que a explica continua existindo, em "Ajustar a
 * semana", para o aluno poder discordar dela.
 *
 * Os preços (montar com a Mentis, remontar) saem do SERVIDOR, em
 * `GET /cronograma`. A tela nunca escreve um número de Sparks.
 */

const DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];
const DIAS_CURTOS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

/** A cor de cada tipo de bloco de estudo: o pontinho antes do horário. A
 *  cor diz o TIPO de trabalho, e o texto diz a matéria. */
const COR_DO_TIPO = {
  revisao: "#FFB547",
  treino: "#A78BFA",
  redacao: "#3DDC97",
  questoes: "#4FD9FF",
  estudo: "#4FD9FF",
};

const ROTULO_TIPO = {
  revisao: "Revisão", treino: "Treino", redacao: "Redação", questoes: "Questões", estudo: "Estudo",
};

const TIPOS_COMPROMISSO = [
  { id: "aula", rotulo: "Aula" },
  { id: "trabalho", rotulo: "Trabalho" },
  { id: "prova", rotulo: "Prova" },
  { id: "pessoal", rotulo: "Pessoal" },
];

function diaLocalISO(data = new Date()) {
  const d = new Date(data.getTime() - data.getTimezoneOffset() * 60000);
  return d.toISOString().slice(0, 10);
}

function deslocarSemana(semanaISO, dias) {
  const base = new Date(`${semanaISO}T12:00:00`);
  base.setDate(base.getDate() + dias);
  return diaLocalISO(base);
}

function rotuloDaSemana(semanaISO) {
  try {
    const inicio = new Date(`${semanaISO}T12:00:00`);
    const fim = new Date(inicio);
    fim.setDate(fim.getDate() + 6);
    const f = (d) => d.toLocaleDateString("pt-BR", { day: "numeric", month: "short" }).replace(".", "");
    return `${f(inicio)} – ${f(fim)}`;
  } catch {
    return semanaISO;
  }
}

function hhmmDoMin(min) {
  const h = Math.floor(min / 60), m = min % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function hhmmDaData(d) {
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/**
 * Os itens de um dia, numa lista só e em ordem de horário: compromissos do
 * aluno, blocos de estudo e — se for o dia dela — a aula ao vivo. O dia
 * inteiro vem primeiro.
 */
function itensDoDia(dia, live) {
  const itens = [
    ...dia.compromissos.map((c) => ({ tipo: "compromisso", chave: `c-${c.id}`, inicio: c.dia_inteiro ? "" : c.inicio, dado: c })),
    ...dia.blocos.map((b) => ({ tipo: "bloco", chave: `b-${b.id}`, inicio: b.inicio, dado: b })),
  ];
  if (live && live.edicao === dia.data) {
    itens.push({ tipo: "live", chave: "live", inicio: hhmmDaData(live.inicio), dado: live });
  }
  return itens.sort((a, b) => a.inicio.localeCompare(b.inicio));
}

/** O bloco de estudo. O cartão inteiro abre a tarefa; o círculo à esquerda
 *  marca feito sem sair da tela (um toque, otimista). */
function CartaoDoBloco({ bloco, onConcluir, salvando, compacto = false }) {
  const nav = useNavigate();
  const cor = COR_DO_TIPO[bloco.tipo] || COR_DO_TIPO.questoes;
  return (
    <div
      role="link"
      tabIndex={0}
      onClick={() => nav(bloco.rota || ROTAS.ESTUDAR)}
      onKeyDown={(e) => { if (e.key === "Enter") nav(bloco.rota || ROTAS.ESTUDAR); }}
      className={`superficie lift group flex cursor-pointer items-start gap-2.5 overflow-hidden rounded-2xl ${
        compacto ? "p-2.5" : "p-4"
      } ${bloco.concluido ? "opacity-60" : ""}`}
      data-testid={`agenda-bloco-${bloco.id}`}
    >
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onConcluir(bloco); }}
        disabled={salvando}
        aria-label={bloco.concluido ? "Desmarcar como feito" : "Marcar como feito"}
        aria-pressed={bloco.concluido}
        className={`relative flex shrink-0 items-center justify-center rounded-full border-2 transition before:absolute before:-inset-2 before:content-[''] ${
          compacto ? "ml-1 h-5 w-5" : "ml-1 h-7 w-7"
        } ${bloco.concluido ? "border-[#3DDC97] bg-[#3DDC97] text-[#06281A]" : "border-[#4A6596] text-transparent hover:border-[#3DDC97]"}`}
        data-testid={`agenda-bloco-feito-${bloco.id}`}
      >
        <Check className={compacto ? "h-3 w-3" : "h-4 w-4"} strokeWidth={3.5} />
      </button>
      <div className="min-w-0 flex-1">
        <div className={`flex items-center gap-1.5 font-mono-alt text-white/60 ${compacto ? "text-[11px]" : "text-xs"}`}>
          <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: cor }} aria-hidden="true" />
          {bloco.inicio}
          {!compacto && `–${bloco.fim}`}
          {!compacto && <span style={{ color: cor }}>· {ROTULO_TIPO[bloco.tipo] || bloco.tipo}</span>}
        </div>
        <p
          className={`font-extrabold leading-snug text-white ${compacto ? "line-clamp-3 text-[13px]" : "text-base"} ${
            bloco.concluido ? "line-through decoration-2" : ""
          }`}
        >
          {bloco.frente_nome || bloco.titulo}
        </p>
        {!compacto && bloco.frente_nome && bloco.titulo !== bloco.frente_nome && (
          <p className="mt-0.5 truncate text-sm text-white/60">{bloco.titulo}</p>
        )}
      </div>
      {!compacto && !bloco.concluido && (
        <ArrowRight className="mt-1 h-5 w-5 shrink-0 text-white/40 transition group-hover:text-white" />
      )}
    </div>
  );
}

/** Compromisso do aluno: aula, trabalho, prova. Ele já existe na vida dele —
 *  então aparece apagado, sem caixa de feito. O X o apaga ali mesmo. */
function LinhaDoCompromisso({ compromisso: c, onApagar, compacto = false }) {
  return (
    <div
      className={`group relative flex items-start gap-2 rounded-xl border-2 border-dashed border-[#2B3F60] ${
        compacto ? "px-2.5 py-2" : "px-4 py-3"
      }`}
      data-testid={`agenda-compromisso-${c.id}`}
    >
      <div className="min-w-0 flex-1">
        <div className={`font-mono-alt text-white/50 ${compacto ? "text-[11px]" : "text-xs"}`}>
          {c.dia_inteiro ? "Dia todo" : compacto ? c.inicio : `${c.inicio}–${c.fim}`}
        </div>
        <p className={`font-bold leading-snug text-white/75 ${compacto ? "line-clamp-2 text-[13px]" : "text-[15px]"}`}>
          {c.titulo}
        </p>
      </div>
      <button
        type="button"
        onClick={() => onApagar(c.id)}
        aria-label={`Apagar ${c.titulo}`}
        className="-m-1.5 shrink-0 rounded-full p-1.5 text-white/40 opacity-100 transition hover:bg-white/10 hover:text-white lg:opacity-0 lg:group-hover:opacity-100"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

/** A aula de quinta como item do dia dela: o único compromisso com hora que
 *  o aluno não agendou. Âmbar, porque é um evento que não se repõe. */
function ItemDaLive({ live, compacto = false }) {
  return (
    <Link
      to={ROTAS.AULA_AO_VIVO}
      className={`block rounded-xl border-2 border-[#FFB547]/60 bg-[#FFB547]/10 transition hover:bg-[#FFB547]/15 ${
        compacto ? "px-2.5 py-2" : "px-4 py-3"
      }`}
      data-testid="agenda-live"
    >
      <div className={`flex items-center gap-1.5 font-mono-alt text-[#FFB547] ${compacto ? "text-[11px]" : "text-xs"}`}>
        {live.aoVivoAgora ? (
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#FF6B81] opacity-80" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-[#FF6B81]" />
          </span>
        ) : (
          <Radio className="h-3 w-3" />
        )}
        {live.aoVivoAgora ? "Agora" : hhmmDaData(live.inicio)}
      </div>
      <p className={`font-extrabold leading-snug text-[#FFE2B0] ${compacto ? "text-[13px]" : "text-[15px]"}`}>
        Aula ao vivo{compacto ? "" : " com Vitor Lara"}
      </p>
      {!compacto && temAcessoLocal(live.edicao) && (
        <p className="text-xs text-white/60">Você já tem esta edição.</p>
      )}
    </Link>
  );
}

function Item({ item, onConcluirBloco, salvandoBloco, onApagarCompromisso, compacto }) {
  if (item.tipo === "bloco") {
    return <CartaoDoBloco bloco={item.dado} onConcluir={onConcluirBloco} salvando={salvandoBloco} compacto={compacto} />;
  }
  if (item.tipo === "live") return <ItemDaLive live={item.dado} compacto={compacto} />;
  return <LinhaDoCompromisso compromisso={item.dado} onApagar={onApagarCompromisso} compacto={compacto} />;
}

/** Os pontinhos de um dia: um por bloco, cheio quando feito. Desenham o
 *  progresso do dia sem número nenhum para ler. */
function PontosDoDia({ blocos }) {
  if (!blocos.length) return <span className="h-1.5" />;
  return (
    <span className="flex items-center justify-center gap-1">
      {blocos.slice(0, 4).map((b) => (
        <span
          key={b.id}
          className={`h-1.5 w-1.5 rounded-full ${b.concluido ? "bg-[#3DDC97]" : "bg-[#4A6596]"}`}
        />
      ))}
    </span>
  );
}

/**
 * O QUADRO DA SEMANA (lg+): sete colunas, uma por dia. Hoje com o número
 * aceso, como numa folhinha. O "+" no pé de cada coluna anota um compromisso
 * naquele dia.
 */
function QuadroDaSemana({ dias, hojeISO, live, onConcluirBloco, salvandoBloco, onApagarCompromisso, onNovo }) {
  return (
    <div className="hidden grid-cols-7 gap-2 lg:grid" data-testid="agenda-quadro">
      {dias.map((dia) => {
        const eHoje = dia.data === hojeISO;
        const itens = itensDoDia(dia, live);
        return (
          <div
            key={dia.data}
            className={`flex min-w-0 flex-col gap-2 rounded-2xl p-1.5 ${eHoje ? "bg-[#4FD9FF]/[0.06] ring-2 ring-[#4FD9FF]/40" : ""}`}
            data-testid={`agenda-dia-${dia.indice}`}
          >
            <div className="flex flex-col items-center gap-1 pb-1 pt-1.5">
              <span className={`text-xs font-extrabold uppercase tracking-wider ${eHoje ? "text-[#4FD9FF]" : "text-white/55"}`}>
                {DIAS_CURTOS[dia.indice]}
              </span>
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-full text-base font-black ${
                  eHoje ? "bg-[#4FD9FF] text-[#062033]" : "text-white"
                }`}
              >
                {Number(dia.data.slice(8, 10))}
              </span>
              <PontosDoDia blocos={dia.blocos} />
            </div>
            {itens.map((item) => (
              <Item
                key={item.chave}
                item={item}
                onConcluirBloco={onConcluirBloco}
                salvandoBloco={salvandoBloco}
                onApagarCompromisso={onApagarCompromisso}
                compacto
              />
            ))}
            <button
              type="button"
              onClick={() => onNovo(dia)}
              className="mt-auto flex h-9 items-center justify-center rounded-xl text-white/35 transition hover:bg-white/5 hover:text-white"
              aria-label={`Anotar compromisso em ${DIAS[dia.indice]}`}
              data-testid={`agenda-novo-${dia.indice}`}
            >
              <Plus className="h-4 w-4" strokeWidth={3} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

/**
 * A SEMANA NO CELULAR (< lg): a tira dos sete dias e a lista do dia
 * escolhido, em cartões grandes. Começa em hoje (ou na segunda, se a semana
 * mostrada não é a atual).
 */
function DiaNoCelular({ dias, hojeISO, live, diaEscolhido, onEscolher, onConcluirBloco, salvandoBloco, onApagarCompromisso, onNovo }) {
  const dia = dias.find((d) => d.data === diaEscolhido) || dias[0];
  const itens = dia ? itensDoDia(dia, live) : [];
  return (
    <div className="lg:hidden">
      <div className="grid grid-cols-7 gap-1" role="tablist" aria-label="Dias da semana">
        {dias.map((d) => {
          const eHoje = d.data === hojeISO;
          const escolhido = d.data === dia?.data;
          return (
            <button
              key={d.data}
              type="button"
              role="tab"
              aria-selected={escolhido}
              onClick={() => onEscolher(d.data)}
              className={`flex flex-col items-center gap-1 rounded-2xl border-2 py-2 transition ${
                escolhido ? "border-[#4FD9FF] bg-[#4FD9FF]/10" : "border-transparent"
              }`}
              data-testid={`agenda-tira-${d.indice}`}
            >
              <span className={`text-[11px] font-extrabold uppercase ${eHoje ? "text-[#4FD9FF]" : "text-white/55"}`}>
                {DIAS_CURTOS[d.indice]}
              </span>
              <span
                className={`flex h-7 w-7 items-center justify-center rounded-full text-sm font-black ${
                  eHoje ? "bg-[#4FD9FF] text-[#062033]" : "text-white"
                }`}
              >
                {Number(d.data.slice(8, 10))}
              </span>
              <PontosDoDia blocos={d.blocos} />
            </button>
          );
        })}
      </div>

      <div className="mt-4 space-y-2.5" data-testid="agenda-lista-do-dia">
        {itens.length === 0 ? (
          <p className="rounded-2xl border-2 border-dashed border-[#2B3F60] px-4 py-6 text-center text-sm text-white/55">
            Nada marcado {dia?.data === hojeISO ? "para hoje" : `na ${DIAS[dia?.indice ?? 0].toLowerCase()}`}.
          </p>
        ) : (
          itens.map((item) => (
            <Item
              key={item.chave}
              item={item}
              onConcluirBloco={onConcluirBloco}
              salvandoBloco={salvandoBloco}
              onApagarCompromisso={onApagarCompromisso}
            />
          ))
        )}
        <button
          type="button"
          onClick={() => dia && onNovo(dia)}
          className="pill btn-vidro flex w-full items-center justify-center gap-2 px-4 py-3 text-sm"
          data-testid="agenda-novo-celular"
        >
          <Plus className="h-4 w-4" strokeWidth={3} /> Anotar compromisso
        </button>
      </div>
    </div>
  );
}

/** A faixa que explica a ordem. Sem ela, o cronograma é uma ordem sem motivo. */
function FaixaDePrioridade({ prioridades }) {
  const topo = (prioridades || []).slice(0, 4);
  if (!topo.length) return null;
  return (
    <div data-testid="agenda-prioridades">
      <h3 className="secao-olho">O que mais rende ponto</h3>
      <p className="mt-1 text-sm text-white/60">
        Peso de cada frente no ENEM cruzado com o que já foi medido em você. É esta ordem que
        decide quantos blocos cada área ganha.
      </p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {topo.map((p, i) => (
          <Link
            key={p.chave}
            to={p.rota}
            className="superficie lift rounded-2xl p-4"
            data-testid={`agenda-prioridade-${p.chave}`}
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-display text-base font-extrabold text-white">
                {i + 1}. {p.nome}
              </span>
              <span className="font-mono-alt text-xs text-white/55">
                {p.estado === "sem_medida"
                  ? "sem medida"
                  : p.chave === "redacao"
                    ? `${p.nota ?? "—"}/1000`
                    : `${p.taxa_acerto}%`}
              </span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-white/60">{p.porque}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function Agenda() {
  const [semanaISO, setSemanaISO] = useState(() => diaLocalISO());
  const [dados, setDados] = useState(null);
  const [prioridades, setPrioridades] = useState([]);
  // A fila de revisão, que era a tela `/revisoes`. Uma leitura, independente
  // de quantas questões o aluno já respondeu — ver `custo-de-leitura.md`.
  const [fila, setFila] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [gerando, setGerando] = useState(null);
  // `null` | "gratis" | "mentis" — qual montagem está esperando confirmação.
  // Só abre quando a ação CUSTA: montar a primeira semana de graça não pede
  // permissão para gastar nada.
  const [confirmando, setConfirmando] = useState(null);
  const [salvandoBloco, setSalvandoBloco] = useState(false);
  const [, setSaldo] = useState(null);
  // O "+" de um dia abre isto: {dia, data, inicio, fim}.
  const [novoCompromisso, setNovoCompromisso] = useState(null);
  const [tituloNovo, setTituloNovo] = useState("");
  const [tipoNovo, setTipoNovo] = useState("aula");
  const [salvandoNovo, setSalvandoNovo] = useState(false);
  // O dia aberto na lista do celular. Começa em hoje.
  const [diaEscolhido, setDiaEscolhido] = useState(() => diaLocalISO());

  useDeclararContextoMentis("Na Agenda, vendo o cronograma da semana e o que precisa revisar.");

  const carregar = useCallback(async (semana) => {
    setCarregando(true);
    setErro(null);
    try {
      // As três numa chamada paralela só: a fila e as prioridades são
      // contexto, e buscá-las depois faria as seções nascerem vazias e pular.
      const [semanaResp, prioridadesResp, filaResp] = await Promise.allSettled([
        api.get("/cronograma", { params: { semana } }),
        api.get("/prioridades"),
        api.get("/revisao/fila"),
      ]);
      if (semanaResp.status === "rejected") throw semanaResp.reason;
      setDados(semanaResp.value.data);
      setSemanaISO(semanaResp.value.data.semana);
      // As prioridades são contexto, não a tela: se elas falharem, o
      // cronograma ainda é a coisa que o aluno veio ver.
      if (prioridadesResp.status === "fulfilled") {
        setPrioridades(prioridadesResp.value.data.prioridades || []);
      }
      // `null` faz a seção dizer que não conseguiu ler, e não "você não tem
      // nada para revisar" — que seria mentira num dia de rede ruim.
      setFila(filaResp.status === "fulfilled" ? filaResp.value.data : null);
    } catch (e) {
      setErro(errMsg(e, "Não consegui abrir o seu cronograma agora."));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => { carregar(undefined); }, [carregar]);

  // A trava do duplo toque. A `ref` barra a segunda chamada no mesmo instante
  // (o `setGerando` só vale depois da re-renderização), e a CHAVE só é trocada
  // quando a montagem termina — uma nova tentativa depois de um erro de rede é
  // o mesmo pedido (ver `cronograma_routes._reivindicar_montagem`).
  const portao = useRef(criarPortao("cron"));

  const gerar = async (comMentis) => {
    if (!portao.current.entrar()) return;
    setConfirmando(null);
    setGerando(comMentis ? "mentis" : "gratis");
    try {
      const { data } = await api.post("/cronograma/gerar", {
        semana: semanaISO,
        com_mentis: comMentis,
        idempotency_key: portao.current.chave,
      });
      portao.current.concluir();
      setDados(data.semana);
      if (data.prioridades) setPrioridades(data.prioridades);
      if (typeof data.sparks_balance === "number") setSaldo(data.sparks_balance);
      // O saldo mudou: a barra precisa saber, senão o chip de Sparks continua
      // mostrando o número de antes da cobrança.
      if (data.cobrado) avisarSparksMudou();
      if (data.aviso) toast.warning(data.aviso);
      else if (data.sem_horario_livre) toast.info("Não sobrou horário livre. Ajuste a janela de estudo.");
      else toast.success(data.cobrado ? `Semana montada · ${data.cobrado} Sparks` : "Semana montada.");
    } catch (e) {
      toast.error(errMsg(e, "Não consegui montar a sua semana agora."));
    } finally {
      portao.current.sair();
      setGerando(null);
    }
  };

  const concluir = async (bloco) => {
    setSalvandoBloco(true);
    // Otimista: marcar um bloco feito precisa responder no dedo, e o pior caso
    // de errar é um check que volta sozinho — nada é perdido.
    setDados((d) => ({
      ...d,
      total_concluidos: (d.total_concluidos || 0) + (bloco.concluido ? -1 : 1),
      dias: d.dias.map((dia) => ({
        ...dia,
        blocos: dia.blocos.map((b) => (b.id === bloco.id ? { ...b, concluido: !b.concluido } : b)),
      })),
    }));
    try {
      await api.post(`/cronograma/bloco/${bloco.id}/concluir`, {
        concluido: !bloco.concluido, semana: semanaISO,
      });
    } catch (e) {
      toast.error(errMsg(e, "Não consegui salvar."));
      carregar(semanaISO);
    } finally {
      setSalvandoBloco(false);
    }
  };

  const abrirNovo = (dia) => {
    // Sem horário clicado (não há grade de horas): a sugestão é a próxima
    // meia hora cheia se o dia é hoje, e 14h nos outros dias.
    const agora = new Date();
    const base = dia.data === diaLocalISO()
      ? Math.min(22 * 60, Math.ceil((agora.getHours() * 60 + agora.getMinutes()) / 30) * 30)
      : 14 * 60;
    setNovoCompromisso({ dia: dia.indice, data: dia.data, inicio: hhmmDoMin(base), fim: hhmmDoMin(base + 60) });
    setTituloNovo("");
    setTipoNovo("aula");
  };

  const salvarNovo = async () => {
    if (!tituloNovo.trim() || salvandoNovo) return;
    setSalvandoNovo(true);
    try {
      await api.post("/cronograma/compromisso", {
        titulo: tituloNovo.trim(), tipo: tipoNovo,
        inicio: novoCompromisso.inicio, fim: novoCompromisso.fim,
        data: novoCompromisso.data,
      });
      setNovoCompromisso(null);
      toast.success("Compromisso anotado.");
      carregar(semanaISO);
    } catch (e) {
      toast.error(errMsg(e, "Não consegui salvar esse compromisso."));
    } finally {
      setSalvandoNovo(false);
    }
  };

  const apagarCompromisso = async (id) => {
    try {
      await api.delete(`/cronograma/compromisso/${id}`);
      carregar(semanaISO);
    } catch (e) {
      toast.error(errMsg(e, "Não consegui apagar."));
    }
  };

  const irPara = (dias) => {
    const alvo = deslocarSemana(semanaISO, dias);
    setSemanaISO(alvo);
    // A lista do celular abre a semana nova pela segunda-feira dela, ou por
    // hoje se a semana nova é a atual.
    const hoje = diaLocalISO();
    const segunda = deslocarSemana(alvo, 0);
    setDiaEscolhido(hoje >= segunda && hoje <= deslocarSemana(segunda, 6) ? hoje : segunda);
    carregar(alvo);
  };

  const compromissos = useMemo(
    () => (dados?.dias || []).flatMap((d) => d.compromissos),
    [dados]
  );
  const hojeISO = diaLocalISO();
  const plano = dados?.plano;
  const temPlano = Boolean(plano?.desta_semana && dados?.total_blocos > 0);
  const total = dados?.total_blocos || 0;
  const feitos = dados?.total_concluidos || 0;
  const pct = total ? Math.round((feitos / total) * 100) : 0;

  // Remontar só custa quando há o que remontar — espelha o servidor
  // (`gerar_cronograma`): semana com plano E com bloco.
  const custoRemontar = temPlano ? (dados?.custo_remontagem ?? 0) : 0;
  const custoDaConfirmacao = confirmando === "mentis" ? (dados?.custo_mentis ?? 0) : custoRemontar;

  // O PRÓXIMO BLOCO: o primeiro não feito de hoje em diante, nesta semana. É
  // a única ação acesa do topo da aba.
  const proximo = useMemo(() => {
    for (const dia of dados?.dias || []) {
      if (dia.data < hojeISO) continue;
      const b = dia.blocos.find((x) => !x.concluido);
      if (b) return { bloco: b, dia };
    }
    return null;
  }, [dados, hojeISO]);

  const vencidas = fila?.resumo?.questoes ?? 0;
  const filaVazia = fila && !fila.indisponivel && !(fila.itens || []).length;

  // A aula ao vivo: calculada no navegador (`lib/live.js`), de graça — a
  // Agenda recusa uma leitura de `/cursos` só para anunciá-la.
  const live = proximaQuinta();

  useAncora(carregando);

  const montar = () => (custoRemontar ? setConfirmando("gratis") : gerar(false));

  return (
    <div className="min-h-screen">
      <div className="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-9">
        {/* ─── CABEÇALHO: o nome da aba e a semana. Nada mais. ─────────── */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="titulo-tela">Agenda</h1>
          <div className="flex items-center gap-1">
            <button
              type="button" onClick={() => irPara(-7)}
              className="chip !h-10 !w-10 justify-center !p-0"
              aria-label="Semana anterior" data-testid="agenda-semana-anterior"
            >
              <ChevronLeft className="h-5 w-5" strokeWidth={2.6} />
            </button>
            <span className="min-w-[8.5rem] text-center text-sm font-extrabold text-white" data-testid="agenda-rotulo-semana">
              {rotuloDaSemana(semanaISO)}
            </span>
            <button
              type="button" onClick={() => irPara(7)}
              className="chip !h-10 !w-10 justify-center !p-0"
              aria-label="Próxima semana" data-testid="agenda-semana-proxima"
            >
              <ChevronRight className="h-5 w-5" strokeWidth={2.6} />
            </button>
          </div>
        </div>

        {erro && (
          <div className="mt-6">
            <EstadoDeErro mensagem={erro} aoTentarNovamente={() => carregar(semanaISO)} />
          </div>
        )}

        {carregando && !dados ? (
          <div className="mt-8 flex items-center gap-2 text-sm text-white/60">
            <Loader2 className="h-4 w-4 animate-spin" /> Abrindo a sua agenda…
          </div>
        ) : dados ? (
          <div className="mt-6 space-y-12">
            {/* ─── 1. O CRONOGRAMA, com o progresso no topo dele ──────────── */}
            <section
              id={ANCORAS.AGENDA_SEMANA}
              className="card-sapiens scroll-mt-24 rounded-3xl p-4 md:p-6"
              data-testid="agenda-cronograma"
              aria-label="Cronograma da semana"
            >
              {temPlano ? (
                <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex min-w-0 items-center gap-4">
                    <AnelDeProgresso valor={pct} tamanho={64} espessura={7} cor="#3DDC97" testid="agenda-anel">
                      <span className="font-mono-alt text-sm text-white">{pct}%</span>
                    </AnelDeProgresso>
                    <div className="min-w-0">
                      <p className="secao-olho">Sua semana</p>
                      <p className="text-xl font-black leading-tight text-white" data-testid="agenda-progresso">
                        {feitos} de {total} blocos feitos
                      </p>
                      <div className="barra mt-2 w-48 max-w-full" data-cor="verde" data-cheia={pct >= 100}>
                        <i style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  </div>
                  {proximo && (
                    <Link
                      to={proximo.bloco.rota || ROTAS.ESTUDAR}
                      className="pill btn-sapiens btn-grande inline-flex w-full items-center justify-center gap-3 sm:w-auto"
                      data-testid="agenda-proximo"
                    >
                      <span className="min-w-0 text-left">
                        <span className="block">Começar</span>
                        <span className="block truncate text-xs font-bold normal-case tracking-normal opacity-80">
                          {proximo.bloco.frente_nome || ROTULO_TIPO[proximo.bloco.tipo] || "Estudar"}
                          {" · "}
                          {proximo.dia.data === hojeISO ? proximo.bloco.inicio : `${DIAS[proximo.dia.indice].toLowerCase()}, ${proximo.bloco.inicio}`}
                        </span>
                      </span>
                      <ArrowRight className="h-5 w-5 shrink-0" strokeWidth={3} />
                    </Link>
                  )}
                </div>
              ) : (
                /* Sem plano, a coisa mais importante é a AÇÃO de montar — a
                   semana vazia vem logo embaixo, com os compromissos que já
                   existem. Montar a primeira é de graça e o botão diz. */
                <div className="mb-5 flex flex-col gap-4 rounded-2xl bg-white/[0.03] p-4 sm:flex-row sm:items-center sm:justify-between" data-testid="agenda-montar">
                  <div className="flex min-w-0 items-start gap-3">
                    <Mentis className="h-11 w-11 shrink-0" estado={gerando ? "analise" : "neutra"} />
                    <div className="min-w-0">
                      <p className="text-lg font-black leading-snug text-white" data-testid="agenda-resumo">
                        {plano && !plano.desta_semana ? "Monte o cronograma desta semana" : "Sua semana ainda não tem cronograma"}
                      </p>
                      <p className="mt-0.5 text-sm text-white/60">
                        {plano && !plano.desta_semana
                          ? "O último é de outra semana — as suas revisões e os seus pontos fracos mudaram desde lá."
                          : "Eu monto nos seus horários livres, com Matemática e Redação na frente."}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={montar}
                    disabled={Boolean(gerando)}
                    className="pill btn-sapiens inline-flex w-full shrink-0 items-center justify-center gap-2 px-5 py-3 text-[15px] disabled:opacity-60 sm:w-auto"
                    data-testid="agenda-gerar"
                  >
                    {gerando === "gratis" ? <Loader2 className="h-4 w-4 animate-spin" /> : <CalendarDays className="h-4 w-4" strokeWidth={2.6} />}
                    Montar minha semana
                    {custoRemontar ? ` · ${custoRemontar} Sparks` : " · grátis"}
                  </button>
                </div>
              )}

              <QuadroDaSemana
                dias={dados.dias}
                hojeISO={hojeISO}
                live={live}
                onConcluirBloco={concluir}
                salvandoBloco={salvandoBloco}
                onApagarCompromisso={apagarCompromisso}
                onNovo={abrirNovo}
              />
              <DiaNoCelular
                dias={dados.dias}
                hojeISO={hojeISO}
                live={live}
                diaEscolhido={diaEscolhido}
                onEscolher={setDiaEscolhido}
                onConcluirBloco={concluir}
                salvandoBloco={salvandoBloco}
                onApagarCompromisso={apagarCompromisso}
                onNovo={abrirNovo}
              />
            </section>

            {/* ─── 2. REVISÕES ──────────────────────────────────────────── */}
            {/* Era a tela `/revisoes`. A fila é INFERIDA: cada linha nasceu de
                um erro que o motor conseguiu explicar. Vazia, ela vira uma
                linha — um cartão grande para dizer "nada" era ruído. */}
            <SecaoDaAba
              id={ANCORAS.AGENDA_REVISOES}
              icone={RotateCw}
              titulo="Revisões"
              descricao={vencidas > 0 ? `${vencidas === 1 ? "1 questão voltou" : `${vencidas} questões voltaram`} para revisão. Revisar no dia em que vence é o que faz a memória durar.` : null}
            >
              {fila == null ? (
                <p className="text-sm text-white/60">
                  Não consegui ler a sua fila de revisões agora.{" "}
                  <button
                    type="button"
                    onClick={() => carregar(semanaISO)}
                    className="font-extrabold text-[#4FD9FF] hover:underline"
                  >
                    Tentar de novo
                  </button>
                </p>
              ) : filaVazia ? (
                <p className="rounded-2xl border-2 border-dashed border-[#2B3F60] px-4 py-4 text-sm text-white/60" data-testid="fila-vazia">
                  Nada para revisar hoje. A fila se monta sozinha a partir dos seus erros.
                </p>
              ) : (
                <FilaDeRevisao fila={fila} />
              )}
            </SecaoDaAba>

            {/* ─── 3. LEMBRETES ─────────────────────────────────────────── */}
            {/* A outra fila, e ela precisa PARECER diferente: esta é declarada
                pelo aluno ("isto eu ainda não domino"), aquela é inferida. */}
            <SecaoDaAba
              id={ANCORAS.AGENDA_LEMBRETES}
              icone={BookmarkPlus}
              titulo="Guardado para rever"
              descricao={'O que você separou com "Lembrar-me com a Mentis".'}
            >
              <ListaDeLembretes />
            </SecaoDaAba>

            {/* ─── 4. AJUSTAR A SEMANA — fechado ────────────────────────── */}
            {/* O que se mexe uma vez por semana: remontar, montar com a Mentis,
                a ordem de prioridade, o porquê da distribuição e a importação
                de compromissos. Fechado por padrão para não disputar a tela
                com o que se usa todo dia. */}
            <details
              id={ANCORAS.AGENDA_PRIORIDADES}
              className="group superficie scroll-mt-24 rounded-3xl"
              data-testid="agenda-ajustes"
            >
              <summary className="flex cursor-pointer list-none items-center gap-3 p-5 [&::-webkit-details-marker]:hidden">
                <SlidersHorizontal className="h-5 w-5 shrink-0 text-white/60" strokeWidth={2.4} />
                <span className="min-w-0 flex-1">
                  <span className="block text-lg font-black text-white">Ajustar a semana</span>
                  <span className="block text-sm text-white/60">Remontar, montar com a Mentis, prioridades e compromissos fixos.</span>
                </span>
                <ChevronDown className="h-5 w-5 shrink-0 text-white/50 transition group-open:rotate-180" strokeWidth={2.6} />
              </summary>

              <div className="space-y-8 border-t-2 border-[#24365A] p-5">
                {temPlano && plano.resumo && (
                  <div className="flex items-start gap-3">
                    <Mentis className="h-9 w-9 shrink-0" estado={gerando ? "analise" : "neutra"} />
                    <div>
                      <p className="text-sm leading-relaxed text-white">{plano.resumo}</p>
                      {plano.recado && <p className="mt-1.5 text-xs leading-relaxed text-white/60">{plano.recado}</p>}
                    </div>
                  </div>
                )}

                {/* Os dois preços saem do SERVIDOR (`custo_remontagem` e
                    `custo_mentis` em `GET /cronograma`). */}
                <div className="flex flex-col gap-2 sm:flex-row">
                  {temPlano && (
                    <button
                      type="button"
                      onClick={montar}
                      disabled={Boolean(gerando)}
                      className="pill btn-vidro inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm disabled:opacity-60"
                      data-testid="agenda-remontar"
                    >
                      {gerando === "gratis" ? <Loader2 className="h-4 w-4 animate-spin" /> : <CalendarDays className="h-4 w-4" />}
                      Remontar · {custoRemontar ? `${custoRemontar} Sparks` : "grátis"}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setConfirmando("mentis")}
                    disabled={Boolean(gerando)}
                    className="pill btn-contorno inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm disabled:opacity-60"
                    data-testid="agenda-gerar-mentis"
                  >
                    {gerando === "mentis" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    Montar com a Mentis · {dados.custo_mentis} Sparks
                  </button>
                </div>

                <FaixaDePrioridade prioridades={prioridades} />

                {temPlano && plano.distribuicao?.length > 0 && (
                  <div data-testid="agenda-distribuicao">
                    <h3 className="secao-olho">Por que a semana ficou assim</h3>
                    <div className="mt-3 space-y-2.5">
                      {plano.distribuicao.map((d) => (
                        <div key={d.chave} className="flex items-start gap-3">
                          <span className="chip shrink-0 !px-2.5 !py-1 font-mono-alt text-xs">{d.blocos}×</span>
                          <p className="text-sm leading-relaxed text-white/60">
                            <span className="font-extrabold text-white">{d.nome}</span> — {d.porque}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div id={ANCORAS.AGENDA_EVENTOS}>
                  <h3 className="secao-olho mb-3 flex items-center gap-1.5">
                    <Info className="h-3.5 w-3.5" /> Compromissos fixos
                  </h3>
                  <CronogramaCompromissos
                    semana={semanaISO}
                    compromissos={compromissos}
                    preferencias={dados.preferencias}
                    custoTexto={dados.custo_texto}
                    onSemana={(nova) => { setDados(nova); setSemanaISO(nova.semana); }}
                    onSaldo={setSaldo}
                  />
                </div>
              </div>
            </details>
          </div>
        ) : null}
      </div>

      {/* A cobrança, dita ANTES de acontecer — mesma regra da redação e da
          loja. O diálogo só abre quando a ação custa alguma coisa. */}
      <Dialog open={Boolean(confirmando)} onOpenChange={(v) => !v && setConfirmando(null)}>
        <DialogContent className="rounded-2xl" data-testid="agenda-confirmar">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl font-black">
              {confirmando === "mentis" ? "Montar com a Mentis?" : "Remontar a semana?"}
            </DialogTitle>
          </DialogHeader>
          <p className="text-sm leading-relaxed text-zinc-600">
            Isto custa <strong>{custoDaConfirmacao} Sparks</strong>.{" "}
            {confirmando === "mentis" ? (
              <>
                A Mentis escreve o conteúdo de cada bloco da sua semana. Se ela não conseguir,
                os Sparks voltam e a semana é montada do mesmo jeito.
              </>
            ) : (
              <>
                A semana é montada de novo do zero — e os blocos que você já marcou como
                feitos <strong>desta semana</strong> são apagados junto.
              </>
            )}
          </p>
          <DialogFooter className="gap-2">
            <button
              onClick={() => setConfirmando(null)}
              className="pill btn-vidro inline-flex items-center justify-center px-5 py-2.5 text-sm"
              data-testid="agenda-cancelar"
            >
              Cancelar
            </button>
            <button
              onClick={() => gerar(confirmando === "mentis")}
              className="pill btn-sapiens inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm"
              data-testid="agenda-confirmar-btn"
            >
              <Sparkles className="h-4 w-4" /> Continuar por {custoDaConfirmacao} Sparks
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* A anotação rápida: o "+" de um dia. */}
      <Dialog open={Boolean(novoCompromisso)} onOpenChange={(v) => !v && setNovoCompromisso(null)}>
        <DialogContent className="rounded-2xl" data-testid="agenda-novo-compromisso">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl font-black">Novo compromisso</DialogTitle>
          </DialogHeader>
          {novoCompromisso && (
            <div className="grid gap-3">
              <p className="text-sm font-extrabold text-zinc-500">
                {DIAS[novoCompromisso.dia]}, {novoCompromisso.data.slice(8, 10)}/{novoCompromisso.data.slice(5, 7)}
              </p>
              <input
                autoFocus
                value={tituloNovo}
                onChange={(e) => setTituloNovo(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") salvarNovo(); }}
                placeholder="O que é? Ex.: Aula de matemática"
                className="w-full rounded-xl border-2 border-zinc-200 px-3 py-2.5 text-sm outline-none"
                data-testid="agenda-novo-titulo"
              />
              <div className="grid grid-cols-3 gap-2">
                <select
                  value={tipoNovo}
                  onChange={(e) => setTipoNovo(e.target.value)}
                  className="rounded-xl border-2 border-zinc-200 px-2 py-2.5 text-sm outline-none"
                  aria-label="Tipo"
                >
                  {TIPOS_COMPROMISSO.map((t) => <option key={t.id} value={t.id}>{t.rotulo}</option>)}
                </select>
                <input
                  type="time" value={novoCompromisso.inicio}
                  onChange={(e) => setNovoCompromisso({ ...novoCompromisso, inicio: e.target.value })}
                  className="rounded-xl border-2 border-zinc-200 px-2 py-2.5 text-sm outline-none"
                  aria-label="Começa"
                />
                <input
                  type="time" value={novoCompromisso.fim}
                  onChange={(e) => setNovoCompromisso({ ...novoCompromisso, fim: e.target.value })}
                  className="rounded-xl border-2 border-zinc-200 px-2 py-2.5 text-sm outline-none"
                  aria-label="Termina"
                />
              </div>
            </div>
          )}
          <DialogFooter className="gap-2">
            <button
              onClick={() => setNovoCompromisso(null)}
              className="pill btn-vidro inline-flex items-center justify-center px-5 py-2.5 text-sm"
            >
              Cancelar
            </button>
            <button
              onClick={salvarNovo}
              disabled={!tituloNovo.trim() || salvandoNovo}
              className="pill btn-sapiens inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm disabled:opacity-60"
              data-testid="agenda-novo-salvar"
            >
              {salvandoNovo ? <Loader2 className="h-4 w-4 animate-spin" /> : "Anotar"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
