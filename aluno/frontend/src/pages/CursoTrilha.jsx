import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Check, ArrowRight, ChevronRight, Clock, Trophy, Zap, Target, RotateCw, Layers,
} from "lucide-react";
import { api, errMsg } from "../lib/api";
import Tela from "../components/Tela";
import EstadoDeErro from "../components/EstadoDeErro";
import { Bloco as Esqueleto, Linha } from "../components/Esqueleto";
import CaminhoDoCurso from "../components/curso/CaminhoDoCurso";
import { useDeclararContextoMentis } from "../lib/mentisContexto";

/**
 * `/cursos/:cursoId` — O MAPA DO CURSO.
 *
 * Três coisas, nesta ordem, e a ordem é a tese da tela:
 *
 * 1. **O próximo passo.** Quem abre um curso quer continuar de onde parou.
 *    Procurar a estação certa no meio de 24 é trabalho que o produto faz
 *    sozinho — e quem decide qual é ela é o servidor (`proxima`), nunca a
 *    tela, senão duas partes do app apontam para estações diferentes.
 * 2. **O caminho**, trilha por trilha, com os seis estados desenhados
 *    (`CaminhoDoCurso`). Uma lista de 24 linhas informa; um caminho situa.
 * 3. **O que o curso rende** — estações, XP e Sparks possíveis. Os números
 *    saem da mesma tabela que paga, no servidor.
 *
 * A tela **não calcula liberação, estado nem progresso**: tudo isso é
 * decisão de `cursos_progresso.mapa_de_estados`. Uma segunda implementação
 * aqui divergiria no dia em que o critério mudasse — e a versão errada é
 * sempre a que o aluno encontra.
 *
 * Tudo vem de `GET /cursos/:id/trilha` numa chamada só.
 */

function EsqueletoDaTrilha() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Carregando o curso">
      <Esqueleto className="rounded-3xl" altura={150} />
      <div className="space-y-3">
        <Linha w="9rem" h={14} />
        <Esqueleto className="rounded-3xl" altura={420} />
      </div>
    </div>
  );
}

/** Área › Curso. A hierarquia do catálogo, navegável de volta. */
function Trilho({ curso }) {
  return (
    <nav className="mb-3 flex items-center gap-1.5 text-xs text-white/40" aria-label="Você está em">
      <Link to="/cursos" className="rounded px-1 py-0.5 transition-colors hover:text-white">
        Cursos
      </Link>
      {curso?.area && (
        <>
          <ChevronRight className="h-3 w-3 shrink-0 opacity-50" />
          <Link
            to={`/cursos#area-${curso.area}`}
            className="rounded px-1 py-0.5 capitalize transition-colors hover:text-white"
          >
            {curso.area}
          </Link>
        </>
      )}
      <ChevronRight className="h-3 w-3 shrink-0 opacity-50" />
      <span className="truncate text-white/70">{curso?.titulo}</span>
    </nav>
  );
}

function Numero({ icone: Icone, valor, rotulo, cor = "text-white/70" }) {
  return (
    <div className="flex items-center gap-2">
      <Icone className={`h-4 w-4 shrink-0 ${cor}`} />
      <div className="min-w-0 leading-tight">
        <div className="font-display text-base font-extrabold tracking-tight text-white tabular-nums">
          {valor}
        </div>
        <div className="font-mono-alt text-[9px] uppercase tracking-[0.18em] text-white/35">
          {rotulo}
        </div>
      </div>
    </div>
  );
}

