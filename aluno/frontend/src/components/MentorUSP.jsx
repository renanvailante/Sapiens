import { useState } from "react";
import { Medal } from "lucide-react";
import { MENTOR } from "../lib/mentor";

/**
 * O rosto do Vitor Lara, 1º colocado de Medicina da USP.
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
 *
 * `variante="medalha"` (2026-09-17) pede a ILUSTRAÇÃO em vez do rosto, e
 * existe por uma razão de composição: onde o rosto já aparece grande, um
 * segundo retrato pequeno da mesma pessoa a poucos centímetros dele compete
 * com o primeiro e enfraquece os dois. A medalha diz a mesma coisa em outro
 * registro. Não é o mesmo que o fallback de arquivo ausente: aqui a escolha
 * é deliberada, e por isso ela não depende de a foto existir.
 */

// O tamanho é menor no celular em `m` e `g` porque o rosto divide a linha com
// texto: a 375px, um retrato de 112px deixava 171px para a frase ao lado — e
// uma frase de 171px quebra em quatro palavras por linha. Encolher aqui, uma
// vez, vale mais do que cada tela inventar a própria régua.
const TAMANHOS = {
  p: { caixa: "h-14 w-14", selo: "h-3 w-3", texto: "text-[9px]" },
  m: { caixa: "h-20 w-20 sm:h-28 sm:w-28", selo: "h-3.5 w-3.5", texto: "text-[10px]" },
  g: { caixa: "h-36 w-36 sm:h-44 sm:w-44 md:h-56 md:w-56", selo: "h-4 w-4", texto: "text-[11px]" },
};

export default function MentorUSP({
  tamanho = "m",
  comSelo = true,
  variante = "foto",
  className = "",
  testid = "mentor-usp",
}) {
  const [falhou, setFalhou] = useState(false);
  const t = TAMANHOS[tamanho] || TAMANHOS.m;
  const ilustracao = variante === "medalha" || falhou;

  return (
    <div className={`relative shrink-0 ${className}`} data-testid={testid}>
      <div
        className={`${t.caixa} overflow-hidden rounded-3xl border border-[#4FD9FF]/30 bg-gradient-to-br from-[#4FD9FF]/20 to-[#8B7BFF]/10`}
        // O brilho é o mesmo do resto do produto (uma família de matiz),
        // então a foto não parece colada de outro site.
        style={{ boxShadow: "0 18px 50px -20px rgba(79,217,255,0.55)" }}
      >
        {ilustracao ? (
          <div className="flex h-full w-full flex-col items-center justify-center gap-1 text-center text-[#7FD8FF]">
            <Medal className="h-1/3 w-1/3" strokeWidth={1.6} />
            <span className={`${t.texto} font-mono-alt uppercase tracking-[0.2em]`}>1º lugar</span>
          </div>
        ) : (
          <img
            src={MENTOR.foto}
            alt={`${MENTOR.nome}, ${MENTOR.titulo} e mentor do Sapiens`}
            className="h-full w-full object-cover"
            loading="lazy"
            onError={() => setFalhou(true)}
          />
        )}
      </div>

      {comSelo && !ilustracao && (
        <span
          className="absolute -bottom-2 left-1/2 inline-flex -translate-x-1/2 items-center gap-1.5 whitespace-nowrap rounded-full border border-amber-300/40 bg-[#0B1524] px-2.5 py-1 font-mono-alt font-bold uppercase tracking-[0.18em] text-amber-200"
          style={{ fontSize: "9px" }}
        >
          <Medal className={t.selo} /> {MENTOR.nome} · 1º lugar USP
        </span>
      )}
    </div>
  );
}
