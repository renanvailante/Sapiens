import { useEffect } from "react";
import { Check, X } from "lucide-react";

/**
 * AS ALTERNATIVAS — uma gramática só, para toda questão do Sapiens.
 *
 * O produto tinha cinco lugares onde o aluno responde uma questão — provas do
 * ENEM, missão do mapa de treino, questões geradas pela Mentis, blocos de
 * curso e o feed — e cada um desenhava a alternativa do seu jeito. As provas
 * e os cursos usavam `.alternativa[data-estado]` (o pé sólido, o raio grande,
 * a letra que vira ícone quando a resposta chega); o treino e as questões
 * geradas montavam `border-zinc-200 bg-white` na mão, com outro verde, outro
 * vermelho e outro tamanho de letra.
 *
 * Isso não é inconsistência de estilo, é inconsistência de APRENDIZADO. O
 * aluno toca esta interface quarenta e cinco vezes seguidas numa sessão: se
 * "verde" tem um desenho na prova e outro no treino, ele gasta atenção
 * reconhecendo a tela em vez de resolver a questão. Um aluno deve ficar bom
 * no Sapiens, não bom em cinco telas do Sapiens.
 *
 * O CSS já era o dono da aparência (`index.css`, bloco "As alternativas").
 * Esta peça passa a ser a dona do COMPORTAMENTO: o estado que cada letra
 * assume, o que acontece no toque, e o teclado.
 *
 * ---------------------------------------------------------------------------
 * O TECLADO, QUE ANTES SÓ EXISTIA NAS PROVAS
 * ---------------------------------------------------------------------------
 *
 * Responder com A–E era um ganho real e morava dentro do `QuestionRunner` das
 * provas — quem treinava pelo mapa ou respondia uma questão gerada tinha de
 * usar o mouse. Ao mudar de casa ele passou a valer em toda parte de graça,
 * que é exatamente o que uma peça compartilhada deve fazer: o conserto num
 * lugar conserta todos.
 *
 * `teclado` é opt-out, não opt-in: quem embute a questão num contexto com
 * outros campos (um bloco de curso com caixa de texto ao lado) desliga.
 */

/** As corretas, em qualquer um dos formatos que o backend usa hoje: `correta`
 *  (uma letra, fluxo de prova) ou `gabarito` (lista, fluxo de treino). Uma
 *  função só, para não haver dois entendimentos de "qual era a resposta". */
export function letrasCorretas(resultado) {
  if (!resultado) return [];
  if (Array.isArray(resultado.corretas)) return resultado.corretas;
  if (Array.isArray(resultado.gabarito)) return resultado.gabarito;
  if (resultado.correta) return [resultado.correta];
  return [];
}

export default function Alternativas({
  alternativas = [],
  selecionada = null,
  resultado = null,
  desabilitado = false,
  aoEscolher,
  figurasPorLetra = null,
  aoAmpliarFigura = null,
  teclado = true,
  testidPrefixo = "alt",
}) {
  const corretas = letrasCorretas(resultado);
  const respondida = Boolean(resultado);
  const travado = respondida || desabilitado;

  useEffect(() => {
    if (!teclado || travado) return undefined;
    const aoTeclar = (e) => {
      // Um atalho de letra não pode roubar o que o aluno está digitando —
      // nem a navegação do navegador.
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const alvo = e.target;
      if (alvo && /^(INPUT|TEXTAREA|SELECT)$/.test(alvo.tagName)) return;
      if (alvo && alvo.isContentEditable) return;
      const letra = (e.key || "").toUpperCase();
      if (letra.length !== 1 || !"ABCDE".includes(letra)) return;
      const existe = alternativas.some((a) => a.letra === letra && a.texto);
      if (!existe) return;
      e.preventDefault();
      aoEscolher?.(letra);
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [teclado, travado, alternativas, aoEscolher]);

  return (
    <div className="grid gap-2" data-testid={`${testidPrefixo}-lista`}>
      {alternativas.map((alt) => {
        const letra = alt.letra;
        const escolhida = selecionada === letra;
        const certa = respondida && corretas.includes(letra);
        const erradaEscolhida = respondida && escolhida && !certa;
        const figura = figurasPorLetra?.[letra] || null;

        // Um atributo em vez de quatro strings de classe montadas à mão: o
        // estado da alternativa é DADO, e quem o desenha é o CSS.
        const estado = certa
          ? "certa"
          : erradaEscolhida
          ? "errada"
          : escolhida
          ? "escolhida"
          : "livre";

        return (
          <button
            key={letra}
            type="button"
            onClick={() => aoEscolher?.(letra)}
            disabled={travado || !alt.texto}
            data-testid={`${testidPrefixo}-${letra}`}
            data-estado={estado}
            className={`alternativa ${escolhida && !respondida ? "select-pop" : ""}`}
          >
            <span className="alternativa-letra">
              {certa ? (
                <Check className="h-4 w-4" />
              ) : erradaEscolhida ? (
                <X className="h-4 w-4" />
              ) : (
                letra
              )}
            </span>
            <span className="flex flex-col gap-2">
              {figura && (
                <img
                  src={figura.src}
                  alt={`Alternativa ${letra}`}
                  className={`max-w-[220px] rounded-lg border border-zinc-200 bg-white ${aoAmpliarFigura ? "cursor-zoom-in" : ""}`}
                  loading="lazy"
                  data-testid={`${testidPrefixo}-${letra}-figura`}
                  onClick={(e) => {
                    if (!aoAmpliarFigura) return;
                    e.stopPropagation();
                    aoAmpliarFigura({ src: figura.src, alt: `Alternativa ${letra}` });
                  }}
                  onError={(e) => {
                    e.currentTarget.style.display = "none";
                  }}
                />
              )}
              {alt.texto ? (
                <span className="text-zinc-700">{alt.texto}</span>
              ) : (
                // EST-02: 18 itens do corpus têm alternativa sem texto. Antes
                // disto o botão vinha em branco, clicável, e o aluno podia
                // "responder" uma alternativa que não existe na prova.
                <span className="italic text-zinc-400">
                  Alternativa indisponível — esta questão está em correção.
                </span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}
