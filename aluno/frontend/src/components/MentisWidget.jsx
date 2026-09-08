import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { X, Send, Zap, Sparkles } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useContextoMentisAtual } from "../lib/mentisContexto";
import Mentis, { MentisPensando } from "./Mentis";
import Baloes, { BALOES_INICIAIS } from "./MentisBaloes";
import MentisAcaoQuestoes from "./MentisAcaoQuestoes";

const CUSTO_MENSAGEM_PADRAO = 10;
const MAX_CHARS = 600;

/**
 * Ícone da Mentis sempre visível no canto inferior direito, em todo o app
 * logado. Abre o MESMO chat de `/mentis` (mesma sessão no servidor — este
 * widget só é outra janela sobre ela), então nunca aparece dobrado com a
 * página cheia: fica escondido enquanto o aluno já está em /mentis.
 */
export default function MentisWidget() {
  const { user, loading } = useAuth() || {};
  const location = useLocation();
  const navigate = useNavigate();
  const contextoTela = useContextoMentisAtual();

  const [aberto, setAberto] = useState(false);
  const [sessao, setSessao] = useState(null);
  const [carregado, setCarregado] = useState(false);
  const [abrindo, setAbrindo] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState(null);
  const [saldo, setSaldo] = useState(null);
  const fimRef = useRef(null);
  const inputRef = useRef(null);

  const mensagens = sessao?.mensagens || [];
  const custoMensagem = sessao?.custo_mensagem ?? CUSTO_MENSAGEM_PADRAO;
  const ativa = !!sessao?.ativa;

  // Carrega a sessão (se houver) só quando o painel abre pela primeira vez —
  // não em toda página, pra não bater no backend em cada navegação do app.
  useEffect(() => {
    if (!aberto || carregado) return;
    api
      .get("/mentis/sessao")
      .then(({ data }) => {
        setSessao(data);
        if (typeof data.sparks_balance === "number") setSaldo(data.sparks_balance);
      })
      .catch((e) => setErro(errMsg(e, "Não foi possível falar com a Mentis agora.")))
      .finally(() => setCarregado(true));
  }, [aberto, carregado]);

  useEffect(() => {
    if (aberto) fimRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensagens.length, enviando, aberto]);

  if (loading || !user) return null;
  if (location.pathname === "/mentis") return null;

  const abrirSessao = async () => {
    setAbrindo(true);
    setErro(null);
    try {
      const { data } = await api.post("/mentis/sessao");
      setSessao({ ...data, ativa: true });
      if (typeof data.sparks_balance === "number") setSaldo(data.sparks_balance);
    } catch (e) {
      setErro(errMsg(e, "Não foi possível abrir a sessão agora."));
    } finally {
      setAbrindo(false);
    }
  };

  const enviarMensagem = async (pergunta, origem) => {
    if (!pergunta || enviando) return;
    if (saldo != null && saldo < custoMensagem) return;
    setEnviando(true);
    setErro(null);
    const provisoria = { papel: "aluno", texto: pergunta, em: new Date().toISOString(), provisoria: true };
    setSessao((s) => ({ ...s, mensagens: [...(s.mensagens || []), provisoria] }));
    setTexto("");
    try {
      const { data } = await api.post("/mentis/sessao/mensagem", {
        texto: pergunta,
        origem,
        contexto_tela: contextoTela || undefined,
      });
      setSessao((s) => ({
        ...s,
        mensagens: [...(s.mensagens || []).filter((m) => !m.provisoria), ...data.mensagens],
      }));
      if (typeof data.sparks_balance === "number") setSaldo(data.sparks_balance);
    } catch (err) {
      setSessao((s) => ({ ...s, mensagens: (s.mensagens || []).filter((m) => !m.provisoria) }));
      setTexto(pergunta);
      setErro(errMsg(err, "A Mentis não conseguiu responder agora."));
      if (err?.response?.status === 409) setSessao((s) => ({ ...s, ativa: false }));
    } finally {
      setEnviando(false);
    }
  };

  const enviar = (e) => {
    e?.preventDefault();
    enviarMensagem(texto.trim(), "digitado");
  };

  const clicarBalao = (balao) => {
    if (enviando) return;
    if (balao.tipo === "completar") {
      const base = balao.texto.replace(/\.{3}\s*$/, "").trimEnd();
      setTexto(`${base} `);
      inputRef.current?.focus();
      return;
    }
    enviarMensagem(balao.texto, "balao");
  };

  const semSaldoMensagem = saldo != null && saldo < custoMensagem;
  const ultimaMsg = mensagens[mensagens.length - 1];
  const mostrarBaloesIniciais = mensagens.length <= 1 && !enviando;
  const baloesContextuais =
    !mostrarBaloesIniciais && !enviando && ultimaMsg?.papel === "mentis" && !ultimaMsg.provisoria
      ? ultimaMsg.sugestoes || []
      : [];
  const baloesAtuais = mostrarBaloesIniciais ? BALOES_INICIAIS : baloesContextuais;

  return (
    <div className="fixed bottom-5 right-5 z-50" data-testid="mentis-widget">
      {aberto && (
        <div
          className="mb-3 flex h-[32rem] w-[22rem] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-3xl border border-white/10 bg-[#060c18] shadow-2xl"
          data-testid="mentis-widget-painel"
        >
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <div className="flex items-center gap-2">
              <Mentis className="w-7 h-7" variante="icone" estado={enviando ? "analise" : "neutra"} />
              <span className="font-display text-sm font-bold text-white">Mentis</span>
              {saldo != null && <span className="text-[11px] text-white/40">saldo {saldo}</span>}
            </div>
            <button
              type="button"
              onClick={() => setAberto(false)}
              className="rounded-full p-1.5 text-white/50 hover:bg-white/10 hover:text-white"
              data-testid="mentis-widget-fechar"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {!carregado ? (
            <div className="flex flex-1 items-center justify-center text-xs text-white/45">Procurando a Mentis…</div>
          ) : !ativa ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
              <Mentis className="w-14 h-14" estado="neutra" />
              <p className="text-xs leading-relaxed text-white/55">
                Abra uma sessão para conversar — ela já entra sabendo onde você mais escorrega.
              </p>
              {erro && <p className="text-xs text-rose-300">{erro}</p>}
              <button
                onClick={abrirSessao}
                disabled={abrindo}
                className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-xs disabled:opacity-50"
                data-testid="mentis-widget-abrir"
              >
                <Zap className="w-3.5 h-3.5" /> {abrindo ? "Lendo seu histórico…" : "Abrir sessão"}
              </button>
              <button
                type="button"
                onClick={() => navigate("/mentis")}
                className="text-[11px] text-white/40 hover:text-white/60 hover:underline"
              >
                Ver tela completa
              </button>
            </div>
          ) : (
            <>
              <div className="flex-1 space-y-3 overflow-y-auto px-3.5 py-3" data-testid="mentis-widget-conversa">
                {mensagens.map((m, i) => (
                  <div key={i} className={`flex gap-2 ${m.papel === "aluno" ? "justify-end" : "justify-start"}`}>
                    {m.papel !== "aluno" && (
                      <Mentis className="mt-0.5 h-5 w-5 shrink-0" variante="icone" animada={false} />
                    )}
                    <div className={`max-w-[82%] ${m.papel === "aluno" ? "" : "flex flex-col items-start"}`}>
                      <div
                        className={`rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed whitespace-pre-line ${
                          m.papel === "aluno" ? "bolha-aluno" : "bolha-mentis"
                        } ${m.provisoria ? "opacity-60" : ""}`}
                      >
                        {m.texto}
                      </div>
                      {m.papel === "mentis" && i === mensagens.length - 1 && (
                        <MentisAcaoQuestoes acao={m.acao} />
                      )}
                    </div>
                  </div>
                ))}
                {enviando && (
                  <div className="flex items-center gap-2">
                    <Mentis className="h-5 w-5 shrink-0" variante="icone" estado="analise" />
                    <div className="bolha-mentis rounded-2xl px-3.5 py-2.5">
                      <MentisPensando ativo={enviando} />
                    </div>
                  </div>
                )}
                {baloesAtuais.length > 0 && (
                  <Baloes itens={baloesAtuais} aoClicar={clicarBalao} enviando={enviando} semSaldo={semSaldoMensagem} />
                )}
                <div ref={fimRef} />
              </div>

              {erro && <div className="px-3.5 pb-1 text-[11px] text-rose-300">{erro}</div>}

              <form onSubmit={enviar} className="border-t border-white/10 p-2.5">
                <div className="flex items-end gap-1.5">
                  <textarea
                    ref={inputRef}
                    value={texto}
                    onChange={(e) => setTexto(e.target.value.slice(0, MAX_CHARS))}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) enviar(e); }}
                    rows={1}
                    placeholder={semSaldoMensagem ? `Precisa de ${custoMensagem} Sparks…` : "Pergunte algo…"}
                    disabled={semSaldoMensagem}
                    className="flex-1 resize-none rounded-xl px-3 py-2 text-[13px] outline-none disabled:opacity-50"
                    data-testid="mentis-widget-input"
                  />
                  <button
                    type="submit"
                    disabled={enviando || !texto.trim() || semSaldoMensagem}
                    className="pill btn-sapiens inline-flex shrink-0 items-center gap-1 rounded-full px-3 py-2 text-xs disabled:opacity-40"
                    data-testid="mentis-widget-enviar"
                  >
                    <Send className="h-3.5 w-3.5" />
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      )}

      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        className="flex h-14 w-14 items-center justify-center rounded-full shadow-xl transition hover:scale-105"
        style={{ background: "radial-gradient(circle at 35% 30%, #4FD9FF, #123A78)" }}
        aria-label={aberto ? "Fechar chat da Mentis" : "Conversar com a Mentis"}
        data-testid="mentis-widget-toggle"
      >
        {aberto ? <X className="h-5 w-5 text-white" /> : <Sparkles className="h-5 w-5 text-white" />}
      </button>
    </div>
  );
}
