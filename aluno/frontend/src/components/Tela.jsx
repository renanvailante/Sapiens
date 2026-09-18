import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import Nav from "./Nav";

/**
 * A CASCA DE UMA TELA — barra, container e cabeçalho, uma vez só.
 *
 * Quinze telas do produto abriam com a mesma construção copiada à mão:
 *
 *     <div className="min-h-screen">
 *       <Nav />
 *       <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
 *         <div className="font-mono-alt text-xs uppercase tracking-[0.35em] …">Olho</div>
 *         <h1 className="font-display text-4xl md:text-5xl font-extrabold …">Título</h1>
 *         <p className="mt-3 text-white/60 max-w-xl">Subtítulo</p>
 *
 * "Mesma" com aspas: entre elas havia quatro larguras de container (3xl, 4xl,
 * 5xl, 6xl), três respiros verticais (py-10, py-12, py-14), dois tamanhos de
 * título e dois espaçamentos de olho. Nenhuma dessas diferenças significava
 * nada — eram a ordem em que as telas foram escritas. O aluno que vai do
 * Painel para a Loja e da Loja para a Redação atravessa três ritmos
 * diferentes em três cliques, e é disso que vem a sensação de "cada tela é de
 * um produto".
 *
 * Aqui a casca é uma peça. O que quem usa escolhe é o que MUDA de tela para
 * tela: o texto, a largura útil e as ações do canto.
 *
 * Duas decisões embutidas:
 *
 * · **O título encolheu.** Era `text-4xl md:text-5xl` (até 48px); agora é
 *   `.titulo-tela`, que vai de 28 a 42px com `clamp`. Um título de 48px numa
 *   tela de 667px de altura come 15% da primeira dobra para dizer o nome da
 *   página — que o aluno já sabe, porque foi ele que clicou para chegar aqui.
 * · **O respiro de cima caiu de `py-12` para `py-7`.** Pelo mesmo motivo: o
 *   conteúdo começa mais cedo. O `md:py-10` devolve o ar onde há tela sobrando.
 */

const LARGURAS = {
  sm: "max-w-2xl",
  md: "max-w-3xl",
  lg: "max-w-4xl",
  xl: "max-w-5xl",
  xxl: "max-w-6xl",
};

export default function Tela({
  olho = null,
  titulo = null,
  subtitulo = null,
  acoes = null,
  voltar = null,
  voltarLabel = "Painel",
  largura = "lg",
  // `semNav` existe para as telas que desenham a própria barra por cima de um
  // conteúdo em sangria (o mapa 3D do treino é a única hoje).
  semNav = false,
  className = "",
  testid,
  children,
}) {
  const temCabeca = olho || titulo || subtitulo || acoes || voltar;

  return (
    <div className="min-h-screen">
      {!semNav && <Nav />}
      <div className={`mx-auto ${LARGURAS[largura] || LARGURAS.lg} px-5 py-7 md:px-10 md:py-10 ${className}`} data-testid={testid}>
        {temCabeca && (
          <header className="mb-7">
            {voltar && (
              <Link
                to={voltar}
                className="-ml-1 mb-3 inline-flex items-center gap-1.5 rounded-full px-1 py-1.5 text-xs font-semibold text-white/45 transition-colors hover:text-white"
                data-testid={testid ? `${testid}-voltar` : undefined}
              >
                <ArrowLeft className="h-3.5 w-3.5" /> {voltarLabel}
              </Link>
            )}
            <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-3">
              <div className="min-w-0">
                {olho && <div className="secao-olho flex items-center gap-1.5">{olho}</div>}
                {titulo && (
                  <h1 className="titulo-tela" data-testid={testid ? `${testid}-title` : undefined}>
                    {titulo}
                  </h1>
                )}
                {subtitulo && (
                  <p className="mt-2.5 max-w-xl text-sm leading-relaxed text-white/55">{subtitulo}</p>
                )}
              </div>
              {acoes && <div className="flex shrink-0 flex-wrap items-center gap-2">{acoes}</div>}
            </div>
          </header>
        )}
        {children}
      </div>
    </div>
  );
}
