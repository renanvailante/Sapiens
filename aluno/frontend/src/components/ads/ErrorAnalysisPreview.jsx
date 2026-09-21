/**
 * A LEITURA DO ERRO, EM TRÊS DEGRAUS.
 *
 * "Você errou" → "não foi só falta de conteúdo" → "foi esta habilidade". É a
 * descida que o produto faz de verdade: a resposta é o sintoma, o padrão é o
 * diagnóstico, e a habilidade é o que vira estudo. A landing mostra a descida
 * porque é ela — e não a lista de recursos — que explica por que o Sapiens não
 * é um banco de questões.
 *
 * ---------------------------------------------------------------------------
 * O QUE ESTA PEÇA NÃO PODE FAZER
 * ---------------------------------------------------------------------------
 *
 * **Não nomear a ontologia.** Os nomes internos de processo, competência e
 * tipo de erro são a propriedade intelectual do produto e nunca aparecem para
 * o aluno — nem dentro do app, nem aqui. O último degrau fala a língua do
 * vestibulando ("ler informação em gráfico"), que é exatamente como o produto
 * já fala com ele.
 *
 * **Não afirmar nada sobre quem está lendo.** Todo texto aqui descreve o
 * exemplo da página; nenhum se dirige ao visitante como se soubesse algo dele.
 * A `DiagnosticPreview` carrega o aviso de que a cena é ilustrativa e as duas
 * peças aparecem sempre juntas.
 */

/** Os três degraus. `tom` decide a cor da linha e do ponto — vermelho para o
 *  sintoma, neutro para a virada, ciano para o que o produto entrega. */
const DEGRAUS = [
  {
    tom: "erro",
    titulo: "Você errou esta questão.",
    corpo: "Marcou D. A resposta era C.",
  },
  {
    tom: "neutro",
    titulo: "Não foi apenas falta de conteúdo.",
    corpo: "As duas alternativas exigiam comparar valores no gráfico — e só uma delas comparava os anos certos.",
  },
  {
    tom: "sinal",
    titulo: "Seu erro indica dificuldade em interpretar informações de um gráfico.",
    corpo: "É essa habilidade que entra no seu estudo — não a questão que você errou.",
  },
];

const COR_DO_PONTO = {
  erro: "bg-rose-400",
  neutro: "bg-white/35",
  sinal: "bg-[#4FD9FF]",
};

export default function ErrorAnalysisPreview({ titulo = "O que o Sapiens leu nesse erro" }) {
  return (
    <section className="superficie rounded-3xl p-5 md:p-6" data-testid="ads-analise-erro">
      <div className="secao-olho">{titulo}</div>

      {/* A linha vertical que liga os degraus é um `::before` do próprio
          container (borda esquerda), não um elemento a mais por degrau: um
          traço decorativo por item multiplica nós sem acrescentar leitura. */}
      <ol className="mt-4 space-y-0 border-l border-white/12 pl-5">
        {DEGRAUS.map((d, i) => (
          <li
            key={d.titulo}
            className={`relative ${i === DEGRAUS.length - 1 ? "" : "pb-5"}`}
            data-testid={`ads-degrau-${i}`}
          >
            <span
              className={`absolute -left-[26px] top-1.5 h-2.5 w-2.5 rounded-full ring-4 ring-[#0A1323] ${COR_DO_PONTO[d.tom]}`}
              aria-hidden="true"
            />
            <p className={`text-[15px] font-bold leading-snug ${d.tom === "sinal" ? "text-white" : "text-white/85"}`}>
              {d.titulo}
            </p>
            <p className="mt-1 text-[13px] leading-relaxed text-white/50">{d.corpo}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
