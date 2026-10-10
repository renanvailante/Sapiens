import { useCallback, useEffect, useState, lazy, Suspense } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Compass, PenLine, Layers, ArrowRight, Loader2 } from "lucide-react";
import { Bloco } from "../components/Esqueleto";
import Mentis from "../components/Mentis";
import { ROTAS } from "../lib/rotas";
import { api } from "../lib/api";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { EVENTO_PASSO, lerPassoAtual } from "../lib/trilhaDoDia";
import { abrirPraticaDirigida } from "../lib/praticaDirigida";

// `Estudar` entra no bundle principal (ver App.js) — mas Cursos e Provas
// arrastam KaTeX e o resto da árvore de conteúdo, e essas duas telas já são
// `lazy()` em App.js para quem entra direto nelas. Um import estático aqui
// desfaz essa divisão: o webpack embute a árvore inteira no chunk principal
// mesmo assim. `lazy()` de novo, agora aqui dentro, mantém o split real.
const Cursos = lazy(() => import("./Cursos"));
const Provas = lazy(() => import("./Provas"));

/**
 * ESTUDAR — tudo o que se pode fazer com conteúdo, numa tela.
 *
 * Pergunta mental: **o que eu vou fazer?**
 *
 * ---------------------------------------------------------------------------
 * QUATRO MODOS, E POR QUE ELES NÃO SÃO QUATRO ABAS
 * ---------------------------------------------------------------------------
 *
 *     APRENDER   cursos e e-books      ler, do zero ao avançado
 *     PRATICAR   provas do ENEM        testar-se no que já caiu
 *     ESCREVER   redação               a única coisa que vale 1000 sozinha
 *     FOLHEAR    feed                  três minutos e nenhuma intenção
 *
 * A divisão entre eles é do ALUNO (o que ele tem energia e tempo para fazer
 * agora), não do produto. Por isso as duas colunas mostram o catálogo de
 * verdade — capas, cadernos, progresso — em vez de dois botões que levam a
 * dois menus: a escolha é feita OLHANDO, não adivinhando. Quem não sabia o
 * que tinha em "Cursos" nunca descobriu enquanto isso era um rótulo.
 *
 * Escrever e Folhear entram como CHAMADAS, não como colunas, e a razão é de
 * forma: redação é uma sessão de uma hora em tela cheia, e o folhear é uma
 * pilha de cartões em sangria total — nenhum dos dois sobrevive espremido numa
 * coluna de 560px. O que eles precisam é de uma porta visível, e é isso que
 * eles ganharam aqui.
 *
 * ---------------------------------------------------------------------------
 * O QUE MUDOU NESTA PASSADA
 * ---------------------------------------------------------------------------
 *
 * Redação era **aba primária** e Folhear (o feed) morava no grupo "Mais" do
 * Menu, atrás de uma gaveta. Os dois são a mesma categoria — coisas que se faz
 * com conteúdo — e estavam em níveis opostos da navegação: um ocupava uma das
 * sete vagas da barra, o outro não existia para quem não soubesse que existia.
 *
 * Redação não perdeu alcance ao sair da barra: ela continua tendo porta aqui,
 * bloco semanal na Agenda (o cronograma gera `tipo: redacao`) e presença no
 * Próximo Passo do Hoje quando faz tempo que o aluno não escreve. Um bloco que
 * aparece na semana dele é mais forte que uma aba que ele precisa lembrar de
 * clicar.
 *
 * ---------------------------------------------------------------------------
 * A COLUNA DA ESQUERDA RECOLHE DURANTE A PROVA
 * ---------------------------------------------------------------------------
 *
 * Quando o aluno escolhe um caderno, `Provas` avisa (`onModo`) e esta página
 * esconde tudo o que não é a prova: o motor roda com a largura inteira,
 * exatamente como rodava quando era tela própria. Nada dentro do
 * `QuestionRunner` mudou.
 */

/** Uma porta para um modo que não cabe em coluna. Link inteiro clicável, no
 *  mouse, no toque e no teclado — nada nesta tela é beco sem saída. */
