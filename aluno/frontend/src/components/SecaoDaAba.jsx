import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * UMA SEÇÃO DE UMA ÁREA — o cabeçalho e a âncora, uma vez só.
 *
 * As cinco áreas absorveram onze telas que antes eram destinos próprios
 * (revisões, conquistas, liga, histórico, lixeira, questões geradas…). Cada
 * uma dessas telas tinha o seu cabeçalho, e empilhá-los como vieram
 * reproduziria dentro de uma aba exatamente a colcha de retalhos que a
 * arquitetura nova existe para acabar: quatro tamanhos de título, três
 * respiros, dois jeitos de escrever o olho.
 *
 * Aqui a seção é uma peça: olho, título, uma linha de explicação e a âncora.
 *
 * ---------------------------------------------------------------------------
 * A ÂNCORA NÃO É DECORAÇÃO — É O QUE SALVA OS LINKS ANTIGOS
 * ---------------------------------------------------------------------------
 *
 * `/conquistas` circulou em conversa e está em favorito de aluno. Ele agora
 * redireciona para `/progresso#conquistas`, e um redirect que despeja a pessoa
 * no topo de uma aba de cinco seções é o mesmo que não ter redirecionado: ela
 * clicou num link que prometia troféus e recebeu um gráfico de acertos.
 *
 * O `id` daqui é o alvo desse salto, e `useAncora` é quem executa o salto —
 * o navegador não rola sozinho numa SPA, porque o elemento com aquele `id`
 * ainda não existe quando a URL muda.
 */
export default function SecaoDaAba({
  id,
  icone: Icone,
  olho = null,
  titulo,
  descricao = null,
  acoes = null,
  className = "",
  testid,
  children,
}) {
  return (
    <section
      id={id}
      // `scroll-mt`: a barra de cima é `sticky` e cobriria o título da seção
      // no fim do salto. Sem isso a âncora funciona e parece que não
      // funcionou, que é pior do que não ter âncora.
      className={`scroll-mt-24 ${className}`}
      data-testid={testid || (id ? `secao-${id}` : undefined)}
      aria-labelledby={id ? `${id}-titulo` : undefined}
    >
      <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          {olho && <div className="secao-olho">{olho}</div>}
          <h2
            id={id ? `${id}-titulo` : undefined}
            className="flex items-center gap-2 font-display text-2xl font-bold tracking-tight text-white"
          >
            {Icone && <Icone className="h-[18px] w-[18px] shrink-0 text-white/45" strokeWidth={2} />}
            {titulo}
          </h2>
          {descricao && (
            <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-white/55">{descricao}</p>
          )}
        </div>
        {acoes && <div className="flex shrink-0 flex-wrap items-center gap-2">{acoes}</div>}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

/**
 * Rola até a seção pedida no endereço.
 *
 * Numa SPA o navegador não faz isso sozinho: quando a URL vira
 * `/progresso#conquistas`, a página que tem esse `id` ainda não montou, e
 * quando ela monta o navegador já desistiu de procurar. Pior: as áreas carregam
 * dados, então a seção alvo pode aparecer segundos depois, empurrada para
 * baixo por conteúdo que chegou antes dela.
 *
 * Por isso o efeito tenta de novo enquanto o alvo não existir, com um teto de
 * tentativas — um laço sem teto ficaria rodando para sempre numa âncora
 * digitada errada, que é exatamente o caso em que ninguém está olhando.
 *
 * `prontidao` é o que quem chama passa quando sabe que o conteúdo ainda vai
 * mudar (`carregando`): mudar esse valor reinicia a procura.
 */
export function useAncora(prontidao = null) {
  const { hash } = useLocation();

  useEffect(() => {
    const alvo = (hash || "").replace(/^#/, "");
    if (!alvo) return undefined;

    let tentativas = 0;
    let timer;
    const procurar = () => {
      const el = document.getElementById(alvo);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      // ~2s no total: o suficiente para uma área terminar de carregar num 4G
      // ruim, e curto o bastante para não roubar a rolagem de quem já começou
      // a ler outra coisa.
      if (++tentativas > 20) return;
      timer = setTimeout(procurar, 100);
    };
    procurar();
    return () => clearTimeout(timer);
  }, [hash, prontidao]);
}
