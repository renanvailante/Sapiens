import { useEffect, useState } from "react";
import Nav from "../components/Nav";
import { api } from "../lib/api";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { Trophy, ArrowUp, ArrowDown, Loader2, Info } from "lucide-react";

/**
 * A liga da semana.
 *
 * O ranking é por XP DA SEMANA, não acumulado: quem começou ontem disputa em
 * pé de igualdade com quem está há seis meses. A liga mede esforço desta
 * semana, não antiguidade — é o que a mantém jogável para quem chega depois.
 *
 * **Sem bots.** Se a divisão tem três pessoas, a tela mostra três pessoas e
 * diz isso. Encher o ranking com adversários fictícios seria mentir sobre com
 * quem o aluno está competindo, e é o tipo de coisa que, descoberta uma vez,
 * contamina a confiança em todos os outros números do produto.
 *
 * Esta tela NÃO chama `/engajamento/me`: usa `/engajamento/liga`, que é 100%
 * Mongo. É a página que mais se atualiza no domingo à noite, quando a semana
 * fecha, e uma leitura do Firestore por refresh sairia cara justamente na hora
 * em que todo mundo olha ao mesmo tempo.
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

export default function Liga() {
  const [liga, setLiga] = useState(null);
  const [carregando, setCarregando] = useState(true);

  useDeclararContextoMentis("Na tela da liga semanal.");

  useEffect(() => {
    api
      .get("/engajamento/liga")
      .then(({ data }) => setLiga(data))
      .catch(() => setLiga(null))
      .finally(() => setCarregando(false));
  }, []);

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-3xl px-6 py-12 md:px-10">
        <div className="font-mono-alt mb-3 flex items-center gap-2 text-xs uppercase tracking-[0.35em] text-white/50">
          <Trophy className="h-3.5 w-3.5" /> Liga
        </div>

        {carregando ? (
          <div className="flex items-center gap-2 text-white/50">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando o ranking…
          </div>
        ) : !liga ? (
          <p className="text-white/60">Não foi possível carregar a liga agora.</p>
        ) : (
          <>
            <h1
              className="font-display text-4xl font-extrabold tracking-tighter text-white md:text-5xl"
              data-testid="liga-title"
            >
              Liga <span style={{ color: liga.cor }}>{liga.nome}</span>
            </h1>
            <p className="mt-3 max-w-xl text-white/60">
              Fecha {formatarFechamento(liga.fecha_em)}. Os {liga.sobem} primeiros sobem de divisão.
              Cada XP que você ganha estudando conta aqui.
            </p>

            {liga.total === 0 ? (
              <div className="card-sapiens mt-8 rounded-2xl p-6" data-testid="liga-vazia">
                <p className="text-sm text-zinc-500">
                  Ninguém pontuou nesta divisão ainda nesta semana. Responda uma questão e você
                  assume o primeiro lugar.
                </p>
              </div>
            ) : (
              <div className="card-sapiens mt-8 overflow-hidden rounded-2xl" data-testid="liga-tabela">
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
                      {sobe && <ArrowUp className="h-3.5 w-3.5 shrink-0 text-emerald-400" title="Zona de subida" />}
                      {cai && <ArrowDown className="h-3.5 w-3.5 shrink-0 text-rose-400" title="Zona de queda" />}
                      <span className="w-20 shrink-0 text-right text-sm tabular-nums text-zinc-500">
                        {linha.pontos.toLocaleString("pt-BR")} XP
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Posição real de quem está fora dos 30 primeiros. Esconder onde
                a pessoa está é pior do que ela estar em 41º. */}
            {liga.minha_posicao && !liga.tabela.some((l) => l.voce) && (
              <p className="mt-4 text-sm text-white/60" data-testid="liga-minha-posicao">
                Você está em {liga.minha_posicao}º de {liga.total}, com {liga.meus_pontos} XP.
              </p>
            )}

            {liga.total > 0 && liga.total < 10 && (
              <p className="mt-6 flex items-start gap-2 text-xs text-white/40" data-testid="liga-grupo-pequeno">
                <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                Esta divisão ainda tem poucas pessoas nesta semana, então ninguém sobe nem desce —
                seria o tamanho da turma decidindo, não o seu esforço.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
