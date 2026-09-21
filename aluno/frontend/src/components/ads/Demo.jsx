import { RotateCcw } from "lucide-react";

/**
 * A MOLDURA DE TODA DEMONSTRAÇÃO.
 *
 * As quatro landings mostram mecanismos diferentes dentro da MESMA caixa:
 * um selo que diz o que aquilo é, um trilho de passos, a peça, e o botão de
 * rever. Sem a moldura, cada página inventaria a sua e a quinta variante
 * nasceria com outra.
 *
 * ---------------------------------------------------------------------------
 * O SELO "DEMONSTRAÇÃO" É REQUISITO, NÃO ENFEITE
 * ---------------------------------------------------------------------------
 *
 * Estas peças mostram questão, erro, porcentagem e padrão — as mesmas coisas
 * que o produto mostra sobre o aluno de verdade. Sem dizer em cada uma que
 * aquilo é uma cena montada, a página estaria afirmando saber algo sobre
 * quem acabou de chegar de um anúncio. Por isso o selo é da MOLDURA e não de
 * cada demo: uma peça nova não tem como esquecer de carregá-lo.
 *
 * ---------------------------------------------------------------------------
 * O TRILHO DE PASSOS E O BOTÃO DE REVER
 * ---------------------------------------------------------------------------
 *
 * O trilho existe para a animação ser lida como uma SEQUÊNCIA e não como
 * coisas piscando: quem chega no meio vê que há um começo. O botão de rever
 * existe porque é exatamente isso que a pessoa que chegou no meio quer, e a
 * alternativa hoje seria recarregar a página.
 *
 * `aria-live="polite"` na área de narração: quem usa leitor de tela recebe o
 * texto de cada passo conforme ele muda, em vez de uma caixa muda com um
 * botão dentro.
 */
