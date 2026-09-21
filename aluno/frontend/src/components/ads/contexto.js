import { createContext, useContext } from "react";
import { ROTAS } from "../../lib/rotas";

/**
 * O destino do CTA e a variante da landing, num contexto próprio.
 *
 * Mora aqui, e não dentro de `AdsLandingLayout`, para não haver ciclo de
 * import: a casca desenha o CTA grudento e o CTA precisa do contexto. Um
 * ciclo de módulos ESM até funcionaria neste caso, e é exatamente o tipo de
 * coisa que funciona até alguém reordenar um import.
 */
export const ContextoDoAnuncio = createContext({ destino: ROTAS.LOGIN, variante: "" });

/** O destino do CTA e a variante — os botões não recebem prop de três níveis
 *  acima, e uma landing tem um destino só. */
export function useAnuncio() {
  return useContext(ContextoDoAnuncio);
}
