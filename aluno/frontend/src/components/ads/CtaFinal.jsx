import CTA from "./CTA";

/**
 * O FECHO. Um título, um botão, e nada mais.
 *
 * Existe como componente por uma razão só: garantir que as quatro páginas
 * terminem igual. A tentação natural de uma landing que não converte é
 * acrescentar alternativas no fim ("ou fale com a gente", "ou veja os
 * planos"), e três saídas no rodapé são três maneiras de não fazer a única
 * coisa que a página pediu. Com o fecho sendo peça compartilhada, incluir uma
 * segunda saída passa a ser uma decisão visível em vez de um acréscimo local.
 */
export default function CtaFinal({
  titulo = "Descubra o que seus erros estão tentando mostrar.",
  cta,
  nota = null,
}) {
  return (
    <section className="mx-auto max-w-xl text-center" data-testid="ads-cta-final">
      <h2 className="titulo-tela">{titulo}</h2>
      <CTA posicao="fim" className="mt-7" nota={nota}>{cta}</CTA>
    </section>
  );
}
