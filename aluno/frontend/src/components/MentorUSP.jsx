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
  p: { caixa: "h-16 w-16", selo: "h-3 w-3", texto: "text-[9px]", curto: true },
  // `m` CRESCE SÓ A PARTIR DE `sm`. No celular ele fica nos 80px de sempre, e
  // isso não é timidez: `m` é o tamanho usado em LINHA com texto ao lado (a
  // ponte da aula, o convite da mentoria), e a medição de 2026-09-17 mostrou
  // que a 375px um retrato de 112px deixa 171px para a frase — que quebra em
  // quatro palavras por linha. O destaque de 2026-09-18 vem da moldura, do
  // halo e do selo explícito, que não custam largura nenhuma.
  m: { caixa: "h-20 w-20 sm:h-32 sm:w-32", selo: "h-3.5 w-3.5", texto: "text-[10px]", curto: true },
  g: { caixa: "h-40 w-40 sm:h-52 sm:w-52 md:h-64 md:w-64", selo: "h-4 w-4", texto: "text-[11px]" },
  // `xg` nasceu em 2026-09-18, para os lugares em que o rosto É o argumento:
  // a seção do mentor na landing e a tela da mentoria. Abaixo de 200px um
  // retrato vira ícone — o cérebro reconhece que ali há uma pessoa, mas não
  // reconhece A pessoa, e a credencial deixa de ter dono.
  xg: { caixa: "h-56 w-56 sm:h-72 sm:w-72 md:h-80 md:w-80", selo: "h-4 w-4", texto: "text-[12px]" },
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
        className={`${t.caixa} overflow-hidden rounded-3xl border-2 border-[#4FD9FF]/45 bg-gradient-to-br from-[#4FD9FF]/20 to-[#8B7BFF]/10`}
        // O brilho é o mesmo do resto do produto (uma família de matiz),
        // então a foto não parece colada de outro site. A borda engrossou
        // para 2px e o halo ficou mais denso em 2026-09-18: o rosto passou a
        // ser tratado como ATIVO do produto, e não como ilustração de apoio —
        // é a prova viva do que o Sapiens promete, e a única coisa na tela
        // que o aluno pode conferir fora do site.
        style={{ boxShadow: "0 22px 64px -22px rgba(79,217,255,0.7), 0 0 0 1px rgba(79,217,255,0.12)" }}
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

      {/* O SELO, e agora ele aparece TAMBÉM quando a foto falta.
          Antes era `comSelo && !ilustracao`: sem o arquivo, o produto perdia a
          foto E a credencial de uma vez, e sobrava uma medalha genérica que
          não dizia de quem era. A credencial é o ativo; a foto é o rosto dela.

          O texto ficou EXPLÍCITO — "1º lugar em Medicina na USP" e não
          "1º lugar USP". A abreviação economizava doze caracteres e deixava a
          conquista ambígua: 1º lugar em quê? Nos tamanhos pequenos, onde a
          frase inteira não cabe sob o retrato, ela encolhe para "Medicina USP"
          em vez de virar sopa de letras. */}
      {comSelo && (
        <span
          className="absolute -bottom-2.5 left-1/2 inline-flex -translate-x-1/2 items-center gap-1.5 whitespace-nowrap rounded-full border border-amber-300/50 bg-[#0B1524] px-3 py-1.5 font-mono-alt font-bold uppercase tracking-[0.16em] text-amber-200"
          style={{ fontSize: t.curto ? "8px" : "10px", boxShadow: "0 10px 24px -12px rgba(251,191,36,0.6)" }}
        >
          <Medal className={t.selo} />
          {t.curto ? "1º lugar · Medicina USP" : `${MENTOR.nome} · 1º lugar em Medicina na USP`}
        </span>
      )}
    </div>
  );
}
