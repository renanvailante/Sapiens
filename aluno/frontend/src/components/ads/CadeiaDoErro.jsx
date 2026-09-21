import { useNaTela } from "./movimento";

/**
 * A CADEIA — Questão → Resposta → Erro → Padrão → Habilidade → Próximo estudo.
 *
 * A mesma seção nas quatro landings, logo abaixo da demonstração. Ela existe
 * para transformar o mecanismo que a pessoa acabou de VER num mecanismo que
 * ela consegue REPETIR de cabeça: a demo prova, a cadeia nomeia.
 *
 * Os seis elos aparecem em cascata quando a seção entra na tela, e não todos
 * de uma vez, porque a ordem é a informação. Uma lista de seis palavras que
 * nasce inteira é uma lista; seis palavras que chegam em fila são um processo.
 *
 * ---------------------------------------------------------------------------
 * VERTICAL NO CELULAR, DEITADA NO DESKTOP — E NUNCA ROLÁVEL
 * ---------------------------------------------------------------------------
 *
 * Uma fileira horizontal arrastável no celular esconderia o último elo, e o
 * último elo ("próximo estudo") é o único que diz o que a pessoa ganha. O
 * produto tem `TiraRolavel` para fileiras de catálogo — ali o que está
 * cortado é "mais do mesmo"; aqui seria a conclusão.
 *
 * A seta é UM ícone girado por CSS (`rotate-90` até `md`), não dois conjuntos
 * montados por condição de largura.
 */

const ELOS = [
  { rotulo: "Questão", tom: "neutro" },
  { rotulo: "Resposta", tom: "neutro" },
  { rotulo: "Erro", tom: "erro" },
  { rotulo: "Padrão", tom: "sinal" },
  { rotulo: "Habilidade", tom: "sinal" },
  { rotulo: "Próximo estudo", tom: "acao" },
];

export default function CadeiaDoErro({
  titulo = "Você não precisa de mais uma lista de questões.",
  corpo = "O Sapiens tenta entender o que acontece quando você erra.",
}) {
  const [alvo, visivel] = useNaTela();

  return (
    <section ref={alvo} className="mx-auto max-w-3xl" data-testid="ads-cadeia">
      <div className="mx-auto max-w-lg text-center">
        <h2 className="titulo-tela">{titulo}</h2>
        <p className="mx-auto mt-3 max-w-md text-[15px] leading-relaxed text-white/60">{corpo}</p>
      </div>

      <ol className="mt-8 flex flex-col items-stretch gap-1.5 md:flex-row md:items-center">
        {ELOS.map((elo, i) => (
          <li key={elo.rotulo} className="flex flex-col items-center gap-1.5 md:flex-1 md:flex-row">
            <span
              className={`ads-elo ads-elo-${elo.tom} ads-revela ${visivel ? "ads-revela-on" : ""}`}
              style={{ transitionDelay: `${i * 110}ms` }}
              data-testid={`ads-elo-${i}`}
            >
              {elo.rotulo}
            </span>
            {i < ELOS.length - 1 && (
              <span
                className={`ads-seta ads-revela ${visivel ? "ads-revela-on" : ""}`}
                style={{ transitionDelay: `${i * 110 + 55}ms` }}
                aria-hidden="true"
              />
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
