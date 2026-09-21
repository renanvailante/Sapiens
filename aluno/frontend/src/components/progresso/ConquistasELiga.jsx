import { useEffect, useState } from "react";
import { Trophy, Medal, ArrowUp, ArrowDown, Loader2, Info } from "lucide-react";
import { api } from "../../lib/api";
import AnelDeProgresso from "../AnelDeProgresso";
import PainelDeConquistas from "../PainelDeConquistas";
import { avaliarConquistas } from "../../lib/conquistas";
import { computeStreak, computeWeek } from "../../lib/atividade";

/**
 * CONQUISTAS E LIGA — as duas metades de "o que o meu esforço rendeu".
 *
 * Eram duas telas (`/conquistas` e `/liga`) que já dividiam uma linha só no
 * Menu desde 17/09, com uma ponte dentro de uma para a outra. Dividir a linha
 * e continuar sendo duas telas é meio caminho: o aluno lia "Conquistas e liga",
 * abria, via troféus, e precisava de um segundo clique para o ranking.
 *
 * Aqui são duas peças da mesma seção, e o contraste entre elas fica visível
 * sem precisar de texto explicando:
 *
 *   · **Troféu** é o que ele já provou. Não zera, não depende de ninguém.
 *   · **Liga** é onde ele está agora, contra os outros, e zera toda segunda.
 *
 * A liga vem primeiro porque é a que muda — uma tabela que fecha no domingo à
 * noite é a única coisa desta seção com prazo. Os troféus estão lá desde
 * sempre e vão continuar.
 *
 * **Sem bots.** Se a divisão tem três pessoas, a tela mostra três e diz isso.
 * Encher o ranking com adversários fictícios é o tipo de coisa que, descoberta
 * uma vez, contamina a confiança em todos os outros números do produto.
 *
 * As seis chamadas dos troféus são as MESMAS que o Hoje já faz — nenhuma conta
 * nova, nenhum contador paralelo, todas O(1). A da liga é `/engajamento/liga`,
 * 100% Mongo: é a página que mais se atualiza no domingo à noite, e uma
 * leitura do Firestore por refresh sairia cara justamente na hora em que todo
 * mundo olha ao mesmo tempo.
 */

function formatarFechamento(iso) {
  try {
    return new Date(`${iso}T23:59:59`).toLocaleDateString("pt-BR", {
      weekday: "long", day: "2-digit", month: "long",
    });
  } catch {
    return iso;
  }
}

