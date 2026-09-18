import { useMemo, useRef, useLayoutEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, Lock, Play, Star, SkipForward, Zap, Trophy, Clock, Target } from "lucide-react";
import SaltoAteAqui from "./SaltoAteAqui";

/**
 * O MAPA DE UMA TRILHA, desenhado como caminho — não como lista.
 *
 * Vinte e quatro linhas numa lista dizem "aqui estão 24 coisas". Um caminho
 * diz "você está AQUI, e o próximo passo é este" — que é a única pergunta que
 * alguém abre um curso para responder. O empréstimo é o mesmo que a trilha de
 * missões do Painel já faz (`TrilhaDeMissoes`): serpenteio, nó como objeto
 * macio, pé sólido que afunda ao toque.
 *
 * **O que muda em relação à trilha do Painel**, e por quê:
 *
 * · **Seis estados, não quatro.** Curso tem `pulada` (provou domínio e não
 *   estudou) e `dominada` (estudou e acertou tudo de primeira), que a trilha
 *   de habilidades não tem. Os dois desenham diferente porque SIGNIFICAM
 *   diferente — pintar os dois de verde apagaria a distinção que o banco
 *   guarda de propósito.
 * · **O caminho percorrido acende.** A linha atrás dos nós vencidos recebe o
 *   gradiente da marca; o resto fica em névoa. É o "quanto eu andei" sem uma
 *   barra de porcentagem em cima da tela.
 * · **O nó é clicável mesmo bloqueado** — e aí abre o cartão dizendo o NOME do
 *   que falta. Cadeado que não explica manda o aluno procurar sozinho.
 *
 * **Sistema de coordenadas fixo**, pelo mesmo motivo de `TrilhaDeMissoes`: a
 * curva de trás é um `<path>` em px e precisa passar pelo centro de cada nó.
 * Com posição em % e nó em px, a linha erra o alvo em toda largura que não
 * seja a testada.
 *
 * Nada aqui decide estado: quem decide é `cursos_progresso.mapa_de_estados`,
 * no servidor, e uma segunda implementação aqui divergiria no dia em que o
 * critério mudasse.
 */

// A GEOMETRIA DO SERPENTEIO.
//
// O caminho anterior era quase uma coluna: ±64px de desvio em 300px de
// largura, com 112px entre nós. Gastava uma tela inteira de altura para
// mostrar cinco estações e deixava as laterais vazias — o oposto do que um
// caminho deve parecer.
//
// Agora o desvio vai a ±96px (60% do meio-vão) e o passo cai para 96px: a
// mesma trilha ocupa ~15% menos altura e usa a largura toda. A referência é
// declarada (Duolingo) e a régua é uma só — o nó mais lateral, com o rótulo
// embaixo, ainda cabe inteiro em 320px, que é o vão útil de um celular de
// 360px com as margens do produto.
//
//   160 (meio) + 96 (desvio) + 52 (meio rótulo) = 308 < 320  ✓
const LARGURA = 320;
const PASSO = 92;      // distância vertical entre centros de nó
const RAIO = 30;
const MARGEM = 36;
// Ciclo de QUATRO, e não de oito. Um ciclo longo é mais bonito num caminho
// longo, mas as trilhas deste curso têm de quatro a seis estações — e com
// oito posições as primeiras cinco caíam todas em offsets positivos: a trilha
// inteira fazia um arco para a direita e nunca visitava o lado esquerdo. Com
// quatro, qualquer trilha a partir de três estações já atravessa os dois
// lados, que é o que faz o caminho parecer caminho.
const OFFSETS = [0, 96, 0, -96];
const ROTULO_W = 104;

