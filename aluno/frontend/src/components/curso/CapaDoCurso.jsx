import {
  Calculator, PenLine, Target, BookOpen, FlaskConical, Rocket, Globe,
  CalendarDays, GraduationCap,
} from "lucide-react";

/**
 * A capa de um card do catálogo — dois tons e um glifo, desenhados aqui.
 *
 * **Por que não é uma imagem.** Um catálogo que precisa crescer não pode
 * exigir um JPEG por item: arte por curso significa que nenhum curso novo
 * entra sem passar por um designer, e o pedido explícito deste catálogo é
 * comportar cursos novos sem refazer a interface. Duas cores e um glifo dão
 * identidade suficiente para o olho separar um card do outro de relance,
 * pesam zero byte, nascem nítidos em qualquer densidade de tela e são uma
 * linha no dado quando um item entra.
 *
 * **Quem escolhe as cores é o SERVIDOR** (`cursos.Capa`), como tudo o mais do
 * catálogo. A tela não deduz cor pelo título nem mantém um mapa paralelo de
 * `curso_id -> cor`, que seria a segunda fonte de verdade a divergir no dia
 * em que um curso trocasse de área.
 *
 * O dia em que houver arte de verdade, um `capa_url` no dado convive com
 * isto: a imagem entra por cima e este degradê vira o fundo dela.
 */

// O único mapa que vive na tela: nome do glifo -> componente de ícone. É
// tradução, não decisão — o servidor manda "frasco", e este arquivo sabe
// desenhar um frasco. Um nome desconhecido cai no capelo, nunca em branco.
const GLIFOS = {
  calculadora: Calculator,
  caneta: PenLine,
  alvo: Target,
  livro: BookOpen,
  frasco: FlaskConical,
  foguete: Rocket,
  globo: Globe,
  calendario: CalendarDays,
};

export default function CapaDoCurso({ capa, className = "", altura = "h-28", testid }) {
  const Glifo = GLIFOS[capa?.glifo] || GraduationCap;
  const de = capa?.de || "#4FD9FF";
  const para = capa?.para || "#2F6BFF";

  return (
    <div
      className={`relative ${altura} w-full overflow-hidden ${className}`}
      style={{ background: `linear-gradient(135deg, ${de} 0%, ${para} 100%)` }}
      aria-hidden="true"
      data-testid={testid}
    >
      {/* O glifo grande, cortado pela borda: é o que faz a capa parecer uma
          capa e não um retângulo colorido. Opacidade baixa para o título que
          vem embaixo continuar sendo a coisa mais legível do card. */}
      <Glifo
        className="absolute -bottom-4 -right-3 h-24 w-24 text-white/25"
        strokeWidth={1.2}
      />
      {/* Um véu escuro no pé: sem ele, um degradê claro deixa o selo de
          status (branco sobre translúcido) ilegível em metade dos cards. */}
      <div
        className="absolute inset-0"
        style={{ background: "linear-gradient(180deg, transparent 45%, rgba(3,6,13,0.45) 100%)" }}
      />
    </div>
  );
}