export default function Demo({
  olho = "Demonstração",
  passo = 0,
  passos = 0,
  aoRever = null,
  narracao = null,
  children,
  testid = "ads-demo",
}) {
  return (
    <section
      className="card-sapiens rounded-3xl p-3.5 md:p-5"
      data-testid={testid}
      data-passo={passo}
    >
      {/* 30px reservados, e o número é a caixa do botão de rever (ícone de
          14px + `p-2`), medida no navegador.

          A demo interativa é a única em que o botão APARECE no meio do uso —
          ela só oferece "rever" depois que a pessoa responde. Sem a altura
          reservada, o cabeçalho pulava de 15 para 30px no instante do toque e
          empurrava a questão inteira 15px para baixo, bem quando o olho
          estava na alternativa que acabou de ser marcada. As outras três
          nascem com o botão e nunca mostraram o defeito: é o tipo de salto
          que só aparece medindo uma peça e não as quatro. */}
      <header className="flex min-h-[30px] items-center justify-between gap-3">
        <span className="secao-olho" data-testid={`${testid}-olho`}>{olho}</span>

        <div className="flex items-center gap-3">
          {passos > 1 && (
            <div className="flex items-center gap-1" aria-hidden="true">
              {Array.from({ length: passos }, (_, i) => (
                <span
                  key={i}
                  className={`ads-passo ${i === passo ? "ads-passo-atual" : ""} ${i < passo ? "ads-passo-feito" : ""}`}
                />
              ))}
            </div>
          )}
          {aoRever && (
            <button
              type="button"
              onClick={aoRever}
              // `-m-2 p-2` cresce o alvo de toque para ~34px sem mover o
              // ícone de 14px — o jeito da casa (ver `ux/mobile.md`).
              className="-m-2 p-2 text-white/35 transition-colors hover:text-white/75"
              aria-label="Rever a demonstração desde o início"
              data-testid={`${testid}-rever`}
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </header>

      <div className="mt-3 md:mt-4">{children}</div>

      {narracao && (
        <p className="sr-only" aria-live="polite" data-testid={`${testid}-narracao`}>
          {narracao}
        </p>
      )}
    </section>
  );
}

/**
 * Uma linha que aparece quando o roteiro chega nela.
 *
 * `visivel` em vez de montar/desmontar: montar o elemento só no passo certo
 * faria o cartão inteiro mudar de altura a cada passo, e a página saltaria
 * sob o dedo de quem está lendo. Aqui o espaço já existe desde o primeiro
 * quadro e o que muda é a opacidade — nenhum reflow, nenhuma linha empurrada.
 */
export function LinhaRevelada({ visivel, children, className = "", ...resto }) {
  return (
    <div
      className={`ads-revela ${visivel ? "ads-revela-on" : ""} ${className}`}
      aria-hidden={!visivel}
      {...resto}
    >
      {children}
    </div>
  );
}

/**
 * A FAIXA ONDE A ANÁLISE APARECE.
 *
 * Ela reserva a altura final desde o primeiro quadro — revelar linha por
 * linha empurrando conteúdo faria a página saltar sob o dedo de quem está
 * lendo o enunciado logo acima. O problema disso, medido no navegador a
 * 390px: nos dois primeiros passos sobravam ~150px de nada embaixo da
 * questão, e área vazia grande dentro de um cartão não lê como "ainda vai
 * preencher", lê como quebrado.
 *
 * A cura é enquadrar em vez de encolher: uma linha fina separa a faixa da
 * questão, e enquanto a análise não começou existe uma frase dizendo o que
 * está sendo esperado. O vazio passa a ser um painel à espera — que é o que
 * ele de fato é, e cria a expectativa de que algo vai cair ali.
 */
export function FaixaDeAnalise({ aguardando = null, children, testid, altura = "min-h-[140px]" }) {
  return (
    <div className="mt-3 border-t border-white/8 pt-3" data-testid={testid}>
      {/* A altura reservada é MEDIDA por demo, não um número redondo: é a do
          estado mais cheio daquela peça. 140px cobre as três demos de três
          achados; a questão interativa tem um parágrafo de fecho a mais e
          precisa de 176px — sem isso ela crescia 34px no instante em que a
          pessoa tocava numa alternativa, empurrando o conteúdo abaixo. */}
      <div className={`relative ${altura}`}>
        {/* A linha de espera é SOBREPOSTA, não empilhada: no fluxo normal ela
            acrescentaria uma altura que some no instante em que a análise
            começa, e o cartão encolheria uma linha bem no meio da sequência.

            > [!warning] Ela fica FORA do `space-y`, e isso não é organização.
            > `space-y-*` do Tailwind é `& > * + * { margin-top }` — ele conta
            > os filhos pelo DOM, não pelo fluxo, então um filho `absolute`
            > (que não ocupa altura nenhuma) mesmo assim faz o irmão seguinte
            > ganhar a margem. Medido: com a linha de espera dentro do
            > `space-y-2.5`, o cartão oscilava exatos 10px — a margem que a
            > primeira linha de análise ganhava enquanto o aviso existia e
            > perdia quando ele saía. Dois contêineres resolvem: um posiciona,
            * o outro espaça. */}
        {aguardando && (
          <div className="absolute inset-x-0 top-0 flex items-start gap-2.5">
            <span className="ads-ponto ads-ponto-espera" aria-hidden="true" />
            <span className="text-[13px] leading-snug text-white/30">{aguardando}</span>
          </div>
        )}
        <div className="space-y-2.5">{children}</div>
      </div>
    </div>
  );
}

/**
 * O par "rótulo → valor" que as quatro demos usam para entregar um achado
 * ("Erro identificado → interpretação da informação").
 *
 * O rótulo é o que o Sapiens FEZ; o valor é o que ele ENCONTROU. Manter os
 * dois com pesos visuais diferentes é o que faz a linha ser lida como
 * resultado de uma análise, e não como mais um item de lista.
 */
export function Achado({ rotulo, valor, tom = "sinal" }) {
  return (
    <div className="flex items-start gap-2.5">
      <span className={`ads-ponto ads-ponto-${tom}`} aria-hidden="true" />
      <div className="min-w-0">
        <div className="font-mono-alt text-[10px] font-semibold uppercase tracking-[0.2em] text-white/40">
          {rotulo}
        </div>
        <div className="mt-0.5 text-[14px] font-bold leading-snug text-white">{valor}</div>
      </div>
    </div>
  );
}
