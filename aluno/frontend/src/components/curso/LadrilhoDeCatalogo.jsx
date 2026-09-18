import CapaDoCurso from "./CapaDoCurso";

/**
 * O LADRILHO — um curso ou um e-book como quadrado pequeno que se abre.
 *
 * O QUE ELE SUBSTITUI. Cada curso era um card de coluna inteira: capa de
 * 112px, título, chamada, descrição, uma lista de módulos atrás de um
 * `<details>` e a linha de preço com os botões. Sete deles empilhados davam
 * umas quatro dobras de rolagem, e o aluno lia tudo de todos para escolher um
 * — ou, o que de fato acontece, não lia nenhum e saía da página. A tela pedia
 * leitura onde o gesto natural é PASSAR O OLHO.
 *
 * O catálogo virou uma grade de quadrados. Um quadrado com capa e título é o
 * bastante para reconhecer ("o de Matemática", "o de Redação"); o resto — a
 * chamada, o status, o preço, o botão — aparece quando o aluno demonstra
 * interesse, que é o que passar o cursor significa. É progressive disclosure
 * no sentido estrito: nada some do produto, só deixa de ser cobrado de
 * antemão de quem ainda está escolhendo.
 *
 * COMO ELE ABRE, e por que não empurra nada. O ladrilho ocupa uma célula
 * quadrada da grade e o corpo é ABSOLUTO dentro dela. Abrir é mudar o `inset`
 * do corpo — ele cresce para fora, por cima dos vizinhos, com `z-index`
 * levantado. Se a abertura mudasse a ALTURA da célula, a linha inteira da
 * grade cresceria junto e tudo abaixo dela pularia; o aluno perderia o card
 * que estava mirando no meio do movimento. Ver `.ladrilho` no `index.css`.
 *
 * NO MOUSE é `:hover` e `:focus-within`, resolvido em CSS — inclusive para
 * quem navega por teclado, que precisa ver a mesma informação ao chegar com
 * Tab. NO TOQUE não existe hover: quem controla é a página, que mantém UM
 * aberto por vez (`aberto` + `aoAbrir`). Sem isso, tocar em quatro ladrilhos
 * deixaria quatro cartões grandes sobrepostos na tela.
 *
 * O primeiro toque ABRE, e só o segundo age. É deliberado: no telefone o dedo
 * cobre o alvo, e um ladrilho de 150px que dispara compra ao primeiro toque
 * cobra caro por um engano. Abrir primeiro dá ao aluno a informação que o
 * mouse dá de graça.
 */
export default function LadrilhoDeCatalogo({
  capa,
  titulo,
  chamada,
  olho,
  selo = null,
  meu = false,
  progresso = null,
  aberto = false,
  aoAbrir,
  children,
  testid,
}) {
  return (
    <li className="ladrilho" data-aberto={aberto || undefined} data-testid={testid}>
      <div
        className="ladrilho-corpo"
        // O toque abre; no mouse quem abre é o `:hover` do CSS e este
        // manipulador não chega a ser útil — um clique no corpo (e não num
        // botão de dentro) simplesmente reabre o que já está aberto.
        onClick={() => aoAbrir?.()}
        onFocus={() => aoAbrir?.()}
      >
        <CapaDoCurso capa={capa} altura="h-full" className="ladrilho-capa" />

        {/* Os selos ficam SOBRE a capa, no fechado e no aberto: "No ar" e
            "Meu" são o que muda a decisão antes de qualquer texto. Quando o
            aluno já começou, o selo de progresso SUBSTITUI o "Meu" (ver
            `pages/Cursos.jsx`, `ladrilhoDoCurso`) — "62%" já diz que é seu
            e diz mais do que "Meu" sozinho. */}
        <div className="ladrilho-selos">
          {meu && <span className="ladrilho-selo ladrilho-selo--meu">Meu</span>}
          {progresso != null && (
            <span className="ladrilho-selo ladrilho-selo--progresso" data-testid={testid && `${testid}-progresso`}>
              {progresso}%
            </span>
          )}
          {selo}
        </div>

        {/* O TÍTULO, sempre visível. "Quadrado pequeno e visual" não quer
            dizer quadrado mudo: sem o nome, a grade vira sete retângulos
            coloridos e o aluno tem de abrir um por um para achar o que
            procura — que é mais trabalho do que a lista que ela substituiu. */}
        <div className="ladrilho-fita">
          {olho && <div className="ladrilho-olho">{olho}</div>}
          <h3 className="ladrilho-titulo">{titulo}</h3>
        </div>

        {/* O QUE APARECE AO ABRIR. `aria-hidden` não entra aqui: o conteúdo
            existe o tempo todo para leitor de tela e para o Tab — o que muda
            é só a altura visível. */}
        <div className="ladrilho-mais">
          {chamada && <p className="ladrilho-chamada">{chamada}</p>}
          <div className="ladrilho-acoes">{children}</div>
        </div>
      </div>
    </li>
  );
}
