import { Link } from "react-router-dom";
import BrandMark from "./BrandMark";

/**
 * O LOCKUP da marca: símbolo + palavra, sempre nesta ordem e sempre com a
 * mesma relação entre os dois.
 *
 * Existia espalhado: `Nav`, `Login` e `Landing` montavam cada um a sua
 * combinação de `<BrandMark>` + `<span>Sapiens</span>`, com tamanhos, pesos e
 * espaçamentos diferentes — três lockups diferentes da mesma marca em três
 * telas que o aluno vê em sequência no primeiro minuto do produto. Aqui é um
 * componente só, e a marca passa a ter uma forma.
 *
 * As três regras do lockup:
 *
 * 1. **A palavra fica ao lado do símbolo, no canto superior esquerdo.** É o
 *    lugar onde o olho procura a identidade de um produto, e é de onde ela
 *    não sai em nenhuma largura de tela.
 * 2. **A altura da palavra é a altura do símbolo.** O espaçamento é 0.32 do
 *    símbolo — apertado o bastante para os dois lerem como UM objeto, folgado
 *    o bastante para o sulco aceso não encostar na letra.
 * 3. **O símbolo carrega a cor; a palavra é branca.** Duas coisas coloridas
 *    lado a lado brigam, e a que perde é sempre a menor — que é justamente o
 *    símbolo, a parte que precisa ser reconhecida sozinha na aba do navegador
 *    e no ícone do aparelho.
 *
 * `tamanho` é a única medida que quem usa escolhe. Os três degraus cobrem
 * todo o produto: `p` na barra do celular, `m` na barra do desktop, `g` nas
 * telas em que a marca é protagonista (entrada, carregamento, primeira dobra
 * da landing) — e é só em `g` que o halo acende.
 */

const TAMANHOS = {
  p: { marca: "h-6 w-6", palavra: "text-lg", gap: "gap-1.5", halo: false },
  m: { marca: "h-8 w-8", palavra: "text-2xl", gap: "gap-2", halo: false },
  g: { marca: "h-12 w-12", palavra: "text-4xl", gap: "gap-3", halo: true },
};

export default function Logo({
  tamanho = "m",
  to = null,
  // Alternativa ao `to`: quem usa a marca como GATILHO de um menu (a barra
  // logada, que abre o lançador lateral ao tocar na marca) passa `onClick` em
  // vez de `to` — os dois juntos não fariam sentido, porque navegar já
  // desmonta o painel que acabou de abrir.
  onClick = null,
  comPalavra = true,
  // `classePalavra` existe por causa da barra do desktop: lá a palavra some
  // abaixo de `xl` por medida (ver a nota de medição no fim de `Nav.jsx`), e
  // isso é uma decisão de LAYOUT da barra, não da marca. O lockup aceita a
  // responsiva de fora em vez de embutir um `hidden xl:inline` que estaria
  // errado em toda outra tela.
  classePalavra = "",
  className = "",
  testid,
}) {
  const t = TAMANHOS[tamanho] || TAMANHOS.m;

  const conteudo = (
    <>
      <BrandMark className={`${t.marca} shrink-0`} halo={t.halo} />
      {comPalavra && (
        <span
          className={`font-display font-extrabold leading-none tracking-[-0.045em] text-white ${t.palavra} ${classePalavra}`}
        >
          Sapiens
        </span>
      )}
    </>
  );

  const classe = `inline-flex items-center ${t.gap} ${className}`;

  if (to) {
    return (
      <Link to={to} className={classe} data-testid={testid} aria-label="Sapiens">
        {conteudo}
      </Link>
    );
  }
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={classe} data-testid={testid} aria-label="Menu · Sapiens">
        {conteudo}
      </button>
    );
  }
  return (
    <span className={classe} data-testid={testid} aria-label="Sapiens">
      {conteudo}
    </span>
  );
}
