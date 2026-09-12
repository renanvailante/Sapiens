import { useMemo } from "react";
import katex from "katex";

// Renderiza `asset.latex` (LaTeX estrutural, validado visualmente contra o
// PNG original no saneamento) via KaTeX. O PNG (`asset.src`) é a
// procedência/fallback: se o LaTeX estiver ausente ou o KaTeX falhar ao
// renderizar (erro de sintaxe, símbolo não suportado etc.), cai
// automaticamente para a imagem — nunca quebra a questão.
export default function FormulaMath({ asset, imgSrc, imgAlt, className, testId, onClick, onError, imgProps }) {
  const html = useMemo(() => {
    if (!asset?.latex) return null;
    try {
      return katex.renderToString(asset.latex, {
        throwOnError: true,
        displayMode: true,
      });
    } catch {
      return null;
    }
  }, [asset?.latex]);

  if (html) {
    // `onClick` também aqui, e não só no `<img>` de fallback: a fórmula
    // renderizada carregava `cursor-zoom-in` da classe e não abria nada. No
    // celular, que é onde uma fórmula densa fica pequena demais para ler, era
    // justamente a versão que não dava para ampliar. O lightbox abre o PNG de
    // procedência — que existe mesmo quando o LaTeX renderiza.
    return (
      <div
        className={className}
        data-testid={testId}
        onClick={onClick}
        role={onClick ? "button" : undefined}
        tabIndex={onClick ? 0 : undefined}
        aria-label={onClick ? imgAlt : undefined}
        onKeyDown={onClick ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(e); } } : undefined}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }

  return (
    <img
      src={imgSrc}
      alt={imgAlt}
      className={className}
      loading="lazy"
      data-testid={testId}
      onClick={onClick}
      onError={onError}
      {...imgProps}
    />
  );
}
