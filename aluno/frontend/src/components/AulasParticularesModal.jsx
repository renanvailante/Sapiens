import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { X, GraduationCap, CheckCircle2 } from "lucide-react";

export const AULAS_PARTICULARES_AREAS = [
  "Matemática",
  "Ciências da Natureza",
  "Linguagens",
  "Ciências Humanas",
  "Redação",
];

export default function AulasParticularesModal({ open, onClose }) {
  const [nomeCompleto, setNomeCompleto] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [areas, setAreas] = useState([]);
  const [descricao, setDescricao] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  // Esc fecha, como em qualquer diálogo. O modal é um portal manual (não o
  // Dialog do Radix), então o atalho precisa ser ligado à mão.
  useEffect(() => {
    if (!open) return undefined;
    const aoTeclar = (e) => { if (e.key === "Escape") handleClose(); };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  });

  if (!open) return null;

  const toggleArea = (area) => {
    setAreas((prev) => (prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area]));
  };

  const reset = () => {
    setNomeCompleto("");
    setWhatsapp("");
    setAreas([]);
    setDescricao("");
    setSent(false);
  };

  // Fechar NÃO apaga o que foi digitado: clique acidental no fundo apagava
  // nome, WhatsApp, áreas e descrição de uma vez. O reset acontece só depois
  // de um envio bem-sucedido, quando o formulário já cumpriu seu papel.
  const handleClose = () => {
    if (sent) reset();
    onClose();
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!nomeCompleto.trim() || !whatsapp.trim() || areas.length === 0) {
      toast.error("Preencha nome, WhatsApp e ao menos uma área.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/aulas-particulares", {
        nome_completo: nomeCompleto.trim(),
        whatsapp: whatsapp.trim(),
        areas,
        descricao: descricao.trim(),
      });
      setSent(true);
      toast.success("Solicitação enviada! Em breve entraremos em contato.");
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível enviar sua solicitação."));
    } finally {
      setSubmitting(false);
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={handleClose}
      role="dialog"
      aria-modal="true"
      aria-label="Solicitar aulas particulares"
      data-testid="aulas-particulares-modal"
    >
      <div
        className="card-sapiens rounded-2xl p-6 md:p-8 w-full max-w-lg max-h-[90dvh] overflow-y-auto relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={handleClose}
          className="absolute right-4 top-4 text-zinc-400 hover:text-zinc-900 transition-colors"
          aria-label="Fechar"
          data-testid="aulas-particulares-close"
        >
          <X className="w-5 h-5" />
        </button>

        {sent ? (
          <div className="py-6 text-center" data-testid="aulas-particulares-success">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />
            <div className="mt-4 font-display text-xl font-bold tracking-tight text-zinc-950">
              Solicitação enviada!
            </div>
            <p className="mt-2 text-sm text-zinc-500 max-w-sm mx-auto">
              Recebemos seu pedido de aula particular. Nossa equipe vai entrar em contato pelo WhatsApp em breve.
            </p>
            <button
              onClick={handleClose}
              className="pill btn-sapiens mt-6 inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-medium"
              data-testid="aulas-particulares-success-close"
            >
              Fechar
            </button>
          </div>
        ) : (
          <>
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-sapiens-accent to-sapiens-navy text-white flex items-center justify-center">
              <GraduationCap className="w-5 h-5" strokeWidth={1.7} />
            </div>
            <div className="mt-4 font-display text-2xl font-bold tracking-tight text-zinc-950">
              Tenha aulas conosco
            </div>
            <p className="mt-2 text-sm text-zinc-500">
              Conte um pouco sobre o que você precisa. Entraremos em contato pelo WhatsApp para combinar os detalhes.
            </p>

            <form onSubmit={submit} className="mt-6 space-y-4">
              <div>
                <label className="text-xs font-medium text-zinc-500 mb-1.5 block">Nome completo</label>
                <input
                  required
                  value={nomeCompleto}
                  onChange={(e) => setNomeCompleto(e.target.value)}
                  placeholder="Seu nome completo"
                  className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none"
                  data-testid="aulas-particulares-nome"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-500 mb-1.5 block">WhatsApp</label>
                <input
                  required
                  type="tel"
                  value={whatsapp}
                  onChange={(e) => setWhatsapp(e.target.value)}
                  placeholder="(11) 91234-5678"
                  className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none"
                  data-testid="aulas-particulares-whatsapp"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-500 mb-1.5 block">Áreas de interesse</label>
                <div className="flex flex-wrap gap-2">
                  {AULAS_PARTICULARES_AREAS.map((area) => {
                    const selected = areas.includes(area);
                    return (
                      <button
                        type="button"
                        key={area}
                        onClick={() => toggleArea(area)}
                        className={`pill text-xs font-medium px-3.5 py-2 rounded-full border transition-colors ${
                          selected
                            ? "border-sapiens-accent bg-sapiens-accentSoft text-sapiens-navy"
                            : "border-zinc-200 text-zinc-500 hover:border-zinc-300"
                        }`}
                        data-testid={`aulas-particulares-area-${area}`}
                        aria-pressed={selected}
                      >
                        {area}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-500 mb-1.5 block">
                  O que você precisa ou deseja estudar?
                </label>
                <textarea
                  value={descricao}
                  onChange={(e) => setDescricao(e.target.value)}
                  placeholder="Ex.: tenho dificuldade em funções e quero reforçar redação para o ENEM."
                  rows={4}
                  className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none resize-none"
                  data-testid="aulas-particulares-descricao"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="pill btn-sapiens w-full inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full text-sm font-medium disabled:opacity-50"
                data-testid="aulas-particulares-submit"
              >
                {submitting ? "Enviando…" : "Solicitar aula"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>,
    document.body
  );
}