function Modo({ para, icone: Icone, nome, frase, cor, testid }) {
  return (
    <Link to={para} className="superficie lift flex items-start gap-3.5 p-4" data-testid={testid}>
      <span
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border ${cor}`}
      >
        <Icone className="h-5 w-5" strokeWidth={1.8} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block font-display text-base font-bold tracking-tight text-white">
          {nome}
        </span>
        <span className="block text-xs leading-relaxed text-white/50">{frase}</span>
      </span>
    </Link>
  );
}

/**
 * "NA DÚVIDA, SIGA A TRILHA" — a ponte de volta ao caminho do dia.
 *
 * Estudar é a tela da escolha livre, e escolha livre é exatamente onde o aluno
 * sem plano trava (2026-10-09: "tenho dificuldade de saber o que fazer"). A
 * Mentis lembra, no topo, que o próximo passo já está escolhido — o nó aceso
 * da trilha que o Hoje publicou (`trilhaDoDia.publicarPassoAtual`), sem
 * requisição nenhuma. Sem passo publicado hoje, ela manda abrir a trilha.
 */
function SigaATrilha() {
  const navegar = useNavigate();
  const [passo, setPasso] = useState(lerPassoAtual);
  const [indo, setIndo] = useState(false);
  useEffect(() => {
    const reler = () => setPasso(lerPassoAtual());
    window.addEventListener(EVENTO_PASSO, reler);
    return () => window.removeEventListener(EVENTO_PASSO, reler);
  }, []);

  const pendente = passo && !passo.completo && passo.titulo;
  const ir = () => {
    const acao = passo?.acao;
    if (!pendente || !acao || passo.estado === "resgatar") return navegar(ROTAS.HOJE);
    if (acao.tipo === "dirigida") {
      setIndo(true);
      abrirPraticaDirigida({ api, navegar, processoId: acao.processoId, escolha: acao.escolha }).finally(() => setIndo(false));
      return undefined;
    }
    return navegar(acao.rota || ROTAS.HOJE);
  };

  return (
    <div className="superficie-viva superficie mb-8 flex flex-col items-stretch gap-4 p-4 sm:flex-row sm:items-center" data-testid="estudar-siga-a-trilha">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <Mentis className="h-12 w-12 shrink-0" variante="icone" estado="confirmando" olhar={0.6} flutuar />
        <div className="min-w-0 flex-1">
          <div className="secao-olho">Na dúvida, siga a trilha</div>
          <p className="mt-0.5 text-sm font-semibold leading-snug text-white">
            {pendente ? passo.titulo : passo?.completo ? "Sua trilha de hoje está completa — escolha à vontade." : "Seu próximo passo já está escolhido no Hoje."}
          </p>
        </div>
      </div>
      {(pendente || !passo?.completo) && (
        <button
          type="button"
          onClick={ir}
          disabled={indo}
          className="pill btn-sapiens inline-flex w-full shrink-0 items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-bold disabled:opacity-60 sm:w-auto"
          data-testid="estudar-siga-a-trilha-ir"
        >
          {indo ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {pendente ? passo.cta || "Começar" : "Ver a trilha"} <ArrowRight className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

export default function Estudar() {
  const [modoDaProva, setModoDaProva] = useState("provas");
  const respondendo = modoDaProva === "practice";

  useDeclararContextoMentis("Na aba Estudar, escolhendo o que fazer agora.");

  // `useCallback` e não uma função nova a cada render: ela vai para dentro de
  // um `useEffect` do filho, e uma identidade nova por render faria o efeito
  // disparar em laço.
  const aoMudarModo = useCallback((modo) => setModoDaProva(modo), []);

  return (
    <div className="min-h-screen">
      <div className="mx-auto max-w-7xl px-5 py-7 md:px-10 md:py-10">
        {!respondendo && (
          <>
            <header className="mb-7">
              <div className="secao-olho">Estudar</div>
              <h1 className="titulo-tela">O que você vai fazer agora.</h1>
              <p className="mt-2.5 max-w-2xl text-sm leading-relaxed text-white/55">
                À esquerda, o conteúdo para aprender. À direita, as provas para se testar. E, aqui
                em cima, as duas coisas que pedem a tela inteira.
              </p>
            </header>

            <SigaATrilha />

            {/* OS MODOS QUE NÃO CABEM EM COLUNA. Ficam no topo porque são os
                dois que o aluno não encontraria sozinho: um acabou de sair da
                barra, o outro estava atrás do Menu. */}
            <div className="mb-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Modo
                para={ROTAS.REDACAO}
                icone={PenLine}
                nome="Escrever uma redação"
                frase="Tema, correção nas cinco competências e foto da folha manuscrita."
                cor="border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
                testid="estudar-modo-redacao"
              />
              <Modo
                para={ROTAS.TREINO}
                icone={Compass}
                nome="Mapa de Treino"
                frase="Missões curtas num mapa que se revela conforme você avança."
                cor="border-[#8B7BFF]/30 bg-[#8B7BFF]/10 text-[#C4B5FD]"
                testid="estudar-modo-treino"
              />
              <Modo
                para={ROTAS.FOLHEAR}
                icone={Layers}
                nome="Folhear"
                frase="Três minutos e nenhuma intenção? Passe o dedo por questões soltas."
                cor="border-white/15 bg-white/[0.06] text-white/70"
                testid="estudar-modo-folhear"
              />
            </div>
          </>
        )}

        <div
          className={
            respondendo
              ? ""
              : "grid gap-x-10 gap-y-12 lg:grid-cols-2 lg:items-start lg:divide-x lg:divide-white/8"
          }
        >
          {/* APRENDER. Recolhida enquanto o aluno responde questão: ela não
              tem o que dizer nesse momento e competiria com o enunciado. */}
          {!respondendo && (
            <section className="order-2 min-w-0 lg:order-1 lg:pr-10" data-testid="estudar-aprender">
              <Suspense fallback={<Bloco className="rounded-3xl" altura={420} />}>
                <Cursos embutido />
              </Suspense>
            </section>
          )}

          {/* PRATICAR. `order-1` no celular: quem abre o app no telefone
              costuma ter dez minutos e uma fila, não uma mesa para ler um
              curso. No desktop volta para a direita. */}
          <section
            className={respondendo ? "min-w-0" : "order-1 min-w-0 lg:order-2 lg:pl-10"}
            data-testid="estudar-praticar"
          >
            <Suspense fallback={<Bloco className="rounded-3xl" altura={420} />}>
              <Provas embutido onModo={aoMudarModo} />
            </Suspense>
          </section>
        </div>
      </div>
    </div>
  );
}
