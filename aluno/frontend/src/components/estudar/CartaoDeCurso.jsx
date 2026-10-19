import { Link } from "react-router-dom";
import { ArrowRight, Bell, BellRing, Infinity as Infinito } from "lucide-react";
import { glifoDaCapa } from "../curso/CapaDoCurso";
import { ROTAS } from "../../lib/rotas";

/**
 * UM CURSO OU UM E-BOOK no catálogo do Estudar.
 *
 * Capa com o glifo grande e aceso, o nome inteiro (duas linhas, nunca
 * cortado em uma) e UMA ação escrita no pé. Quando o item já é do aluno e
 * tem conteúdo, o cartão inteiro é o link — o Duolingo não pede para achar o
 * botão dentro do cartão. Quando não é, o cartão não navega e a ação é o
 * botão de preço, com o número do SERVIDOR (`custo_sparks`), nunca daqui.
 *
 * Substitui o `LadrilhoDeCatalogo` (2026-09-18 a 2026-10-10), que escondia
 * nome, status e ação atrás de um hover e empilhava quatro selos sobre a capa.
 */
export default function CartaoDeCurso({
  item,
  tipo = "curso",
  comprando = false,
  marcando = false,
  aoComprar,
  aoAvisar,
}) {
  const ebook = tipo === "ebook";
  const id = ebook ? item.ebook_id : item.curso_id;
  const Glifo = glifoDaCapa(item.capa);
  const cor = {
    "--de": item.capa?.de || "#4FD9FF",
    "--para": item.capa?.para || "#2F6BFF",
    // O pé é a cor final do degradê escurecida — a mesma regra do `--btn-pe`.
    "--pe": `color-mix(in srgb, ${item.capa?.para || "#2F6BFF"} 55%, #03060D)`,
    "--tinta": "#BFE7FF",
  };
  const p = item.progresso || {};
  const podeAbrir = item.tenho_acesso && item.tem_conteudo;
  const destino = ebook ? ROTAS.EBOOK.replace(":ebookId", id) : `${ROTAS.CURSOS}/${id}`;
  const meta = ebook ? `${item.paginas} páginas` : [item.carga, item.nivel].filter(Boolean).join(" · ");
  const testid = `cartao-${tipo}-${id}`;

  const corpo = (
    <>
      <div className="cartao-curso-capa">
        <Glifo strokeWidth={2} aria-hidden="true" />
        {!item.tem_conteudo && <span className="cartao-gordo-selo">Em breve</span>}
        {/* Só para quem ainda não tem um curso que ainda não abriu: avisar
            "quando abrir" um curso que já está no ar não diz nada. */}
        {!ebook && !item.tenho_acesso && !item.tem_conteudo && aoAvisar && (
          <button
            type="button"
            onClick={() => aoAvisar(item)}
            disabled={marcando}
            title={item.tenho_interesse ? "Você será avisado" : "Me avise quando abrir"}
            aria-label={item.tenho_interesse ? "Não me avisar mais" : "Me avise quando abrir"}
            aria-pressed={!!item.tenho_interesse}
            className={`cartao-curso-sino pill inline-flex h-8 w-8 items-center justify-center rounded-full border backdrop-blur-sm disabled:opacity-50 ${
              item.tenho_interesse
                ? "border-emerald-300/60 bg-emerald-500/70 text-white"
                : "border-white/30 bg-black/35 text-white hover:bg-black/50"
            }`}
            data-testid={`${testid}-avisar`}
          >
            {item.tenho_interesse ? <BellRing className="h-3.5 w-3.5" /> : <Bell className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-3 p-3.5 pt-3">
        <div className="min-w-0">
          <h3 className="cartao-gordo-titulo cartao-gordo-titulo--p">{item.titulo}</h3>
          {meta && <div className="cartao-gordo-sub mt-0.5">{meta}</div>}
        </div>
        <div className="mt-auto">
          {podeAbrir ? (
            <div className="space-y-2">
              {!ebook && p.comecou && (
                <div className="cartao-gordo-barra" style={{ height: 8 }}>
                  <i style={{ width: `${Math.max(p.percentual || 0, 4)}%` }} />
                </div>
              )}
              <span className="cartao-gordo-acao" data-testid={`${testid}-acao`}>
                {ebook ? "Ler" : p.comecou ? `Continuar · ${p.percentual || 0}%` : "Começar"}
                <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.6} />
              </span>
            </div>
          ) : item.tenho_acesso ? (
            <span className="text-xs font-semibold text-white/60">Já é seu · avisamos quando abrir</span>
          ) : (
            <button
              type="button"
              onClick={() => aoComprar?.(item)}
              disabled={comprando}
              title="Acesso vitalício: paga uma vez, é seu para sempre"
              className="pill btn-sapiens inline-flex w-full items-center justify-center gap-1.5 rounded-full px-3 py-2 text-xs font-bold disabled:opacity-50"
              data-testid={`${testid}-comprar`}
            >
              <Infinito className="h-3.5 w-3.5 shrink-0" />
              {comprando ? "Garantindo…" : `${item.custo_sparks} Sparks`}
            </button>
          )}
        </div>
      </div>
    </>
  );

  return (
    <li className="list-none">
      {podeAbrir ? (
        <Link to={destino} className="cartao-gordo h-full" style={cor} data-testid={testid} title={item.chamada}>
          {corpo}
        </Link>
      ) : (
        <article className="cartao-gordo h-full" style={cor} data-testid={testid} title={item.chamada}>
          {corpo}
        </article>
      )}
    </li>
  );
}
