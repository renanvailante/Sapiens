/**
 * Esqueletos de carregamento.
 *
 * O Painel esperava com a frase "Preparando seu painel..." centralizada numa
 * tela vazia. Três problemas, e nenhum deles é estético:
 *
 * 1. Não diz nada sobre o que vem. O aluno não sabe se a tela terá dois
 *    blocos ou vinte, e por isso não sabe se vale esperar.
 * 2. O conteúdo entra de uma vez e EMPURRA a página. Quem já tinha começado a
 *    ler perde o lugar.
 * 3. É a mesma espera de qualquer site. O esqueleto, com a forma real da
 *    tela, é a espera DESTE produto.
 *
 * A régua para escrever um: o esqueleto imita a SILHUETA, nunca o conteúdo.
 * Blocos, alturas e a grade — nada de texto falso, nada de números de mentira
 * piscando. Um esqueleto que finge ter dados é pior que uma tela vazia.
 */

export function Bloco({ className = "", altura }) {
  return (
    <div
      className={`esqueleto ${className}`}
      style={altura ? { height: altura } : undefined}
      aria-hidden="true"
    />
  );
}

export function Linha({ w = "100%", h = 12, className = "" }) {
  return (
    <div
      className={`esqueleto ${className}`}
      style={{ width: w, height: h, borderRadius: 999 }}
      aria-hidden="true"
    />
  );
}

/** O esqueleto do Painel. A silhueta segue a ordem real da tela: o passo
 *  seguinte, a tira de progresso, as missões e o resto. */
export default function EsqueletoDoPainel() {
  return (
    <div className="space-y-6" data-testid="esqueleto-painel" aria-busy="true" aria-label="Carregando o painel">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between gap-4">
        <Linha w="min(58%, 16rem)" h={30} />
        <Linha w="5rem" h={30} />
      </div>

      {/* O passo seguinte — a peça grande */}
      <Bloco className="rounded-[26px]" altura={208} />

      {/* Tira de progresso: quatro medidas */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Bloco key={i} className="rounded-3xl" altura={112} />
        ))}
      </div>

      {/* Missões do dia */}
      <div className="space-y-3">
        <Linha w="9rem" h={16} />
        <div className="grid gap-3 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Bloco key={i} className="rounded-3xl" altura={128} />
          ))}
        </div>
      </div>

      {/* Onde focar */}
      <div className="space-y-3">
        <Linha w="7rem" h={16} />
        <div className="grid gap-3 md:grid-cols-2">
          {[0, 1].map((i) => (
            <Bloco key={i} className="rounded-3xl" altura={116} />
          ))}
        </div>
      </div>
    </div>
  );
}
