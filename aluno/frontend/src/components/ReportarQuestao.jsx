import { useState } from "react";
import { Flag, X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";

/** Bandeira de "algo errado com esta questão" — presente em toda questão que
 * o aluno responde. Se um admin aprova a sugestão em `/admin/reportes-questoes`,
 * o aluno ganha 5 Sparks (crédito é do servidor, nunca daqui). */
export default function ReportarQuestao({ itemId, className = "" }) {
  const [aberto, setAberto] = useState(false);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);

  const enviar = () => {
    if (texto.trim().length < 3) {
      toast.error("Descreva em poucas palavras o que parece errado.");
      return;
    }
    setEnviando(true);
    api
      .post(`/questoes/${encodeURIComponent(itemId)}/reportar`, { texto: texto.trim() })
      .then(() => {
        setEnviado(true);
        toast.success("Reportado! Se um admin aprovar, você ganha 5 Sparks.");
      })
      .catch((e) => toast.error(errMsg(e, "Não foi possível enviar seu aviso.")))
      .finally(() => setEnviando(false));
  };

  const fechar = () => {
    setAberto(false);
    setTexto("");
    setEnviado(false);
  };

  return (
    <div className={`relative inline-block ${className}`} data-testid={`reportar-questao-${itemId}`}>
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        title="Algo errado com esta questão?"
        className="inline-flex items-center justify-center w-8 h-8 rounded-full text-zinc-400 hover:text-rose-500 hover:bg-rose-50 transition-colors"
        data-testid={`reportar-questao-abrir-${itemId}`}
      >
        <Flag className="w-4 h-4" />
      </button>

      {aberto && (
        <div
          className="absolute right-0 z-20 mt-1 w-72 rounded-xl border border-zinc-200 bg-white p-4 shadow-lg"
          data-testid={`reportar-questao-balao-${itemId}`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs font-bold text-zinc-700">Algo errado com esta questão?</div>
            <button onClick={fechar} className="text-zinc-400 hover:text-zinc-700" data-testid={`reportar-questao-fechar-${itemId}`}>
              <X className="w-4 h-4" />
            </button>
          </div>
          {enviado ? (
            <p className="text-xs text-emerald-700">Obrigado! Sua sugestão foi enviada para revisão.</p>
          ) : (
            <>
              <textarea
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
                rows={3}
                placeholder="Ex.: o gabarito parece errado, falta uma imagem, o enunciado está confuso..."
                className="w-full rounded-lg border border-zinc-200 px-2.5 py-2 text-xs text-zinc-800 outline-none focus:border-sapiens-accent resize-none"
                data-testid={`reportar-questao-texto-${itemId}`}
              />
              <button
                onClick={enviar}
                disabled={enviando}
                className="pill btn-sapiens mt-2 w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-full text-xs font-medium disabled:opacity-60"
                data-testid={`reportar-questao-enviar-${itemId}`}
              >
                {enviando ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Enviar sugestão"}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
