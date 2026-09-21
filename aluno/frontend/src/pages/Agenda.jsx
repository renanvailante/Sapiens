import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  CalendarDays, ChevronLeft, ChevronRight, Sparkles, Loader2, Check,
  TrendingUp, Info, X, RotateCw, BookmarkPlus, Radio, Sun,
} from "lucide-react";
import { api, errMsg } from "../lib/api";
import { avisarSparksMudou } from "../components/Navegacao";
import Mentis from "../components/Mentis";
import CronogramaCompromissos from "../components/CronogramaCompromissos";
import EstadoDeErro from "../components/EstadoDeErro";
import FilaDeRevisao from "../components/FilaDeRevisao";
import ListaDeLembretes from "../components/ListaDeLembretes";
import MentorUSP from "../components/MentorUSP";
import SecaoDaAba, { useAncora } from "../components/SecaoDaAba";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { criarPortao } from "../lib/idempotencia";
import { useCortesDaRolagem } from "../components/TiraRolavel";
import { ROTAS, ANCORAS } from "../lib/rotas";
import { proximaQuinta, temAcessoLocal } from "../lib/live";

/**
 * AGENDA — tudo o que tem hora, num lugar só.
 *
 * Pergunta mental: **quando?**
 *
 * ---------------------------------------------------------------------------
 * A FILA DE REVISÕES MORA AQUI (2026-09-18)
 * ---------------------------------------------------------------------------
 *
 * `/revisoes` era uma tela própria que empilhava três coisas de naturezas
 * diferentes: a fila de hoje (ação, com prazo), o que o aluno marcou pelo app
 * (ação, curada por ele) e a trajetória por habilidade (análise longitudinal).
 * As duas primeiras respondem "quando", que é a pergunta desta aba; a terceira
 * responde "eu melhorei?", que é a de Progresso — e foi para lá.
 *
 * O sintoma de que a tela estava no lugar errado estava no próprio código: o
 * cronograma gerava blocos de `tipo: revisao` apontando para `/revisoes`, e
 * `/revisoes` desenhava a fila que o cronograma já tinha agendado. Uma tela
 * apontando para a outra e de volta, com o aluno no meio.
 *
 * Agora o bloco de revisão da grade rola até a seção `#revisoes` desta mesma
 * página — é um deslocamento, não uma navegação, e o laço deixou de existir.
 *
 * ---------------------------------------------------------------------------
 * AS DUAS FILAS PRECISAM PARECER DIFERENTES
 * ---------------------------------------------------------------------------
 *
 * `FilaDeRevisao` é INFERIDA: cada linha nasceu de um erro que o motor
 * cognitivo conseguiu explicar, e a data de voltar a cobrar sai daí.
 * `ListaDeLembretes` é DECLARADA: cada linha nasceu do aluno lendo algo e
 * dizendo "isto eu ainda não domino". Postas na mesma seção, a segunda lê como
 * uma versão pior da primeira — por isso são duas seções, com título próprio.
 *
 * ---------------------------------------------------------------------------
 * O RESTO, QUE JÁ ERA DAQUI
 * ---------------------------------------------------------------------------
 *
 * A grade mostra as duas metades da semana e as distingue no olho: o que o
 * aluno JÁ TEM (aula, trabalho, prova) em chip sólido, e o que o Sapiens
 * propõe em card clicável. Um cronograma que só mostrasse estudo seria mais um
 * plano bonito que ignora a vida de quem vai cumpri-lo.
 *
 * Nenhum bloco morre em si mesmo: todo bloco leva à tela onde aquilo é feito.
 * Um cronograma que só informa é uma lista de tarefas; um que abre a tarefa é
 * uma rotina.
 *
 * A ordem das áreas não é escolha da tela nem do modelo: vem de
 * `/api/prioridades` (peso da frente na nota do ENEM x lacuna medida). A tela
 * só a explica — a faixa "o que mais rende pontos" existe para o aluno poder
 * discordar da ordem, e não só obedecê-la.
 */

const DIAS_CURTOS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];

const CORES_TIPO = {
  aula: "border-sky-400/30 bg-sky-400/10 text-sky-100",
  trabalho: "border-violet-400/30 bg-violet-400/10 text-violet-100",
  prova: "border-rose-400/35 bg-rose-400/12 text-rose-100",
  pessoal: "border-white/15 bg-white/8 text-white/75",
};

const CORES_BLOCO = {
  revisao: "border-amber-400/35 hover:border-amber-400/60",
  treino: "border-[#8B7BFF]/35 hover:border-[#8B7BFF]/60",
  redacao: "border-emerald-400/35 hover:border-emerald-400/60",
  questoes: "border-white/12 hover:border-[#4FD9FF]/50",
};

