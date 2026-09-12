import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import Mentis, { MentisPensando } from "../components/Mentis";
import Baloes, { BALOES_INICIAIS } from "../components/MentisBaloes";
import MentisAcao from "../components/MentisAcao";
import { useContextoMentisAtual } from "../lib/mentisContexto";
import { Send, Zap, Clock, Target, TrendingUp, AlertCircle } from "lucide-react";

/**
 * Chat com a Mentis — a única tela do produto onde o aluno CONVERSA com a
 * plataforma em vez de responder a ela.
 *
 * O que a diferencia de um chat genérico: antes da primeira palavra, a Mentis
 * já recebeu o dossiê real do aluno (os mesmos números de `/diagnostico` —
 * processos fracos, domínios fracos, padrões de erro catalogados, sempre com
 * a amostra ao lado). É por isso que abrir a sessão custa Sparks: as 70
 * pagam a leitura do histórico e 24h de acesso, não uma mensagem.
 *
 * Preços vêm do servidor (`custo_sessao` / `custo_mensagem`) — as constantes
 * daqui são só o valor exibido enquanto a primeira resposta não chegou; quem
 * cobra de fato é `mentis_routes.py`.
 */

const CUSTO_SESSAO_PADRAO = 70;
const CUSTO_MENSAGEM_PADRAO = 10;
const MAX_CHARS = 600;

function formatarExpiracao(iso) {
  if (!iso) return null;
  const restante = new Date(iso).getTime() - Date.now();
  if (restante <= 0) return "expirada";
  const horas = Math.floor(restante / 3_600_000);
  const minutos = Math.floor((restante % 3_600_000) / 60_000);
  return horas > 0 ? `${horas}h${String(minutos).padStart(2, "0")}` : `${minutos}min`;
}

/** Painel do dossiê: o que a Mentis sabe, em números, à vista do aluno.
 *  Existe para a conversa não parecer mágica — o aluno vê a mesma medida que
 *  o modelo recebeu, e pode conferir de onde saiu cada afirmação. */
