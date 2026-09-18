import { useEffect, useState } from "react";

/**
 * Um anel de progresso — a peça que faz um número virar QUANTIDADE antes de
 * ser lido.
 *
 * O produto tinha barras horizontais em toda parte e nenhum anel. A diferença
 * não é estética: uma barra de 8px de altura no meio de um card de texto é
 * lida como enfeite, e um anel que envolve o próprio número é lido como o
 * estado daquele número. É por isso que ele é usado onde o dado é a
 * identidade do bloco (nível, domínio, pontos do mapa) e não onde o dado é
 * mais um campo (progresso de missão continua sendo barra).
 *
 * **O traço se desenha ao chegar.** Nasce em zero e vai até o valor medido em
 * 900ms. É a única animação do produto que mostra um número crescendo, e ela
 * só é honesta porque o destino é o dado real e a duração é fixa: nada aqui
 * "enche até" nada — ele desenha o que já é verdade. Com movimento reduzido
 * ligado, o traço aparece direto no valor final (ver `.anel-traco`).
 *
 * O degradê é o mesmo ciano -> violeta da barra, do traço da aba ativa e do
 * sulco da marca: a luz do produto é uma só.
 */
export default function AnelDeProgresso({
  valor = 0,           // 0..100
  tamanho = 76,
  espessura = 7,
  cor = null,          // sobrescreve o degradê (domínio usa a cor da faixa)
  className = "",
  children,
  testid,
}) {
  const pct = Math.max(0, Math.min(100, Number(valor) || 0));
  // O traço só sai de zero DEPOIS da primeira pintura: mudar `strokeDashoffset`
  // no mesmo quadro em que o elemento nasce não dispara transição nenhuma, e o
  // anel apareceria cheio, parado.
  const [desenhado, setDesenhado] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setDesenhado(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const r = (tamanho - espessura) / 2;
  const volta = 2 * Math.PI * r;
  const gradId = `anel-${Math.round(tamanho)}-${espessura}`;

  return (
    <div
      className={`relative inline-flex shrink-0 items-center justify-center ${className}`}
      style={{ width: tamanho, height: tamanho }}
      data-testid={testid}
    >
      <svg width={tamanho} height={tamanho} className="-rotate-90" aria-hidden="true">
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#4FD9FF" />
            <stop offset="100%" stopColor="#8B7BFF" />
          </linearGradient>
        </defs>
        {/* O trilho. Existe sempre, inclusive em 0% — sem ele o anel vazio
            some e o bloco fica com um buraco no lugar de um estado. */}
        <circle
          cx={tamanho / 2}
          cy={tamanho / 2}
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.09)"
          strokeWidth={espessura}
        />
        <circle
          className="anel-traco"
          cx={tamanho / 2}
          cy={tamanho / 2}
          r={r}
          fill="none"
          stroke={cor || `url(#${gradId})`}
          strokeWidth={espessura}
          strokeLinecap="round"
          strokeDasharray={volta}
          strokeDashoffset={desenhado ? volta * (1 - pct / 100) : volta}
          style={{ filter: pct > 0 ? "drop-shadow(0 0 6px rgba(79,217,255,0.45))" : undefined }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center leading-none">
        {children}
      </div>
    </div>
  );
}
