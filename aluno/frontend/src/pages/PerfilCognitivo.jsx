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
import { avisarSparksMudou } from "../components/Nav";
import { Brain, ThumbsUp, Target, ArrowRight } from "lucide-react";

/**
 * SEU PERFIL COGNITIVO — o retrato e, agora, o filme.
 *
 * O que esta tela era: dois montes de cartões dizendo no que o aluno é bom e
 * no que não é. Verdadeiro, e inútil — um estado sem escala, sem passado e sem
 * nada para fazer com ele. Ninguém volta a uma tela dessas duas vezes.
 *
 * O que ela é agora: onze gráficos sobre o que o aluno realmente fez, servidos
 * por `GET /perfil/painel` numa chamada só, com a Mentis lendo tudo em voz
 * alta no topo e apontando para o gráfico de cada frase.
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

function Secao({ id, olho, titulo, descricao, children }) {
  return (
    <section className="mt-8" id={id} style={{ scrollMarginTop: "6rem" }}>
      <div className="secao-olho">{olho}</div>
      <h2 className="mt-1.5 font-display text-xl font-bold tracking-tight text-white md:text-2xl">
        {titulo}
      </h2>
      {descricao && <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-white/50">{descricao}</p>}
      <div className="mt-4">{children}</div>
    </section>
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

export default function PerfilCognitivo() {
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [indice, setIndice] = useState(0);
  const jaNavegou = useRef(false);

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

  return (
    <Tela
      largura="xxl"
      olho={<><Brain className="h-3.5 w-3.5" /> Seu perfil cognitivo</>}
      titulo="Tudo o que a sua prática já contou sobre você."
      subtitulo="Cada gráfico aqui é feito das suas próprias respostas — nada é estimado, nada é inventado. Onde a amostra for pequena, está escrito."
      voltar="/dashboard"
      testid="perfil"
    >
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
            to="/exams"
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
        <div className="space-y-6">
          {leituras.length > 0 && (
            <MentisGuia
              leituras={leituras}
              indice={Math.min(indice, leituras.length - 1)}
              aoTrocar={trocar}
              aoSaldo={avisarSparksMudou}
            />
          )}

          <ResumoDoPainel resumo={dados.resumo} />

          <Secao
            olho="A mudança"
            titulo="Como você está evoluindo"
            descricao="A pergunta que um retrato não responde: você está melhor do que estava?"
          >
            <div className="grid gap-3 lg:grid-cols-2">
              <CurvaDeAcerto diaria={dados.evolucao.diaria} destacado={aceso("evolucao")} />
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
            descricao="Matéria por matéria, com o peso que cada uma tem no ENEM — a mesma conta que monta o seu cronograma."
          >
            <div className="grid gap-3 lg:grid-cols-2">
              <AcertoPorFrente linhas={dados.frentes.linhas} destacado={aceso("frentes")} />
              <OndeRendeMais linhas={dados.frentes.linhas} destacado={aceso("prioridade")} />
              <DistribuicaoDoEsforco linhas={dados.frentes.linhas} destacado={aceso("esforco")} />
              <Calendario constancia={dados.constancia} destacado={aceso("constancia")} />
            </div>
          </Secao>

          <Secao
            olho="Mil pontos"
            titulo="A sua redação"
            descricao="O único componente da prova que não depende de acertar questão nenhuma — e o que mais sobe com treino."
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

          <Forcas forcas={dados.forcas} destacado={aceso("forcas")} />

          <Rodape cobertura={dados.cobertura} />
        </div>
        </ContextoDaMentis.Provider>
      )}
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
    <section className="mt-8" id="forcas" style={{ scrollMarginTop: "6rem" }}>
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
                treino={{ href: "/treino", rotulo: "Ir para o Treino" }}
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
