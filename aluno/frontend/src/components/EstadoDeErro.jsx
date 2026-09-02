import { AlertCircle, RotateCw, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

/**
 * Estado de erro padrão das telas de conteúdo. Diz o que aconteceu e oferece
 * uma saída — as duas coisas que faltavam quando a tela simplesmente ficava
 * girando para sempre.
 */
export default function EstadoDeErro({ mensagem, aoTentarNovamente, voltarPara = "/dashboard", voltarLabel = "Ir para o painel" }) {
  return (
    <div className="card-sapiens rounded-2xl p-8 md:p-10 text-center" data-testid="estado-de-erro">
      <div className="w-12 h-12 mx-auto rounded-full bg-amber-50 flex items-center justify-center">
        <AlertCircle className="w-5 h-5 text-amber-600" />
      </div>
      <div className="mt-5 font-display text-xl font-bold tracking-tight text-zinc-950">
        Não conseguimos carregar
      </div>
      <p className="mt-2 text-sm text-zinc-500 leading-relaxed max-w-sm mx-auto">
        {mensagem || "Algo deu errado no caminho até o servidor."}
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        {aoTentarNovamente && (
          <button
            onClick={aoTentarNovamente}
            className="pill btn-sapiens inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium"
            data-testid="estado-de-erro-retry"
          >
            <RotateCw className="w-4 h-4" /> Tentar de novo
          </button>
        )}
        <Link
          to={voltarPara}
          className="pill inline-flex items-center gap-2 border border-zinc-200 text-sapiens-navy hover:border-sapiens-accent px-5 py-2.5 rounded-full text-sm font-medium"
        >
          <ArrowLeft className="w-4 h-4" /> {voltarLabel}
        </Link>
      </div>
    </div>
  );
}
