import { useCallback, useEffect, useState, lazy, Suspense } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Compass, PenLine, Layers, ArrowRight, Loader2 } from "lucide-react";
import ContagemEnem from "../components/ContagemEnem";
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
 * agora), não do produto. Por isso a tela mostra o catálogo de verdade —
 * capas, cadernos, progresso — em vez de dois botões que levam a dois menus:
 * a escolha é feita OLHANDO, não adivinhando. Quem não sabia o que tinha em
 * "Cursos" nunca descobriu enquanto isso era um rótulo.
 *
 * ---------------------------------------------------------------------------
 * UMA COLUNA, COMO O DUOLINGO (2026-10-10)
 * ---------------------------------------------------------------------------
 *
 * De 2026-09-18 a 2026-10-10 Aprender e Praticar eram DUAS colunas de meia
 * tela, lado a lado. Era a causa de quase tudo que o dono chamou de "muito
 * ruim e pouco atrativo": meia tela cortava todo título ("ENEM 20…",
 * "Curso de Matemática…"), forçava o catálogo a virar quadrados de 150px que
 * escondiam o nome atrás de um hover, e punha dois títulos do mesmo tamanho
 * disputando a mesma dobra. Agora são seções empilhadas na largura inteira,
 * cada uma com o seu cabeçalho de ícone (`CabecaDeSecao`): primeiro as
 * provas (o que o aluno faz em dez minutos), depois os cursos. Os cartões
 * são `.cartao-gordo` — ver `index.css`.
 *
 * Escrever e Folhear entram como CHAMADAS, não como seções, e a razão é de
 * forma: redação é uma sessão de uma hora em tela cheia, e o folhear é uma
 * pilha de cartões em sangria total. O que eles precisam é de uma porta
 * visível, e é isso que eles ganharam aqui.
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
 * O RESTO RECOLHE DURANTE A PROVA
 * ---------------------------------------------------------------------------
 *
 * Quando o aluno escolhe um caderno, `Provas` avisa (`onModo`) e esta página
 * esconde tudo o que não é a prova: o motor roda sozinho na tela, exatamente
 * como rodava quando era tela própria. Nada dentro do `QuestionRunner` mudou.
 */

/** Uma porta para um modo que não cabe numa seção. Link inteiro clicável, no
 *  mouse, no toque e no teclado — nada nesta tela é beco sem saída. Mesma
 *  peça dos cartões do catálogo (`.cartao-gordo`), deitada. */
function Modo({ para, icone: Icone, nome, frase, cor, testid }) {
  return (
    <Link
      to={para}
      className="cartao-gordo cartao-gordo--modo gap-2 px-2 py-3 sm:gap-3.5 sm:p-3.5"
      style={{ "--de": cor.de, "--para": cor.para, "--pe": cor.pe, "--tinta": cor.de }}
      data-testid={testid}
    >
      <span className="cartao-gordo-icone" style={{ width: 46, height: 46, borderRadius: 15 }} aria-hidden="true">
        <Icone strokeWidth={2.2} style={{ width: 23, height: 23 }} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block font-display text-[13px] font-extrabold leading-tight tracking-tight text-white sm:text-base">{nome}</span>
        <span className="hidden text-xs leading-snug text-white/65 sm:block">{frase}</span>
      </span>
      <ArrowRight className="hidden h-4 w-4 shrink-0 text-white/40 sm:block" aria-hidden="true" />
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
      <div className="mx-auto max-w-6xl px-5 py-7 md:px-10 md:py-10">
        {!respondendo && (
          <>
            <header className="mb-6">
              <div className="secao-olho">Estudar</div>
              <h1 className="titulo-tela">O que vamos estudar agora?</h1>
              {/* O relógio do ENEM numa linha só: ele morava dentro da coluna
                  das provas, num azulejo de 13rem que empurrava os cadernos
                  para baixo. Aqui ele dá o contexto da página inteira. */}
              <div className="mt-3">
                <ContagemEnem variante="linha" testid="estudar-contagem-enem" />
              </div>
            </header>

            <SigaATrilha />

            {/* OS MODOS QUE NÃO CABEM NUMA SEÇÃO. Ficam no topo porque são os
                dois que o aluno não encontraria sozinho: um acabou de sair da
                barra, o outro estava atrás do Menu. */}
            <div className="mb-12 grid grid-cols-3 gap-2.5 sm:gap-3">
              <Modo
                para={ROTAS.REDACAO}
                icone={PenLine}
                nome="Escrever redação"
                frase="Correção nas cinco competências."
                cor={{ de: "#A78BFA", para: "#5B3FD0", pe: "#3B2A8A" }}
                testid="estudar-modo-redacao"
              />
              <Modo
                para={ROTAS.TREINO}
                icone={Compass}
                nome="Mapa de Treino"
                frase="Missões curtas num mapa que se revela."
                cor={{ de: "#5EEAD4", para: "#0E7490", pe: "#0B4F5C" }}
                testid="estudar-modo-treino"
              />
              <Modo
                para={ROTAS.FOLHEAR}
                icone={Layers}
                nome="Folhear"
                frase="Questões soltas, sem compromisso."
                cor={{ de: "#94A3B8", para: "#475569", pe: "#2A3444" }}
                testid="estudar-modo-folhear"
              />
            </div>
          </>
        )}

        {/* PRATICAR primeiro: quem abre esta aba costuma ter dez minutos e
            uma fila, não uma mesa para ler um curso. */}
        <section className="min-w-0" data-testid="estudar-praticar">
          <Suspense fallback={<Bloco className="rounded-3xl" altura={420} />}>
            <Provas embutido onModo={aoMudarModo} />
          </Suspense>
        </section>

        {/* APRENDER. Recolhida enquanto o aluno responde questão: ela não
            tem o que dizer nesse momento e competiria com o enunciado. */}
        {!respondendo && (
          <section className="mt-14 min-w-0 border-t border-white/10 pt-12" data-testid="estudar-aprender">
            <Suspense fallback={<Bloco className="rounded-3xl" altura={420} />}>
              <Cursos embutido />
            </Suspense>
          </section>
        )}
      </div>
    </div>
  );
}
