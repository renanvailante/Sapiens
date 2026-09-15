import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { avisarSparksMudou } from "./Nav";
import {
  Flame, Snowflake, Trophy, Zap, CalendarDays, ArrowRight, Check, Loader2,
} from "lucide-react";

/**
 * O painel de retorno — ofensiva, nível, missões do dia, liga e contagem do ENEM.
 *
 * Fica no topo do Painel porque é a primeira coisa que responde "o que mudou
 * desde ontem e o que eu faço agora". Tudo vem de `GET /engajamento/me` numa
 * chamada só.
 *
 * **O que esta tela se recusa a fazer** (a mesma linha ética de
 * `engajamento.py`, do lado de cá):
 *
 * * Nenhum contador regressivo além da virada do dia, que existe no relógio.
 * * Nenhum número inventado de "alunos estudando agora".
 * * O aviso de ofensiva em risco leva a ESTUDAR primeiro; o congelador é a
 *   segunda opção, e só aparece para quem tem sequência de verdade a perder.
 * * O preço de tudo aparece antes do clique.
 */

function BarraDeProgresso({ percentual, className = "" }) {
  return (
    <div className={`h-1.5 w-full overflow-hidden rounded-full bg-white/10 ${className}`}>
      <div
        className="h-full rounded-full bg-gradient-to-r from-[#4FD9FF] to-[#B794F6] transition-[width] duration-500"
        style={{ width: `${Math.max(0, Math.min(100, percentual))}%` }}
      />
    </div>
  );
}

/** A sequência. O número grande é o que o aluno construiu; as sete bolinhas
 *  são a prova — cada uma só acende com resposta real por trás. */
