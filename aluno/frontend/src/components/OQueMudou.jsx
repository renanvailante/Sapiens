import { Link } from "react-router-dom";
import {
  RotateCw, PenLine, Flame, CalendarClock, Trophy, ArrowRight, GraduationCap, TrendingUp, Bookmark,
} from "lucide-react";
import { ROTAS, ANCORAS, com } from "../lib/rotas";
import { diaLocal } from "../lib/atividade";
import { rotuloDoProcesso } from "../lib/rotulosDoMotor";

/**
 * O QUE MUDOU — os EVENTOS do aluno, não os lugares do produto.
 *
 * ---------------------------------------------------------------------------
 * O QUE ISTO SUBSTITUI
 * ---------------------------------------------------------------------------
 *
 * O Hoje tinha quatro blocos que eram, cada um, um resumo de outra aba: a tira
 * da semana (Agenda), o aviso de revisão (Agenda de novo), a grade de focos e
 * domínio (Progresso) e a fileira de conquistas (Progresso de novo). Somados,
 * eram ~12 blocos simultâneos e três respostas para "e agora?" na mesma
 * rolagem — e nenhum deles era a coisa em si: eram vitrines de vitrines.
 *
 * A pergunta que o Hoje responde é "e agora?", e ela tem duas metades:
 *
 *   1. **o que eu faço** → `ProximoPasso`, uma ação, escolhida numa escada de
 *      prioridade. Continua sendo a primeira coisa da tela.
 *   2. **o que aconteceu enquanto eu não estava aqui** → esta peça.
 *
 * A diferença entre um resumo e um evento é o que os torna complementares:
 * um resumo ("você tem 12 blocos na semana") existe sempre e por isso não
 * chama atenção; um evento ("sua redação foi corrigida") só existe quando
 * aconteceu, e por isso pode.
 *
 * ---------------------------------------------------------------------------
 * AS TRÊS REGRAS
 * ---------------------------------------------------------------------------
 *
 * 1. **Zero requisição.** Tudo aqui sai dos payloads que o Hoje já carregou —
 *    a mesma disciplina do `ProximoPasso`. Um mural de novidades que fizesse
 *    quatro chamadas para montar cinco linhas seria a forma mais cara
 *    possível de dizer o que já estava na mão. Ver `custo-de-leitura.md`.
 *
 * 2. **Nada genérico.** Cada linha cita um número ou uma data do próprio
 *    aluno. Se a frase serve para qualquer aluno do Sapiens, ela não deveria
 *    ter sido dita: um painel que enche de avisos vazios ensina a ignorar o
 *    painel, e aí o aviso que importava some junto.
 *
 * 3. **Não repete o Próximo Passo.** Quando a ação do topo já é a fila de
 *    revisão, a linha da fila não aparece aqui. Duas peças cobrando a mesma
 *    coisa na mesma rolagem leem como duas coisas a fazer.
 *
 * Sem eventos, a seção inteira não é desenhada — um cabeçalho "o que mudou"
 * sobre "nada mudou" é ruído com aparência de informação.
 *
 * ---------------------------------------------------------------------------
 * A MICROVITÓRIA (2026-09-28)
 * ---------------------------------------------------------------------------
 *
 * O único evento que faltava era o mais importante: "hoje consegui algo que
 * antes não conseguia". Ele já existia no dado — a trajetória da revisão
 * espaçada grava um marco quando o aluno ACERTA a revisão marcada de um ponto
 * (`reteste_ok`) e quando acerta o mesmo raciocínio num contexto diferente
 * daquele em que errava (`transferencia`) — e só aparecia enterrado no fim do
 * Progresso. Os dois marcos só nascem de acerto (`revisao_espacada.py`),
 * então a frase é verdade por construção. E ela DESCREVE, não alega causa:
 * com o portão de crença desligado, "você melhorou por causa da revisão" é
 * uma afirmação que o produto não pode fazer (`trajetoria.nexo_causal`).
 *
 * O Hoje carrega a trajetória junto com o resto (uma leitura O(1) do
 * `students/{uid}`); esta peça continua sem requisição própria.
 */