function TabelaDaLiga({ liga }) {
  if (!liga) return null;

  return (
    <div data-testid="liga">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-lg font-bold tracking-tight text-white">
          Liga <span style={{ color: liga.cor }}>{liga.nome}</span>
        </h3>
        <span className="text-xs text-white/45">
          Fecha {formatarFechamento(liga.fecha_em)} · só os {liga.sobem} primeiros sobem
        </span>
      </div>

      {liga.total === 0 ? (
        <div className="card-sapiens mt-3 rounded-2xl p-6" data-testid="liga-vazia">
          <p className="text-sm text-zinc-500">
            Ninguém pontuou nesta divisão ainda nesta semana. Responda uma questão e você
            assume o primeiro lugar.
          </p>
        </div>
      ) : (
        <div className="card-sapiens mt-3 overflow-hidden rounded-2xl" data-testid="liga-tabela">
          {liga.tabela.map((linha, i) => {
            const sobe = linha.posicao <= liga.sobem && liga.total >= 10;
            const cai = liga.total >= 30 && linha.posicao > liga.total - liga.caem;
            return (
              <div
                key={`${linha.uid}-${linha.posicao}`}
                className={[
                  "flex items-center gap-3 px-5 py-3",
                  i > 0 ? "border-t border-white/5" : "",
                  linha.voce ? "bg-[#4FD9FF]/10" : "",
                ].join(" ")}
                data-testid={linha.voce ? "liga-linha-voce" : `liga-linha-${linha.posicao}`}
              >
                <span
                  className={`w-7 shrink-0 text-center font-mono-alt text-sm ${
                    linha.posicao <= 3 ? "text-amber-300" : "text-white/40"
                  }`}
                >
                  {linha.posicao}
                </span>
                <span
                  className={`flex-1 truncate text-sm ${
                    linha.voce ? "font-semibold text-white" : "text-zinc-950"
                  }`}
                >
                  {linha.nome}
                  {linha.voce && <span className="ml-2 text-xs text-[#7FD8FF]">você</span>}
                </span>
                {sobe && <ArrowUp className="h-3.5 w-3.5 shrink-0 text-emerald-400" aria-label="Zona de subida" />}
                {cai && <ArrowDown className="h-3.5 w-3.5 shrink-0 text-rose-400" aria-label="Zona de queda" />}
                <span className="w-20 shrink-0 text-right text-sm tabular-nums text-zinc-500">
                  {linha.pontos.toLocaleString("pt-BR")} XP
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Posição real de quem está fora dos 30 primeiros. Esconder onde a
          pessoa está é pior do que ela estar em 41º. */}
      {liga.minha_posicao && !liga.tabela.some((l) => l.voce) && (
        <p className="mt-3 text-sm text-white/60" data-testid="liga-minha-posicao">
          Você está em {liga.minha_posicao}º de {liga.total}, com {liga.meus_pontos} XP.
        </p>
      )}

      {liga.total > 0 && liga.total < 10 && (
        <p className="mt-4 flex items-start gap-2 text-xs text-white/40" data-testid="liga-grupo-pequeno">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Esta divisão ainda tem poucas pessoas nesta semana, então ninguém sobe nem desce —
          seria o tamanho da turma decidindo, não o seu esforço.
        </p>
      )}
    </div>
  );
}

export default function ConquistasELiga() {
  const [ctx, setCtx] = useState(null);
  const [liga, setLiga] = useState(null);
  const [carregandoLiga, setCarregandoLiga] = useState(true);

  useEffect(() => {
    let ativo = true;
    Promise.allSettled([
      api.get("/firestore/students/me/respondidas").then(({ data }) => (data.item_ids || []).length),
      api.get("/firestore/students/me/activity").then(({ data }) => data.dates || []),
      api.get("/skills-map").then(({ data }) => data.hubs || []),
      api.get("/analyses").then(({ data }) => data),
      api.get("/firestore/students/me/rounds").then(({ data }) => data.rounds || []),
      api.get("/redacao", { params: { limit: 20 } }).then(({ data }) => data.items || []),
    ]).then(([q, a, h, an, r, red]) => {
      if (!ativo) return;
      const valor = (res, vazio) => (res.status === "fulfilled" ? res.value : vazio);
      const dates = valor(a, []);
      const redacoes = valor(red, []);
      setCtx({
        totalRespondidas: valor(q, 0),
        streak: computeStreak(dates),
        weekActiveDays: computeWeek(dates).filter((d) => d.active).length,
        hubs: valor(h, []),
        analyses: valor(an, []),
        rounds: valor(r, []),
        redacoesCorrigidas: redacoes.filter((x) => x.avaliacao).length,
        melhorRedacao: redacoes.reduce((m, x) => Math.max(m, x.avaliacao?.nota_total ?? 0), 0),
      });
    });

    api
      .get("/engajamento/liga")
      .then(({ data }) => { if (ativo) setLiga(data); })
      .catch(() => { if (ativo) setLiga(null); })
      .finally(() => { if (ativo) setCarregandoLiga(false); });

    return () => { ativo = false; };
  }, []);

  const avaliadas = avaliarConquistas(ctx);
  const feitas = avaliadas.filter((c) => c.desbloqueada).length;

  return (
    <div className="space-y-10">
      {/* A LIGA primeiro: é a metade com prazo. */}
      {carregandoLiga ? (
        <div className="flex items-center gap-2 text-sm text-white/50">
          <Loader2 className="h-4 w-4 animate-spin" /> Carregando o ranking…
        </div>
      ) : liga ? (
        <TabelaDaLiga liga={liga} />
      ) : (
        <p className="text-sm text-white/55">Não foi possível carregar a liga agora.</p>
      )}

      {/* OS TROFÉUS. O anel no lugar do contador em pílula: o mesmo par de
          números, mas o olho lê a PROPORÇÃO antes do número, que é a única
          coisa que interessa numa coleção. */}
      <div data-testid="conquistas">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Medal className="h-[18px] w-[18px] text-amber-300" strokeWidth={2} />
            <h3 className="font-display text-lg font-bold tracking-tight text-white">
              Os seus troféus
            </h3>
          </div>
          <div className="flex items-center gap-3" data-testid="conquistas-contagem">
            <AnelDeProgresso
              valor={avaliadas.length ? (100 * feitas) / avaliadas.length : 0}
              tamanho={62}
              espessura={6}
            >
              <span className="medida-n text-lg">{feitas}</span>
            </AnelDeProgresso>
            <div>
              <div className="font-mono-alt text-sm font-bold text-white">de {avaliadas.length}</div>
              <div className="medida-rotulo">desbloqueadas</div>
            </div>
          </div>
        </div>

        <p className="mt-2 max-w-2xl text-sm text-white/45">
          Troféu é o que você já provou — não zera na segunda e não depende de mais ninguém.
          Cada medalha abre com o seu progresso, a condição exata e o caminho até ela.
        </p>

        <div className="mt-5">
          {ctx ? (
            <PainelDeConquistas contexto={ctx} agrupado testid="conquistas-grade" />
          ) : (
            <div className="grid grid-cols-4 gap-2.5 sm:grid-cols-6">
              {Array.from({ length: 12 }).map((_, i) => (
                <div key={i} className="esqueleto aspect-square rounded-2xl" />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* A linha ética, dita onde ela vale: conquista não paga Sparks nem XP.
          Quem paga são as missões diárias, e o detalhe de uma medalha nunca
          inventa uma recompensa que o backend não vai entregar. */}
      <p className="flex items-start gap-2 text-xs text-white/35">
        <Trophy className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        Troféu é reconhecimento, não moeda: nenhum deles paga Sparks ou XP. O que paga são as
        missões do dia.
      </p>
    </div>
  );
}
