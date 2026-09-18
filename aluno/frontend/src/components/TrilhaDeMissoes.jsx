import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Star, Lock, Play } from "lucide-react";
import Mentis from "./Mentis";
import { ordenarMissoes } from "../lib/trilha";

/**
 * A trilha — as próximas missões do Mapa de Treino desenhadas como um caminho.
 *
 * Empréstimo declarado do Duolingo (o caminho de nós que serpenteia) e do
 * Animal Crossing (nada tem quina; cada nó é um objeto macio que parece dar
 * para pegar). Antes isto era uma lista de três links de texto com uma
 * porcentagem à direita — informação idêntica, zero sensação de percurso. A
 * diferença é que uma lista diz "aqui estão três coisas" e uma trilha diz
 * "você está AQUI, e o próximo passo é este".
 *
 * Nada de novo por baixo: os nós são as mesmas habilidades de
 * `GET /treino/habilidades` que o Painel já carregava, e cada um leva ao mesmo
 * `/treino?hab=` de sempre. O estado de cada nó sai de `classificacao` e
 * `respondidas` — medida real, nunca um progresso decorativo.
 *
 * **Sistema de coordenadas fixo.** A trilha é desenhada num espaço de
 * `LARGURA` px e centralizada, em vez de reagir à largura do contêiner. É o
 * que permite a curva de trás (um `<path>` SVG) passar exatamente pelo centro
 * de cada nó: com posição em porcentagem e nó em px, a linha erra o alvo em
 * toda largura que não seja a que foi testada. 260px cabe num aparelho de
 * 320px com folga.
 */

const LARGURA = 260;
// 104 e não 84: o rótulo de um nó ocupa duas linhas logo abaixo dele, e com
// passo curto a segunda linha passava POR TRÁS do nó seguinte. O passo é
// ditado pelo texto, não pelo desenho.
const PASSO = 104;     // distância vertical entre centros
const RAIO = 30;       // metade do diâmetro do nó
const MARGEM = 34;     // folga acima do primeiro e abaixo do último centro
const ROTULO_W = 120;  // largura do nome sob o nó

// O serpenteio. Ciclo de oito para o caminho nunca parecer um zigue-zague de
// dois passos. O extremo (±60) é o maior offset em que o RÓTULO ainda cabe:
// 130 + 60 + 120/2 = 250 < LARGURA. O nó cabe com folga muito antes disso —
// quem limita aqui é o texto.
const OFFSETS = [0, 44, 60, 44, 0, -44, -60, -44];

/** Estado visual de um nó, a partir da medida real da habilidade. */
function estadoDe(hab, indice, primeiroNaoDominado) {
  if (hab.classificacao === "forte") return "dominado";
  if (indice === primeiroNaoDominado) return "atual";
  if (hab.respondidas > 0) return "comecado";
  return "novo";
}

const ESTILO = {
  dominado: {
    circulo: "no-trilha no-dominado",
    icone: Check,
    rotulo: "text-white/70",
  },
  atual: {
    circulo: "no-trilha no-atual",
    icone: Play,
    rotulo: "text-white font-semibold",
  },
  comecado: {
    circulo: "no-trilha no-comecado",
    icone: Star,
    rotulo: "text-white/70",
  },
  novo: {
    circulo: "no-trilha no-novo",
    icone: Lock,
    rotulo: "text-white/40",
  },
};

export default function TrilhaDeMissoes({ habilidades, limite = 5, testid = "trilha" }) {
  const nav = useNavigate();

  // A ordem mora em `lib/trilha.js` desde 2026-09-16: o Painel usa a mesma
  // função para dizer QUAL é o próximo passo, e o desenho aqui e a frase lá
  // têm de apontar para o mesmo nó.
  const nos = useMemo(() => ordenarMissoes(habilidades, limite), [habilidades, limite]);

  const primeiroNaoDominado = nos.findIndex((h) => h.classificacao !== "forte");

  const pontos = nos.map((_, i) => ({
    x: LARGURA / 2 + OFFSETS[i % OFFSETS.length],
    y: MARGEM + i * PASSO,
  }));
  const altura = MARGEM * 2 + Math.max(0, nos.length - 1) * PASSO;

  // A curva que liga os nós: um passo quadrático por par, com o ponto de
  // controle na altura média. Suave o bastante para ler como caminho, sem
  // nenhuma biblioteca.
  const caminho = pontos
    .map((p, i) => {
      if (i === 0) return `M ${p.x} ${p.y}`;
      const a = pontos[i - 1];
      return `Q ${a.x} ${(a.y + p.y) / 2} ${p.x} ${p.y}`;
    })
    .join(" ");

  if (!nos.length) {
    return (
      <p className="text-sm leading-relaxed text-white/50" data-testid={`${testid}-vazia`}>
        Cada ponto de luz é uma missão curta. Domine um e o território ao redor se revela.
      </p>
    );
  }

  return (
    <div className="flex justify-center" data-testid={testid}>
      <div className="relative" style={{ width: LARGURA, height: altura }}>
        <svg
          width={LARGURA}
          height={altura}
          className="absolute inset-0"
          aria-hidden="true"
          style={{ pointerEvents: "none" }}
        >
          {/* Duas passadas: um traço largo e apagado como "chão" do caminho, e
              um fino e aceso por cima. Uma linha só ou some no fundo, ou fica
              gritando mais que os nós. */}
          <path d={caminho} fill="none" stroke="rgba(150,200,255,0.10)" strokeWidth="16" strokeLinecap="round" />
          <path
            d={caminho}
            fill="none"
            stroke="rgba(79,217,255,0.30)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeDasharray="1 9"
          />
        </svg>

        {nos.map((hab, i) => {
          const estado = estadoDe(hab, i, primeiroNaoDominado);
          const estilo = ESTILO[estado];
          const Icone = estilo.icone;
          const p = pontos[i];
          return (
            <div
              key={hab.hab_id}
              className="absolute"
              style={{ left: p.x - RAIO, top: p.y - RAIO, width: RAIO * 2 }}
            >
              <button
                type="button"
                onClick={() => nav(`/treino?hab=${hab.hab_id}`)}
                className={estilo.circulo}
                title={hab.nome}
                data-testid={`${testid}-no-${hab.hab_id}`}
                data-estado={estado}
              >
                <Icone className="h-5 w-5" strokeWidth={2.4} />
              </button>

              {/* O nome fica FORA do nó, centralizado nele e com largura
                  própria: dentro do círculo caberiam três letras. */}
              <span
                className={`pointer-events-none absolute left-1/2 top-[66px] -translate-x-1/2 text-center text-[11px] leading-tight line-clamp-2 ${estilo.rotulo}`}
                style={{ width: ROTULO_W }}
              >
                {hab.nome}
              </span>

              {/* A Mentis marca onde o aluno está. Um mascote que aponta o
                  próximo passo vale mais que uma legenda dizendo "você está
                  aqui" — e é o papel dela no produto. */}
              {estado === "atual" && (
                <Mentis
                  className="pointer-events-none absolute -right-9 -top-3 h-9 w-9"
                  variante="icone"
                  estado="confirmando"
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
