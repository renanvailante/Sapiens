import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import Tela from "../components/Tela";
import { Bloco, Linha } from "../components/Esqueleto";
import CardDeMelhora from "../components/CardDeMelhora";
import MentisGuia from "../components/MentisGuia";
import ResumoDoPainel from "../components/perfil/ResumoDoPainel";
import Calendario from "../components/perfil/Calendario";
import { CurvaDeAcerto, VolumePorSemana, ComecoEAgora } from "../components/perfil/GraficosEvolucao";
import {
  AcertoPorFrente, OndeRendeMais, DistribuicaoDoEsforco, EvolucaoPorFrente, TendenciaPorFrente,
} from "../components/perfil/GraficosFrentes";
import { EvolucaoDaRedacao, CompetenciasDaRedacao } from "../components/perfil/GraficosRedacao";
import { ContextoDaMentis } from "../components/perfil/Grafico";
import {
  QuandoVoceEstuda, AcertoPorPeriodo, SuaSemana, RitmoDeResposta,
  MudarDeResposta, DeOndeVemSuasRespostas,
} from "../components/perfil/GraficosRitmo";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { avisarSparksMudou } from "../components/Navegacao";
import { ThumbsUp, Target, ArrowRight, LineChart, Trophy, History as HistoryIcon, Loader2 } from "lucide-react";
import PainelDeSugestoes from "../components/perfil/PainelDeSugestoes";
import Trajetoria from "../components/Trajetoria";
import ConquistasELiga from "../components/progresso/ConquistasELiga";
import Historico from "../components/progresso/Historico";
import SecaoDaAba, { useAncora } from "../components/SecaoDaAba";
import { ROTAS, ANCORAS } from "../lib/rotas";

/**
 * PROGRESSO — o retrato, o filme e o que já ficou para trás.
 *
 * Pergunta mental: **estou evoluindo?**
 *
 * ---------------------------------------------------------------------------
 * CINCO TELAS VIRARAM UMA (2026-09-18)
 * ---------------------------------------------------------------------------
 *
 * O aluno tinha cinco endereços para responder a mesma pergunta, e nenhum
 * deles dizia que os outros existiam:
 *
 *   `/desempenho`   os 17 gráficos            → a seção "Evolução"
 *   `/revisoes`     (metade dela) a trajetória → a seção "Trajetória"
 *   `/conquistas`   os troféus                → a seção "Conquistas e liga"
 *   `/liga`         o ranking da semana        → a mesma seção
 *   `/history`      os simulados corrigidos    → a seção "Histórico"
 *   `/trash`        os mesmos, apagados        → um FILTRO do histórico
 *
 * A trajetória é a que mais estava fora do lugar: ela morava no fim de
 * `/revisoes`, que é uma tela de AÇÃO com prazo, e é a única peça do produto
 * que narra causalidade ("trabalhamos isto, e você melhorou"). Evidência de
 * mudança pertence a onde se pergunta se houve mudança.
 *
 * ---------------------------------------------------------------------------
 * A ORDEM DAS SEÇÕES É A ESCALA DE TEMPO
 * ---------------------------------------------------------------------------
 *
 * Retrato (agora) → Evolução (semanas) → Trajetória (por habilidade, ao longo
 * de tudo) → Conquistas (o acumulado) → Histórico (o arquivo). Quem abre a aba
 * quer saber como está; quem rola quer saber como chegou aqui.
 *
 * Dentro do retrato, desde 2026-10-19: números → gráficos → a leitura da
 * Mentis → o raciocínio. O que se VÊ vem antes do que se lê.
 *
 * ---------------------------------------------------------------------------
 * O QUE NÃO MUDOU, E NÃO PODE MUDAR
 * ---------------------------------------------------------------------------
 *
 * Os gráficos são servidos por `GET /perfil/painel` numa chamada só, com a
 * Mentis lendo tudo em voz alta no topo e apontando para o gráfico de cada
 * frase.
 *
 * A fronteira continua exatamente onde estava, e é ela que explica por que
 * esta tela tem número em todo lugar MENOS num:
 *
 *   · **frente da prova, dia, hora, tempo, volume** são o que o aluno fez —
 *     podem virar percentual, tabela e gráfico;
 *   · **a leitura cognitiva** (o que a ontologia sabe) continua saindo só em
 *     palavras, sem nome de catálogo, sem id e sem percentual. É a seção "O
 *     que a sua prática mostra", lá embaixo, e ela é de propósito a única sem
 *     um número sequer.
 */

