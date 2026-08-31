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
    return (
      <div
        className={className}
        data-testid={testId}
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
