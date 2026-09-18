import { createContext, useContext, useState } from "react";
import { Table2, ChevronDown, ArrowRight } from "lucide-react";
import Mentis from "../Mentis";
import { BALAO, TINTA, GRADE, pct } from "./paleta";

/**
 * A MENTIS DENTRO DO GRÁFICO.
 *
 * O guia no topo da tela diz uma coisa de cada vez. Este contexto é o outro
 * lado disso: cada cartão sabe se ela tem uma leitura SOBRE ELE e mostra a
 * marca dela ali, no canto. É o que transforma "um texto no topo" em
 * "alguém acompanhando a tela inteira".
 *
 * Vive como contexto, e não como propriedade, porque são onze gráficos: passar
 * a mesma coisa onze vezes à mão é como se produz o décimo segundo esquecido.
 */
export const ContextoDaMentis = createContext({ porAncora: {}, ativa: null, aoFocar: () => {} });

function SeloDaMentis({ id }) {
  const { porAncora, ativa, aoFocar } = useContext(ContextoDaMentis);
  const leitura = porAncora?.[id];
  if (!leitura) return null;
  const ativo = ativa === id;

  return (
    <button
      type="button"
      onClick={() => aoFocar(leitura.indice)}
      className={[
        "mt-3 flex w-full items-start gap-2.5 rounded-2xl border p-3 text-left transition-colors",
        ativo
          ? "border-[rgba(79,217,255,0.42)] bg-[rgba(79,217,255,0.07)]"
          : "border-zinc-100 hover:border-zinc-200",
      ].join(" ")}
      data-testid={`mentis-no-grafico-${id}`}
    >
      <Mentis className="h-6 w-6 shrink-0" variante="icone" animada={ativo} />
      <span className="min-w-0 flex-1">
        <span className="block text-[11px] font-semibold leading-snug text-zinc-300">
          {leitura.titulo}
        </span>
        {ativo && (
          <span className="mt-1 block text-[11px] leading-relaxed text-zinc-500">{leitura.texto}</span>
        )}
      </span>
      {!ativo && <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-500" />}
    </button>
  );
}

/**
 * A CASCA DE UM GRÁFICO — título, legenda, altura e a tabela por baixo.
 *
 * Onze gráficos numa tela só viram onze jeitos diferentes de mostrar a mesma
 * coisa se cada um for escrito à mão. Aqui a anatomia é uma peça:
 *
 *  · **olho + título + explicação.** A explicação não é enfeite: é onde o
 *    gráfico diz de onde vem o número e qual a amostra. Um gráfico sobre a
 *    vida de alguém sem a amostra ao lado é uma afirmação sem evidência.
 *  · **legenda sempre que houver duas séries ou mais**, e nunca o contrário:
 *    com uma série só, o título já diz o que está desenhado, e uma caixinha
 *    com um quadrado repete o título e come espaço.
 *  · **a tabela.** Todo gráfico daqui abre numa tabela com os mesmos números.
 *    Balão de valor que só aparece no hover não existe no celular e não existe
 *    para quem usa leitor de tela — se o valor só vive lá, ele não está
 *    disponível.
 *  · **a âncora.** `id` é o que a Mentis usa para apontar: quando ela comenta
 *    um gráfico, a tela rola até ele e ele acende (`destacado`).
 */
export default function Grafico({
  id,
  olho,
  titulo,
  explicacao,
  legenda,          // [{ cor, rotulo }] — omitido quando há uma série só
  altura = 260,
  tabela,           // { colunas: [...], linhas: [[...]] }
  destacado = false,
  acaoTopo,
  // Tudo o que vem DEPOIS do gráfico (uma frase de leitura, um botão de ação)
  // entra por aqui, e não como filho: o filho vive dentro de uma caixa de
  // altura fixa — a do desenho — e qualquer coisa a mais ali dentro é
  // espremida por cima do próprio gráfico. Foi o que aconteceu, e é o tipo de
  // defeito que nenhum teste de render pega: o HTML está certo, a altura é
  // que não é.
  rodape,
  className = "",
  children,
}) {
  const [verTabela, setVerTabela] = useState(false);

  return (
    <section
      id={id}
      data-testid={`grafico-${id}`}
      className={[
        "card-sapiens rounded-3xl p-4 md:p-5 transition-shadow duration-500",
        destacado ? "ring-1 ring-[#4FD9FF]/60 shadow-[0_0_46px_-16px_rgba(79,217,255,0.55)]" : "",
        className,
      ].join(" ")}
      // `scroll-margin` porque a barra do topo é fixa: sem isto a Mentis rola
      // até o gráfico e o título dele fica escondido atrás da barra.
      style={{ scrollMarginTop: "6rem" }}
    >
      <header className="mb-3 flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          {olho && <div className="secao-olho flex items-center gap-1.5">{olho}</div>}
          <h3 className="mt-1.5 font-display text-base font-bold leading-snug tracking-tight text-zinc-950 md:text-lg">
            {titulo}
          </h3>
          {explicacao && (
            <p className="mt-1 max-w-prose text-xs leading-relaxed text-zinc-500">{explicacao}</p>
          )}
        </div>
        {acaoTopo}
      </header>

      {legenda?.length > 1 && (
        <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1.5">
          {legenda.map((l) => (
            <span key={l.rotulo} className="inline-flex items-center gap-1.5 text-[11px] text-zinc-400">
              <span
                className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: l.cor }}
                aria-hidden="true"
              />
              {l.rotulo}
            </span>
          ))}
        </div>
      )}

      <div style={{ height: altura }}>{children}</div>

      {rodape}

      <SeloDaMentis id={id} />

      {tabela?.linhas?.length > 0 && (
        <div className="mt-3 border-t border-zinc-100 pt-2">
          <button
            type="button"
            onClick={() => setVerTabela((v) => !v)}
            className="pill inline-flex min-h-[32px] items-center gap-1.5 rounded-full px-2 py-1 text-[11px] font-semibold text-zinc-500 hover:text-zinc-200"
            data-testid={`grafico-${id}-tabela`}
            aria-expanded={verTabela}
          >
            <Table2 className="h-3.5 w-3.5" />
            {verTabela ? "Esconder os números" : "Ver os números"}
            <ChevronDown className={`h-3.5 w-3.5 transition-transform ${verTabela ? "rotate-180" : ""}`} />
          </button>
          {verTabela && (
            <div className="mt-2 max-h-64 overflow-auto no-scrollbar">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wide text-zinc-500">
                    {tabela.colunas.map((c) => (
                      <th key={c} className="py-1.5 pr-3 font-semibold">{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="font-mono-alt text-zinc-300">
                  {tabela.linhas.map((linha, i) => (
                    <tr key={i} className="border-t border-zinc-100">
                      {linha.map((celula, j) => (
                        <td key={j} className="py-1.5 pr-3 align-top">{celula}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

/**
 * O balão de valor. Escrito à mão em vez de usar o padrão do recharts por um
 * motivo só: o padrão mostra a chave crua do dado (`movel`, `taxa`) e o número
 * com seis casas. Aqui cada linha é uma frase.
 */
export function Balao({ active, payload, label, titulo, linhas }) {
  if (!active || !payload?.length) return null;
  const ponto = payload[0]?.payload || {};
  const itens = linhas ? linhas(ponto, payload) : payload.map((p) => ({
    cor: p.color,
    rotulo: p.name,
    valor: typeof p.value === "number" ? pct(p.value) : String(p.value ?? "—"),
  }));
  return (
    <div style={BALAO}>
      <div style={{ color: TINTA.media, fontSize: 11, marginBottom: 4 }}>
        {titulo ? titulo(ponto) : label}
      </div>
      {itens.filter(Boolean).map((i, k) => (
        <div key={k} style={{ display: "flex", alignItems: "center", gap: 6, lineHeight: 1.6 }}>
          {i.cor && (
            <span
              style={{ width: 8, height: 8, borderRadius: 999, background: i.cor, flex: "0 0 auto" }}
            />
          )}
          <span style={{ color: TINTA.media }}>{i.rotulo}</span>
          <strong style={{ color: TINTA.forte, marginLeft: "auto" }}>{i.valor}</strong>
        </div>
      ))}
    </div>
  );
}

/** Estado vazio de UM gráfico — a tela não some, o gráfico é que ainda não
 *  tem o que dizer. Dizer POR QUE falta é o que separa "sem dados" de "faça
 *  isto e o gráfico aparece". */
export function SemDado({ children }) {
  return (
    <div
      className="flex h-full items-center justify-center rounded-2xl border border-dashed px-6 text-center text-xs leading-relaxed text-zinc-500"
      style={{ borderColor: GRADE }}
    >
      {children}
    </div>
  );
}
