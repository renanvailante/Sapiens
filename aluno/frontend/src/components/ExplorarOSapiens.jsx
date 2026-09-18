import { useCallback, useState } from "react";
import { ChevronDown, Compass } from "lucide-react";

/**
 * EXPLORAR O SAPIENS — a descoberta, sem competir com a ação.
 *
 * O Painel tinha duas aberturas ao mesmo tempo: as dez Portas e o Próximo
 * Passo. Duas respostas para "e agora?" na mesma dobra, e a de cima sempre
 * ganha — o que na prática enterrava a única peça da tela que sabe o que o
 * aluno deveria fazer hoje.
 *
 * Esta seção não resolve isso apagando a descoberta. Ela a move para onde
 * descoberta pertence: DEPOIS da decisão, e atrás de um clique.
 *
 * Três regras:
 *
 * 1. **Fechada não quer dizer escondida.** O cabeçalho é um botão de largura
 *    inteira que diz quantas portas existem e quantas o aluno ainda não
 *    abriu. Um acordeão que não conta o que tem dentro é uma gaveta; um que
 *    conta é um convite.
 * 2. **Aberta por padrão para quem ainda não tem trajetória.** Quem nunca
 *    respondeu nada não tem revisão vencendo nem bloco marcado: para ele o
 *    Próximo Passo é fraco e a vitrine é a peça forte. `abertoInicial` é o
 *    Painel dizendo isso — ver `Dashboard.jsx`.
 * 3. **A escolha do aluno vence a nossa.** Abriu ou fechou, fica como ele
 *    deixou, no `localStorage` — conveniência de quem está olhando, nunca
 *    estado de produto. Se o navegador bloquear, a seção continua correta:
 *    volta a abrir pela regra do item 2.
 *
 * O conteúdo entra por `children` de propósito. Esta peça é sobre HIERARQUIA,
 * não sobre portas; em P3 o Lançador de Ferramentas passa por aqui também.
 */

const CHAVE = "sapiens:explorar-aberto";

function lerPreferencia() {
  try {
    const cru = localStorage.getItem(CHAVE);
    return cru === null ? null : cru === "1";
  } catch {
    return null;
  }
}

function gravarPreferencia(aberto) {
  try {
    localStorage.setItem(CHAVE, aberto ? "1" : "0");
  } catch {
    /* navegador sem armazenamento: a seção funciona igual, só não lembra */
  }
}

export default function ExplorarOSapiens({
  children,
  abertoInicial = false,
  titulo = "Explorar o Sapiens",
  descricao = "Dez portas. Cada uma te conta algo que você ainda não sabe.",
  testid = "explorar",
}) {
  // A preferência gravada ganha; sem preferência, vale o que o Painel sugeriu.
  const [aberto, setAberto] = useState(() => lerPreferencia() ?? abertoInicial);

  const alternar = useCallback(() => {
    setAberto((a) => {
      gravarPreferencia(!a);
      return !a;
    });
  }, []);

  return (
    <section data-testid={testid}>
      <button
        type="button"
        onClick={alternar}
        aria-expanded={aberto}
        className="superficie lift flex w-full items-center gap-3.5 p-4 text-left"
        data-testid={`${testid}-botao`}
      >
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[#7FD8FF]/25 bg-[#7FD8FF]/10 text-[#7FD8FF]">
          <Compass className="h-5 w-5" strokeWidth={1.8} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-display text-base font-bold tracking-tight text-white">
            {titulo}
          </span>
          <span className="block text-xs text-white/50">{descricao}</span>
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-white/40 transition-transform duration-200 ${aberto ? "rotate-180" : ""}`}
        />
      </button>

      {/* Desmonta quando fechada em vez de esconder com CSS: as portas leem
          quatro payloads e desenham dez cards: mantê-los montados atrás de um
          `hidden` custa renderização em toda atualização do Painel para uma
          seção que ninguém está olhando. */}
      {aberto && <div className="mt-3">{children}</div>}
    </section>
  );
}