function Ofensiva({ dados, aoComprarCongelador, comprando }) {
  const { dias, recorde, estudou_hoje, em_risco, congeladores, custo_congelador, semana } = dados;

  return (
    <div className="card-sapiens rounded-2xl p-5" data-testid="progresso-ofensiva">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">
            Ofensiva
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <Flame className={`h-7 w-7 ${dias > 0 ? "text-amber-400" : "text-white/25"}`} />
            <span className="font-display text-4xl font-extrabold tracking-tighter text-zinc-950">
              {dias}
            </span>
            <span className="text-sm text-zinc-500">{dias === 1 ? "dia" : "dias"}</span>
          </div>
        </div>
        {congeladores > 0 && (
          <span
            className="pill inline-flex items-center gap-1 rounded-full border border-sky-400/30 bg-sky-500/15 px-2.5 py-1 text-xs text-sky-200"
            title="Protege sua ofensiva em um dia que você não estudar."
            data-testid="progresso-congeladores"
          >
            <Snowflake className="h-3.5 w-3.5" /> {congeladores}
          </span>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between gap-1">
        {semana.map((d) => (
          <div key={d.dia} className="flex flex-col items-center gap-1.5">
            <div
              className={[
                "flex h-7 w-7 items-center justify-center rounded-full border text-[10px] transition-colors",
                d.ativo
                  ? "border-amber-400/50 bg-amber-400/20 text-amber-200"
                  : d.congelado
                  ? "border-sky-400/40 bg-sky-500/15 text-sky-200"
                  : "border-white/10 bg-white/5 text-white/25",
                d.hoje ? "ring-1 ring-[#4FD9FF]/60" : "",
              ].join(" ")}
              title={d.congelado ? "Dia protegido por congelador" : d.dia}
            >
              {d.ativo ? <Check className="h-3.5 w-3.5" /> : d.congelado ? <Snowflake className="h-3 w-3" /> : ""}
            </div>
            <span className="text-[9px] text-white/30">
              {["D", "S", "T", "Q", "Q", "S", "S"][new Date(`${d.dia}T12:00:00Z`).getUTCDay()]}
            </span>
          </div>
        ))}
      </div>

      {recorde > dias && (
        <p className="mt-3 text-xs text-zinc-500">Seu recorde é de {recorde} dias.</p>
      )}

      {/* O aviso só aparece quando há sequência DE VERDADE em risco, e o
          primeiro caminho é estudar — não comprar. */}
      {em_risco && (
        <div className="mt-4 rounded-xl border border-amber-400/25 bg-amber-500/10 p-3" data-testid="progresso-risco">
          <p className="text-xs text-amber-100">
            Você ainda não estudou hoje. Responda uma questão para manter seus {dias}{" "}
            {dias === 1 ? "dia" : "dias"}.
          </p>
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <Link
              to="/exams"
              className="pill btn-sapiens inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium"
              data-testid="progresso-risco-praticar"
            >
              Praticar agora <ArrowRight className="h-3 w-3" />
            </Link>
            {congeladores === 0 && (
              <button
                onClick={aoComprarCongelador}
                disabled={comprando}
                className="pill btn-vidro inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs disabled:opacity-60"
                data-testid="progresso-comprar-congelador"
              >
                {comprando ? <Loader2 className="h-3 w-3 animate-spin" /> : <Snowflake className="h-3 w-3" />}
                Congelador · {custo_congelador} Sparks
              </button>
            )}
          </div>
        </div>
      )}

      {estudou_hoje && (
        <p className="mt-3 text-xs text-emerald-300" data-testid="progresso-hoje-ok">
          Hoje já está garantido.
        </p>
      )}
    </div>
  );
}

function Nivel({ dados }) {
  return (
    <div className="card-sapiens rounded-2xl p-5" data-testid="progresso-nivel">
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">Nível</div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="font-display text-4xl font-extrabold tracking-tighter text-zinc-950">
          {dados.nivel}
        </span>
        <span className="text-sm text-zinc-500">{dados.xp_total.toLocaleString("pt-BR")} XP</span>
      </div>
      <BarraDeProgresso percentual={dados.percentual} className="mt-4" />
      <p className="mt-2 text-xs text-zinc-500">
        Faltam {dados.xp_para_o_proximo.toLocaleString("pt-BR")} XP para o nível {dados.nivel + 1}.
      </p>
    </div>
  );
}

function Liga({ dados }) {
  return (
    <Link
      to="/liga"
      className="lift card-sapiens block rounded-2xl p-5"
      data-testid="progresso-liga"
    >
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">
        Liga da semana
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <Trophy className="h-5 w-5" style={{ color: dados.cor }} />
        <span className="font-display text-2xl font-bold tracking-tight text-zinc-950">{dados.nome}</span>
      </div>
      <p className="mt-2 text-xs text-zinc-500">
        {dados.minha_posicao
          ? `Você está em ${dados.minha_posicao}º de ${dados.total}, com ${dados.meus_pontos} XP nesta semana.`
          : "Estude esta semana para entrar no ranking."}
      </p>
      <span className="mt-3 inline-flex items-center gap-1 text-xs text-[#7FD8FF]">
        Ver o ranking <ArrowRight className="h-3 w-3" />
      </span>
    </Link>
  );
}

function Missoes({ missoes, aoResgatar, resgatando }) {
  return (
    <section className="mt-4" data-testid="progresso-missoes">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h3 className="font-display text-lg font-bold tracking-tight text-white">Missões de hoje</h3>
        <span className="text-xs text-white/40">Trocam à meia-noite</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {missoes.map((m) => (
          <div
            key={m.id}
            className="card-sapiens flex flex-col rounded-2xl p-4"
            data-testid={`missao-${m.id}`}
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium leading-snug text-zinc-950">{m.titulo}</p>
              <span className="pill inline-flex shrink-0 items-center gap-1 rounded-full border border-amber-400/25 bg-amber-500/10 px-2 py-0.5 text-[11px] text-amber-200">
                <Zap className="h-3 w-3" /> {m.sparks}
              </span>
            </div>
            <div className="mt-auto pt-3">
              <BarraDeProgresso percentual={(m.progresso / m.alvo) * 100} />
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="text-xs text-zinc-500">
                  {m.progresso}/{m.alvo}
                </span>
                {m.resgatada ? (
                  <span className="inline-flex items-center gap-1 text-xs text-emerald-300">
                    <Check className="h-3 w-3" /> Resgatada
                  </span>
                ) : m.concluida ? (
                  <button
                    onClick={() => aoResgatar(m.id)}
                    disabled={resgatando === m.id}
                    className="pill btn-sapiens inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium disabled:opacity-60"
                    data-testid={`missao-resgatar-${m.id}`}
                  >
                    {resgatando === m.id ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                    Resgatar
                  </button>
                ) : (
                  <Link
                    to={m.rota}
                    className="inline-flex items-center gap-1 text-xs text-[#7FD8FF] hover:underline"
                  >
                    {m.cta} <ArrowRight className="h-3 w-3" />
                  </Link>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function PainelDeProgresso() {
  const [estado, setEstado] = useState(null);
  const [erro, setErro] = useState(false);
  const [resgatando, setResgatando] = useState(null);
  const [comprando, setComprando] = useState(false);

  const carregar = useCallback(() => {
    api
      .get("/engajamento/me")
      .then(({ data }) => { setEstado(data); setErro(false); })
      .catch(() => setErro(true));
  }, []);

  useEffect(carregar, [carregar]);

  const resgatar = async (missaoId) => {
    setResgatando(missaoId);
    try {
      const { data } = await api.post(`/engajamento/missoes/${missaoId}/resgatar`);
      toast.success(`+${data.sparks_ganhos} Sparks e +${data.xp_ganho} XP.`);
      avisarSparksMudou();
      carregar();
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível resgatar agora."));
    } finally {
      setResgatando(null);
    }
  };

  const comprarCongelador = async () => {
    setComprando(true);
    try {
      await api.post("/engajamento/congelador");
      toast.success("Congelador guardado. Ele entra sozinho no dia em que você não estudar.");
      avisarSparksMudou();
      carregar();
    } catch (err) {
      // 402 é saldo insuficiente — a mensagem do servidor já diz quantos
      // Sparks faltam, e a loja fica a um clique. Nada de empurrar a compra
      // para quem não pediu: só quem clicou no congelador chega aqui.
      toast.error(errMsg(err, "Não foi possível comprar agora."), {
        action: err?.response?.status === 402
          ? { label: "Ver Sparks", onClick: () => { window.location.href = "/sparks"; } }
          : undefined,
      });
    } finally {
      setComprando(false);
    }
  };

  // Falha de rede não pode deixar um buraco no topo do Painel: a tela inteira
  // funciona sem este bloco, então ele simplesmente não aparece.
  if (erro || !estado) return null;

  return (
    <section className="reveal" data-testid="painel-progresso">
      {estado.enem && (
        <div className="mb-4 flex items-center gap-2 text-xs text-white/50" data-testid="progresso-enem">
          <CalendarDays className="h-3.5 w-3.5" />
          Faltam <strong className="font-semibold text-white/80">{estado.enem.dias} dias</strong> para o
          {estado.enem.fase === 1 ? " primeiro" : " segundo"} dia do ENEM.
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-3">
        <Ofensiva
          dados={estado.ofensiva}
          aoComprarCongelador={comprarCongelador}
          comprando={comprando}
        />
        <Nivel dados={estado.nivel} />
        <Liga dados={estado.liga} />
      </div>

      <Missoes missoes={estado.missoes} aoResgatar={resgatar} resgatando={resgatando} />
    </section>
  );
}