/**
 * As conquistas que são NOTÍCIA hoje. O catálogo é calculado no navegador e
 * não guarda data de desbloqueio — então "a última desbloqueada" era sempre a
 * mesma, e a linha "Você desbloqueou…" aparecia todo dia para sempre: um
 * resumo disfarçado de evento, o que esta peça existe para não ser.
 *
 * `vistas` é `{id: "AAAA-MM-DD"}` do dia em que cada uma apareceu pela
 * primeira vez NESTE aparelho (o Hoje guarda em `localStorage` — conveniência
 * por aparelho, não estado do produto). Na primeira visita (`vistas` nulo)
 * tudo vira "já visto" e nada é anunciado: não há como saber o que é novo, e
 * anunciar o antigo como novo seria falso. Pura; quem persiste é o Hoje.
 */
export function conquistasDoDia(conquistas = [], vistas = null, hoje = diaLocal()) {
  const desbloqueadas = (conquistas || []).filter((c) => c?.desbloqueada && c.id);
  const primeiraVez = vistas == null;
  const atualizadas = { ...(vistas || {}) };
  for (const c of desbloqueadas) {
    if (!atualizadas[c.id]) atualizadas[c.id] = primeiraVez ? "antes" : hoje;
  }
  const doDia = desbloqueadas.filter((c) => atualizadas[c.id] === hoje);
  return { doDia, vistas: atualizadas };
}

/** Janela da microvitória: depois de três dias ela deixa de ser notícia. */
const DIAS_DA_VITORIA = 3;

const FRASES_DA_VITORIA = {
  reteste_ok: {
    titulo: (nome) => `A revisão de «${nome}» saiu certa`,
    detalhe: "O ponto voltou na data marcada, e desta vez você acertou.",
  },
  transferencia: {
    titulo: (nome) => `Você acertou «${nome}» num contexto novo`,
    detalhe: "Não era a questão de antes: era o mesmo raciocínio, em outro assunto.",
  },
};

/** O marco de acerto mais recente da trajetória, se couber na janela. */
export function microvitoria(trajetoria) {
  let melhor = null;
  for (const h of trajetoria?.habilidades || []) {
    for (const m of h?.marcos || []) {
      if (!FRASES_DA_VITORIA[m?.tipo] || !m.quando || !h.processo_id) continue;
      // O rótulo de produto, nunca o nome do catálogo (`lib/rotulosDoMotor`).
      if (!melhor || m.quando > melhor.quando) melhor = { ...m, processo_nome: rotuloDoProcesso(h.processo_id) };
    }
  }
  if (!melhor) return null;
  const dias = diasDesde(melhor.quando);
  if (dias == null || dias > DIAS_DA_VITORIA) return null;
  return melhor;
}

function diasDesde(iso) {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  return Math.floor((Date.now() - t) / 86400000);
}

/**
 * Os eventos, em ordem de urgência. Função pura e exportada porque é ela que
 * o teste trava — regra que só se confere abrindo o navegador não se confere.
 */
