import { clsx } from "clsx";
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/** Centavos -> "R$ 54,90". Mora aqui porque a LOJA e a aba de CURSOS dizem o
 *  mesmo preço do mesmo pacote: duas formatações diferentes do mesmo número
 *  em duas telas é um jeito silencioso de elas divergirem. */
export function formatBRL(cents) {
  return (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
