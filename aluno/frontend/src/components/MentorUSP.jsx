import { useState } from "react";
import { Medal } from "lucide-react";

/**
 * O rosto do 1º colocado de Medicina da USP.
 *
 * Isto é um componente e não um `<img>` solto por um motivo de produto: ele é
 * o maior ativo do Sapiens, aparece em cinco telas (mentoria, cursos, painel,
 * landing e a barra de anúncio) e **não pode aparecer diferente em cada uma**.
 * Tamanho, moldura, o selo "1º lugar" e o comportamento quando o arquivo
 * falta vivem aqui, uma vez.
 *
 * **O arquivo mora em `public/mentor-usp.jpg`.** Se ele não estiver lá, o
 * componente cai no selo em vez de mostrar o ícone de imagem quebrada do
 * navegador — uma foto que falha é constrangedora justamente na tela que
 * vende a pessoa.
 */

const TAMANHOS = {
  p: { caixa: "h-14 w-14", selo: "h-3 w-3", texto: "text-[9px]" },
  m: { caixa: "h-28 w-28", selo: "h-3.5 w-3.5", texto: "text-[10px]" },
  g: { caixa: "h-44 w-44 md:h-56 md:w-56", selo: "h-4 w-4", texto: "text-[11px]" },
};

export default function MentorUSP({ tamanho = "m", comSelo = true, className = "", testid = "mentor-usp" }) {
  const [falhou, setFalhou] = useState(false);
  const t = TAMANHOS[tamanho] || TAMANHOS.m;

  return (
    <div className={`relative shrink-0 ${className}`} data-testid={testid}>
      <div
        className={`${t.caixa} overflow-hidden rounded-3xl border border-[#4FD9FF]/30 bg-gradient-to-br from-[#4FD9FF]/20 to-[#8B7BFF]/10`}
        // O brilho é o mesmo do resto do produto (uma família de matiz),
        // então a foto não parece colada de outro site.
        style={{ boxShadow: "0 18px 50px -20px rgba(79,217,255,0.55)" }}
      >
        {falhou ? (
          <div className="flex h-full w-full flex-col items-center justify-center gap-1 text-center text-[#7FD8FF]">
            <Medal className="h-1/3 w-1/3" strokeWidth={1.6} />
            <span className={`${t.texto} font-mono-alt uppercase tracking-[0.2em]`}>1º lugar</span>
          </div>
        ) : (
          <img
            src="/mentor-usp.jpg"
            alt="O 1º colocado de Medicina da USP, mentor do Sapiens"
            className="h-full w-full object-cover"
            loading="lazy"
            onError={() => setFalhou(true)}
          />
        )}
      </div>

      {comSelo && !falhou && (
        <span
          className="absolute -bottom-2 left-1/2 inline-flex -translate-x-1/2 items-center gap-1.5 whitespace-nowrap rounded-full border border-amber-300/40 bg-[#0B1524] px-2.5 py-1 font-mono-alt font-bold uppercase tracking-[0.18em] text-amber-200"
          style={{ fontSize: "9px" }}
        >
          <Medal className={t.selo} /> 1º lugar · Medicina USP
        </span>
      )}
    </div>
  );
}
