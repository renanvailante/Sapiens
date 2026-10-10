import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { X, Send, Zap, ArrowRight, Loader2 } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { EVENTO_PASSO, lerPassoAtual } from "../lib/trilhaDoDia";
import { dicaPara, marcarDicaVista } from "../lib/dicasDaMentis";
import { abrirPraticaDirigida } from "../lib/praticaDirigida";
import { useAuth } from "../lib/auth";
import { useContextoMentisAtual } from "../lib/mentisContexto";
import Mentis, { MentisPensando } from "./Mentis";
import Baloes, { BALOES_INICIAIS } from "./MentisBaloes";
import MentisAcao from "./MentisAcao";
import MentisAtalhos from "./MentisAtalhos";
import { ROTAS } from "../lib/rotas";

const CUSTO_MENSAGEM_PADRAO = 10;
const MAX_CHARS = 600;

/**
 * Ícone da Mentis sempre visível no canto inferior direito, em todo o app
 * logado. Abre o MESMO chat de `/mentis` (mesma sessão no servidor — este
 * widget só é outra janela sobre ela), então nunca aparece dobrado com a
 * página cheia: fica escondido enquanto o aluno já está em /mentis.
 *
 * DESDE 2026-10-09 ELA É A GUIA EM TODA TELA, não só a porta do chat:
 *
 *   · o botão é a própria Mentis (olhos, órbita, flutuando), e não um ícone
 *     de brilho genérico — a mesma personagem que fala no Hoje;
 *   · na primeira visita a cada área ela diz, num balão, o que se faz ali
 *     (`lib/dicasDaMentis.js`) — e some sozinha;
 *   · o painel abre com **"Seu próximo passo"** antes da conversa: o nó aceso
 *     da trilha do dia, que o Hoje publica (`trilhaDoDia.publicarPassoAtual`).
 *     De qualquer tela, um toque nela e um toque no botão levam ao próximo
 *     passo — de graça, porque navegar nunca custa Spark. É a garantia de que
 *     o aluno nunca fica sem saber para onde ir.
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
  const [passo, setPasso] = useState(lerPassoAtual);
  const [indo, setIndo] = useState(false);
  const [dica, setDica] = useState(null);

  // O passo aceso muda quando o Hoje recalcula a trilha (no mesmo aparelho).
  useEffect(() => {
    const reler = () => setPasso(lerPassoAtual());
    window.addEventListener(EVENTO_PASSO, reler);
    window.addEventListener("storage", reler);
    return () => {
      window.removeEventListener(EVENTO_PASSO, reler);
      window.removeEventListener("storage", reler);
    };
  }, []);

  // A dica da área: entra um instante depois da tela (para não competir com a
  // chegada dela), fica uns segundos e sai. Marcada como vista ao APARECER —
  // quem a viu e não fechou não precisa dela de novo amanhã.
  useEffect(() => {
    setDica(null);
    if (!user) return undefined;
    const d = dicaPara(location.pathname, location.search);
    if (!d) return undefined;
    const entra = setTimeout(() => {
      marcarDicaVista(d.rota);
      setDica(d);
    }, 1100);
    const sai = setTimeout(() => setDica(null), 13000);
    return () => { clearTimeout(entra); clearTimeout(sai); };
  }, [location.pathname, location.search, user]);

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
  // `/feed` é a única tela em sangria total, sem barra e com controles
  // próprios no rodapé: um ícone flutuante por cima dela cobre o conteúdo e
  // não tem o que oferecer que a tela já não ofereça.
  if (location.pathname === ROTAS.FOLHEAR) return null;
  // `/bem-vindo` é a única tela em que a Mentis já está presente NO conteúdo,
  // conduzindo o onboarding. O ícone flutuante ali seria ela oferecendo abrir
  // uma conversa consigo mesma, por cima da conversa em curso.
  if (location.pathname === "/bem-vindo") return null;

  // Leva ao próximo passo da trilha. Sem passo publicado (o aluno ainda não
  // abriu o Hoje neste aparelho hoje), o próximo passo É abrir a trilha.
  const irAoPasso = () => {
    setAberto(false);
    setDica(null);
    const acao = passo?.acao;
    if (!acao || passo?.estado === "resgatar") {
      navigate(ROTAS.HOJE);
      return;
    }
    if (acao.tipo === "dirigida") {
      setIndo(true);
      abrirPraticaDirigida({ api, navegar: navigate, processoId: acao.processoId, escolha: acao.escolha })
        .finally(() => setIndo(false));
      return;
    }
    navigate(acao.rota || ROTAS.HOJE);
  };
  const naTrilha = location.pathname === ROTAS.HOJE;

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
    <div className="flutuante-mentis" data-testid="mentis-widget">
      {aberto && (
        <div
          className="mb-3 flex w-[22rem] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-3xl border border-white/10 bg-[#060c18] shadow-2xl"
          // Altura fixa de 32rem (512px) mais o ícone e as folgas dava ~590px:
          // num iPhone SE/8 com as barras do Safari isso empurrava o cabeçalho
          // — e o X de fechar junto — para fora do topo da tela, e o painel é
          // `fixed`, então não havia como rolar até ele. `dvh` e não `vh`
          // porque no Safari `vh` ignora a barra de endereço.
          style={{ height: "min(32rem, calc(100dvh - 8.5rem))" }}
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

          {/* SEU PRÓXIMO PASSO — grátis, antes de qualquer conversa. No Hoje
              ele sai: lá a trilha inteira já está na tela. */}
          {!naTrilha && (
            <div className="border-b border-white/10 px-4 py-3" data-testid="mentis-widget-passo">
              <div className="secao-olho">Seu próximo passo</div>
              <div className="mt-1 flex items-center gap-3">
                <p className="min-w-0 flex-1 text-sm font-semibold leading-snug text-white">
                  {passo?.completo
                    ? "Sua trilha de hoje está completa."
                    : passo?.titulo || "Ver a sua trilha de hoje"}
                </p>
                <button
                  type="button"
                  onClick={irAoPasso}
                  disabled={indo}
                  className="pill btn-sapiens inline-flex shrink-0 items-center gap-1.5 rounded-full px-4 py-2 text-xs font-bold disabled:opacity-60"
                  data-testid="mentis-widget-ir-passo"
                >
                  {indo ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                  {passo?.titulo && !passo?.completo ? passo.cta || "Ir" : "Abrir"} <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}

          {!carregado ? (
            <div className="flex flex-1 items-center justify-center text-xs text-white/45">Procurando a Mentis…</div>
          ) : !ativa ? (
            // `overflow-y-auto`: com os atalhos, este painel passou a poder
            // ser mais alto que os 32rem do widget num aparelho baixo — sem a
            // rolagem, o botão de abrir sessão sairia por baixo sem volta.
            <div className="flex flex-1 flex-col items-center justify-center gap-3 overflow-y-auto px-6 py-4 text-center">
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
              {/* Levar o aluno a uma tela não exige sessão paga: quem só quer
                  chegar em algum lugar chega daqui mesmo, de graça. */}
              <div className="mt-3 w-full text-left">
                <MentisAtalhos compacto limite={6} />
              </div>
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
                        <MentisAcao acao={m.acao} />
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
                {mostrarBaloesIniciais && (
                  <div className="pt-1">
                    <MentisAtalhos compacto limite={6} />
                  </div>
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

      {/* A DICA DA ÁREA — o balão do Duolingo saindo da própria Mentis. */}
      {!aberto && dica && (
        <div className="dica-mentis mb-3" role="status" data-testid="mentis-dica">
          <button
            type="button"
            onClick={() => setDica(null)}
            className="dica-mentis-fechar"
            aria-label="Fechar dica"
          >
            <X className="h-3.5 w-3.5" />
          </button>
          <p className="pr-5 text-[13px] leading-relaxed text-white/85">{dica.texto}</p>
          {passo?.titulo && !passo?.completo && !naTrilha && (
            <button
              type="button"
              onClick={irAoPasso}
              className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-[#9FE9FF] hover:underline"
              data-testid="mentis-dica-passo"
            >
              Continuar a trilha <ArrowRight className="h-3 w-3" />
            </button>
          )}
        </div>
      )}

      <button
        type="button"
        onClick={() => { setDica(null); setAberto((v) => !v); }}
        className="mentis-botao"
        aria-label={aberto ? "Fechar a Mentis" : "Falar com a Mentis"}
        data-testid="mentis-widget-toggle"
        data-tour="mentis-widget"
      >
        {aberto ? (
          <X className="h-5 w-5 text-white" />
        ) : (
          <Mentis className="h-[60px] w-[60px]" estado={dica ? "falando" : "neutra"} olhar={-0.6} flutuar />
        )}
      </button>
    </div>
  );
}
