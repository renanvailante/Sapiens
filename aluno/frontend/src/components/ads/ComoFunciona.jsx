import { useNaTela } from "./movimento";

/**
 * COMO FUNCIONA — três passos, e nenhuma palavra sobre tecnologia.
 *
 * A seção existe para responder "o que eu faço?" logo depois de a demo ter
 * respondido "o que ele faz?". As duas perguntas são diferentes e a segunda
 * sem a primeira deixa a pessoa impressionada e parada.
 *
 * Três decisões de copy que valem para as quatro landings:
 *
 * - **"Responda" é o primeiro passo, não "cadastre-se".** O cadastro é o
 *   pedágio, não a proposta; anunciá-lo como passo 01 é abrir a conversa pelo
 *   que a pessoa não quer fazer.
 * - **Nenhuma menção a IA, modelo ou algoritmo.** A análise de erro do
 *   Sapiens é determinística e não chama LLM nenhum — dizer "inteligência
 *   artificial" aqui seria, além de ruído de landing genérica, impreciso.
 * - **O passo 03 entrega uma DIREÇÃO, não uma promessa de nota.** "Aumenta
 *   sua nota em X%" é exatamente o claim que este produto não faz.
 *
 * Os três aparecem em cascata ao entrar na tela — mesma primitiva da cadeia,
 * mesmo motivo: a ordem é parte do conteúdo.
 */

const PASSOS = [
  {
    n: "01",
    titulo: "Responda",
    corpo: "Faça questões normalmente, como você já faz.",
  },
  {
    n: "02",
    titulo: "O Sapiens analisa",
    corpo: "Seus erros são analisados em conjunto, não um a um.",
  },
  {
    n: "03",
    titulo: "Você recebe um próximo passo",
    corpo: "Os padrões encontrados viram uma direção de estudo.",
  },
];

export default function ComoFunciona() {
  const [alvo, visivel] = useNaTela();

  return (
    <section ref={alvo} className="mx-auto max-w-3xl" data-testid="ads-como-funciona">
      <ol className="grid gap-3 md:grid-cols-3">
        {PASSOS.map((p, i) => (
          <li
            key={p.n}
            className={`superficie rounded-2xl p-5 ads-revela ${visivel ? "ads-revela-on" : ""}`}
            style={{ transitionDelay: `${i * 130}ms` }}
            data-testid={`ads-passo-${p.n}`}
          >
            <div className="font-mono-alt text-[11px] font-bold tracking-[0.2em] text-[#7FD8FF]/70">
              {p.n}
            </div>
            <h3 className="mt-2 text-[15px] font-extrabold leading-tight text-white">{p.titulo}</h3>
            <p className="mt-1.5 text-[13px] leading-relaxed text-white/50">{p.corpo}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
