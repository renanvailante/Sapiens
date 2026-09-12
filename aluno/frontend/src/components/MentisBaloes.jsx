/**
 * Balões de sugestão do chat da Mentis — compartilhados entre a página cheia
 * (`MentisChat.jsx`) e o widget flutuante (`MentisWidget.jsx`) para não
 * duplicar a mesma lógica de clique/cobrança nos dois lugares.
 */

// Balões de abertura: sempre os mesmos, sempre visíveis assim que a sessão
// abre. Fixos de propósito — não dependem do modelo, então não custam Sparks
// nem tokens extras só para existir.
export const BALOES_INICIAIS = [
  // Primeiro da lista de propósito: organizar a semana é o pedido que mais
  // aparece e o único que termina numa tela pronta em vez de numa resposta.
  { texto: "🗓️ Crie um cronograma de estudos pra mim", tipo: "enviar" },
  { texto: "📈 Quero descobrir o que mais pode aumentar minha nota", tipo: "enviar" },
  { texto: "💡 Tenho uma dúvida, mas não sei nem por onde começar", tipo: "enviar" },
  { texto: "🧩 Crie 5 questões para eu descobrir onde estou errando", tipo: "enviar" },
  { texto: "🎯 Monte um treino só para mim", tipo: "enviar" },
  { texto: "🔥 Me desafie com algo que eu provavelmente erraria", tipo: "enviar" },
  { texto: "🔍 Veja o que está impedindo minha evolução", tipo: "enviar" },
];

/** Fileira de balões clicáveis. "enviar" manda a mensagem na hora, pelo
 *  mesmo fluxo (e custo) de digitar e apertar enviar. "completar" só
 *  preenche o campo, para o aluno terminar antes de mandar. */
export default function Baloes({ itens, aoClicar, enviando, semSaldo }) {
  if (!itens || itens.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2 pt-1" data-testid="mentis-baloes">
      {itens.map((b, i) => {
        const bloqueado = enviando || (b.tipo !== "completar" && semSaldo);
        return (
          <button
            key={`${b.texto}-${i}`}
            type="button"
            onClick={() => aoClicar(b)}
            disabled={bloqueado}
            className="rounded-full border border-white/15 bg-white/5 px-3.5 py-2 text-left text-xs text-white/80 transition hover:border-white/25 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
            data-testid="mentis-balao"
          >
            {b.texto}
          </button>
        );
      })}
    </div>
  );
}
