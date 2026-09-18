import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import Nav, { avisarSparksMudou } from "../components/Nav";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { tempoRelativo } from "./Comunidade";
import {
  ArrowLeft, ArrowUp, CheckCircle2, Flag, Loader2, Sparkles, MessageCircle, Send,
} from "lucide-react";

/**
 * Uma dúvida e suas respostas.
 *
 * Duas coisas acontecem aqui e em nenhum outro lugar do produto: um aluno gera
 * Sparks para outro (marcando a resposta que resolveu) e um aluno pode tirar o
 * conteúdo de outro do ar (reportando). As duas têm trava no servidor; a tela
 * só precisa não mentir sobre elas — por isso o botão de marcar só aparece
 * para o autor da dúvida, e o de reportar nunca mostra quantos reportes já
 * existem (viraria um placar de "quantos faltam para derrubar").
 */

function Voto({ tipo, alvoId, votos, jaVotou, ehMeu, aoVotar }) {
  const [enviando, setEnviando] = useState(false);
  const bloqueado = jaVotou || ehMeu || enviando;

  const votar = async () => {
    if (bloqueado) return;
    setEnviando(true);
    try {
      await api.post(`/comunidade/${tipo}/${alvoId}/voto`);
      aoVotar();
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível votar."));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <button
      onClick={votar}
      disabled={bloqueado}
      title={ehMeu ? "Você não vota no próprio conteúdo" : jaVotou ? "Você já votou" : "Isto me ajudou"}
      className={`pill inline-flex shrink-0 flex-col items-center gap-0.5 rounded-xl border px-2.5 py-1.5 transition-colors ${
        jaVotou
          ? "border-sapiens-accent/50 bg-sapiens-accent/20 text-white"
          : "border-white/10 bg-white/5 text-white/50 hover:text-white disabled:opacity-40"
      }`}
      data-testid={`voto-${alvoId}`}
    >
      <ArrowUp className="h-3.5 w-3.5" />
      <span className="text-[11px] tabular-nums">{votos}</span>
    </button>
  );
}

function Reportar({ tipo, alvoId }) {
  const [enviando, setEnviando] = useState(false);

  const reportar = async () => {
    // eslint-disable-next-line no-alert
    const motivo = window.prompt("O que há de errado com esta publicação?");
    if (motivo === null) return;
    setEnviando(true);
    try {
      await api.post(`/comunidade/${tipo}/${alvoId}/reportar`, { motivo });
      toast.success("Obrigado. A equipe vai olhar.");
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível reportar."));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <button
      onClick={reportar}
      disabled={enviando}
      className="inline-flex items-center gap-1 text-xs text-white/30 hover:text-white/70"
      data-testid={`reportar-${alvoId}`}
    >
      <Flag className="h-3 w-3" /> Reportar
    </button>
  );
}

export default function ComunidadeDuvida() {
  const { duvidaId } = useParams();
  const { user } = useAuth();
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [resposta, setResposta] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [destacando, setDestacando] = useState(false);

  useDeclararContextoMentis("Lendo uma dúvida da comunidade.");

  const carregar = useCallback(() => {
    api
      .get(`/comunidade/duvidas/${duvidaId}`)
      .then(({ data }) => setDados(data))
      .catch(() => setDados(null))
      .finally(() => setCarregando(false));
  }, [duvidaId]);

  useEffect(carregar, [carregar]);

  const responder = async (e) => {
    e.preventDefault();
    if (resposta.trim().length < 5 || enviando) return;
    setEnviando(true);
    try {
      await api.post(`/comunidade/duvidas/${duvidaId}/respostas`, { corpo: resposta.trim() });
      setResposta("");
      toast.success("Resposta publicada. Se ela resolver, você ganha Sparks.");
      carregar();
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível responder agora."));
    } finally {
      setEnviando(false);
    }
  };

  const marcarMelhor = async (respostaId) => {
    try {
      const { data } = await api.post(`/comunidade/duvidas/${duvidaId}/melhor/${respostaId}`);
      toast.success(
        data.limite_diario_atingido
          ? "Marcada! Quem respondeu já bateu o limite de Sparks do dia, mas ganhou o XP."
          : `Marcada! ${data.sparks_para_o_autor} Sparks para quem te ajudou.`
      );
      carregar();
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível marcar."));
    }
  };

  const destacar = async () => {
    setDestacando(true);
    try {
      await api.post(`/comunidade/duvidas/${duvidaId}/destacar`);
      toast.success("Sua dúvida está no topo da área por 24 horas.");
      avisarSparksMudou();
      carregar();
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível destacar."), {
        action: err?.response?.status === 402
          ? { label: "Ver Sparks", onClick: () => { window.location.href = "/sparks"; } }
          : undefined,
      });
    } finally {
      setDestacando(false);
    }
  };

  if (carregando) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="mx-auto flex max-w-3xl items-center gap-2 px-6 py-12 text-white/50 md:px-10">
          <Loader2 className="h-4 w-4 animate-spin" /> Carregando…
        </div>
      </div>
    );
  }

  if (!dados) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="mx-auto max-w-3xl px-5 py-7 md:px-10 md:py-10">
          <p className="text-white/60">Esta dúvida não está disponível.</p>
          <Link to="/comunidade" className="mt-4 inline-flex items-center gap-1 text-sm text-[#7FD8FF] hover:underline">
            <ArrowLeft className="h-3.5 w-3.5" /> Voltar ao mural
          </Link>
        </div>
      </div>
    );
  }

  const { duvida, respostas, meus_votos } = dados;
  const souAutor = duvida.student_id === user?.user_id;
  const destacada = duvida.destacada_ate && duvida.destacada_ate > new Date().toISOString();

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-3xl px-5 py-7 md:px-10 md:py-10">
        <Link
          to="/comunidade"
          className="inline-flex items-center gap-1 text-sm text-white/50 hover:text-white"
          data-testid="voltar-mural"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Mural
        </Link>

        <article className="card-sapiens mt-5 rounded-2xl p-6" data-testid="duvida-detalhe">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono-alt rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-[10px] uppercase tracking-[0.18em] text-white/50">
              {duvida.area}
            </span>
            {duvida.resolvida && (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/25 bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-200">
                <CheckCircle2 className="h-3 w-3" /> Resolvida
              </span>
            )}
            {duvida.status === "em_revisao" && (
              <span className="rounded-full border border-amber-400/25 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-200">
                Em revisão — só você está vendo
              </span>
            )}
          </div>

          <div className="mt-3 flex gap-4">
            <Voto
              tipo="duvida"
              alvoId={duvida.duvida_id}
              votos={duvida.votos}
              jaVotou={meus_votos.includes(duvida.duvida_id)}
              ehMeu={souAutor}
              aoVotar={carregar}
            />
            <div className="min-w-0 flex-1">
              <h1 className="font-display text-2xl font-bold leading-snug tracking-tight text-zinc-950">
                {duvida.titulo}
              </h1>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-zinc-700">
                {duvida.corpo}
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-white/40">
                <span>{duvida.autor_nome}</span>
                <span>{tempoRelativo(duvida.created_at)}</span>
                {!souAutor && <Reportar tipo="duvida" alvoId={duvida.duvida_id} />}
                {souAutor && !destacada && (
                  <button
                    onClick={destacar}
                    disabled={destacando}
                    className="inline-flex items-center gap-1 text-xs text-amber-300 hover:text-amber-200"
                    data-testid="duvida-destacar"
                  >
                    {destacando ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
                    Destacar por 24h · 30 Sparks
                  </button>
                )}
                {destacada && (
                  <span className="inline-flex items-center gap-1 text-xs text-amber-300">
                    <Sparkles className="h-3 w-3" /> No topo da área
                  </span>
                )}
              </div>
            </div>
          </div>
        </article>

        <h2 className="mt-8 flex items-center gap-2 font-display text-xl font-bold tracking-tight text-white">
          <MessageCircle className="h-4 w-4" />
          {respostas.length} {respostas.length === 1 ? "resposta" : "respostas"}
        </h2>

        <div className="mt-4 space-y-3">
          {respostas.map((r) => (
            <div
              key={r.resposta_id}
              className={`card-sapiens rounded-2xl p-5 ${r.melhor ? "border-emerald-400/30" : ""}`}
              data-testid={`resposta-${r.resposta_id}`}
            >
              {r.melhor && (
                <div className="mb-2.5 inline-flex items-center gap-1 rounded-full border border-emerald-400/25 bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-200">
                  <CheckCircle2 className="h-3 w-3" /> Resolveu a dúvida
                </div>
              )}
              <div className="flex gap-4">
                <Voto
                  tipo="resposta"
                  alvoId={r.resposta_id}
                  votos={r.votos}
                  jaVotou={meus_votos.includes(r.resposta_id)}
                  ehMeu={r.student_id === user?.user_id}
                  aoVotar={carregar}
                />
                <div className="min-w-0 flex-1">
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-700">{r.corpo}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-white/40">
                    <span>{r.autor_nome}</span>
                    <span>{tempoRelativo(r.created_at)}</span>
                    {r.student_id !== user?.user_id && <Reportar tipo="resposta" alvoId={r.resposta_id} />}
                    {/* Só o autor da dúvida marca, e só enquanto nenhuma foi
                        marcada. A trava de verdade está no servidor. */}
                    {souAutor && !duvida.melhor_resposta_id && r.student_id !== user?.user_id && (
                      <button
                        onClick={() => marcarMelhor(r.resposta_id)}
                        className="inline-flex items-center gap-1 text-xs text-emerald-300 hover:text-emerald-200"
                        data-testid={`marcar-melhor-${r.resposta_id}`}
                      >
                        <CheckCircle2 className="h-3 w-3" /> Esta resolveu
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {duvida.status === "publicada" && (
          <form onSubmit={responder} className="card-sapiens mt-6 rounded-2xl p-5" data-testid="form-resposta">
            <label className="secao-olho">
              {souAutor ? "Acrescentar algo" : "Ajudar quem perguntou"}
            </label>
            <textarea
              value={resposta}
              onChange={(e) => setResposta(e.target.value)}
              rows={4}
              maxLength={4000}
              placeholder="Explique o raciocínio, não só a resposta — é isso que faz alguém marcar a sua."
              className="mt-1.5 w-full resize-y rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-base text-white placeholder:text-white/25 outline-none focus:border-sapiens-accent"
              data-testid="resposta-corpo"
            />
            <button
              type="submit"
              disabled={resposta.trim().length < 5 || enviando}
              className="pill btn-sapiens mt-3 inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium disabled:opacity-50"
              data-testid="resposta-enviar"
            >
              {enviando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Responder
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
