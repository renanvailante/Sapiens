import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import {
  Check, ArrowRight, ArrowLeft, Trophy, ShieldCheck,
} from "lucide-react";
import { api, errMsg } from "../lib/api";
import Tela from "../components/Tela";
import EstadoDeErro from "../components/EstadoDeErro";
import { Bloco as Esqueleto, Linha } from "../components/Esqueleto";
import Bloco from "../components/curso/Blocos";
import TrilhoDeProgresso from "../components/curso/TrilhoDeProgresso";
import SondagemDeDominio from "../components/curso/SondagemDeDominio";
import {
  dividirEmEtapas, etapaCumprida, etapaParaRetomar, progressoDasEtapas,
} from "../lib/etapas";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { avisarSparksMudou } from "../components/Nav";

/**
 * `/cursos/:cursoId/estacao/:estacaoId` — A SALA DE AULA, uma tela por vez.
 *
 *     explicação  →  exemplos resolvidos  →  5 exercícios  →  5 exercícios
 *
 * Era uma página só, que se rolava inteira. O conteúdo é o mesmo; o que muda
 * é o RITMO — cada trecho cabe numa tela, termina num "Continuar" e dá a
 * sensação de ter terminado alguma coisa. O empréstimo é declarado (Duolingo)
 * e a razão de funcionar é velha: tarefa com fim visível é tarefa que se
 * começa. Quem volta não recomeça: cai na etapa onde parou
 * (`etapaParaRetomar`).
 *
 * **A tela não corrige nada e não sabe nenhum gabarito.** Cada resposta vai
 * para o servidor, que devolve o degrau de devolutiva que aquela tentativa
 * merece (dica → comentário do erro → resolução). A conclusão também é dele:
 * quando a resposta cumpre o critério, a estação já vem concluída na própria
 * resposta — não existe botão de "concluir", porque um botão que o aluno não
 * visse deixaria a estação seguinte trancada para sempre.
 *
 * Onde a divisão em etapas mora: `lib/etapas.js`, pura e testada. Aqui só se
 * desenha o que ela decidiu.
 *
 * **O progresso mora todo no trilho da direita** (`TrilhoDeProgresso`), e não
 * mais espalhado entre chips do cabeçalho, uma régua no topo e uma frase no
 * rodapé. A tela ficou em duas colunas: a aula rola, o trilho fica. No celular
 * ele vira uma faixa acima do conteúdo — lá não existe canto direito.
 */

function EsqueletoDaEstacao() {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Carregando a estação">
      <Linha w="min(70%, 22rem)" h={26} />
      <Esqueleto className="rounded-3xl" altura={200} />
      <Esqueleto className="rounded-3xl" altura={160} />
    </div>
  );
}