export function eventosDoDia({
  revisoes = null,
  cronograma = null,
  redacoes = [],
  engajamento = null,
  conquistas = [],
  passoAtual = null,
  trajetoria = null,
  lembretes = null,
} = {}) {
  const eventos = [];

  // 1. O QUE TEM PRAZO. A fila de revisão é a única coisa do produto com data
  //    por baixo: revisar depois do dia em que vence rende menos.
  const vencidas = revisoes?.resumo?.questoes ?? 0;
  if (vencidas > 0 && passoAtual?.chave !== "revisao") {
    eventos.push({
      chave: "revisao",
      icone: RotateCw,
      cor: "text-amber-300",
      titulo: vencidas === 1 ? "1 questão voltou para revisão" : `${vencidas} questões voltaram para revisão`,
      detalhe: "Revisar no dia em que vence é o que faz a memória durar.",
      rota: com(ROTAS.AGENDA, ANCORAS.AGENDA_REVISOES),
      cta: "Ver a fila",
    });
  }

  // 1b. O QUE VOCÊ GUARDOU E VOLTOU. A revisão programada dos trechos que o
  //     próprio aluno marcou (`/lembretes`, escada de 1-3-7-16-35 dias): o
  //     motivo para abrir o app amanhã é ele mesmo quem escolheu.
  const voltaram = lembretes?.vencidos ?? 0;
  if (voltaram > 0) {
    const de = lembretes?.primeiro_vencido?.titulo;
    eventos.push({
      chave: "lembretes",
      icone: Bookmark,
      cor: "text-amber-300",
      titulo: voltaram === 1 ? "1 trecho que você guardou voltou hoje" : `${voltaram} trechos que você guardou voltaram hoje`,
      detalhe: de ? `O primeiro é de «${de}».` : "Rever no dia da volta é o que faz a memória durar.",
      rota: com(ROTAS.AGENDA, ANCORAS.AGENDA_LEMBRETES),
      cta: "Rever",
    });
  }

  // 2. O QUE O PRODUTO ENTREGOU. Uma redação corrigida é a devolutiva mais
  //    cara do Sapiens e a que o aluno mais espera — e ela chega sem aviso.
  const corrigida = redacoes.find((r) => r?.avaliacao?.nota_total != null);
  const diasDaCorrecao = diasDesde(corrigida?.avaliacao?.corrigida_em || corrigida?.criada_em);
  if (corrigida && diasDaCorrecao != null && diasDaCorrecao <= 3) {
    eventos.push({
      chave: "redacao",
      icone: PenLine,
      cor: "text-emerald-300",
      titulo: `Sua redação saiu: ${corrigida.avaliacao.nota_total}/1000`,
      detalhe:
        diasDaCorrecao === 0
          ? "Corrigida hoje, nas cinco competências."
          : `Corrigida há ${diasDaCorrecao} ${diasDaCorrecao === 1 ? "dia" : "dias"}, nas cinco competências.`,
      rota: ROTAS.REDACAO,
      cta: "Ler a correção",
    });
  }

  // 3. O QUE VOCÊ CONSEGUIU. Antes das pendências de agenda e da ofensiva:
  //    é o único evento que responde "estou evoluindo?", e o teto de quatro
  //    linhas o cortaria se viesse no fim.
  const vitoria = microvitoria(trajetoria);
  if (vitoria) {
    const frase = FRASES_DA_VITORIA[vitoria.tipo];
    eventos.push({
      chave: "vitoria",
      icone: TrendingUp,
      cor: "text-emerald-300",
      titulo: frase.titulo(vitoria.processo_nome),
      detalhe: frase.detalhe,
      rota: com(ROTAS.PROGRESSO, ANCORAS.PROGRESSO_TRAJETORIA),
      cta: "Ver a trajetória",
    });
  }

  // 4. O QUE VOCÊ MARCOU E NÃO CUMPRIU. O bloco de hoje que ainda não foi
  //    feito — e só ele: o resumo da semana inteira é da Agenda.
  const hoje = (cronograma?.dias || []).find((d) => d.data === diaLocal());
  const pendente = (hoje?.blocos || []).find((b) => !b.concluido);
  if (pendente && passoAtual?.chave !== `bloco-${pendente.id}`) {
    eventos.push({
      chave: "bloco",
      icone: CalendarClock,
      cor: "text-[#7FD8FF]",
      titulo: pendente.titulo,
      detalhe:
        pendente.inicio && pendente.fim
          ? `Você marcou ${pendente.inicio}–${pendente.fim} para isto.`
          : "Você mesmo marcou esta hora.",
      rota: pendente.rota || ROTAS.AGENDA,
      cta: "Começar",
    });
  }

  // 5. A SEQUÊNCIA EM RISCO. Só quando há sequência DE VERDADE a perder e o
  //    dia ainda não está garantido — nunca um aviso construído sobre um
  //    número que não existe. Ver a linha ética em `engajamento.py`.
  const ofensiva = engajamento?.ofensiva?.dias ?? 0;
  const estudouHoje = engajamento?.ofensiva?.estudou_hoje ?? true;
  if (ofensiva >= 2 && !estudouHoje) {
    eventos.push({
      chave: "ofensiva",
      icone: Flame,
      cor: "text-orange-300",
      titulo: `Você está no dia ${ofensiva} e ainda não estudou hoje`,
      detalhe: "Uma questão já conta e mantém a corrente de pé.",
      rota: ROTAS.ESTUDAR,
      cta: "Estudar agora",
    });
  }

  // 6. O CURSO PARADO. `cronograma` traz o que a semana reservou para estudo
  //    de curso; se há bloco de curso e nenhum foi concluído, houve uma aula
  //    começada que ficou pelo caminho.
  const curso = (hoje?.blocos || []).find((b) => b.tipo === "curso" && !b.concluido);
  if (curso && curso !== pendente) {
    eventos.push({
      chave: "curso",
      icone: GraduationCap,
      cor: "text-violet-300",
      titulo: curso.titulo,
      detalhe: "A estação onde você parou continua aberta.",
      rota: curso.rota || ROTAS.CURSOS,
      cta: "Retomar",
    });
  }

  // 7. O RECONHECIMENTO, por último e de propósito: um elogio no topo de uma
  //    lista de ações empurra as ações para baixo, e quem abriu o Hoje abriu
  //    para agir. O elogio é o fecho, não a manchete.
  const recente = conquistas.filter((c) => c.desbloqueada).slice(-1)[0];
  if (recente && eventos.length < 4) {
    eventos.push({
      chave: "conquista",
      icone: Trophy,
      cor: "text-amber-300",
      // O catálogo (`lib/conquistas.js`) chama o nome de `label`. Lendo só
      // `nome || titulo`, a linha saía "Você desbloqueou "undefined"" para
      // todo aluno com uma conquista.
      titulo: `Você desbloqueou "${recente.label || recente.nome || recente.titulo}"`,
      detalhe: "Está na sua sala de troféus.",
      rota: com(ROTAS.PROGRESSO, ANCORAS.PROGRESSO_CONQUISTAS),
      cta: "Ver",
    });
  }

  // Quatro é o teto. A quinta linha de uma lista de novidades já não é lida, e
  // uma lista longa reintroduz exatamente o problema que esta peça resolve.
  return eventos.slice(0, 4);
}

export default function OQueMudou(props) {
  const eventos = eventosDoDia(props);
  if (eventos.length === 0) return null;

  return (
    <section data-testid="hoje-mudou" data-tour="hoje-mudou">
      <div className="secao-cabeca">
        <h2 className="secao-titulo">O que mudou</h2>
      </div>
      <div className="grid gap-2.5 sm:grid-cols-2">
        {eventos.map((e) => (
          <Link
            key={e.chave}
            to={e.rota}
            className="superficie lift flex items-start gap-3 p-4"
            data-testid={`hoje-mudou-${e.chave}`}
          >
            <e.icone className={`mt-0.5 h-4 w-4 shrink-0 ${e.cor}`} strokeWidth={2} />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold leading-snug text-white">{e.titulo}</span>
              <span className="mt-0.5 block text-xs leading-relaxed text-white/50">{e.detalhe}</span>
              <span className="mt-1.5 inline-flex items-center gap-1 text-xs font-semibold text-[#7FD8FF]">
                {e.cta} <ArrowRight className="h-3 w-3" />
              </span>
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
