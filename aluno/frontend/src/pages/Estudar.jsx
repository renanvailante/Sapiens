import { useCallback, useState } from "react";
import Nav from "../components/Nav";
import ContagemEnem from "../components/ContagemEnem";
import Cursos from "./Cursos";
import ExamSelect from "./ExamSelect";

/**
 * ESTUDAR — uma aba onde havia duas.
 *
 * O PROBLEMA ERA A PERGUNTA QUE A BARRA FAZIA. "Praticar" e "Cursos" eram dois
 * destinos de topo, e a divisão entre eles é do produto, não do aluno: ninguém
 * abre o app querendo "o módulo de questões" ou "o módulo de cursos" — abre
 * querendo estudar. A barra obrigava a escolher entre dois rótulos ANTES de
 * ver o que havia dentro de cada um, que é o pior momento possível para pedir
 * uma decisão. Quem não sabia o que tinha em "Cursos" nunca descobriu.
 *
 * DUAS ÁREAS, LADO A LADO, e a escolha passa a ser feita OLHANDO.
 *
 *     ┌───────────────────────────┬───────────────────────────┐
 *     │  APRENDER                 │  PRATICAR                 │
 *     │  cursos · e-books         │  provas do ENEM           │
 *     │  ladrilhos com capa       │  cadernos por banca/ano   │
 *     └───────────────────────────┴───────────────────────────┘
 *
 * A ordem das colunas não é arbitrária. Aprender vem à esquerda porque é o
 * lado em que a leitura ocidental começa e porque é o que o aluno faz ANTES:
 * estuda o conteúdo, depois se testa nele. A direita é a prática — e é também
 * a coluna mais usada pelo aluno veterano, que já sabe onde ela está e não
 * precisa que ela venha primeiro.
 *
 * NO CELULAR VIRA UMA COLUNA SÓ, e aí a ordem se inverte em importância: a
 * prática é o que o aluno de telefone abre para fazer em dez minutos de fila,
 * enquanto ler um curso pede mesa. Por isso a coluna da prática sobe no
 * empilhamento — `order` no CSS, sem duplicar marcação.
 *
 * RESPONDER QUESTÃO TOMA A TELA INTEIRA. Quando o aluno escolhe um caderno, o
 * `ExamSelect` avisa (`onModo`) e esta página recolhe a coluna da esquerda: o
 * motor de prova continua rodando com a largura inteira, exatamente como
 * rodava quando era uma tela própria. Nada dentro do `QuestionRunner` mudou.
 */
export default function Estudar() {
  const [modoDaProva, setModoDaProva] = useState("provas");
  const respondendo = modoDaProva === "practice";

  // `useCallback` e não uma função nova a cada render: ela vai para dentro de
  // um `useEffect` do filho, e uma identidade nova por render faria o efeito
  // disparar em laço.
  const aoMudarModo = useCallback((modo) => setModoDaProva(modo), []);

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-7xl px-5 py-7 md:px-10 md:py-10">
        {!respondendo && (
          <header className="mb-8">
            <div className="secao-olho">Estudar</div>
            <h1 className="titulo-tela">Aprender e praticar, no mesmo lugar.</h1>
            <p className="mt-2.5 max-w-2xl text-sm leading-relaxed text-white/55">
              À esquerda, o conteúdo: cursos e e-books. À direita, as provas —
              cada questão que você responde vira informação sobre você.
            </p>
            {/* O relógio do ENEM subiu para o cabeçalho da aba unida. Ele
                estava dentro de "Cursos" e explicava por que aquela página
                importava hoje; aqui ele explica a aba inteira, e aparece uma
                vez em vez de duas. */}
            <div className="mt-6">
              <ContagemEnem comCta={false} testid="estudar-contagem-enem" />
            </div>
          </header>
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
              <Cursos embutido />
            </section>
          )}

          {/* PRATICAR. `order-1` no celular: quem abre o app no telefone
              costuma ter dez minutos e uma fila, não uma mesa para ler um
              curso. No desktop volta para a direita. */}
          <section
            className={
              respondendo
                ? "min-w-0"
                : "order-1 min-w-0 lg:order-2 lg:pl-10"
            }
            data-testid="estudar-praticar"
          >
            <ExamSelect embutido onModo={aoMudarModo} />
          </section>
        </div>
      </div>
    </div>
  );
}