export default function CursoEstacao() {
  const { cursoId, estacaoId } = useParams();
  const navegar = useNavigate();

  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [acertos, setAcertos] = useState(0);
  const [concluida, setConcluida] = useState(false);
  const [pulada, setPulada] = useState(false);
  const [sondando, setSondando] = useState(false);
  const [etapa, setEtapa] = useState(0);
  // O que esta visita rendeu. Somado a partir do que o SERVIDOR disse ter
  // creditado em cada resposta — nunca calculado aqui.
  const [ganho, setGanho] = useState({ sparks: 0, xp: 0 });
  // Respostas desta estação, do jeito que a etapa precisa saber: quantas
  // tentativas por bloco. Nasce do servidor e cresce a cada resposta.
  const [respostas, setRespostas] = useState({});
  // Blocos de leitura já percorridos. O `ref` é a guarda contra requisição
  // repetida (sem ele, o observador de interseção dispararia uma a cada vez
  // que o aluno rolasse de volta por um texto que já leu); o estado é o que o
  // trilho desenha — sem ele, ler uma explicação não movia nada na tela.
  const vistos = useRef(new Set());
  const [lidos, setLidos] = useState([]);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const { data } = await api.get(`/cursos/${cursoId}/estacoes/${estacaoId}`);
      setDados(data);
      setAcertos(data.progresso?.acertos || 0);
      setConcluida(Boolean(data.progresso?.concluida_em));
      setPulada(Boolean(data.progresso?.pulada_em));
      setRespostas(data.progresso?.respostas || {});
      vistos.current = new Set(data.progresso?.blocos_vistos || []);
      setLidos(data.progresso?.blocos_vistos || []);
      // Quem volta cai onde parou, e não na primeira tela de leitura.
      const etapas = dividirEmEtapas(data.estacao?.blocos);
      setEtapa(etapaParaRetomar(etapas, data.progresso?.respostas || {}, data.progresso?.blocos_vistos || []));
    } catch (e) {
      setErro(errMsg(e, "Não conseguimos abrir esta estação."));
    } finally {
      setCarregando(false);
    }
  }, [cursoId, estacaoId]);

  useEffect(() => { carregar(); }, [carregar]);

  useEffect(() => {
    setSondando(false);
    setGanho({ sparks: 0, xp: 0 });
  }, [estacaoId]);

  const etapas = useMemo(
    () => dividirEmEtapas(dados?.estacao?.blocos),
    [dados],
  );
  const atual = etapas[etapa] || null;
  // O estado de cada etapa, decidido num lugar só e testado fora do React.
  // Era calculado aqui com dois `if` que não sabiam o que tinha sido LIDO:
  // uma explicação só contava como feita depois de o aluno passar dela, e
  // recarregar a página apagava o rastro.
  const passos = useMemo(
    () => progressoDasEtapas(etapas, respostas, lidos),
    [etapas, respostas, lidos],
  );

  // Trocar de etapa leva ao topo: sem isto o aluno cai no meio da tela nova,
  // na altura em que estava na anterior.
  useEffect(() => { window.scrollTo({ top: 0, behavior: "smooth" }); }, [etapa, estacaoId]);

  useDeclararContextoMentis(
    useMemo(
      () => (dados ? `Na estação "${dados.estacao.titulo}": ${dados.estacao.objetivo}` : ""),
      [dados],
    ),
  );

  /** O que toda resposta desta estação faz com a tela — venha ela do estudo
   *  ou da sondagem de domínio. As duas respondem exercícios de verdade. */
  const contabilizar = useCallback((data) => {
    if (typeof data?.acertos === "number") setAcertos(data.acertos);
    if (data?.bloco_id) {
      setRespostas((atuais) => ({
        ...atuais,
        [data.bloco_id]: {
          acertou: Boolean(data.acertou) || Boolean(atuais[data.bloco_id]?.acertou),
          tentativas: data.tentativa || (atuais[data.bloco_id]?.tentativas || 0) + 1,
        },
      }));
    }
    if (data?.recompensa?.sparks) {
      setGanho((g) => ({
        sparks: g.sparks + (data.recompensa.sparks || 0),
        xp: g.xp + (data.recompensa.xp || 0),
      }));
      // O saldo mudou de verdade: a barra do topo precisa saber, senão o
      // número lá em cima contradiz o "+1 Spark" que acabou de aparecer.
      avisarSparksMudou();
    } else if (data?.recompensa?.xp) {
      setGanho((g) => ({ ...g, xp: g.xp + data.recompensa.xp }));
    }
  }, []);

  const aoResponder = useCallback(async (blocoId, resposta, tempoSegundos, dissertativa = false) => {
    try {
      // A dissertativa tem rota própria porque tem CUSTO próprio: quem
      // corrige texto é a Mentis, por Sparks. Mandá-la para `/resposta` faria
      // o servidor recusar (ele não corrige texto sozinho, de propósito).
      const { data } = await api.post(
        `/cursos/${cursoId}/estacoes/${estacaoId}/blocos/${blocoId}/${dissertativa ? "dissertativa" : "resposta"}`,
        { resposta, tempo_segundos: tempoSegundos },
      );
      if (data.cobrado) avisarSparksMudou();
      contabilizar(data);
      if (data.concluiu_agora) {
        setConcluida(true);
        avisarSparksMudou();
      }
      return data;
    } catch (e) {
      toast.error(errMsg(e, "Não conseguimos registrar sua resposta."));
      return null;
    }
  }, [cursoId, estacaoId, contabilizar]);

  const aoVer = useCallback((blocoId) => {
    if (vistos.current.has(blocoId)) return;
    vistos.current.add(blocoId);
    setLidos((atuais) => (atuais.includes(blocoId) ? atuais : [...atuais, blocoId]));
    // Sinal de percurso: se falhar, não muda nada para o aluno e não vale um
    // aviso na tela.
    api.post(`/cursos/${cursoId}/estacoes/${estacaoId}/blocos/${blocoId}/visto`).catch(() => {});
  }, [cursoId, estacaoId]);

  // "Explicar melhor" — 10 Sparks, cobrados no servidor. O componente do
  // bloco só chama isto e desenha o que voltar; quem sabe que isto é um
  // CURSO (e não um e-book) é esta tela.
  const aoExplicar = useCallback(async (blocoId) => {
    const { data } = await api.post(
      `/cursos/${cursoId}/estacoes/${estacaoId}/blocos/${blocoId}/explicar`,
    );
    avisarSparksMudou();
    return data;
  }, [cursoId, estacaoId]);

  const estacao = dados?.estacao;
  const alvo = estacao?.acertos_para_concluir || 0;
  // Um pacote só, usado pelas duas encarnações do trilho (a faixa do celular
  // e a coluna do desktop): duas listas de propriedades para o mesmo objeto
  // divergem na primeira vez que alguém mexe em uma delas.
  const trilho = {
    etapas,
    passos,
    etapaAtual: etapa,
    aoIrParaEtapa: setEtapa,
    acertos,
    alvo,
    ganho,
    concluida,
    pulada,
    duracaoMinutos: estacao?.duracao_minutos || null,
  };
  const seguinte = dados?.navegacao?.seguinte;
  const anterior = dados?.navegacao?.anterior;
  const ultima = etapa >= etapas.length - 1;
  const podeAvancar = etapaCumprida(atual, respostas);
  const faltamRespostas = atual?.tipo === "exercicios" && !podeAvancar
    ? atual.blocos.filter((b) => !(respostas[b.bloco_id]?.tentativas > 0)).length
    : 0;

  return (
    <Tela
      olho="Estação"
      titulo={estacao?.titulo || "Estação"}
      subtitulo={etapa === 0 ? estacao?.objetivo : null}
      voltar={`/cursos/${cursoId}`}
      voltarLabel="Mapa do curso"
      largura="xl"
      testid="curso-estacao"
      className="pb-28 md:pb-10"
    >
      {carregando && <EsqueletoDaEstacao />}

      {!carregando && erro && (
        <EstadoDeErro
          mensagem={erro}
          aoTentarNovamente={carregar}
          voltarPara={`/cursos/${cursoId}`}
          voltarLabel="Voltar ao mapa do curso"
        />
      )}

      {!carregando && !erro && estacao && (
        <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_17rem] lg:items-start lg:gap-7">
          <div className="min-w-0 space-y-5">
            {/* No celular o trilho é uma faixa acima da aula: é o único lugar
                onde ele cabe sem empurrar o conteúdo para fora da tela. */}
            <TrilhoDeProgresso {...trilho} compacto className="lg:hidden" />

            {/* "Já sei isto" só na primeira tela e só enquanto há o que pular:
                oferecer o atalho depois da aula seria oferecê-lo depois da
                viagem. */}
            {etapa === 0 && !concluida && !pulada && (
              <SondagemDeDominio
                cursoId={cursoId}
                estacaoId={estacaoId}
                jaUsada={Boolean(dados.progresso?.sondagem_usada)}
                aberta={sondando}
                aoAbrir={() => setSondando(true)}
                aoFechar={() => setSondando(false)}
                aoResponder={contabilizar}
                aoPular={() => {
                  setPulada(true);
                  avisarSparksMudou();
                  toast.success("Estação pulada por domínio.");
                }}
              />
            )}

            {pulada && etapa === 0 && (
              <section
                className="superficie rounded-3xl border-violet-400/25 p-5"
                data-testid="estacao-pulada"
              >
                <div className="flex items-start gap-3">
                  <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-violet-300" />
                  <div className="min-w-0">
                    <p className="font-display text-base font-bold tracking-tight text-white">
                      Você provou que já sabia isto.
                    </p>
                    <p className="mt-1 text-sm leading-relaxed text-white/55">
                      O conteúdo continua aqui se quiser conferir alguma coisa.
                    </p>
                  </div>
                </div>
              </section>
            )}

            {/* A ETAPA. `key` no índice força a remontagem ao avançar: sem ela,
                o React reaproveita os componentes de exercício e o estado da
                questão anterior (escolha, devolutiva) aparece na seguinte. */}
            <div key={etapa} className="space-y-5 reveal">
              {(atual?.blocos || []).map((bloco) => (
                <Bloco
                  key={bloco.bloco_id}
                  bloco={bloco}
                  progresso={respostas[bloco.bloco_id]}
                  aoResponder={aoResponder}
                  aoVer={aoVer}
                  aoExplicar={aoExplicar}
                />
              ))}
            </div>

            {/* CONTINUAR — a única saída da tela, e o que dá ritmo à estação. */}
            {!ultima ? (
              <div className="flex flex-col items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setEtapa((i) => i + 1)}
                  disabled={!podeAvancar}
                  className="pill btn-sapiens inline-flex w-full items-center justify-center gap-2 rounded-full px-8 py-4 text-base font-bold disabled:opacity-40 sm:w-auto"
                  data-testid="continuar"
                >
                  Continuar <ArrowRight className="h-4 w-4" />
                </button>
                {faltamRespostas > 0 && (
                  <p className="text-[12px] text-white/35" data-testid="faltam">
                    {faltamRespostas === 1
                      ? "Falta responder 1 questão desta tela."
                      : `Faltam responder ${faltamRespostas} questões desta tela.`}
                  </p>
                )}
              </div>
            ) : (
              <section
                className={`superficie rounded-3xl p-6 text-center ${concluida || pulada ? "superficie-viva" : ""}`}
                data-testid="estacao-fim"
              >
                {concluida || pulada ? (
                  <>
                    {pulada
                      ? <ShieldCheck className="mx-auto h-6 w-6 text-violet-300" />
                      : <Trophy className="mx-auto h-6 w-6 text-amber-300" />}
                    <p className="mt-3 font-display text-lg font-extrabold tracking-tight text-white">
                      {pulada ? "Estação pulada por domínio" : "Estação concluída"}
                    </p>
                    <p className="mt-1 text-sm text-white/60">
                      {seguinte ? "A próxima já está liberada." : "Você chegou ao fim desta trilha."}
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-white/55">
                    Acerte {alvo} exercícios para concluir esta estação — você está em {acertos}.
                  </p>
                )}

                <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                  {seguinte && (concluida || pulada) ? (
                    <button
                      onClick={() => navegar(`/cursos/${cursoId}/estacao/${seguinte.estacao_id}`)}
                      className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold"
                      data-testid="ir-para-seguinte"
                    >
                      {seguinte.titulo} <ArrowRight className="h-4 w-4" />
                    </button>
                  ) : null}
                  <Link to={`/cursos/${cursoId}`} className="chip">Voltar ao mapa</Link>
                </div>
              </section>
            )}

            {/* Voltar uma etapa, e a navegação entre estações. Discretos: são
                saídas, não o caminho. */}
            <nav className="flex items-center justify-between gap-3 pt-2">
              {etapa > 0 ? (
                <button
                  type="button"
                  onClick={() => setEtapa((i) => Math.max(0, i - 1))}
                  className="chip inline-flex items-center gap-1.5"
                  data-testid="etapa-anterior"
                >
                  <ArrowLeft className="h-3 w-3" /> Voltar
                </button>
              ) : anterior ? (
                <Link
                  to={`/cursos/${cursoId}/estacao/${anterior.estacao_id}`}
                  className="chip inline-flex items-center gap-1.5"
                  data-testid="estacao-anterior"
                >
                  <ArrowLeft className="h-3 w-3" /> {anterior.titulo}
                </Link>
              ) : <span />}
              {ultima && seguinte ? (
                <Link
                  to={`/cursos/${cursoId}/estacao/${seguinte.estacao_id}`}
                  className="chip inline-flex items-center gap-1.5"
                  data-testid="estacao-seguinte"
                >
                  {seguinte.titulo} <ArrowRight className="h-3 w-3" />
                </Link>
              ) : <span />}
            </nav>

            {(concluida || pulada) && (
              <p className="flex items-center justify-center gap-1.5 text-xs text-white/35">
                <Check className="h-3 w-3" /> Você pode refazer qualquer exercício sem perder o que já concluiu.
              </p>
            )}
          </div>

          {/* O TRILHO. `sticky` porque a pergunta que ele responde ("quanto
              falta?") é feita no meio da estação, e não no topo dela. */}
          <TrilhoDeProgresso {...trilho} className="hidden lg:block lg:sticky lg:top-24" />
        </div>
      )}
    </Tela>
  );
}
