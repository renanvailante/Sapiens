import { AlertTriangle } from "lucide-react";
import { pendenciasDoOperador } from "../lib/operador";

const ROTULOS = {
  razaoSocial: "razão social",
  cnpj: "CNPJ",
  endereco: "endereço",
  emailPrivacidade: "e-mail do encarregado de dados",
};

/**
 * Aviso exibido enquanto faltam os dados de identificação do operador.
 *
 * Um documento legal com dado inventado é pior que um declaradamente
 * incompleto: o primeiro engana, o segundo avisa. Some sozinho quando
 * `lib/operador.js` for preenchido.
 */
export default function AvisoLegalPendente() {
  const pendentes = pendenciasDoOperador();
  if (pendentes.length === 0) return null;

  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 flex gap-3" data-testid="aviso-legal-pendente">
      <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
      <div className="text-sm text-amber-900">
        <strong>Documento em finalização.</strong> Faltam os dados de identificação do
        responsável ({pendentes.map((p) => ROTULOS[p] || p).join(", ")}). Enquanto isso,
        fale conosco pelo e-mail de contato ao final desta página.
      </div>
    </div>
  );
}
