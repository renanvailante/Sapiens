import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import { Dialog, DialogContent } from "./ui/dialog";
import Mentis from "./Mentis";
import { useContextoMentisAtual } from "../lib/mentisContexto";
import { Zap, Send, Loader2, MessageCircle, Sparkles, HelpCircle, ArrowRight } from "lucide-react";

/**
 * "Pedir isto à Mentis" — a ponte entre um card de dificuldade (Painel,
 * perfil, redação) e o chat, sem nunca gastar Spark do aluno por acidente.
 *
 * A regra de produto que este componente existe para cumprir: **a mensagem
 * pré-pronta NUNCA sai sozinha**. O clique no card abre esta janela com o
 * texto já escrito e visível; o que acontece depois é sempre uma segunda
 * decisão, explicitamente precificada:
 *
 *  - sem sessão aberta → "Abrir chat · N Sparks" (o mesmo preço de abrir
 *    qualquer sessão, `SESSAO_COST`). Abrir NÃO envia: depois de aberta, a
 *    janela mostra o botão de enviar, e o aluno decide de novo.
 *  - com sessão aberta → "Enviar · M Sparks" (o mesmo preço de qualquer
 *    mensagem, `MENSAGEM_COST`).
 *
 * Os dois preços vêm do servidor (`custo_sessao`/`custo_mensagem` em
 * `GET /mentis/sessao`); as constantes daqui são só o que aparece enquanto a
 * primeira leitura não chegou. Quem cobra é `mentis_routes.py`, sempre.
 */

const CUSTO_SESSAO_PADRAO = 70;
const CUSTO_MENSAGEM_PADRAO = 10;
const MAX_CHARS = 600;

/** Os dois pedidos que um card de dificuldade sabe formular sozinho. O texto
 *  é montado aqui, e não no card, para que a Mentis receba sempre a mesma
 *  forma de pergunta venha de onde vier o clique. */
export function pedidosPadrao(assunto, evidencia) {
  const contexto = evidencia ? ` (${evidencia})` : "";
  return [
    {
      id: "explicar",
      rotulo: "Explicar meu erro",
      icone: HelpCircle,
      texto:
        `Explique por que eu erro em "${assunto}"${contexto}. ` +
        "Quero entender o passo do raciocínio em que eu escorrego e o que fazer para não repetir.",
    },
    {
      id: "questoes",
      rotulo: "Treinar com questões",
      icone: Sparkles,
      texto:
        `Quero treinar "${assunto}"${contexto}. ` +
        "Monte questões nesse ponto, da mais simples para a mais difícil, e me diga o que cada erro revelaria.",
    },
  ];
}

