import { useCallback, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  PlayCircle, Compass, RotateCw, PenLine, CalendarDays, Radio,
  Users, Trophy, Gauge, Shuffle, ArrowRight, Sparkles,
} from "lucide-react";
import Mentis from "./Mentis";

/**
 * OS PORTAIS — a vitrine de descoberta do produto.
 *
 * O problema que isto resolve: o Painel abria pelo mapa de missões, uma peça
 * bonita mas FECHADA — quem chegava via um caminho já traçado e uma única
 * porta. Para quem ainda não sabe o que o produto tem, um caminho único não
 * convida: ele estreita. Khan Academy e Duolingo abrem do jeito oposto, com
 * várias entradas visíveis ao mesmo tempo, cada uma mostrando quanto já foi
 * feito e o que ainda não foi tocado — é a vitrine que gera a vontade, não o
 * corredor.
 *
 * ---------------------------------------------------------------------------
 * QUANDO ELA ABRE, E POR QUE NÃO ABRE SEMPRE (2026-09-17)
 * ---------------------------------------------------------------------------
 *
 * Dez portas e um Próximo Passo na mesma dobra são DUAS respostas para a
 * mesma pergunta — "e agora?" — e a de cima ganha. O comentário do próprio
 * `ProximoPasso` já dizia que escolher entre dez coisas é o jeito mais
 * confiável de não fazer nenhuma; a vitrine tinha sido posta exatamente
 * acima dele.
 *
 * A saída não é escolher entre vitrine e ação: é saber QUANDO cada uma
 * responde melhor.
 *
 * - **Aluno sem medida nenhuma** (nunca respondeu): o Próximo Passo cai no
 *   último degrau, "responda uma prova", que é verdadeiro mas fraco — ele não
 *   sabe ainda o que o produto tem. A vitrine é a peça forte. Abre inteira.
 * - **Aluno com trajetória**: o passo é uma revisão que vence hoje ou o bloco
 *   que ele mesmo marcou. Aí a vitrine vira ruído sobre uma decisão já
 *   tomada, e desce para a seção "Explorar", fechada, ao alcance de um
 *   clique (ver `ExplorarOSapiens`).
 *
 * `compacto` é o que a seção Explorar usa: a grade sem o cabeçalho grande,
 * porque quem desenha o título ali é a seção.
 *
 * Três regras que não se quebram aqui:
 *
 * 1. **Cada portal faz uma PERGUNTA, não anuncia um recurso.** "Banco de
 *    questões" descreve a ferramenta; "qual erro você repete sem perceber?"
 *    descreve o que o aluno vai descobrir. Curiosidade é a moeda desta tela.
 * 2. **Número só entra quando é MEDIDO.** O selo de estado lê o dado real que
 *    o Painel já carregou (fila vencida, blocos da semana, questões
 *    respondidas). Onde não há medida, o portal diz "ainda não explorado" —
 *    que é verdade e, ainda por cima, é o convite mais forte da grade.
 * 3. **Nada aqui é beco sem saída.** Todo card é um link inteiro, no mouse, no
 *    toque e no teclado.
 *
 * O "não explorado" mora no `localStorage` de propósito: é conveniência de
 * quem está olhando, não estado do produto — se o navegador estiver de
 * anônimo ou bloquear, a grade continua correta, só volta a chamar tudo de
 * novo. Nunca guarde aqui nada que precise ser verdade no servidor.
 */

const CHAVE_VISITADOS = "sapiens:portais-visitados";

function lerVisitados() {
  try {
    const cru = localStorage.getItem(CHAVE_VISITADOS);
    return cru ? new Set(JSON.parse(cru)) : new Set();
  } catch {
    return new Set();
  }
}

function marcarVisitado(id) {
  try {
    const atual = lerVisitados();
    atual.add(id);
    localStorage.setItem(CHAVE_VISITADOS, JSON.stringify([...atual]));
  } catch {
    /* navegador sem armazenamento: a grade funciona igual */
  }
}