function Dossie({ dossie }) {
  const fracos = dossie?.fracos || [];
  const fortes = dossie?.fortes || [];
  const padroes = dossie?.padroes || [];

  return (
    <aside className="card-sapiens rounded-2xl p-5 h-fit lg:sticky lg:top-24" data-testid="mentis-dossie">
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-white/40">
        O que ela leu de você
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="font-display text-3xl font-extrabold tracking-tighter text-white">
          {dossie?.total_respostas ?? 0}
        </span>
        <span className="text-xs text-white/50">questões respondidas</span>
      </div>

      {fracos.length > 0 && (
        <div className="mt-5">
          <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-rose-300">
            <Target className="w-3 h-3" /> Onde você mais escorrega
          </div>
          <ul className="mt-2 space-y-1.5">
            {fracos.map((f) => (
              <li key={f.id} className="text-xs text-white/70 flex items-baseline justify-between gap-2">
                <span className="truncate">{f.nome}</span>
                <span className="font-mono-alt shrink-0 text-white/40">
                  {f.acertos}/{f.respondidas}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {fortes.length > 0 && (
        <div className="mt-5">
          <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-emerald-300">
            <TrendingUp className="w-3 h-3" /> Onde você já está firme
          </div>
          <ul className="mt-2 space-y-1.5">
            {fortes.map((f) => (
              <li key={f.id} className="text-xs text-white/70 flex items-baseline justify-between gap-2">
                <span className="truncate">{f.nome}</span>
                <span className="font-mono-alt shrink-0 text-white/40">
                  {f.acertos}/{f.respondidas}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {padroes.length > 0 && (
        <div className="mt-5">
          <div className="text-[11px] font-bold uppercase tracking-wide text-white/50">
            Padrões de erro catalogados
          </div>
          {padroes.map((p, i) => (
            <div key={i} className="mt-2 text-xs text-white/70 leading-relaxed">
              <span className="text-[#7FD8FF]">{p.erro_nome}</span> em {p.processo_nome}.
            </div>
          ))}
        </div>
      )}

      {fracos.length === 0 && fortes.length === 0 && (
        <p className="mt-4 text-xs text-white/50 leading-relaxed">
          Você ainda não respondeu questões suficientes para a Mentis afirmar um ponto forte
          ou fraco sem chutar. Ela vai dizer isso com todas as letras — e ajudar mesmo assim.
        </p>
      )}
    </aside>
  );
}

/** Tela de entrada: o que a sessão é, quanto custa, o que ela não faz. */
function Portao({ custoSessao, custoMensagem, saldo, abrindo, erro, aoAbrir }) {
  const semSaldo = saldo != null && saldo < custoSessao;
  return (
    <div className="max-w-2xl mx-auto">
      <div className="card-sapiens rounded-3xl p-8 md:p-10 text-center" data-testid="mentis-portao">
        <div className="flex justify-center">
          <Mentis className="w-28 h-28" estado="neutra" title="Mentis" />
        </div>
        <h1 className="mt-6 font-display text-3xl md:text-4xl font-extrabold tracking-tighter text-white">
          Converse com a Mentis.
        </h1>
        <p className="mt-3 text-sm md:text-base text-white/60 leading-relaxed max-w-lg mx-auto">
          Ela não é um chat genérico. Antes da primeira palavra, a Mentis lê o seu histórico
          inteiro: em quais processos você erra mais, com que amostra, e qual padrão de erro
          está catalogado por trás disso. Você pergunta; ela responde sobre <em>você</em>.
        </p>

        <div className="mt-7 grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
          <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
            <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-white/40">
              <Zap className="w-3 h-3 text-amber-400" /> Abrir a sessão
            </div>
            <div className="mt-1 font-display text-xl font-bold text-white">{custoSessao} Sparks</div>
            <div className="text-xs text-white/50">vale 24h — entre e saia à vontade</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
            <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-white/40">
              <Send className="w-3 h-3 text-[#4FD9FF]" /> Cada mensagem
            </div>
            <div className="mt-1 font-display text-xl font-bold text-white">{custoMensagem} Sparks</div>
            <div className="text-xs text-white/50">cobrada só quando ela responde</div>
          </div>
        </div>

        {erro && (
          <p className="mt-5 text-sm font-medium text-rose-300" data-testid="mentis-portao-erro">{erro}</p>
        )}

        {semSaldo ? (
          <div className="mt-7">
            <p className="text-sm text-white/60">
              Você tem {saldo} Sparks — faltam {custoSessao - saldo} para abrir a sessão.
            </p>
            <Link
              to="/sparks"
              className="pill btn-sapiens mt-4 inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm"
              data-testid="mentis-ir-sparks"
            >
              <Zap className="w-4 h-4" /> Conseguir Sparks
            </Link>
          </div>
        ) : (
          <button
            onClick={aoAbrir}
            disabled={abrindo}
            className="pill btn-sapiens mt-7 inline-flex items-center gap-2 px-7 py-3.5 rounded-full text-sm disabled:opacity-50"
            data-testid="mentis-abrir"
          >
            {abrindo ? "Lendo o seu histórico…" : `Abrir sessão · ${custoSessao} Sparks`}
          </button>
        )}

        <p className="mt-5 text-[11px] text-white/35 leading-relaxed max-w-md mx-auto">
          A Mentis fala só sobre o que foi medido nas suas respostas. Ela não entrega gabarito
          de questão que você ainda não respondeu, e diz quando não tem dado suficiente em vez
          de inventar um diagnóstico.
        </p>
      </div>
    </div>
  );
}

export default function MentisChat() {
  const [sessao, setSessao] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [abrindo, setAbrindo] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState(null);
  const [saldo, setSaldo] = useState(null);
  const fimRef = useRef(null);
  const inputRef = useRef(null);
  const contextoTela = useContextoMentisAtual();

  const custoSessao = sessao?.custo_sessao ?? CUSTO_SESSAO_PADRAO;
  const custoMensagem = sessao?.custo_mensagem ?? CUSTO_MENSAGEM_PADRAO;
  const ativa = !!sessao?.ativa;
  const mensagens = sessao?.mensagens || [];

  useEffect(() => {
    api
      .get("/mentis/sessao")
      .then(({ data }) => {
        setSessao(data);
        if (typeof data.sparks_balance === "number") setSaldo(data.sparks_balance);
      })
      .catch((e) => setErro(errMsg(e, "Não foi possível falar com a Mentis agora.")))
      .finally(() => setCarregando(false));
  }, []);

  // Rolar para a última fala sempre que a conversa cresce — sem isso o aluno
  // recebe a resposta fora da tela e acha que nada aconteceu.
  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensagens.length, enviando]);

  const abrir = async () => {
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
    // Otimista: a pergunta do aluno aparece na hora. Se a resposta falhar, ela
    // é removida junto com o erro — nada de pergunta órfã na conversa.
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
      const msg = errMsg(err, "A Mentis não conseguiu responder agora.");
      setErro(msg);
      if (err?.response?.status === 409) setSessao((s) => ({ ...s, ativa: false }));
    } finally {
      setEnviando(false);
    }
  };

  const enviar = (e) => {
    e?.preventDefault();
    enviarMensagem(texto.trim(), "digitado");
  };

  // Balão "enviar": manda na hora, como se o aluno tivesse digitado — mesmo
  // fluxo, mesma cobrança. Balão "completar": só preenche o campo, com o
  // "..." final removido, e devolve o foco para o aluno terminar a frase.
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

  if (carregando) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="flex flex-col items-center justify-center py-28 gap-4">
          <Mentis className="w-16 h-16" estado="analise" />
          <div className="text-sm text-white/50">Procurando a Mentis…</div>
        </div>
      </div>
    );
  }

  if (!ativa) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="px-6 md:px-10 py-12">
          <Portao
            custoSessao={custoSessao}
            custoMensagem={custoMensagem}
            saldo={saldo}
            abrindo={abrindo}
            erro={erro}
            aoAbrir={abrir}
          />
        </div>
      </div>
    );
  }

  const semSaldoMensagem = saldo != null && saldo < custoMensagem;

  // Balões a mostrar agora: os fixos de abertura enquanto só existe a
  // mensagem de boas-vindas, ou os contextuais que vieram junto da última
  // resposta da Mentis. Nunca os dois ao mesmo tempo, nunca durante o envio.
  const ultimaMsg = mensagens[mensagens.length - 1];
  const mostrarBaloesIniciais = mensagens.length <= 1 && !enviando;
  const baloesContextuais =
    !mostrarBaloesIniciais && !enviando && ultimaMsg?.papel === "mentis" && !ultimaMsg.provisoria
      ? ultimaMsg.sugestoes || []
      : [];
  const baloesAtuais = mostrarBaloesIniciais ? BALOES_INICIAIS : baloesContextuais;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-6xl mx-auto px-4 md:px-10 py-8 md:py-12">
        <div className="flex items-center gap-3 mb-6">
          <Mentis className="w-12 h-12 shrink-0" estado={enviando ? "analise" : "neutra"} title="Mentis" />
          <div className="min-w-0">
            <h1 className="font-display text-2xl md:text-3xl font-extrabold tracking-tighter text-white">
              Mentis
            </h1>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-white/45">
              <span className="inline-flex items-center gap-1">
                <Clock className="w-3 h-3" /> sessão termina em {formatarExpiracao(sessao.expira_em)}
              </span>
              <span className="inline-flex items-center gap-1">
                <Zap className="w-3 h-3 text-amber-400" /> {custoMensagem} Sparks por mensagem
              </span>
              {saldo != null && <span>saldo {saldo}</span>}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_18rem] gap-5">
          <div className="card-sapiens rounded-2xl flex flex-col min-h-[60dvh]">
            <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4" data-testid="mentis-conversa">
              {mensagens.map((m, i) => (
                <div
                  key={i}
                  className={`flex gap-2.5 ${m.papel === "aluno" ? "justify-end" : "justify-start"}`}
                >
                  {m.papel !== "aluno" && (
                    <Mentis className="w-7 h-7 shrink-0 mt-0.5" variante="icone" animada={false} />
                  )}
                  <div className={`max-w-[85%] ${m.papel === "aluno" ? "" : "flex flex-col items-start"}`}>
                    <div
                      className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-line ${
                        m.papel === "aluno" ? "bolha-aluno" : "bolha-mentis"
                      } ${m.provisoria ? "opacity-60" : ""}`}
                      data-testid={`mentis-msg-${m.papel}`}
                    >
                      {m.texto}
                    </div>
                    {m.papel === "mentis" && i === mensagens.length - 1 && (
                      <MentisAcao acao={m.acao} />
                    )}
                  </div>
                </div>
              ))}
              {enviando && (
                <div className="flex gap-2.5 items-center">
                  <Mentis className="w-7 h-7 shrink-0" variante="icone" estado="analise" />
                  <div className="bolha-mentis rounded-2xl px-4 py-3">
                    <MentisPensando ativo={enviando} />
                  </div>
                </div>
              )}
              {baloesAtuais.length > 0 && (
                <Baloes
                  itens={baloesAtuais}
                  aoClicar={clicarBalao}
                  enviando={enviando}
                  semSaldo={semSaldoMensagem}
                />
              )}
              <div ref={fimRef} />
            </div>

            {erro && (
              <div className="mx-4 md:mx-6 mb-2 flex items-start gap-2 rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-700" data-testid="mentis-erro">
                <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>{erro}</span>
              </div>
            )}

            <form onSubmit={enviar} className="border-t border-white/10 p-3 md:p-4">
              <div className="flex items-end gap-2">
                <textarea
                  ref={inputRef}
                  value={texto}
                  onChange={(e) => setTexto(e.target.value.slice(0, MAX_CHARS))}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) enviar(e);
                  }}
                  rows={2}
                  placeholder={
                    semSaldoMensagem
                      ? `Você precisa de ${custoMensagem} Sparks para enviar.`
                      : "Pergunte por que você erra o que erra…"
                  }
                  disabled={semSaldoMensagem}
                  className="flex-1 resize-none rounded-xl px-3.5 py-2.5 text-sm outline-none disabled:opacity-50"
                  data-testid="mentis-input"
                />
                <button
                  type="submit"
                  disabled={enviando || !texto.trim() || semSaldoMensagem}
                  className="pill btn-sapiens shrink-0 inline-flex items-center gap-2 px-4 py-2.5 rounded-full text-sm disabled:opacity-40"
                  data-testid="mentis-enviar"
                >
                  <Send className="w-4 h-4" />
                  <span className="hidden sm:inline">{custoMensagem}</span>
                </button>
              </div>
              <div className="mt-1.5 flex items-center justify-between text-[10px] text-white/30">
                <span>Enter envia · Shift+Enter quebra linha</span>
                <span className="font-mono-alt">{texto.length}/{MAX_CHARS}</span>
              </div>
              {semSaldoMensagem && (
                <Link to="/sparks" className="mt-2 inline-flex items-center gap-1.5 text-xs text-[#7FD8FF] hover:underline">
                  <Zap className="w-3 h-3" /> Conseguir mais Sparks
                </Link>
              )}
            </form>
          </div>

          <Dossie dossie={sessao.dossie} />
        </div>
      </div>
    </div>
  );
}
