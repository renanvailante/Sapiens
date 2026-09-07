import { useMemo } from "react";
import { primitivasDe } from "./glifos";

/** Sigilo de uma missão: o glifo da família mais os pontos da variante.
 * Duas missões da mesma família compartilham a forma — é isso que deixa a
 * coleção legível como progressão — mas nenhuma tem o mesmo desenho, porque
 * a contagem de pontos difere. */
export default function IconeMissao({ familia, variante = 1, cor = "#4FD9FF", tamanho = 22, opacidade = 1 }) {
  const primitivas = useMemo(() => primitivasDe(familia), [familia]);

  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke={cor}
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      opacity={opacidade}
      aria-hidden="true"
    >
      {primitivas.map((prim, i) => {
        if (prim.tipo === "p") return <path key={i} d={prim.d} />;
        if (prim.tipo === "l") {
          const [x1, y1, x2, y2] = prim.n;
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
        }
        if (prim.tipo === "c") {
          const [cx, cy, r] = prim.n;
          return <circle key={i} cx={cx} cy={cy} r={r} />;
        }
        if (prim.tipo === "d") {
          const [cx, cy, r] = prim.n;
          return <circle key={i} cx={cx} cy={cy} r={r} fill={cor} stroke="none" />;
        }
        const [x, y, w, h] = prim.n;
        return <rect key={i} x={x} y={y} width={w} height={h} rx={1.2} />;
      })}

      {/* Marca da variante: o que separa Proporção I de Proporção II. */}
      {Array.from({ length: Math.max(0, variante - 1) }).map((_, i) => (
        <circle key={`v${i}`} cx={21.2} cy={21.2 - i * 3.4} r={1} fill={cor} stroke="none" />
      ))}
    </svg>
  );
}
