import { Fragment, useMemo } from "react";
import katex from "katex";
import { dividirEmBlocos, dividirInline } from "../../lib/conteudoMarkdown";

/**
 * Desenha o markdown dos blocos de conteúdo. A gramática mora em
 * `lib/conteudoMarkdown.js` (pura, testada); aqui só se transforma token em
 * elemento.
 *
 * **Nada de `dangerouslySetInnerHTML` no texto.** O parser devolve tokens e
 * este componente devolve elementos React — o conteúdo nunca vira HTML por
 * caminho nenhum. A ÚNICA exceção é a fórmula, cujo HTML é produzido pelo
 * KaTeX a partir do LaTeX; é a mesma escolha que `FormulaMath` já faz no
 * banco de questões.
 */

function Formula({ latex }) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(latex, { throwOnError: true, displayMode: false });
    } catch {
      return null;
    }
  }, [latex]);

  // LaTeX que o KaTeX não entende vira o texto cru, e não um buraco: quem
  // escreveu consegue ver o que quebrou, e o aluno ainda lê alguma coisa.
  if (!html) return <code className="rounded bg-black/10 px-1">{latex}</code>;
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function Tokens({ tokens }) {
  return (
    <>
      {tokens.map((token, i) => {
        if (token.tipo === "matematica") return <Formula key={i} latex={token.conteudo} />;
        if (token.tipo === "codigo") {
          return (
            <code key={i} className="rounded bg-black/10 px-1 py-0.5 text-[0.9em]">
              {token.conteudo}
            </code>
          );
        }
        if (token.tipo === "forte") {
          return (
            <strong key={i} className="font-semibold">
              <Tokens tokens={token.conteudo} />
            </strong>
          );
        }
        if (token.tipo === "enfase") {
          return <em key={i}><Tokens tokens={token.conteudo} /></em>;
        }
        return <Fragment key={i}>{token.conteudo}</Fragment>;
      })}
    </>
  );
}

function Linha({ texto }) {
  return <Tokens tokens={dividirInline(texto)} />;
}

export default function TextoRico({ markdown, className = "" }) {
  const partes = useMemo(() => dividirEmBlocos(markdown), [markdown]);

  return (
    <div className={`space-y-3 leading-relaxed ${className}`} data-testid="texto-rico">
      {partes.map((parte, i) => {
        if (parte.tipo === "titulo") {
          return (
            <h3 key={i} className="font-display text-base font-bold tracking-tight">
              <Linha texto={parte.texto} />
            </h3>
          );
        }
        if (parte.tipo === "citacao") {
          return (
            <blockquote key={i} className="border-l-2 border-current/30 pl-3 italic opacity-80">
              <Linha texto={parte.texto} />
            </blockquote>
          );
        }
        if (parte.tipo === "lista" || parte.tipo === "numerada") {
          const Lista = parte.tipo === "lista" ? "ul" : "ol";
          return (
            <Lista
              key={i}
              className={`ml-5 space-y-1.5 ${parte.tipo === "lista" ? "list-disc" : "list-decimal"}`}
            >
              {parte.itens.map((item, j) => (
                <li key={j}><Linha texto={item} /></li>
              ))}
            </Lista>
          );
        }
        return <p key={i}><Linha texto={parte.texto} /></p>;
      })}
    </div>
  );
}