/** As subseções de gráficos usam a MESMA peça das seções grandes, para não
 *  haver dois ritmos de cabeçalho dentro da mesma aba. */
function Secao(props) {
  return <SecaoDaAba {...props} />;
}

/**
 * A instrumentação do ciclo adaptativo, mostrada ao aluno como o que ela é:
 * uma medida. Veio junto da trajetória, de `/revisoes`.
 *
 * Medida pedagógica é de graça. O que custa Spark no Sapiens é geração de
 * conteúdo, nunca medir o que o próprio aluno produziu respondendo.
 */
function ComoVaoAsRevisoes({ dados }) {
  const r = dados?.retestes;
  const t = dados?.transferencia;
  if (!r?.total) return null;
  return (
    <div className="card-sapiens mt-4 rounded-2xl p-5" data-testid="progresso-instrumentacao">
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-400">
        Como vão as suas revisões
      </div>
      <div className="mt-3 flex flex-wrap gap-6">
        <div>
          <div className="font-display text-2xl font-extrabold tracking-tight text-zinc-950">{r.taxa}%</div>
          <div className="text-[11px] text-zinc-500">
            de acerto nas revisões ({r.acertos} de {r.total})
          </div>
        </div>
        {t?.total > 0 && (
          <div>
            <div className="font-display text-2xl font-extrabold tracking-tight text-zinc-950">{t.taxa}%</div>
            <div className="text-[11px] text-zinc-500">
              quando a mesma habilidade aparece em outro contexto ({t.acertos} de {t.total})
            </div>
          </div>
        )}
      </div>
      {t?.total > 0 && (
        <p className="mt-3 text-xs leading-relaxed text-zinc-500">
          O segundo número é o que importa: acertar a revisão pode ser memória da questão. Acertar em
          outro contexto é a habilidade.
        </p>
      )}
    </div>
  );
}

function Esqueleto() {
  return (
    <div className="space-y-6" data-testid="perfil-carregando" aria-busy="true">
      <Bloco className="rounded-[26px]" altura={196} />
      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-5">
        {[0, 1, 2, 3, 4].map((i) => <Bloco key={i} className="rounded-3xl" altura={104} />)}
      </div>
      <Linha w="12rem" h={20} />
      <div className="grid gap-3 lg:grid-cols-2">
        {[0, 1, 2, 3].map((i) => <Bloco key={i} className="rounded-3xl" altura={300} />)}
      </div>
    </div>
  );
}