export default function CursoTrilha() {
  const { cursoId } = useParams();
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [selecionada, setSelecionada] = useState(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const { data } = await api.get(`/cursos/${cursoId}/trilha`);
      setDados(data);
    } catch (e) {
      setErro(errMsg(e, "Não conseguimos abrir este curso."));
    } finally {
      setCarregando(false);
    }
  }, [cursoId]);

  useEffect(() => { carregar(); }, [carregar]);

  // String e não objeto: o hook compara por identidade para decidir se
  // redeclara, e um objeto novo a cada render dispararia o efeito sem parar.
  useDeclararContextoMentis(
    useMemo(
      () => (dados
        ? `Estudando o curso "${dados.curso?.titulo}" — ${dados.progresso.concluidas} de ${dados.progresso.estacoes} estações.`
        : ""),
      [dados],
    ),
  );

  const proxima = dados?.proxima;
  const progresso = dados?.progresso;

  return (
    <Tela
      olho={null}
      titulo={null}
      largura="xl"
      testid="curso-trilha"
      className="pb-24 md:pb-10"
    >
      {carregando && <EsqueletoDaTrilha />}

      {!carregando && erro && (
        <EstadoDeErro
          mensagem={erro}
          aoTentarNovamente={carregar}
          voltarPara="/cursos"
          voltarLabel="Voltar para Cursos"
        />
      )}

      {!carregando && !erro && dados && (
        <div className="space-y-8">
          <header>
            <Trilho curso={dados.curso} />
            <h1 className="titulo-tela" data-testid="curso-trilha-title">{dados.curso.titulo}</h1>
            <p className="mt-2.5 max-w-2xl text-sm leading-relaxed text-white/55">
              {dados.curso.chamada}
            </p>

            {/* O que o curso rende, antes de começar. Números do servidor. */}
            <div
              className="superficie mt-5 grid grid-cols-2 gap-4 rounded-3xl p-5 sm:grid-cols-4"
              data-testid="curso-numeros"
            >
              <Numero
                icone={Layers}
                valor={`${progresso.concluidas}/${progresso.estacoes}`}
                rotulo="Estações"
              />
              <Numero icone={Target} valor={progresso.exercicios} rotulo="Exercícios" />
              <Numero
                icone={Trophy}
                valor={progresso.xp_possivel}
                rotulo="XP possível"
                cor="text-violet-300"
              />
              <Numero
                icone={Zap}
                valor={progresso.sparks_possiveis}
                rotulo="Sparks possíveis"
                cor="text-amber-300"
              />
            </div>

            <div className="mt-4 flex items-center gap-3">
              <div className="barra flex-1" data-cheia={progresso.percentual >= 100} aria-hidden="true">
                <i style={{ width: `${progresso.percentual}%` }} />
              </div>
              <span className="shrink-0 font-mono-alt text-xs text-white/45 tabular-nums" data-testid="curso-progresso">
                {progresso.percentual}%
              </span>
            </div>
            {progresso.puladas > 0 && (
              <p className="mt-1.5 text-[11px] text-white/35" data-testid="curso-puladas">
                {progresso.estudadas} estudada{progresso.estudadas === 1 ? "" : "s"} ·{" "}
                {progresso.puladas} pulada{progresso.puladas === 1 ? "" : "s"} por domínio comprovado.
              </p>
            )}
          </header>

          {/* O PRÓXIMO PASSO — a peça viva da tela, e só ela. */}
          {proxima ? (
            <Link
              to={`/cursos/${cursoId}/estacao/${proxima.estacao_id}`}
              className="superficie superficie-viva lift block rounded-3xl p-5 md:p-6"
              data-testid="proximo-passo"
            >
              <div className="secao-olho">
                {proxima.estado === "em_andamento" ? "Continuar de onde parou" : "Comece por aqui"}
              </div>
              <h2 className="mt-2 font-display text-xl font-extrabold tracking-tight text-white md:text-2xl">
                {proxima.titulo}
              </h2>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-white/60">{proxima.objetivo}</p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <span className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold">
                  {proxima.estado === "em_andamento" ? "Continuar" : "Começar"}
                  <ArrowRight className="h-4 w-4" />
                </span>
                {proxima.duracao_minutos ? (
                  <span className="chip">
                    <Clock className="h-3 w-3" /> {proxima.duracao_minutos} min
                  </span>
                ) : null}
              </div>
            </Link>
          ) : (
            <div className="superficie rounded-3xl p-6 text-center" data-testid="curso-completo">
              <Check className="mx-auto h-6 w-6 text-emerald-300" />
              <p className="mt-3 font-display text-lg font-bold text-white">Você concluiu este curso.</p>
              <p className="mt-1 text-sm text-white/55">
                Todas as estações saíram do caminho. Volte quando quiser rever qualquer uma.
              </p>
            </div>
          )}

          {dados.trilhas.map((trilha) => (
            <section key={trilha.trilha_id} data-testid={`trilha-${trilha.trilha_id}`}>
              <div className="secao-cabeca">
                <div className="min-w-0">
                  <h2 className="secao-titulo">{trilha.titulo}</h2>
                  {trilha.resumo && <p className="mt-1 text-sm text-white/45">{trilha.resumo}</p>}
                </div>
                <span className="shrink-0 font-mono-alt text-[11px] text-white/40">
                  {trilha.concluidas}/{trilha.total}
                </span>
              </div>
              <CaminhoDoCurso
                cursoId={cursoId}
                estacoes={trilha.estacoes}
                selecionada={selecionada}
                aoSelecionar={setSelecionada}
                // Depois de uma prova de salto o mapa inteiro mudou: várias
                // estações viraram puladas de uma vez. Recarregar é a forma
                // honesta de redesenhar — a tela não recalcula estado.
                aoSaltar={() => { setSelecionada(null); carregar(); }}
                testid={`caminho-${trilha.trilha_id}`}
              />
            </section>
          ))}

          <button
            onClick={carregar}
            className="chip mx-auto flex items-center gap-1.5"
            data-testid="curso-recarregar"
          >
            <RotateCw className="h-3 w-3" /> Atualizar
          </button>
        </div>
      )}
    </Tela>
  );
}