const ROTULO_TIPO = {
  revisao: "Revisão", treino: "Treino", redacao: "Redação", questoes: "Questões", estudo: "Estudo",
};

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
    const f = (d) => d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
    return `${f(inicio)} – ${f(fim)}`;
  } catch {
    return semanaISO;
  }
}

/** A faixa que explica a ordem. Sem ela, o cronograma é uma ordem sem motivo. */
function FaixaDePrioridade({ prioridades }) {
  const topo = (prioridades || []).slice(0, 4);
  if (!topo.length) return null;
  return (
    <section className="card-sapiens rounded-3xl p-6 md:p-7" data-testid="agenda-prioridades">
      <p className="text-sm text-zinc-500">
        É esta ordem que decide quantos blocos cada área ganha na sua semana.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {topo.map((p, i) => (
          <Link
            key={p.chave}
            to={p.rota}
            className="lift rounded-2xl border border-white/10 bg-white/5 p-4"
            data-testid={`agenda-prioridade-${p.chave}`}
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-display text-base font-bold tracking-tight text-zinc-950">
                {i + 1}. {p.nome}
              </span>
              <span className="font-mono-alt text-[10px] uppercase tracking-[0.22em] text-zinc-400">
                {p.estado === "sem_medida"
                  ? "sem medida"
                  : p.chave === "redacao"
                    ? `${p.nota ?? "—"}/1000`
                    : `${p.taxa_acerto}%`}
              </span>
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-zinc-500">{p.porque}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}

const TIPOS_COMPROMISSO = [
  { id: "aula", rotulo: "Aula" },
  { id: "trabalho", rotulo: "Trabalho" },
  { id: "prova", rotulo: "Prova" },
  { id: "pessoal", rotulo: "Pessoal" },
];

const HORA_PX = 52;
const HORA_INICIO = 6;
const HORA_FIM = 23;

function minDoDia(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}
function hhmmDoMin(min) {
  const h = Math.floor(min / 60), m = min % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/**
 * A semana como uma linha do tempo contínua (uma coluna por dia, o relógio
 * correndo por trás), não sete listas soltas — para o olho comparar horários
 * entre dias tão fácil quanto numa agenda de verdade. Tocar num horário livre
 * abre a anotação rápida; o X no próprio compromisso o apaga ali mesmo — sem
 * abas, sem formulário para tirar o que já está certo.
 */
function GradeSemana({ dias, hojeISO, onConcluirBloco, salvandoBloco, onApagarCompromisso, onClicarVazio }) {
  const nav = useNavigate();
  // A grade tem 760px de largura mínima e a tela do aluno tem 375: no celular
  // ela SEMPRE rola, e terminava exatamente na borda — a mesma imagem de uma
  // semana que acabasse na quinta. A máscara mostra o próximo dia cortado.
  const { ref: refGrade, atributos: cortes } = useCortesDaRolagem(dias);
  const alturaTotal = (HORA_FIM - HORA_INICIO) * HORA_PX;
  const horas = Array.from({ length: HORA_FIM - HORA_INICIO }, (_, i) => HORA_INICIO + i);

  return (
    <div
      ref={refGrade}
      {...cortes}
      className="card-sapiens corta-rolagem mt-6 overflow-x-auto rounded-3xl p-3"
      data-testid="agenda-grade"
    >
      <div className="flex min-w-[760px]">
        <div className="w-10 shrink-0">
          <div className="h-9" />
          {horas.map((h) => (
            <div key={h} style={{ height: HORA_PX }} className="relative">
              <span className="absolute -top-2 right-1 font-mono-alt text-[9px] text-zinc-400">
                {String(h).padStart(2, "0")}h
              </span>
            </div>
          ))}
        </div>
        {dias.map((dia) => {
          const eHoje = dia.data === hojeISO;
          const diaInteiro = dia.compromissos.filter((c) => c.dia_inteiro);
          const comHorario = dia.compromissos.filter((c) => !c.dia_inteiro);
          return (
            <div key={dia.data} className="min-w-0 flex-1 border-l border-white/[0.06]">
              <div className={`flex h-9 flex-col items-center justify-center ${eHoje ? "text-[#7FD8FF]" : "text-zinc-400"}`}>
                <span className="font-display text-xs font-bold tracking-tight">{DIAS_CURTOS[dia.indice].slice(0, 3)}</span>
                <span className="font-mono-alt text-[9px]">{dia.data.slice(8, 10)}</span>
              </div>
              {diaInteiro.map((c) => (
                <div
                  key={c.id}
                  className={`group relative mx-1 mb-1 rounded-lg border px-2 py-1 text-[10px] ${CORES_TIPO[c.tipo] || CORES_TIPO.pessoal}`}
                >
                  {c.titulo}
                  <span
                    role="button"
                    onClick={() => onApagarCompromisso(c.id)}
                    aria-label={`Apagar ${c.titulo}`}
                    className="absolute right-1 top-1 rounded-full p-1 opacity-0 transition hover:bg-black/20 group-hover:opacity-70"
                  >
                    <X className="h-2.5 w-2.5" />
                  </span>
                </div>
              ))}
              <div
                className={`relative cursor-copy ${eHoje ? "bg-[#4FD9FF]/[0.03]" : ""}`}
                style={{ height: alturaTotal }}
                onClick={(e) => {
                  const y = e.clientY - e.currentTarget.getBoundingClientRect().top;
                  onClicarVazio(dia, HORA_INICIO * 60 + Math.round((y / HORA_PX) * 60));
                }}
                data-testid={`agenda-dia-${dia.indice}`}
              >
                {horas.map((h) => (
                  <div key={h} className="absolute inset-x-0 border-t border-white/[0.05]" style={{ top: (h - HORA_INICIO) * HORA_PX }} />
                ))}

                {comHorario.map((c) => {
                  const ini = Math.max(0, minDoDia(c.inicio) - HORA_INICIO * 60);
                  const fim = Math.min(alturaTotal, minDoDia(c.fim) - HORA_INICIO * 60);
                  if (fim <= ini) return null;
                  return (
                    <div
                      key={c.id}
                      onClick={(e) => e.stopPropagation()}
                      style={{ top: (ini / 60) * HORA_PX, height: Math.max((fim - ini) / 60 * HORA_PX, 26) }}
                      className={`group absolute inset-x-1 overflow-hidden rounded-lg border px-1.5 py-1 text-left text-[10px] leading-tight ${CORES_TIPO[c.tipo] || CORES_TIPO.pessoal}`}
                      data-testid={`agenda-compromisso-${c.id}`}
                    >
                      <span className="block font-mono-alt text-[8px] opacity-70">{c.inicio}–{c.fim}</span>
                      <p className="truncate">{c.titulo}</p>
                      <span
                        role="button"
                        onClick={(e) => { e.stopPropagation(); onApagarCompromisso(c.id); }}
                        aria-label={`Apagar ${c.titulo}`}
                        className="absolute right-1 top-1 rounded-full p-1 opacity-0 transition hover:bg-black/20 group-hover:opacity-70"
                      >
                        <X className="h-2.5 w-2.5" />
                      </span>
                    </div>
                  );
                })}

                {dia.blocos.map((b) => {
                  const ini = Math.max(0, minDoDia(b.inicio) - HORA_INICIO * 60);
                  const fim = Math.min(alturaTotal, minDoDia(b.fim) - HORA_INICIO * 60);
                  if (fim <= ini) return null;
                  return (
                    <div
                      key={b.id}
                      onClick={(e) => { e.stopPropagation(); nav(b.rota); }}
                      style={{ top: (ini / 60) * HORA_PX, height: Math.max((fim - ini) / 60 * HORA_PX, 26) }}
                      className={`absolute inset-x-1 cursor-pointer overflow-hidden rounded-lg border bg-white/5 px-1.5 py-1 text-left text-[10px] leading-tight transition ${CORES_BLOCO[b.tipo] || CORES_BLOCO.questoes} ${b.concluido ? "opacity-50" : ""}`}
                      data-testid={`agenda-bloco-${b.id}`}
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-mono-alt text-[8px] uppercase tracking-[0.15em] text-zinc-400">
                          {ROTULO_TIPO[b.tipo] || b.tipo}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); onConcluirBloco(b); }}
                          disabled={salvandoBloco}
                          aria-label={b.concluido ? "Desmarcar como feito" : "Marcar como feito"}
                          className={`relative flex h-3 w-3 shrink-0 items-center justify-center rounded border before:absolute before:-inset-2 before:content-[''] ${
                            b.concluido ? "border-emerald-400/60 bg-emerald-400/25 text-emerald-200" : "border-white/25 text-transparent hover:border-white/50"
                          }`}
                        >
                          <Check className="h-2 w-2" />
                        </button>
                      </div>
                      <p className={`truncate ${b.concluido ? "line-through" : ""}`}>{b.titulo}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
      <p className="mt-2 text-center text-[10px] text-zinc-400">Toque num horário livre para anotar um compromisso.</p>
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
  // O clique num horário livre da grade abre isto: {dia, data, inicio, fim}.
  const [novoCompromisso, setNovoCompromisso] = useState(null);
  const [tituloNovo, setTituloNovo] = useState("");
  const [tipoNovo, setTipoNovo] = useState("aula");
  const [salvandoNovo, setSalvandoNovo] = useState(false);

  useDeclararContextoMentis("Na Agenda, vendo o que tem hora marcada e o que precisa revisar.");

  const carregar = useCallback(async (semana) => {
    setCarregando(true);
    setErro(null);
    try {
      // As três numa chamada paralela só. A fila entrou aqui quando `/revisoes`
      // deixou de ser tela: ela é a primeira coisa que a Agenda responde, e
      // buscá-la depois faria a seção "Hoje" nascer vazia e pular de altura.
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
      // Mesma regra para a fila: `null` faz a seção dizer que não conseguiu
      // ler, e não "você não tem nada para revisar" — que seria mentira num
      // dia de rede ruim, e a mentira mais cara que esta tela pode contar.
      setFila(filaResp.status === "fulfilled" ? filaResp.value.data : null);
    } catch (e) {
      setErro(errMsg(e, "Não consegui abrir o seu cronograma agora."));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => { carregar(undefined); }, [carregar]);

  // A trava do duplo toque. Duas partes, e as duas são necessárias: a `ref`
  // barra a segunda chamada no mesmo instante (o `setGerando` que desabilita o
  // botão só vale depois da re-renderização, e dois toques em 50ms acontecem
  // antes dela), e a CHAVE só é trocada quando a montagem termina — uma nova
  // tentativa depois de um erro de rede é o mesmo pedido, e o servidor precisa
  // reconhecê-la como tal (ver `cronograma_routes._reivindicar_montagem`).
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

  const abrirNovo = (dia, minutosClicados) => {
    const base = Math.round(minutosClicados / 30) * 30;
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
    carregar(alvo);
  };

  const compromissos = useMemo(
    () => (dados?.dias || []).flatMap((d) => d.compromissos),
    [dados]
  );
  const hojeISO = diaLocalISO();
  const plano = dados?.plano;
  const temPlano = Boolean(plano?.desta_semana && dados?.total_blocos > 0);

  /**
   * A GRADE, definida aqui porque a ORDEM dela na página depende do estado.
   *
   * A aba se chama "Semana" e o cronograma semanal é o que o aluno vem ver:
   * ele precisa ser a primeira coisa, não a quarta. Estava atrás do resumo da
   * Mentis, dos dois botões de montar e da faixa de prioridades — três blocos
   * de meta-informação sobre um plano que o aluno ainda não tinha olhado.
   *
   * Com uma exceção, e ela não é um detalhe: quando NÃO HÁ plano, a grade
   * está vazia, e abrir a tela com sete colunas em branco é pior do que
   * abri-la com o botão que as preenche. Sem plano, o conteúdo mais importante
   * é a AÇÃO de montar. A régua é a mesma nos dois casos — o que estiver no
   * topo tem de ser o que importa agora —, e é o estado que decide qual é.
   */
  const grade = dados ? (
    <GradeSemana
      dias={dados.dias}
      hojeISO={hojeISO}
      onConcluirBloco={concluir}
      salvandoBloco={salvandoBloco}
      onApagarCompromisso={apagarCompromisso}
      onClicarVazio={abrirNovo}
    />
  ) : null;
  // Remontar só custa quando há o que remontar. Espelha a mesma condição do
  // servidor (`gerar_cronograma`): semana com plano E com bloco.
  const custoRemontar = temPlano ? (dados?.custo_remontagem ?? 0) : 0;
  const custoDaConfirmacao = confirmando === "mentis" ? (dados?.custo_mentis ?? 0) : custoRemontar;

  // Os blocos de HOJE, que abrem a aba. `dias` vem da semana inteira; o aluno
  // que abre a Agenda às sete da noite quer ver a noite dele, não a segunda.
  const hoje = (dados?.dias || []).find((d) => d.data === hojeISO);
  const blocosDeHoje = (hoje?.blocos || []).filter((b) => !b.concluido);
  const compromissosDeHoje = hoje?.compromissos || [];
  const vencidas = fila?.resumo?.questoes ?? 0;

  // A aula ao vivo: o único compromisso do produto com HORA MARCADA que o
  // aluno não agendou. Ela é calculada no navegador (`lib/live.js`), de graça
  // — o Painel recusou uma leitura de `/cursos` só para anunciá-la, e a
  // Agenda recusa pelo mesmo motivo.
  const live = proximaQuinta();
  const liveDias = Math.max(0, Math.ceil((live.inicio - Date.now()) / 86400000));

  useAncora(carregando);

  return (
    <div className="min-h-screen">
      <div className="max-w-6xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="secao-olho">Agenda</p>
            <h1 className="titulo-tela">Tudo o que tem hora.</h1>
            <p className="mt-2 max-w-2xl text-sm text-white/55">
              O que vence hoje, o que você marcou para rever, a sua semana montada nos
              seus horários — e a aula de quinta, que não se repõe.
            </p>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              type="button" onClick={() => irPara(-7)}
              className="pill flex h-9 w-9 items-center justify-center rounded-full border border-white/12 bg-white/5 text-white/70 hover:text-white"
              aria-label="Semana anterior" data-testid="agenda-semana-anterior"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="min-w-[9.5rem] text-center text-xs text-white/70" data-testid="agenda-rotulo-semana">
              {rotuloDaSemana(semanaISO)}
            </span>
            <button
              type="button" onClick={() => irPara(7)}
              className="pill flex h-9 w-9 items-center justify-center rounded-full border border-white/12 bg-white/5 text-white/70 hover:text-white"
              aria-label="Próxima semana" data-testid="agenda-semana-proxima"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        {erro && (
          <div className="mt-8">
            <EstadoDeErro mensagem={erro} aoTentarNovamente={() => carregar(semanaISO)} />
          </div>
        )}

        {carregando && !dados ? (
          <div className="mt-10 flex items-center gap-2 text-sm text-white/50">
            <Loader2 className="h-4 w-4 animate-spin" /> Abrindo a sua agenda…
          </div>
        ) : (
          <div className="mt-10 space-y-14">
            {/* ─── HOJE ─────────────────────────────────────────────────── */}
            <SecaoDaAba
              id={ANCORAS.AGENDA_HOJE}
              icone={Sun}
              olho="Agora"
              titulo="O seu dia"
              descricao="O que está marcado para hoje, e o que a memória vai perder se você não voltar."
            >
              {blocosDeHoje.length === 0 && compromissosDeHoje.length === 0 && vencidas === 0 ? (
                <p className="superficie rounded-2xl p-5 text-sm leading-relaxed text-white/55">
                  Hoje não há nada marcado nem nada vencendo.{" "}
                  <Link to={ROTAS.ESTUDAR} className="font-semibold text-[#7FD8FF] hover:underline">
                    Escolher o que estudar
                  </Link>{" "}
                  ou montar a semana aqui embaixo.
                </p>
              ) : (
                <div className="grid gap-2.5 sm:grid-cols-2">
                  {vencidas > 0 && (
                    <a
                      href={`#${ANCORAS.AGENDA_REVISOES}`}
                      className="superficie lift flex items-start gap-3 rounded-2xl border-amber-400/30 p-4"
                      data-testid="agenda-hoje-revisoes"
                    >
                      <RotateCw className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
                      <span className="min-w-0">
                        <span className="block text-sm font-semibold text-white">
                          {vencidas === 1 ? "1 questão voltou para revisão" : `${vencidas} questões voltaram para revisão`}
                        </span>
                        <span className="block text-xs text-white/50">
                          Revisar no dia em que vence é o que faz a memória durar.
                        </span>
                      </span>
                    </a>
                  )}
                  {compromissosDeHoje.map((c) => (
                    <div
                      key={c.id}
                      className={`rounded-2xl border px-4 py-3 ${CORES_TIPO[c.tipo] || CORES_TIPO.pessoal}`}
                      data-testid={`agenda-hoje-compromisso-${c.id}`}
                    >
                      <span className="secao-olho">{c.dia_inteiro ? "dia todo" : `${c.inicio}–${c.fim}`}</span>
                      <span className="mt-0.5 block text-sm font-semibold">{c.titulo}</span>
                    </div>
                  ))}
                  {blocosDeHoje.map((b) => (
                    <Link
                      key={b.id}
                      to={b.rota || ROTAS.ESTUDAR}
                      className={`superficie lift rounded-2xl border p-4 ${CORES_BLOCO[b.tipo] || CORES_BLOCO.questoes}`}
                      data-testid={`agenda-hoje-bloco-${b.id}`}
                    >
                      <span className="secao-olho">
                        {b.inicio}–{b.fim} · {b.frente_nome || ROTULO_TIPO[b.tipo] || b.tipo}
                      </span>
                      <span className="mt-0.5 block text-sm font-semibold text-white">{b.titulo}</span>
                    </Link>
                  ))}
                </div>
              )}
            </SecaoDaAba>

            {/* ─── REVISÕES ─────────────────────────────────────────────── */}
            {/* Era a tela `/revisoes`. A fila é INFERIDA: cada linha nasceu de
                um erro que o motor conseguiu explicar, e a data de voltar a
                cobrar sai daí — não é uma lista de matérias. */}
            <SecaoDaAba
              id={ANCORAS.AGENDA_REVISOES}
              icone={RotateCw}
              olho="Revisão espaçada"
              titulo="O que voltar a estudar"
              descricao="Cada linha veio de um erro seu que o Sapiens conseguiu explicar — e a data de voltar a cobrar sai daí."
            >
              {fila ? (
                <FilaDeRevisao fila={fila} />
              ) : (
                <p className="superficie rounded-2xl p-5 text-sm text-white/55">
                  Não consegui ler a sua fila de revisões agora.{" "}
                  <button
                    type="button"
                    onClick={() => carregar(semanaISO)}
                    className="font-semibold text-[#7FD8FF] hover:underline"
                  >
                    Tentar de novo
                  </button>
                </p>
              )}
            </SecaoDaAba>

            {/* ─── LEMBRETES ────────────────────────────────────────────── */}
            {/* A outra fila, e ela precisa PARECER diferente: esta é declarada
                pelo aluno ("isto eu ainda não domino"), aquela é inferida do
                erro. Juntas na mesma seção, esta lê como uma versão pior. */}
            <SecaoDaAba
              id={ANCORAS.AGENDA_LEMBRETES}
              icone={BookmarkPlus}
              olho="Você marcou"
              titulo="Guardado para rever"
              descricao={'Os trechos que você separou pelo app com "Lembrar-me com a Mentis" — o que a fila de cima não tem como adivinhar.'}
            >
              <ListaDeLembretes />
            </SecaoDaAba>

            {dados && (
              <>
                {/* ─── SEMANA ───────────────────────────────────────────── */}
                <SecaoDaAba
                  id={ANCORAS.AGENDA_SEMANA}
                  icone={CalendarDays}
                  olho="Segunda a domingo"
                  titulo="A sua semana"
                  descricao="Os seus compromissos, e o estudo montado no que sobra — priorizado pelo que mais rende ponto na sua prova."
                >
                  {/* A grade primeiro quando há plano: é o que o aluno vem
                      ver. Sem plano ela está vazia, e sete colunas em branco
                      são piores que o botão que as preenche — aí a AÇÃO sobe. */}
                  {temPlano && grade}

                  <section
                    className={`card-sapiens rounded-3xl p-6 md:p-8 ${temPlano ? "mt-6" : ""}`}
                    data-testid="agenda-montar"
                  >
                    <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
                      <div className="flex items-start gap-3">
                        <Mentis className="mt-0.5 h-9 w-9 shrink-0" estado={gerando ? "analise" : "neutra"} />
                        <div>
                          <p className="text-sm leading-relaxed text-zinc-950" data-testid="agenda-resumo">
                            {temPlano
                              ? plano.resumo
                              : "Esta semana ainda não tem cronograma. Eu monto em cima dos seus compromissos, " +
                                "priorizando onde você ganha mais ponto — Matemática e Redação primeiro, e o " +
                                "que os seus erros mostrarem depois."}
                          </p>
                          {temPlano && plano.recado && (
                            <p className="mt-2 text-xs leading-relaxed text-zinc-500">{plano.recado}</p>
                          )}
                          {temPlano && (
                            <p className="mt-2 font-mono-alt text-[10px] uppercase tracking-[0.22em] text-zinc-400">
                              {dados.total_concluidos}/{dados.total_blocos} blocos feitos
                              {plano.com_mentis ? " · comentada pela Mentis" : ""}
                            </p>
                          )}
                        </div>
                      </div>
                      {/* Os dois preços saem do SERVIDOR (`custo_remontagem` e
                          `custo_mentis` em `GET /cronograma`): a tela nunca
                          escreve um número de Sparks, e quem cobra é quem
                          monta. Remontar só custa quando a semana já tem
                          plano — a primeira montagem é de graça e o botão diz. */}
                      <div className="flex shrink-0 flex-col gap-2 sm:flex-row md:flex-col lg:flex-row">
                        <button
                          type="button"
                          onClick={() => (custoRemontar ? setConfirmando("gratis") : gerar(false))}
                          disabled={Boolean(gerando)}
                          className="pill btn-sapiens inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full px-5 py-2.5 text-sm font-medium disabled:opacity-50"
                          data-testid="agenda-gerar"
                        >
                          {gerando === "gratis" ? <Loader2 className="h-4 w-4 animate-spin" /> : <CalendarDays className="h-4 w-4" />}
                          {temPlano ? "Remontar" : "Montar minha semana"} ·{" "}
                          {custoRemontar ? `${custoRemontar} Sparks` : "grátis"}
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmando("mentis")}
                          disabled={Boolean(gerando)}
                          className="pill btn-vidro inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full px-5 py-2.5 text-sm font-medium disabled:opacity-50"
                          data-testid="agenda-gerar-mentis"
                        >
                          {gerando === "mentis" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                          Com a Mentis · {dados.custo_mentis} Sparks
                        </button>
                      </div>
                    </div>
                    {plano && !plano.desta_semana && (
                      <p className="mt-4 flex items-start gap-2 rounded-2xl border border-amber-400/25 bg-amber-400/8 px-3.5 py-2.5 text-xs text-amber-100">
                        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                        O seu último cronograma é de outra semana. Monte de novo para esta — as revisões
                        marcadas e os seus pontos fracos mudaram desde lá.
                      </p>
                    )}
                  </section>

                  {!temPlano && <div className="mt-6">{grade}</div>}
                </SecaoDaAba>

                {/* ─── PRIORIDADES ──────────────────────────────────────── */}
                <SecaoDaAba
                  id={ANCORAS.AGENDA_PRIORIDADES}
                  icone={TrendingUp}
                  olho="Peso na prova × sua lacuna"
                  titulo="O que mais rende ponto"
                  descricao="A ordem não é escolha da tela nem da Mentis: sai do peso de cada frente na nota do ENEM cruzado com o que já foi medido em você. Ela está aqui para você poder discordar dela."
                >
                  <FaixaDePrioridade prioridades={prioridades} />

                  {temPlano && plano.distribuicao?.length > 0 && (
                    <section className="card-sapiens mt-6 rounded-3xl p-6" data-testid="agenda-distribuicao">
                      <h3 className="font-display text-lg font-bold tracking-tight text-zinc-950">
                        Por que a semana ficou assim
                      </h3>
                      <div className="mt-3 space-y-2.5">
                        {plano.distribuicao.map((d) => (
                          <div key={d.chave} className="flex items-start gap-3">
                            <span className="mt-0.5 shrink-0 rounded-full border border-white/12 bg-white/5 px-2.5 py-1 font-mono-alt text-[10px] text-white/70">
                              {d.blocos}×
                            </span>
                            <p className="text-xs leading-relaxed text-zinc-500">
                              <span className="font-medium text-zinc-950">{d.nome}</span> — {d.porque}
                            </p>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}
                </SecaoDaAba>

                {/* ─── EVENTOS E COMPROMISSOS ───────────────────────────── */}
                <SecaoDaAba
                  id={ANCORAS.AGENDA_EVENTOS}
                  icone={Radio}
                  olho="Hora marcada"
                  titulo="Aulas e compromissos"
                  descricao="A aula ao vivo acontece uma vez por semana e não tem reposição. O resto desta lista é o que você mesmo anotou."
                >
                  {/* A aula de quinta como EVENTO DATADO. Ela era uma aba
                      permanente em âmbar na barra — um botão quente para algo
                      que acontece 60 minutos por semana, chamando atenção nos
                      outros seis dias sem ter o que dizer. Aqui ela tem o que
                      lhe faltava: uma data. */}
                  <Link
                    to={ROTAS.AULA_AO_VIVO}
                    className="superficie lift flex flex-col items-stretch gap-4 rounded-2xl border-amber-400/25 p-5 sm:flex-row sm:items-center"
                    data-testid="agenda-live"
                  >
                    <div className="flex min-w-0 flex-1 items-start gap-4 sm:items-center">
                      <MentorUSP tamanho="m" testid="agenda-live-mentor" />
                      <div className="min-w-0">
                        <div className="secao-olho flex items-center gap-1.5 text-amber-200/90">
                          {live.aoVivoAgora ? (
                            <>
                              <span className="relative flex h-2 w-2">
                                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-500 opacity-80" />
                                <span className="relative inline-flex h-2 w-2 rounded-full bg-rose-500" />
                              </span>
                              Acontecendo agora
                            </>
                          ) : (
                            <>
                              <Radio className="h-3 w-3" />
                              {liveDias === 0 ? "Hoje" : liveDias === 1 ? "Amanhã" : `Em ${liveDias} dias`}
                            </>
                          )}
                        </div>
                        <div className="mt-0.5 font-display text-base font-bold tracking-tight text-white">
                          Aula ao vivo com Vitor Lara
                        </div>
                        <div className="text-xs text-white/50">
                          {live.inicio.toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })}
                          {" · "}
                          {live.inicio.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                          {temAcessoLocal(live.edicao) ? " · você já tem esta edição" : ""}
                        </div>
                      </div>
                    </div>
                    <span className="pill btn-vidro inline-flex w-full items-center justify-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold sm:w-auto">
                      {live.aoVivoAgora ? "Entrar" : "Ver a aula"}
                    </span>
                  </Link>

                  <div className="mt-6">
                    <CronogramaCompromissos
                      semana={semanaISO}
                      compromissos={compromissos}
                      preferencias={dados.preferencias}
                      custoTexto={dados.custo_texto}
                      onSemana={(nova) => { setDados(nova); setSemanaISO(nova.semana); }}
                      onSaldo={setSaldo}
                    />
                  </div>
                </SecaoDaAba>
              </>
            )}
          </div>
        )}
      </div>

      {/* A cobrança, dita ANTES de acontecer — mesma regra da redação e da
          loja. O diálogo só abre quando a ação custa alguma coisa: montar a
          primeira semana continua sendo um clique só. */}
      <Dialog open={Boolean(confirmando)} onOpenChange={(v) => !v && setConfirmando(null)}>
        <DialogContent className="rounded-2xl" data-testid="agenda-confirmar">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight">
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
          <DialogFooter>
            <button
              onClick={() => setConfirmando(null)}
              className="pill inline-flex items-center justify-center rounded-full border border-zinc-200 px-5 py-2.5 text-sm font-medium text-zinc-700 hover:border-zinc-300"
              data-testid="agenda-cancelar"
            >
              Cancelar
            </button>
            <button
              onClick={() => gerar(confirmando === "mentis")}
              className="pill btn-sapiens inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium"
              data-testid="agenda-confirmar-btn"
            >
              <Sparkles className="h-4 w-4" /> Continuar por {custoDaConfirmacao} Sparks
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* A anotação rápida nascida do clique na grade — mesmo endpoint do
          formulário da aba "Adicionar à mão", só que sem trocar de aba. */}
      <Dialog open={Boolean(novoCompromisso)} onOpenChange={(v) => !v && setNovoCompromisso(null)}>
        <DialogContent className="rounded-2xl" data-testid="agenda-novo-compromisso">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight">Novo compromisso</DialogTitle>
          </DialogHeader>
          {novoCompromisso && (
            <div className="grid gap-3">
              <input
                autoFocus
                value={tituloNovo}
                onChange={(e) => setTituloNovo(e.target.value)}
                placeholder="O que é? Ex.: Aula de matemática"
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none"
                data-testid="agenda-novo-titulo"
              />
              <div className="grid grid-cols-3 gap-2">
                <select
                  value={tipoNovo}
                  onChange={(e) => setTipoNovo(e.target.value)}
                  className="rounded-xl border border-zinc-200 px-2 py-2 text-sm outline-none"
                >
                  {TIPOS_COMPROMISSO.map((t) => <option key={t.id} value={t.id}>{t.rotulo}</option>)}
                </select>
                <input
                  type="time" value={novoCompromisso.inicio}
                  onChange={(e) => setNovoCompromisso({ ...novoCompromisso, inicio: e.target.value })}
                  className="rounded-xl border border-zinc-200 px-2 py-2 text-sm outline-none"
                />
                <input
                  type="time" value={novoCompromisso.fim}
                  onChange={(e) => setNovoCompromisso({ ...novoCompromisso, fim: e.target.value })}
                  className="rounded-xl border border-zinc-200 px-2 py-2 text-sm outline-none"
                />
              </div>
              <p className="text-xs text-zinc-500">
                {DIAS_CURTOS[novoCompromisso.dia]}, {novoCompromisso.data.slice(8, 10)}/{novoCompromisso.data.slice(5, 7)}
              </p>
            </div>
          )}
          <DialogFooter>
            <button
              onClick={() => setNovoCompromisso(null)}
              className="pill inline-flex items-center justify-center rounded-full border border-zinc-200 px-5 py-2.5 text-sm font-medium text-zinc-700 hover:border-zinc-300"
            >
              Cancelar
            </button>
            <button
              onClick={salvarNovo}
              disabled={!tituloNovo.trim() || salvandoNovo}
              className="pill btn-sapiens inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium disabled:opacity-50"
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