export default function MentisPedido({
  aberto,
  onFechar,
  assunto,
  evidencia,
  pedidos,
  onSaldo,
  testid = "mentis-pedido",
}) {
  const nav = useNavigate();
  const contextoTela = useContextoMentisAtual();
  const opcoes = pedidos?.length ? pedidos : pedidosPadrao(assunto, evidencia);

  const [escolha, setEscolha] = useState(opcoes[0].id);
  const [texto, setTexto] = useState(opcoes[0].texto);
  const [sessao, setSessao] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [abrindo, setAbrindo] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);

  const custoSessao = sessao?.custo_sessao ?? CUSTO_SESSAO_PADRAO;
  const custoMensagem = sessao?.custo_mensagem ?? CUSTO_MENSAGEM_PADRAO;
  const saldo = sessao?.sparks_balance ?? null;
  const ativa = !!sessao?.ativa;

  // Ler a sessão é de graça (`GET /mentis/sessao` não cobra nada) e só
  // acontece quando o aluno abre esta janela — nenhum card paga essa leitura
  // por estar na tela.
  useEffect(() => {
    if (!aberto) return undefined;
    let vivo = true;
    setCarregando(true);
    setErro(null);
    api
      .get("/mentis/sessao")
      .then(({ data }) => {
        if (!vivo) return;
        setSessao(data);
        if (typeof data.sparks_balance === "number") onSaldo?.(data.sparks_balance);
      })
      .catch((e) => { if (vivo) setErro(errMsg(e, "Não foi possível falar com a Mentis agora.")); })
      .finally(() => { if (vivo) setCarregando(false); });
    return () => { vivo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aberto]);

  const trocarPedido = useCallback((opcao) => {
    setEscolha(opcao.id);
    setTexto(opcao.texto);
  }, []);

  const abrirSessao = async () => {
    setAbrindo(true);
    setErro(null);
    try {
      const { data } = await api.post("/mentis/sessao");
      setSessao({ ...data, ativa: true });
      if (typeof data.sparks_balance === "number") onSaldo?.(data.sparks_balance);
    } catch (e) {
      setErro(errMsg(e, "Não foi possível abrir a sessão agora."));
    } finally {
      setAbrindo(false);
    }
  };

  const enviar = async () => {
    const pergunta = texto.trim();
    if (!pergunta) return;
    setEnviando(true);
    setErro(null);
    try {
      const { data } = await api.post("/mentis/sessao/mensagem", {
        texto: pergunta,
        origem: "card",
        contexto_tela: contextoTela || undefined,
      });
      if (typeof data.sparks_balance === "number") onSaldo?.(data.sparks_balance);
      onFechar?.();
      // A resposta já está na sessão: o chat cheio a mostra inteira, com o
      // histórico em volta — em vez de repetir aqui uma segunda janela de
      // conversa que sairia de sincronia com a de verdade.
      nav("/mentis");
    } catch (e) {
      setErro(errMsg(e, "A Mentis não conseguiu responder agora."));
      if (e?.response?.status === 409) setSessao((s) => ({ ...s, ativa: false }));
    } finally {
      setEnviando(false);
    }
  };

  const custoAgora = ativa ? custoMensagem : custoSessao;
  const semSaldo = saldo != null && saldo < custoAgora;
  const ocupado = carregando || abrindo || enviando;

  return (
    <Dialog open={!!aberto} onOpenChange={(v) => { if (!v) onFechar?.(); }}>
      <DialogContent className="rounded-2xl max-w-lg max-h-[88dvh] overflow-y-auto" data-testid={testid}>
        <div className="flex items-start gap-3">
          <Mentis className="w-11 h-11 shrink-0" estado={ocupado ? "analise" : "neutra"} />
          <div className="min-w-0">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-sapiens-accentDeep">
              Pedir à Mentis
            </div>
            <div className="font-display text-xl font-bold tracking-tight text-zinc-950 leading-snug">
              {assunto}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {opcoes.map((o) => (
            <button
              key={o.id}
              type="button"
              onClick={() => trocarPedido(o)}
              className={`pill inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-xs font-medium transition ${
                escolha === o.id
                  ? "border-sapiens-accent bg-sapiens-accentSoft text-sapiens-navy"
                  : "border-zinc-200 text-zinc-500 hover:border-zinc-300"
              }`}
              data-testid={`${testid}-opcao-${o.id}`}
            >
              <o.icone className="w-3.5 h-3.5" /> {o.rotulo}
            </button>
          ))}
        </div>

        <div>
          <textarea
            value={texto}
            onChange={(e) => setTexto(e.target.value.slice(0, MAX_CHARS))}
            rows={4}
            className="w-full resize-none rounded-xl px-3.5 py-3 text-sm leading-relaxed outline-none"
            data-testid={`${testid}-texto`}
          />
          <div className="mt-1 flex items-center justify-between text-[10px] text-white/35">
            <span>Você pode editar antes de enviar.</span>
            <span className="font-mono-alt">{texto.length}/{MAX_CHARS}</span>
          </div>
        </div>

        {erro && (
          <p className="text-xs font-medium text-rose-600" data-testid={`${testid}-erro`}>{erro}</p>
        )}

        {carregando ? (
          <div className="flex items-center gap-2 text-sm text-zinc-500">
            <Loader2 className="w-4 h-4 animate-spin" /> Vendo se você já tem uma conversa aberta…
          </div>
        ) : semSaldo ? (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-sm text-amber-900">
              {ativa
                ? `Enviar custa ${custoMensagem} Sparks e você tem ${saldo}.`
                : `Abrir o chat custa ${custoSessao} Sparks e você tem ${saldo}.`}
            </p>
            <button
              type="button"
              onClick={() => { onFechar?.(); nav("/sparks"); }}
              className="pill btn-sapiens mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium"
              data-testid={`${testid}-sparks`}
            >
              <Zap className="w-3.5 h-3.5" /> Conseguir Sparks
            </button>
          </div>
        ) : ativa ? (
          <div>
            <button
              type="button"
              onClick={enviar}
              disabled={enviando || !texto.trim()}
              className="pill btn-sapiens w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-full text-sm font-medium disabled:opacity-50"
              data-testid={`${testid}-enviar`}
            >
              {enviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              {enviando ? "A Mentis está respondendo…" : `Enviar · ${custoMensagem} Sparks`}
            </button>
            <p className="mt-2 text-center text-[11px] text-zinc-500">
              Seu chat está aberto. Enviar custa o mesmo que qualquer mensagem — e leva você direto para a resposta.
            </p>
          </div>
        ) : (
          <div>
            <button
              type="button"
              onClick={abrirSessao}
              disabled={abrindo}
              className="pill btn-sapiens w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-full text-sm font-medium disabled:opacity-50"
              data-testid={`${testid}-abrir`}
            >
              {abrindo ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageCircle className="w-4 h-4" />}
              {abrindo ? "Lendo o seu histórico…" : `Abrir chat · ${custoSessao} Sparks`}
            </button>
            <p className="mt-2 text-center text-[11px] text-zinc-500">
              Abrir não envia nada: a sessão vale 24h e a mensagem acima só sai quando você mandar.
            </p>
          </div>
        )}

        <button
          type="button"
          onClick={() => { onFechar?.(); nav("/mentis"); }}
          className="inline-flex items-center justify-center gap-1.5 text-[11px] text-zinc-400 hover:text-zinc-200"
          data-testid={`${testid}-ver-chat`}
        >
          Ver o chat da Mentis <ArrowRight className="w-3 h-3" />
        </button>
      </DialogContent>
    </Dialog>
  );
}