export const ESTADOS = {
  pulada: {
    rotulo: "Você já sabia",
    ajuda: "Provada na avaliação de domínio, sem precisar estudar.",
    circulo: "no-trilha no-pulado",
    icone: SkipForward,
    texto: "text-violet-200",
    vencida: true,
  },
  dominada: {
    rotulo: "Dominada",
    ajuda: "Concluída acertando tudo de primeira.",
    circulo: "no-trilha no-dominado-curso",
    icone: Star,
    texto: "text-amber-200",
    vencida: true,
  },
  concluida: {
    rotulo: "Concluída",
    ajuda: "Você chegou ao fim desta estação.",
    circulo: "no-trilha no-dominado",
    icone: Check,
    texto: "text-sky-200",
    vencida: true,
  },
  em_andamento: {
    rotulo: "Em andamento",
    ajuda: "Você começou e ainda não terminou.",
    circulo: "no-trilha no-atual",
    icone: Play,
    texto: "text-white",
    vencida: false,
  },
  disponivel: {
    rotulo: "Disponível",
    ajuda: "Liberada — é por aqui que se continua.",
    circulo: "no-trilha no-comecado",
    icone: Play,
    texto: "text-white/85",
    vencida: false,
  },
  bloqueada: {
    rotulo: "Ainda fechada",
    ajuda: "Conclua a estação anterior para abrir esta.",
    circulo: "no-trilha no-novo",
    icone: Lock,
    texto: "text-white/40",
    vencida: false,
  },
};

function estilo(estado) {
  return ESTADOS[estado] || ESTADOS.disponivel;
}