export default function Progresso() {
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [indice, setIndice] = useState(0);
  const jaNavegou = useRef(false);
  // A trajetória por habilidade, que era a metade analítica de `/revisoes`.
  // Uma leitura, independente de quantas questões o aluno já respondeu.
  const [trajetoria, setTrajetoria] = useState(null);
  const [carregandoTrajetoria, setCarregandoTrajetoria] = useState(true);

  const carregar = useCallback(() => {
    setCarregando(true);
    setErro(null);
    api
      .get("/perfil/painel")
      .then(({ data }) => setDados(data))
      .catch((e) => setErro(errMsg(e, "Não foi possível carregar o seu painel agora.")))
      .finally(() => setCarregando(false));
  }, []);

  useEffect(carregar, [carregar]);

  useEffect(() => {
    let ativo = true;
    api
      .get("/revisao/trajetoria")
      .then(({ data }) => { if (ativo) setTrajetoria(data); })
      // `indisponivel` e não uma lista vazia: "nada aconteceu com as suas
      // habilidades" é uma afirmação sobre o aluno, e não é para ser feita
      // por causa de uma falha de rede.
      .catch(() => { if (ativo) setTrajetoria({ indisponivel: true, habilidades: [] }); })
      .finally(() => { if (ativo) setCarregandoTrajetoria(false); });
    return () => { ativo = false; };
  }, []);

  const leituras = dados?.mentis?.leituras || [];
  const atual = leituras[Math.min(indice, Math.max(0, leituras.length - 1))];
  const ancora = atual?.ancora;

  // A Mentis APONTA: trocar de leitura leva a tela até o gráfico que sustenta
  // a frase. Só a partir da primeira navegação — rolar a página sozinha na
  // abertura roubaria o cabeçalho de quem acabou de chegar.
  const trocar = useCallback((calcular) => {
    jaNavegou.current = true;
    setIndice((i) => (typeof calcular === "function" ? calcular(i) : calcular));
  }, []);

  useEffect(() => {
    if (!jaNavegou.current || !ancora) return;
    const alvo = document.getElementById(ancora);
    if (alvo) alvo.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [ancora, indice]);

  // De âncora para leitura: é isto que faz cada cartão saber se a Mentis tem
  // algo a dizer sobre ELE. A primeira leitura de cada âncora ganha o cartão —
  // duas bolhas no mesmo gráfico seriam duas vozes falando juntas.
  const porAncora = {};
  leituras.forEach((l, i) => {
    if (!porAncora[l.ancora]) porAncora[l.ancora] = { ...l, indice: i };
  });

  const primeiroFoco = dados?.frentes?.linhas?.[0]?.nome;
  useDeclararContextoMentis(
    primeiroFoco
      ? `Vendo o painel do perfil cognitivo. A matéria no topo da prioridade dele é ${primeiroFoco}.`
      : "Vendo o painel do perfil cognitivo."
  );

  const aceso = (id) => ancora === id;

  // `/conquistas`, `/liga`, `/history` e `/trash` redirecionam para cá com
  // âncora. Sem isto, os quatro links caem no topo da aba e o aluno recebe um
  // gráfico de acertos onde clicou por troféus.
  useAncora(carregando);

  return (
    <Tela
      largura="xxl"
      titulo="Progresso"
      subtitulo="Feito só das suas respostas — nada estimado. Onde a amostra é pequena, está escrito."
      testid="progresso"
    >
      {/* O QUE FAZER COM ISTO. O painel descreve; o balão prescreve. Ele só
          aparece quando há dado suficiente para uma sugestão que cite um
          número deste aluno — ver `lib/sugestoes.js`. Fica fora do fluxo
          (`position: fixed`), então não muda o layout de nenhum gráfico, e
          recolhe na horizontal para o canto direito continuar sendo de quem
          está comparando duas curvas. */}
      {!carregando && !erro && dados && <PainelDeSugestoes painel={dados} />}

      {carregando ? (
        <Esqueleto />
      ) : erro ? (
        <div className="card-sapiens rounded-3xl p-6 text-center">
          <div className="text-zinc-600">{erro}</div>
          <button
            onClick={carregar}
            className="pill btn-sapiens mt-4 rounded-full px-4 py-2 text-sm font-medium"
          >
            Tentar de novo
          </button>
        </div>
      ) : dados?.amostra_insuficiente ? (
        <div className="card-sapiens rounded-3xl p-7 text-center" data-testid="perfil-vazio">
          <div className="font-display text-lg font-bold text-zinc-950">
            O seu painel começa na próxima questão.
          </div>
          <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-zinc-500">
            Ainda são {dados.resumo.respondidas} respostas registradas. A partir de{" "}
            {dados.minimo_para_painel} eu já consigo desenhar a sua primeira curva — e ela só fica
            interessante quando você responde em dias diferentes.
          </p>
          <Link
            to="/estudar/provas"
            className="pill btn-sapiens mt-5 inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium"
            data-testid="perfil-vazio-praticar"
          >
            Responder questões <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      ) : (
        <ContextoDaMentis.Provider
          value={{ porAncora, ativa: ancora, aoFocar: (i) => trocar(() => i) }}
        >
        <div className="space-y-10">
          {/* OS NÚMEROS E OS GRÁFICOS PRIMEIRO (2026-10-19). Pedido do dono:
              "os gráficos bem evidentes lá em cima, e não lá embaixo". Antes
              a aba abria com a leitura da Mentis e com a seção de raciocínio
              (só texto) — a primeira curva aparecia na terceira dobra. Agora:
              os cinco números, e logo abaixo a curva de acerto em largura
              inteira, que é a resposta direta a "estou evoluindo?". A leitura
              da Mentis e o raciocínio vêm depois dos gráficos que eles
              comentam — e cada gráfico continua com a bolha dela. */}
          <ResumoDoPainel resumo={dados.resumo} />

          <Secao
            olho="A mudança"
            titulo="Como você está evoluindo"
          >
            <div className="grid gap-3 lg:grid-cols-2">
              <div className="lg:col-span-2">
                <CurvaDeAcerto diaria={dados.evolucao.diaria} destacado={aceso("evolucao")} />
              </div>
              <ComecoEAgora comparativo={dados.evolucao.comparativo} destacado={aceso("comparativo")} />
              <VolumePorSemana semanal={dados.evolucao.semanal} destacado={aceso("volume")} />
              <TendenciaPorFrente
                tendencia={dados.frentes.tendencia}
                semanas={dados.frentes.janela_tendencia_semanas}
                destacado={aceso("tendencia")}
              />
              <EvolucaoPorFrente porFrente={dados.evolucao.por_frente} destacado={aceso("evolucao-frente")} />
            </div>
          </Secao>

          <Secao
            olho="A prova"
            titulo="Onde a sua nota está sendo decidida"
            descricao="Matéria por matéria, com o peso de cada uma no ENEM."
          >
            <div className="grid gap-3 lg:grid-cols-2">
              <AcertoPorFrente linhas={dados.frentes.linhas} destacado={aceso("frentes")} />
              <OndeRendeMais linhas={dados.frentes.linhas} destacado={aceso("prioridade")} />
              <DistribuicaoDoEsforco linhas={dados.frentes.linhas} destacado={aceso("esforco")} />
              <Calendario constancia={dados.constancia} destacado={aceso("constancia")} />
            </div>
          </Secao>

          {leituras.length > 0 && (
            <MentisGuia
              leituras={leituras}
              indice={Math.min(indice, leituras.length - 1)}
              aoTrocar={trocar}
              aoSaldo={avisarSparksMudou}
            />
          )}

          {/* O RACIOCÍNIO — a única seção sem número, de propósito (ver
              `Forcas`). Vem depois dos gráficos: é a leitura deles. */}
          <Forcas forcas={dados.forcas} destacado={aceso("forcas")} />

          <Secao
            olho="Mil pontos"
            titulo="A sua redação"
            descricao="O único componente da prova que não depende de acertar questão — e o que mais sobe com treino."
          >
            <div className="grid gap-3 lg:grid-cols-2">
              <EvolucaoDaRedacao redacao={dados.redacao} destacado={aceso("redacao")} />
              <CompetenciasDaRedacao redacao={dados.redacao} destacado={aceso("competencias")} />
            </div>
          </Secao>

          <Secao
            olho="O seu jeito"
            titulo="Como você estuda"
            descricao="Horário, ritmo e hábito. Isto descreve o que você fez — não é um veredito sobre quem você é."
          >
            <div className="grid gap-3 lg:grid-cols-2">
              <QuandoVoceEstuda porHora={dados.ritmo.por_hora} destacado={aceso("ritmo")} />
              <AcertoPorPeriodo blocos={dados.ritmo.blocos} destacado={aceso("periodo")} />
              <SuaSemana porDiaSemana={dados.ritmo.por_dia_semana} destacado={aceso("semana")} />
              <RitmoDeResposta faixas={dados.ritmo.por_faixa_de_tempo} destacado={aceso("tempo")} />
              <MudarDeResposta decisao={dados.habitos.decisao} destacado={aceso("habitos")} />
              <DeOndeVemSuasRespostas origem={dados.habitos.origem} destacado={aceso("origem")} />
            </div>
          </Secao>

          <Rodape cobertura={dados.cobertura} />
        </div>
        </ContextoDaMentis.Provider>
      )}

      {/* ─── TRAJETÓRIA ─────────────────────────────────────────────────
          A metade analítica da antiga tela de revisões. Ela é a ÚNICA peça do
          produto que narra causalidade — "trabalhamos isto, e você melhorou" —
          e é a afirmação mais forte que o Sapiens faz sobre alguém. Enquanto o
          perfil for provisório (anotação sem revisão humana), ela DESCREVE o
          que aconteceu e não afirma por quê: quem decide isso é o servidor, em
          `nexo_causal`, e a tela obedece. Não é conservadorismo — é a
          diferença entre relatar e alegar.

          Fica fora do bloco de gráficos de propósito: ela não depende de
          `amostra_insuficiente`, porque quem tem pouca resposta para uma curva
          pode já ter uma habilidade com história. */}
      <div className="mt-14 space-y-14">
        <SecaoDaAba
          id={ANCORAS.PROGRESSO_TRAJETORIA}
          icone={LineChart}
          olho="Habilidade por habilidade"
          titulo="A sua trajetória"
          descricao="O que aconteceu com cada habilidade ao longo do tempo — não o seu estado de hoje."
        >
          {carregandoTrajetoria ? (
            <div className="flex items-center gap-2 text-sm text-white/50">
              <Loader2 className="h-4 w-4 animate-spin" /> Carregando…
            </div>
          ) : (
            <>
              <Trajetoria dados={trajetoria} />
              <ComoVaoAsRevisoes dados={trajetoria?.instrumentacao} />
            </>
          )}
        </SecaoDaAba>

        {/* ─── CONQUISTAS E LIGA ──────────────────────────────────────── */}
        <SecaoDaAba
          id={ANCORAS.PROGRESSO_CONQUISTAS}
          icone={Trophy}
          olho="O que o seu esforço rendeu"
          titulo="Conquistas e liga"
          descricao="Troféu é o que você já provou e não zera. A liga é onde você está agora, contra os outros alunos — e ela zera toda segunda."
        >
          <ConquistasELiga />
        </SecaoDaAba>

        {/* ─── HISTÓRICO ──────────────────────────────────────────────── */}
        <SecaoDaAba
          id={ANCORAS.PROGRESSO_HISTORICO}
          icone={HistoryIcon}
          olho="O arquivo"
          titulo="Simulados que você corrigiu"
          descricao="Cada tentativa fica guardada por inteiro: refazer uma prova nunca sobrescreve a análise anterior."
        >
          <Historico />
        </SecaoDaAba>
      </div>
    </Tela>
  );
}

/**
 * A ÚNICA SEÇÃO SEM NÚMERO — e isso é uma decisão, não um esquecimento.
 *
 * O que está aqui vem da ontologia (o catálogo cognitivo do produto), e a
 * regra é antiga: o aluno recebe o RÓTULO e a EXPLICAÇÃO, escritos à mão, e
 * nunca o nome interno, o id nem o percentual por trás. Um número ao lado
 * destes cartões entregaria a medida de um nó do catálogo — que é justamente
 * o que a fronteira de `perfil_pedagogico` existe para não deixar sair.
 */
function Forcas({ forcas, destacado }) {
  const fortes = forcas?.pontos_fortes || [];
  const desenvolver = forcas?.pontos_a_desenvolver || [];
  if (!fortes.length && !desenvolver.length) return null;

  return (
    <section id="forcas" style={{ scrollMarginTop: "6rem" }}>
      <div className="secao-olho">O raciocínio</div>
      <h2 className="mt-1.5 font-display text-xl font-bold tracking-tight text-white md:text-2xl">
        O que a sua prática mostra de você
      </h2>
      <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-white/50">
        Esta parte não vem em porcentagem de propósito: é leitura, não placar.
      </p>

      <div
        className={`mt-4 grid gap-6 rounded-3xl md:grid-cols-2 ${
          destacado ? "ring-1 ring-[#4FD9FF]/40 p-3 -m-3" : ""
        }`}
      >
        <div>
          <h3 className="flex items-center gap-2 font-display text-base font-bold text-white">
            <ThumbsUp className="h-4 w-4 text-emerald-400" /> Onde você já manda bem
          </h3>
          <div className="mt-3 space-y-2.5">
            {fortes.map((item, i) => (
              <div
                key={i}
                className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4"
                data-testid="perfil-cartao-forte"
              >
                <div className="font-display font-bold text-emerald-900">{item.rotulo}</div>
                <p className="mt-1 text-sm leading-relaxed text-zinc-700">{item.explicacao}</p>
              </div>
            ))}
            {fortes.length === 0 && (
              <p className="text-sm text-white/45">
                Ainda não há respostas suficientes para eu apontar um ponto forte com segurança.
              </p>
            )}
          </div>
        </div>

        <div>
          <h3 className="flex items-center gap-2 font-display text-base font-bold text-white">
            <Target className="h-4 w-4 text-amber-400" /> O que vale destravar
          </h3>
          <div className="mt-3 space-y-2.5">
            {desenvolver.map((item, i) => (
              <CardDeMelhora
                key={i}
                titulo={item.rotulo}
                descricao={item.explicacao}
                treino={{ href: ROTAS.TREINO, rotulo: "Ir para o Treino" }}
                assunto={item.rotulo}
                testid={`perfil-cartao-fraco-${i}`}
              />
            ))}
            {desenvolver.length === 0 && (
              <p className="text-sm text-white/45">
                Nada com amostra suficiente para virar um ponto de atenção. Continue praticando.
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

/** A honestidade de amostra, no rodapé: quantas das respostas do aluno estão
 *  no acervo anotado por matéria. Sem isto, o gráfico de matérias parece
 *  descrever tudo o que ele respondeu — e não descreve. */
function Rodape({ cobertura }) {
  if (!cobertura?.eventos) return null;
  const fora = cobertura.eventos - cobertura.com_anotacao;
  if (fora <= 0) return null;
  return (
    <p className="mt-8 border-t border-white/10 pt-4 text-xs leading-relaxed text-white/40">
      Dos seus {cobertura.eventos} registros de resposta, {cobertura.com_anotacao} vêm de questões
      catalogadas por matéria — são essas que alimentam os gráficos por matéria. As outras{" "}
      {fora} (treino, questões geradas e aulas) contam no seu esforço, na sua curva e na sua
      constância.
    </p>
  );
}