const TOTAL_TERRITORIOS = 56;

export default function PortaisDaJornada({
  habilidades = [],
  revisoes = null,
  cronograma = null,
  redacoes = [],
  engajamento = null,
  conquistas = [],
  totalRespondidas = 0,
  compacto = false,
  testid = "portais",
}) {
  const nav = useNavigate();
  const [visitados, setVisitados] = useState(lerVisitados);

  const tocados = habilidades.filter((h) => h.respondidas > 0).length;
  // `resumo.questoes` é o tamanho da fila DE HOJE — não existe `vencidas` no
  // payload, e inventar o nome do campo devolveria 0 para sempre. Mesma
  // leitura de `ProximoPasso.escolherPasso`, de propósito: dois números
  // diferentes para a mesma fila, na mesma tela, leem como bug.
  const vencidas = revisoes?.resumo?.questoes ?? 0;
  const blocosFeitos = cronograma?.total_concluidos ?? 0;
  const blocosTotal = cronograma?.total_blocos ?? 0;
  const medalhas = conquistas.filter((c) => c.desbloqueada).length;
  // A nota vem dentro de `avaliacao`, e redação sem correção não tem nenhuma.
  const ultimaNota = redacoes.find((r) => r?.avaliacao?.nota_total != null)?.avaliacao?.nota_total ?? null;
  const ofensiva = engajamento?.ofensiva?.dias ?? 0;

  const portais = useMemo(
    () => [
      {
        id: "praticar",
        rota: "/exams",
        icone: PlayCircle,
        nome: "Praticar",
        pergunta: "Qual erro você repete sem perceber?",
        estado: totalRespondidas > 0 ? `${totalRespondidas} respondidas` : null,
        cor: "#7FD8FF",
      },
      {
        id: "treino",
        rota: "/treino",
        icone: Compass,
        nome: "Mapa de treino",
        pergunta: `${TOTAL_TERRITORIOS} territórios. Você pisou em ${tocados}.`,
        progresso: { feito: tocados, total: TOTAL_TERRITORIOS },
        cor: "#8B7BFF",
      },
      {
        id: "revisoes",
        rota: "/revisoes",
        icone: RotateCw,
        nome: "Revisões",
        pergunta:
          vencidas > 0
            ? "O que você aprendeu ontem ainda está aí?"
            : "O esquecimento tem hora marcada. Veja a sua.",
        estado: vencidas > 0 ? `${vencidas} vencem hoje` : null,
        urgente: vencidas > 0,
        cor: "#FFB86B",
      },
      {
        id: "redacao",
        rota: "/redacao",
        icone: PenLine,
        nome: "Redação",
        pergunta:
          ultimaNota != null
            ? "Dá para subir da última nota. Onde exatamente?"
            : "Sua redação valeria quanto hoje?",
        estado: ultimaNota != null ? `última: ${ultimaNota}` : null,
        cor: "#7FE8C0",
      },
      {
        id: "mentis",
        rota: "/mentis",
        icone: null,
        mentis: true,
        nome: "Falar com a Mentis",
        pergunta: "Pergunte por que você erra o que erra.",
        cor: "#7FD8FF",
      },
      {
        id: "cronograma",
        rota: "/cronograma",
        icone: CalendarDays,
        nome: "Sua semana",
        pergunta: "A decisão do que estudar hoje já está tomada.",
        estado: blocosTotal > 0 ? `${blocosFeitos}/${blocosTotal} feitos` : null,
        progresso: blocosTotal > 0 ? { feito: blocosFeitos, total: blocosTotal } : null,
        cor: "#8B7BFF",
      },
      {
        id: "perfil",
        rota: "/cognitive-profile",
        icone: Gauge,
        nome: "Seu perfil",
        pergunta: "No que você já é bom — e ninguém te disse.",
        cor: "#7FE8C0",
      },
      {
        id: "live",
        rota: "/aula-ao-vivo",
        icone: Radio,
        nome: "Aula ao vivo",
        pergunta: "Quinta, 20h, com quem passou em 1º na USP.",
        urgente: true,
        cor: "#FF8FA8",
      },
      {
        id: "comunidade",
        rota: "/comunidade",
        icone: Users,
        nome: "Mural de dúvidas",
        pergunta: "Ninguém trava sozinho.",
        cor: "#FFB86B",
      },
      {
        id: "conquistas",
        rota: "/conquistas",
        icone: Trophy,
        nome: "Conquistas",
        pergunta: "A próxima medalha está a quantos acertos?",
        estado: conquistas.length ? `${medalhas}/${conquistas.length}` : null,
        progresso: conquistas.length ? { feito: medalhas, total: conquistas.length } : null,
        cor: "#FFD479",
      },
    ],
    [tocados, vencidas, blocosFeitos, blocosTotal, medalhas, conquistas.length, ultimaNota, totalRespondidas],
  );

  const abrir = useCallback(
    (id) => {
      marcarVisitado(id);
      setVisitados((s) => new Set(s).add(id));
    },
    [],
  );

  /** "Surpreenda-me": sorteia entre o que o aluno AINDA NÃO abriu. Quando já
   *  conhece tudo, sorteia entre tudo — a porta nunca devolve "não tem nada". */
  const surpresa = useCallback(() => {
    const inexplorados = portais.filter((p) => !visitados.has(p.id));
    const pool = inexplorados.length ? inexplorados : portais;
    const escolhido = pool[Math.floor(Math.random() * pool.length)];
    abrir(escolhido.id);
    nav(escolhido.rota);
  }, [portais, visitados, abrir, nav]);

  const novos = portais.filter((p) => !visitados.has(p.id)).length;

  return (
    <section data-testid={testid} data-tour="dash-portais">
      {/* O cabeçalho grande só existe no modo vitrine. Dentro de "Explorar"
          quem já anunciou a seção foi a própria seção, e repetir o título ali
          seria o mesmo texto duas vezes em quatro centímetros de tela. */}
      {!compacto && (
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <div className="secao-olho inline-flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-[#7FD8FF]" /> Por onde começar hoje
            </div>
            <h2 className="mt-1.5 font-display text-xl font-extrabold tracking-tight text-white md:text-2xl">
              {ofensiva > 0
                ? `${ofensiva} ${ofensiva === 1 ? "dia" : "dias"} seguidos. Escolha o de hoje.`
                : "Dez portas. Cada uma te conta algo que você ainda não sabe."}
            </h2>
          </div>
          <button
            type="button"
            onClick={surpresa}
            className="pill btn-vidro inline-flex shrink-0 items-center gap-2 rounded-full px-4 py-2.5 text-xs font-semibold"
            data-testid={`${testid}-surpresa`}
            title={novos ? `${novos} portas você ainda não abriu` : "Sorteia uma porta"}
          >
            <Shuffle className="h-3.5 w-3.5" /> Surpreenda-me
            {novos > 0 && <span className="text-[#7FD8FF]">· {novos} novas</span>}
          </button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
        {portais.map((p) => {
          const Icone = p.icone;
          const novo = !visitados.has(p.id);
          return (
            <Link
              key={p.id}
              to={p.rota}
              onClick={() => abrir(p.id)}
              className="group superficie relative flex flex-col justify-between overflow-hidden p-4 transition duration-200 hover:-translate-y-1 hover:border-white/25 focus-visible:-translate-y-1"
              data-testid={`${testid}-${p.id}`}
              style={{ "--portal": p.cor }}
            >
              {/* O brilho que acende no hover. `pointer-events-none` para não
                  roubar o clique do card, que é o alvo inteiro. */}
              <span
                aria-hidden
                className="pointer-events-none absolute -right-6 -top-6 h-20 w-20 rounded-full opacity-0 blur-2xl transition-opacity duration-300 group-hover:opacity-60"
                style={{ background: p.cor }}
              />
              <div className="relative">
                <div className="flex items-start justify-between gap-2">
                  <span
                    className="flex h-10 w-10 items-center justify-center rounded-2xl border transition-transform duration-200 group-hover:scale-110"
                    style={{ borderColor: `${p.cor}40`, background: `${p.cor}14`, color: p.cor }}
                  >
                    {p.mentis ? <Mentis className="h-7 w-7" variante="icone" /> : <Icone className="h-5 w-5" strokeWidth={1.8} />}
                  </span>
                  {/* O selo do canto: a MEDIDA sempre ganha do rótulo "novo".
                      Na primeira visita nada tinha sido aberto ainda, então
                      todo card mostrava "novo" e engolia justamente o número
                      que mais convida a entrar ("7 vencem hoje"). Quem nunca
                      abriu aquela porta continua sabendo disso pelo ponto
                      pulsante ao lado do nome. */}
                  {p.estado ? (
                    <span
                      className={`rounded-full px-2 py-0.5 font-mono-alt text-[9px] font-bold uppercase tracking-[0.12em] ${
                        p.urgente
                          ? "border border-amber-300/30 bg-amber-400/12 text-amber-100"
                          : "border border-white/10 bg-white/5 text-white/50"
                      }`}
                    >
                      {p.estado}
                    </span>
                  ) : (
                    novo && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-[#7FD8FF]/30 bg-[#7FD8FF]/10 px-2 py-0.5 font-mono-alt text-[9px] font-bold uppercase tracking-[0.14em] text-[#7FD8FF]">
                        <span className="relative flex h-1.5 w-1.5">
                          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#7FD8FF] opacity-75" />
                          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#7FD8FF]" />
                        </span>
                        novo
                      </span>
                    )
                  )}
                </div>

                <div className="mt-3 flex items-center gap-1.5 font-display text-sm font-bold tracking-tight text-white">
                  {novo && p.estado && (
                    <span className="relative flex h-1.5 w-1.5 shrink-0" title="você ainda não abriu esta">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#7FD8FF] opacity-75" />
                      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#7FD8FF]" />
                    </span>
                  )}
                  {p.nome}
                </div>
                <div className="mt-1 text-xs leading-relaxed text-white/50">{p.pergunta}</div>
              </div>

              <div className="relative mt-4">
                {p.progresso && p.progresso.total > 0 && (
                  <div className="mb-2.5 h-1 w-full overflow-hidden rounded-full bg-white/8">
                    <div
                      className="h-full rounded-full transition-[width] duration-500"
                      style={{
                        width: `${Math.min(100, Math.round((p.progresso.feito / p.progresso.total) * 100))}%`,
                        background: p.cor,
                      }}
                    />
                  </div>
                )}
                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-white/35 transition-colors group-hover:text-white/80">
                  Descobrir
                  <ArrowRight className="h-3 w-3 transition-transform duration-200 group-hover:translate-x-0.5" />
                </span>
              </div>
            </Link>
          );
        })}
      </div>

      {/* No modo compacto o sorteio desce para cá: ele é bom demais para
          sumir — é o único caminho do produto que não exige o aluno já saber
          o que quer — mas não é o que a seção anuncia, então vira rodapé. */}
      {compacto && (
        <button
          type="button"
          onClick={surpresa}
          className="pill btn-vidro mt-3 inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-xs font-semibold"
          data-testid={`${testid}-surpresa`}
          title={novos ? `${novos} portas você ainda não abriu` : "Sorteia uma porta"}
        >
          <Shuffle className="h-3.5 w-3.5" /> Surpreenda-me
          {novos > 0 && <span className="text-[#7FD8FF]">· {novos} novas</span>}
        </button>
      )}
    </section>
  );
}
