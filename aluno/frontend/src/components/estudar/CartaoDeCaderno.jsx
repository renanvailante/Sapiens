import { Calculator, BookOpenText, Landmark, FlaskConical, BookOpen, ArrowRight, Check, RotateCw } from "lucide-react";
import { identidadeDaArea, rotuloDoCaderno, estadoDoCaderno } from "../../lib/cadernos";

// Nome do glifo (de `lib/cadernos.js`) -> ícone. Tradução, não decisão.
const GLIFOS = {
  matematica: Calculator,
  linguagens: BookOpenText,
  humanas: Landmark,
  natureza: FlaskConical,
  generico: BookOpen,
};

/**
 * UM CADERNO — 45 questões de uma área de uma prova real.
 *
 * O título é a ÁREA (o aluno escolhe "vou fazer Matemática"), não a edição,
 * que já está no cabeçalho do grupo (ver `lib/cadernos.js`). O cartão inteiro
 * é o botão; reiniciar é um botão irmão no canto — botão dentro de botão não
 * é HTML válido e o leitor de tela anunciaria os dois como um só.
 *
 * Progresso é o que o aluno RESPONDEU (`provas-progresso`), nunca o tamanho
 * do bloco; "última X%" só com rodada concluída de verdade.
 */
export default function CartaoDeCaderno({ prova, respondidas = 0, ultima = null, aoAbrir, aoReiniciar }) {
  const p = prova;
  const r = rotuloDoCaderno(p);
  const cor = identidadeDaArea(p.disciplinas?.[0]);
  const Glifo = GLIFOS[cor.glifo] || BookOpen;
  const total = p.count || 0;
  const feitas = Math.min(respondidas, total);
  const pct = total > 0 ? Math.round((100 * feitas) / total) : 0;
  const estado = estadoDoCaderno(feitas, total);
  const id = `${p.banca}-${p.ano}-${p.prova}-${p.numero_min}`;

  return (
    <li className="relative list-none">
      <button
        type="button"
        onClick={() => aoAbrir(p)}
        className="cartao-gordo h-full w-full gap-3 p-4"
        style={{ "--de": cor.de, "--para": cor.para, "--pe": cor.pe, "--tinta": cor.tinta }}
        data-testid={`prova-card-${id}`}
        data-estado={estado}
        aria-label={`${r.titulo}, ${r.edicao} ${r.caderno}, ${feitas} de ${total} respondidas`}
      >
        <div className="flex items-start justify-between gap-2">
          <span className="cartao-gordo-icone" aria-hidden="true">
            <Glifo strokeWidth={2.2} />
          </span>
          {estado === "concluido" && (
            <span className="cartao-gordo-selo cartao-gordo-selo--feito">
              <Check className="h-3 w-3" strokeWidth={3.5} /> Feito
            </span>
          )}
        </div>

        <div className="min-w-0">
          <div className="cartao-gordo-titulo">{r.titulo}</div>
          <div className="cartao-gordo-sub mt-0.5">{r.sub}</div>
        </div>

        <div className="mt-auto space-y-2">
          <div className="cartao-gordo-barra" data-testid={`prova-progresso-${id}`}>
            <i style={{ width: `${pct}%` }} />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold tabular-nums text-white/65" data-testid={`prova-stats-${id}`}>
              {feitas}/{total}
              {ultima != null ? ` · última ${ultima}%` : ""}
            </span>
            <span className="cartao-gordo-acao">
              {estado === "concluido" ? "Ver" : estado === "andamento" ? "Continuar" : "Começar"}
              <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.6} />
            </span>
          </div>
        </div>
      </button>

      {feitas > 0 && aoReiniciar && (
        <button
          type="button"
          onClick={() => aoReiniciar(p)}
          title="Recomeçar este caderno"
          aria-label={`Recomeçar ${r.titulo}, ${r.edicao} ${r.caderno}`}
          className={`absolute ${estado === "concluido" ? "right-3 top-12" : "right-3 top-3"} z-10 inline-flex h-8 w-8 items-center justify-center rounded-full text-white/45 transition-colors hover:bg-white/10 hover:text-white`}
          data-testid={`prova-reset-${id}`}
        >
          <RotateCw className="h-3.5 w-3.5" />
        </button>
      )}
    </li>
  );
}
