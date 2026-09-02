import { useEffect } from "react";

const SUFIXO = "Sapiens";

/**
 * Define o `<title>` da aba por rota. Todas as páginas se chamavam "Sapiens",
 * o que torna várias abas abertas indistinguíveis e o histórico do navegador
 * inútil para voltar a uma tela específica.
 */
export default function TituloDaPagina({ titulo }) {
  useEffect(() => {
    document.title = titulo ? `${titulo} · ${SUFIXO}` : SUFIXO;
  }, [titulo]);
  return null;
}
