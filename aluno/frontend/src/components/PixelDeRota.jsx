import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { paginaPublicaVista } from "../lib/rastreio";

/**
 * O `PageView` DAS TELAS PÚBLICAS QUE NÃO SÃO LANDING DE ANÚNCIO — hoje `/` e
 * `/login`.
 *
 * Existe porque o Sapiens é uma SPA. O snippet do Meta dispara `PageView` no
 * carregamento do documento, e mais nunca: quem chega em `/` e vai para
 * `/login` não recarrega nada, então o Meta veria todo mundo parado na
 * primeira tela e o funil do anúncio terminaria no primeiro clique — que é
 * justamente o clique que a campanha pagou para acontecer.
 *
 * Quem decide QUAIS rotas contam é `lib/rastreio.ROTAS_PUBLICAS`, não este
 * arquivo: a fronteira entre "superfície de aquisição" e "app do aluno" é
 * decisão de produto e mora junto com o resto do rastreio. Aqui só se observa
 * a rota. É a mesma disciplina do módulo: **nenhum componente chama `fbq`.**
 *
 * Montado dentro do `<BrowserRouter>` e fora do `<Routes>`, de propósito: se
 * vivesse dentro de uma rota, ele desmontaria e remontaria a cada navegação e
 * perderia a memória de onde a pessoa estava.
 */
export default function PixelDeRota() {
  const { pathname } = useLocation();
  // O caminho da ÚLTIMA visita contada. É o que separa "a rota mudou" de "o
  // React montou este efeito duas vezes" — o StrictMode do desenvolvimento
  // faz exatamente isso, e sem a trava cada visita nasceria dupla no
  // relatório. Um `ref` e não um `state`: contar uma visita não redesenha
  // nada na tela.
  const ultimo = useRef(null);

  useEffect(() => {
    if (ultimo.current === pathname) return;
    ultimo.current = pathname;
    paginaPublicaVista(pathname);
  }, [pathname]);

  return null;
}
