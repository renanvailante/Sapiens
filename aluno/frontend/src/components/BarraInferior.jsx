import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { LayoutGrid, CalendarDays, Brain, PlayCircle, Grip } from "lucide-react";
import { useAuth } from "../lib/auth";
import Mentis from "./Mentis";
import LancadorDeFerramentas from "./LancadorDeFerramentas";

/**
 * A barra inferior do celular — o buraco mais caro que o produto tinha.
 *
 * Até 2026-09-16, abaixo de 1024px NÃO HAVIA navegação nenhuma. A barra de
 * cima ficava com um botão de menu à esquerda e mais nada: painel, mapa de
 * treino, redação, cronograma, mural, liga, revisões, Mentis — o produto
 * inteiro — vivia atrás de um painel modal que só abre quem já sabe que ele
 * existe. E a maioria dos alunos entra pelo celular.
 *
 * O que a barra resolve, nesta ordem:
 *
 * 1. **Onde eu estou.** A aba da rota atual acende, com traço em cima e
 *    rótulo mais forte (ver `.aba-inferior[data-ativa]` no `index.css`). Era
 *    informação que só existia no título da página.
 * 2. **O que eu faço agora.** O alvo do MEIO é elevado, aceso e é o único
 *    objeto brilhante da barra: praticar. A navegação passa a responder a
 *    pergunta do produto, e não só "para onde eu vou".
 * 3. **O resto continua alcançável.** "Mais" abre o mesmo lançador de
 *    ferramentas de sempre, agora subindo de baixo — nenhuma tela saiu do
 *    alcance, e as que estavam a um modal de distância continuam a um.
 *
 * As quatro abas fixas são as quatro coisas que um aluno faz TODO dia. O
 * critério não é quantas telas existem, é quantas o polegar precisa alcançar
 * sem pensar; a quinta vaga é a porta para todas as outras.
 *
 * A LISTA MUDOU EM 2026-09-17 (segunda passada), para espelhar a barra de
 * cima: Painel · Semana · [Praticar] · Desempenho · Mais. Duas trocas, e as
 * duas têm motivo:
 *
 *   · **Semana entrou** porque o cronograma é a única peça do produto que
 *     responde "o que eu faço NA QUINTA" em vez de "o que eu faço agora", e
 *     ele estava enterrado na quarta dobra do Painel.
 *   · **Mentis saiu da tira, e não do produto.** Ela é camada, não página: o
 *     ícone flutuante (`MentisWidget`, montado em `App.js`) já a chama de
 *     QUALQUER tela, inclusive destas cinco. Uma aba para ela era a mesma
 *     porta duas vezes a 60px de distância — e era a vaga que a Semana
 *     precisava.
 */

const ABAS = [
  { to: "/dashboard", icone: LayoutGrid, rotulo: "Painel", testid: "barra-painel" },
  { to: "/cronograma", icone: CalendarDays, rotulo: "Semana", testid: "barra-semana" },
  // O meio é a ação — ver `ACAO` abaixo.
  { to: "/desempenho", icone: Brain, rotulo: "Desempenho", testid: "barra-desempenho" },
];

const ACAO = { to: "/exams", icone: PlayCircle, rotulo: "Praticar", testid: "barra-praticar" };

// Telas em que a barra não entra, e por quê:
//
// `/feed`      — sangria total, com controles próprios no rodapé. É a mesma
//                lista que o ícone flutuante da Mentis já respeita.
// `/bem-vindo` — o primeiro acesso é uma conversa conduzida; navegar para
//                fora dela no meio é sair do onboarding sem ter terminado.
// `/exam/*`    — registrar respostas é a única tela do produto com um
//                estado não salvo dentro. Uma barra de navegação permanente
//                embaixo de um gabarito pela metade é um convite a perdê-lo.
const SEM_BARRA = ["/feed", "/bem-vindo"];

function ehRotaAtual(pathname, to) {
  if (to === "/dashboard") return pathname === "/dashboard";
  return pathname === to || pathname.startsWith(`${to}/`);
}

export default function BarraInferior() {
  const { user, loading, logout } = useAuth() || {};
  const { pathname } = useLocation();
  const nav = useNavigate();
  const [lancador, setLancador] = useState(false);

  if (loading || !user) return null;
  if (SEM_BARRA.includes(pathname)) return null;
  if (pathname.startsWith("/exam/")) return null;

  const sair = async () => {
    await logout();
    nav("/");
  };

  const aba = (item) => {
    const ativa = ehRotaAtual(pathname, item.to);
    return (
      <Link
        key={item.to}
        to={item.to}
        className="aba-inferior"
        data-ativa={ativa}
        data-testid={item.testid}
        aria-current={ativa ? "page" : undefined}
      >
        {item.mascote ? (
          <Mentis className="h-[22px] w-[22px]" variante="icone" animada={false} />
        ) : (
          <item.icone className="h-[22px] w-[22px]" strokeWidth={ativa ? 2.2 : 1.8} />
        )}
        <span>{item.rotulo}</span>
      </Link>
    );
  };

  return (
    <>
      <nav
        className="barra-inferior lg:hidden"
        aria-label="Navegação principal"
        data-testid="barra-inferior"
        data-tour="barra-inferior"
      >
        {aba(ABAS[0])}
        {aba(ABAS[1])}

        {/* A AÇÃO. Fora do fluxo de rótulo das outras para poder subir 22px
            acima da barra sem empurrar as vizinhas. */}
        <Link
          to={ACAO.to}
          className="flex flex-1 flex-col items-center justify-start"
          data-testid={ACAO.testid}
          aria-label="Praticar questões"
        >
          <span className="aba-acao">
            <ACAO.icone className="h-6 w-6" strokeWidth={2.1} />
          </span>
          <span className="aba-acao-rotulo">{ACAO.rotulo}</span>
        </Link>

        {aba(ABAS[2])}

        <button
          type="button"
          onClick={() => setLancador(true)}
          className="aba-inferior"
          data-ativa={lancador}
          data-testid="barra-mais"
          data-tour="barra-mais"
          aria-label="Todas as ferramentas"
        >
          {/* A MESMA malha de pontos do botão de menu da barra de cima: o
              painel que abre é o mesmo, e dois símbolos diferentes para a
              mesma porta obrigam o aluno a aprendê-la duas vezes. */}
          <Grip className="h-[22px] w-[22px]" strokeWidth={1.8} />
          <span>Menu</span>
        </button>
      </nav>

      <LancadorDeFerramentas
        aberto={lancador}
        aoFechar={() => setLancador(false)}
        user={user}
        aoSair={sair}
        lado="bottom"
      />
    </>
  );
}
