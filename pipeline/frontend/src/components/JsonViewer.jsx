import { useMemo } from "react";

/**
 * Zero-dependency JSON highlighter that produces a compact IBM Plex Mono block
 * respecting the Swiss / high-contrast aesthetic.
 */
function highlight(json) {
  const text = typeof json === "string" ? json : JSON.stringify(json, null, 2);
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return escaped.replace(
    /("(?:\\.|[^"\\])*"\s*:)|("(?:\\.|[^"\\])*")|\b(true|false|null)\b|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g,
    (m, key, str, bool, num) => {
      if (key) return `<span style="color:#002FA7;font-weight:600">${key}</span>`;
      if (str) return `<span style="color:#059669">${str}</span>`;
      if (bool) return `<span style="color:#E11D48;font-weight:600">${bool}</span>`;
      if (num) return `<span style="color:#0f172a">${num}</span>`;
      return m;
    },
  );
}

export default function JsonViewer({ data, className = "", testId }) {
  const html = useMemo(() => highlight(data ?? {}), [data]);
  return (
    <pre
      data-testid={testId}
      className={`font-mono text-[12.5px] leading-relaxed bg-white border border-border p-4 overflow-auto whitespace-pre-wrap break-words ${className}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