/** O cartão que abre ao lado (ou abaixo, no celular) do nó selecionado. */
function CartaoDaEstacao({ cursoId, estacao, aoFechar, aoSaltar }) {
  const [saltando, setSaltando] = useState(false);
  const visual = estilo(estacao.estado);
  const bloqueada = estacao.estado === "bloqueada";
  const vencida = visual.vencida;
  const alvo = estacao.acertos_para_concluir || 0;
  const feito = Math.min(estacao.acertos || 0, alvo);

  return (
    <div
      className="superficie superficie-viva rounded-3xl p-5"
      data-testid={`estacao-cartao-${estacao.estacao_id}`}
      role="group"
      aria-label={`Estação ${estacao.numero ?? ""}: ${estacao.titulo}`}
    >
      {/* A prova de salto toma o cartão inteiro: dividir a atenção dela com o
          resumo da estação seria desenhar duas coisas pedindo foco — e, no
          celular, um cartão de três telas de altura. */}
      {saltando ? null : (
      <>
      <div className="secao-olho flex items-center gap-1.5">
        {estacao.numero != null && <span>Estação {String(estacao.numero).padStart(2, "0")}</span>}
        <span className={visual.texto}>· {visual.rotulo}</span>
      </div>
      <h3 className="mt-1.5 font-display text-lg font-extrabold tracking-tight text-white">
        {estacao.titulo}
      </h3>
      <p className="mt-1.5 text-sm leading-relaxed text-white/60">{estacao.objetivo}</p>

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-white/45">
        {estacao.duracao_minutos ? (
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3 w-3" /> {estacao.duracao_minutos} min
          </span>
        ) : null}
        <span className="inline-flex items-center gap-1">
          <Target className="h-3 w-3" /> {feito}/{alvo} exercícios
        </span>
        {estacao.xp_possivel ? (
          <span className="inline-flex items-center gap-1 text-violet-300/70">
            <Trophy className="h-3 w-3" /> até {estacao.xp_possivel} XP
          </span>
        ) : null}
        {estacao.sparks_possiveis ? (
          <span className="inline-flex items-center gap-1 text-amber-300/70">
            <Zap className="h-3 w-3" /> até {estacao.sparks_possiveis} Sparks
          </span>
        ) : null}
      </div>

      {alvo > 0 && !bloqueada && (
        <div className="barra mt-3" data-cheia={feito >= alvo} aria-hidden="true">
          <i style={{ width: `${alvo ? Math.round((feito / alvo) * 100) : 0}%` }} />
        </div>
      )}

      {bloqueada && (
        <p className="mt-3 text-[12px] leading-relaxed text-white/40">
          {estacao.pre_requisitos_faltando?.length > 0 ? (
            <>Antes desta, conclua: {estacao.pre_requisitos_faltando.map((p) => p.titulo).join(", ")}.</>
          ) : (
            visual.ajuda
          )}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {!bloqueada && (
          <Link
            to={`/cursos/${cursoId}/estacao/${estacao.estacao_id}`}
            className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold"
            data-testid={`estacao-abrir-${estacao.estacao_id}`}
          >
            {vencida ? "Rever" : estacao.estado === "em_andamento" ? "Continuar" : "Começar"}
          </Link>
        )}
        {aoFechar && (
          <button onClick={aoFechar} className="chip" type="button">Fechar</button>
        )}
      </div>
      </>
      )}

      {/* PULAR ATÉ AQUI — em qualquer estação que tenha o que pular antes
          dela, trancada ou não. É o caminho de quem chega sabendo metade da
          matéria, e é justamente na estação trancada que ele é mais útil:
          é lá que essa pessoa quer estar. */}
      {estacao.pode_saltar && !estacao.salto_usado && (
        <div className={saltando ? "" : "mt-3 border-t border-white/8 pt-3"}>
          <SaltoAteAqui
            cursoId={cursoId}
            estacao={estacao}
            aoAbrir={() => setSaltando(true)}
            aoFechar={() => { setSaltando(false); aoSaltar?.(); }}
          />
        </div>
      )}
    </div>
  );
}

export default function CaminhoDoCurso({
  cursoId, estacoes, selecionada, aoSelecionar, aoSaltar, testid = "caminho",
}) {
  const pontos = useMemo(
    () => estacoes.map((_, i) => ({
      x: LARGURA / 2 + OFFSETS[i % OFFSETS.length],
      y: MARGEM + i * PASSO,
    })),
    [estacoes],
  );
  const altura = MARGEM * 2 + Math.max(0, estacoes.length - 1) * PASSO;

  const caminho = pontos
    .map((p, i) => {
      if (i === 0) return `M ${p.x} ${p.y}`;
      const a = pontos[i - 1];
      return `Q ${a.x} ${(a.y + p.y) / 2} ${p.x} ${p.y}`;
    })
    .join(" ");

  // Quanto do caminho já foi andado, em comprimento real de traço. Medido no
  // DOM (`getTotalLength`) e não estimado: a curva é quadrática, e a fração
  // "3 de 8 nós" não corresponde a 3/8 do comprimento.
  const traco = useRef(null);
  const [andado, setAndado] = useState(0);
  const vencidas = estacoes.filter((e) => estilo(e.estado).vencida).length;

  useLayoutEffect(() => {
    if (!traco.current || !estacoes.length) return;
    const total = traco.current.getTotalLength?.() || 0;
    const fracao = estacoes.length > 1 ? Math.min(1, vencidas / (estacoes.length - 1)) : 0;
    setAndado(total * fracao);
  }, [vencidas, estacoes.length, caminho]);

  // A estação selecionada pode ser de OUTRA trilha: a página tem um caminho
  // por trilha e uma seleção só, e quem não tem o nó selecionado desenha a
  // legenda. Sem esta resolução, o caminho vizinho procurava um id que não
  // está na lista dele e tentava desenhar um cartão de `undefined`.
  const aberta = estacoes.find((e) => e.estacao_id === selecionada) || null;

  if (!estacoes.length) return null;

  return (
    <div
      // A coluna do caminho tem a largura EXATA do sistema de coordenadas
      // (`LARGURA`). Com um valor menor, o serpenteio é recortado e os nós
      // laterais parecem quase alinhados — que foi exatamente o que aconteceu
      // quando a amplitude cresceu e esta coluna continuou em 300px.
      className="md:grid md:grid-cols-[320px_22rem] md:justify-center md:gap-8"
      data-testid={testid}
    >
      <div className="relative mx-auto" style={{ width: LARGURA, height: altura }}>
        <svg width={LARGURA} height={altura} className="absolute inset-0" aria-hidden="true" style={{ pointerEvents: "none" }}>
          <defs>
            <linearGradient id="caminho-gradiente" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7FD8FF" />
              <stop offset="100%" stopColor="#8B7BFF" />
            </linearGradient>
          </defs>
          <path d={caminho} className="caminho-traco" strokeWidth="7" fill="none" strokeLinecap="round" />
          <path
            ref={traco}
            d={caminho}
            className="caminho-andado"
            strokeWidth="7"
            fill="none"
            strokeLinecap="round"
            style={{
              strokeDasharray: `${andado} 99999`,
              transition: "stroke-dasharray .6s ease-out",
            }}
          />
        </svg>

        {estacoes.map((estacao, i) => {
          const visual = estilo(estacao.estado);
          const Icone = visual.icone;
          const p = pontos[i];
          const selecionadoAqui = selecionada === estacao.estacao_id;
          return (
            <div key={estacao.estacao_id} className="absolute" style={{ left: p.x - RAIO, top: p.y - RAIO }}>
              <button
                type="button"
                onClick={() => aoSelecionar(selecionadoAqui ? null : estacao.estacao_id)}
                className={visual.circulo}
                aria-expanded={selecionadoAqui}
                aria-label={`Estação ${estacao.numero ?? i + 1}: ${estacao.titulo} — ${visual.rotulo}`}
                data-testid={`estacao-${estacao.estacao_id}`}
                data-estado={estacao.estado}
              >
                <Icone className="h-6 w-6" />
              </button>
              <div
                className={`pointer-events-none absolute left-1/2 top-[64px] -translate-x-1/2 text-center text-[11px] leading-tight ${visual.texto}`}
                style={{ width: ROTULO_W }}
              >
                <span className="font-mono-alt opacity-50">
                  {String(estacao.numero ?? i + 1).padStart(2, "0")}
                </span>{" "}
                {estacao.titulo}
              </div>
            </div>
          );
        })}
      </div>

      {/* O cartão vive FORA do sistema de coordenadas: dentro dele ficaria
          preso aos 300px que a curva exige.

          No desktop a coluna da direita existe sempre — e quando nada está
          selecionado ela mostra a legenda dos estados. Assim o caminho não
          salta de lugar a cada toque, e a legenda ocupa um espaço que
          sobraria vazio. No celular o cartão sobe do rodapé e a legenda fica
          fora: lá não há coluna sobrando para gastar com ela. */}
      {aberta ? (
        <div className="folha-inferior md:sticky md:top-24 md:self-start">
          <CartaoDaEstacao
            cursoId={cursoId}
            estacao={aberta}
            aoFechar={() => aoSelecionar(null)}
            aoSaltar={aoSaltar}
          />
        </div>
      ) : (
        <div className="hidden md:sticky md:top-24 md:block md:self-start">
          <Legenda estacoes={estacoes} />
        </div>
      )}
    </div>
  );
}

/**
 * A legenda dos seis estados — e quantas estações estão em cada um.
 *
 * Não é decoração: "dominada" e "pulada" são estados que só este produto tem,
 * e um nó dourado sem explicação é um enigma. Só aparecem as linhas dos
 * estados que EXISTEM neste curso agora, senão a legenda fica maior que a
 * informação que carrega.
 */
function Legenda({ estacoes }) {
  const contagem = estacoes.reduce((acc, e) => {
    acc[e.estado] = (acc[e.estado] || 0) + 1;
    return acc;
  }, {});
  const linhas = Object.entries(ESTADOS).filter(([chave]) => contagem[chave]);

  return (
    <div className="superficie rounded-3xl p-5" data-testid="caminho-legenda">
      <div className="secao-olho">Como ler o caminho</div>
      <ul className="mt-3 space-y-3">
        {linhas.map(([chave, visual]) => {
          const Icone = visual.icone;
          return (
            <li key={chave} className="flex items-start gap-3">
              <span
                className={`${visual.circulo} !h-8 !w-8 shrink-0`}
                aria-hidden="true"
                style={{ boxShadow: "none" }}
              >
                <Icone className="h-3.5 w-3.5" />
              </span>
              <div className="min-w-0">
                <div className={`text-[13px] font-semibold ${visual.texto}`}>
                  {visual.rotulo}
                  <span className="ml-1.5 font-mono-alt text-[11px] font-normal opacity-50">
                    {contagem[chave]}
                  </span>
                </div>
                <div className="text-[11px] leading-snug text-white/40">{visual.ajuda}</div>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="mt-4 text-[11px] leading-relaxed text-white/35">
        Toque em qualquer estação do caminho para ver o que ela pede.
      </p>
    </div>
  );
}
