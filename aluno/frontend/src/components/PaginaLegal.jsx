import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import BrandMark from "./BrandMark";
import AvisoLegalPendente from "./AvisoLegalPendente";
import { ATUALIZADO_EM, OPERADOR } from "../lib/operador";

/** Moldura comum de Termos e Privacidade: fundo claro e legível, porque são
 *  documentos para ler por inteiro, não telas de produto. */
export default function PaginaLegal({ titulo, resumo, children }) {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-2xl mx-auto px-6 py-12">
        <Link to="/" className="inline-flex items-center gap-2 font-display text-xl font-extrabold tracking-tighter text-sapiens-navy">
          <BrandMark className="w-5 h-5" tone="dark" />
          Sapiens
        </Link>

        <h1 className="mt-10 font-display text-3xl md:text-4xl font-extrabold tracking-tight text-zinc-950">
          {titulo}
        </h1>
        <p className="mt-2 text-sm text-zinc-500">Atualizado em {ATUALIZADO_EM}</p>
        {resumo && <p className="mt-6 text-zinc-700 leading-relaxed">{resumo}</p>}

        <div className="mt-8"><AvisoLegalPendente /></div>

        <div className="mt-8 space-y-8 text-[15px] leading-relaxed text-zinc-700 [&_h2]:font-display [&_h2]:text-xl [&_h2]:font-bold [&_h2]:text-zinc-950 [&_h2]:tracking-tight [&_h2]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1.5 [&_strong]:text-zinc-900">
          {children}
        </div>

        <div className="mt-12 pt-8 border-t border-zinc-200 text-sm text-zinc-500">
          <div className="font-medium text-zinc-800">Como falar conosco</div>
          <p className="mt-1">
            {OPERADOR.razaoSocial || OPERADOR.nomeFantasia}
            {OPERADOR.cnpj && ` — CNPJ ${OPERADOR.cnpj}`}
            {OPERADOR.endereco && <><br />{OPERADOR.endereco}</>}
            <br />
            <a className="text-sapiens-accentDeep hover:underline" href={`mailto:${OPERADOR.emailContato}`}>
              {OPERADOR.emailContato}
            </a>
          </p>
          <Link to="/" className="mt-6 inline-flex items-center gap-2 text-sapiens-accentDeep hover:underline">
            <ArrowLeft className="w-4 h-4" /> Voltar ao início
          </Link>
        </div>
      </div>
    </div>
  );
}
