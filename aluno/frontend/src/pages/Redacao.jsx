import { useCallback, useEffect, useRef, useState } from "react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { toast } from "sonner";
import { useCarregamento } from "../hooks/useCarregamento";
import { COMPETENCIAS_REDACAO } from "../constants/redacao";
import CardDeMelhora from "../components/CardDeMelhora";
import { PenLine, Loader2, AlertTriangle, Sparkles, Zap } from "lucide-react";

const MIN_CARACTERES = 200;

// Espelham `redacao_routes.CORRECAO_COST` / `FEEDBACK_COST`. São só o valor
// exibido enquanto `GET /redacao/precos` não responde — quem cobra é o
// servidor, e é a resposta dele que manda na tela.
const CUSTO_CORRECAO_PADRAO = 120;
const CUSTO_FEEDBACK_PADRAO = 90;

// As cinco competências do ENEM, 0–200 cada. Os rótulos são os oficiais,
// encurtados para caber na tela; o corretor devolve só o `id`.
const COMPETENCIAS = COMPETENCIAS_REDACAO;

/** Uma chave por TENTATIVA de envio. Enquanto ela não muda, o servidor trata
 *  qualquer reenvio como retry da mesma correção e não cobra de novo — é o que
 *  protege o aluno do duplo clique, do retry de rede e do F5 no meio. */
function novaChave() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `red-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

function BarraCompetencia({ comp }) {
  const pontos = comp.nivel_pontos ?? 0;
  const pct = Math.round((pontos / 200) * 100);

  return (
    <div data-testid={`redacao-comp-${comp.id}`}>
      <div className="flex items-baseline justify-between text-sm mb-1">
        <span className="text-zinc-700">{COMPETENCIAS[comp.id] || comp.id}</span>
        <span className="font-mono-alt font-bold text-zinc-900">
          {pontos}
          <span className="text-zinc-400 font-normal">/200</span>
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-zinc-100 overflow-hidden">
        <div
          className={`h-full rounded-full ${comp.confirmado ? "bg-gradient-to-r from-sapiens-accentSoft to-sapiens-accent" : "bg-zinc-300"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {!comp.confirmado && (
        <div className="mt-1 text-[11px] text-amber-700">
          Estimativa — este critério não pôde ser confirmado automaticamente.
        </div>
      )}
      {comp.cap_aplicado != null && (
        <div className="mt-1 text-[11px] text-zinc-500">Teto aplicado por tangenciamento do tema.</div>
      )}
    </div>
  );
}

function Secao({ titulo, children }) {
  return (
    <div>
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-2">{titulo}</div>
      <div className="space-y-2 text-sm text-zinc-700 leading-relaxed">{children}</div>
    </div>
  );
}

function FeedbackMentis({ feedback }) {
  return (
    <div className="card-sapiens rounded-2xl p-6 md:p-8 space-y-6" data-testid="redacao-feedback">
      <div className="flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-sapiens-accent" />
        <span className="font-display text-lg font-bold tracking-tight text-zinc-950">
          A leitura da Mentis
        </span>
      </div>

      <p className="text-sm text-zinc-800 leading-relaxed">{feedback.abertura}</p>

      {feedback.o_que_ficou_bom?.length > 0 && (
        <Secao titulo="O que ficou bom">
          {feedback.o_que_ficou_bom.map((p, i) => <p key={i}>{p}</p>)}
        </Secao>
      )}

      {feedback.o_que_ficou_ruim?.length > 0 && (
        <Secao titulo="O que ficou ruim">
          {feedback.o_que_ficou_ruim.map((p, i) => <p key={i}>{p}</p>)}
        </Secao>
      )}

      {feedback.onde_melhorar?.length > 0 && (
        <Secao titulo="Onde e como melhorar">
          {feedback.onde_melhorar.map((item, i) => (
            <div key={i}>
              <div className="font-medium text-zinc-900">{item.titulo}</div>
              <p>{item.texto}</p>
            </div>
          ))}
        </Secao>
      )}

      {feedback.principais_perdas?.length > 0 && (
        <Secao titulo="O que mais derrubou a nota">
          <ul className="space-y-1.5">
            {feedback.principais_perdas.map((item, i) => (
              <li key={i}>
                <span className="font-medium text-zinc-900">{item.competencia}</span> — {item.motivo}
              </li>
            ))}
          </ul>
        </Secao>
      )}

      {feedback.fechamento && (
        <p className="text-sm text-zinc-800 leading-relaxed border-t border-zinc-100 pt-4">
          {feedback.fechamento}
        </p>
      )}
    </div>
  );
}

function Resultado({ avaliacao, feedback, custoFeedback, saldo, gerandoFeedback, aoPedirFeedback, aoEscreverOutra }) {
  const anulada = avaliacao.estado_geral === "ANULADA";
  const estimados = avaliacao.nota_pontos_estimados || 0;
  const semSaldo = saldo != null && saldo < custoFeedback;
  // As duas competências de menor nota, e só quando sobrou ponto de verdade
  // para ganhar (< 160 de 200). Acima disso o card viraria cobrança de quem
  // já foi bem.
  const competenciasFracas = [...(avaliacao.competencias || [])]
    .filter((c) => (c.nivel_pontos ?? 0) < 160)
    .sort((a, b) => (a.nivel_pontos ?? 0) - (b.nivel_pontos ?? 0))
    .slice(0, 2);

  return (
    <div className="space-y-4" data-testid="redacao-resultado">
      <div className={`card-sapiens rounded-2xl p-8 text-center ${anulada ? "border-rose-200" : ""}`}>
        <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">
          {anulada ? "Redação anulada" : "Sua nota"}
        </div>
        <div className="mt-2 font-display text-6xl font-extrabold tracking-tighter text-zinc-950">
          {avaliacao.nota_total}
          <span className="text-zinc-300 text-3xl">/1000</span>
        </div>
        {estimados > 0 && (
          <div className="mt-4 inline-flex items-start gap-2 text-left rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-900">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>
              <strong>{estimados} destes pontos são estimativa.</strong> Parte dos critérios não pôde
              ser confirmada automaticamente — um corretor humano pode chegar a outro número neles.
            </span>
          </div>
        )}
      </div>

      {avaliacao.gatilhos_disparados?.some((g) => g.disparado && g.confirmado) && (
        <div className="card-sapiens rounded-2xl p-6" data-testid="redacao-gatilhos">
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-rose-700 mb-3">
            Motivos de anulação identificados
          </div>
          <ul className="space-y-1.5 text-sm text-zinc-700">
            {avaliacao.gatilhos_disparados
              .filter((g) => g.disparado && g.confirmado)
              .map((g, i) => <li key={i}>· {g.motivo || g.id}</li>)}
          </ul>
        </div>
      )}

      {avaliacao.competencias?.length > 0 && (
        <div className="card-sapiens rounded-2xl p-6 space-y-4" data-testid="redacao-competencias">
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">
            Competências
          </div>
          {avaliacao.competencias.map((c) => <BarraCompetencia key={c.id} comp={c} />)}
        </div>
      )}

      {/* Competências que mais custaram pontos — cada uma com saída, como
          qualquer card de erro do produto: aqui, um pedido pronto à Mentis
          sobre AQUELA competência (ver `CardDeMelhora`). */}
      {competenciasFracas.length > 0 && (
        <div className="space-y-3" data-testid="redacao-competencias-fracas">
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-white/40">
            O que mais custou pontos
          </div>
          {competenciasFracas.map((c) => (
            <CardDeMelhora
              key={c.id}
              rotuloTopo="Competência a desenvolver"
              titulo={COMPETENCIAS[c.id] || c.id}
              descricao="Peça à Mentis o que fazer para subir esta competência na próxima redação."
              medida={`${c.nivel_pontos ?? 0}`}
              medidaLabel="de 200"
              assunto={`Redação · ${COMPETENCIAS[c.id] || c.id}`}
              evidencia={`${c.nivel_pontos ?? 0} de 200 pontos nessa competência na minha última redação`}
              testid={`redacao-fraca-${c.id}`}
            />
          ))}
        </div>
      )}

      {avaliacao.tangenciamento_detectado && (
        <div className="card-sapiens rounded-2xl p-6 text-sm text-zinc-700">
          <strong className="text-zinc-900">Tangenciamento do tema.</strong> O texto passa perto do
          tema proposto, mas não o enfrenta diretamente — no ENEM isso limita a nota das
          competências II, III e V.
        </div>
      )}

      {feedback ? (
        <FeedbackMentis feedback={feedback} />
      ) : (
        <div className="card-sapiens rounded-2xl p-6 space-y-3" data-testid="redacao-oferta-feedback">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-sapiens-accent" />
            <span className="font-display text-lg font-bold tracking-tight text-zinc-950">
              Quer entender a nota?
            </span>
          </div>
          <p className="text-sm text-zinc-600 leading-relaxed">
            A Mentis lê esta redação e escreve uma devolutiva completa: o que ficou bom, o que ficou
            ruim, onde e como melhorar, e o que mais derrubou a sua nota — citando trechos do seu
            próprio texto.
          </p>
          <button
            onClick={aoPedirFeedback}
            disabled={gerandoFeedback || semSaldo}
            className="pill btn-sapiens inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-medium disabled:opacity-40"
            data-testid="redacao-pedir-feedback"
          >
            {gerandoFeedback
              ? <><Loader2 className="w-4 h-4 animate-spin" /> A Mentis está lendo...</>
              : <><Zap className="w-4 h-4" /> Pedir a devolutiva por {custoFeedback} Sparks</>}
          </button>
          {semSaldo && (
            <div className="text-xs text-rose-600" data-testid="redacao-feedback-sem-saldo">
              Saldo insuficiente ({saldo} / {custoFeedback} Sparks).
            </div>
          )}
        </div>
      )}

      <button
        onClick={aoEscreverOutra}
        className="pill inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-medium border border-white/20 text-white/80 hover:border-white/40"
        data-testid="redacao-nova"
      >
        Corrigir outra redação
      </button>
    </div>
  );
}

export default function Redacao() {
  const [texto, setTexto] = useState("");
  const [tema, setTema] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [avaliacao, setAvaliacao] = useState(null);
  const [redacaoId, setRedacaoId] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [gerandoFeedback, setGerandoFeedback] = useState(false);
  const [confirmandoFeedback, setConfirmandoFeedback] = useState(false);
  const [erro, setErro] = useState(null);
  const [saldo, setSaldo] = useState(null);
  const [precos, setPrecos] = useState({
    custo_correcao: CUSTO_CORRECAO_PADRAO,
    custo_feedback: CUSTO_FEEDBACK_PADRAO,
  });

  // A chave só muda quando o aluno começa uma redação NOVA. Enquanto ele
  // estiver na mesma tentativa, todo reenvio cai na mesma cobrança.
  const chave = useRef(novaChave());

  const { dados: historico, recarregar } = useCarregamento(
    async () => (await api.get("/redacao")).data.items || [],
    [],
  );

  useEffect(() => {
    let ativo = true;
    api.get("/redacao/precos").then(({ data }) => { if (ativo) setPrecos(data); }).catch(() => {});
    api
      .get("/firestore/students/me/sparks")
      .then(({ data }) => { if (ativo) setSaldo(data.sparks_balance); })
      .catch(() => {});
    return () => { ativo = false; };
  }, []);

  const enviar = async () => {
    setConfirmando(false);
    setEnviando(true);
    setErro(null);
    try {
      const { data } = await api.post("/redacao", {
        texto,
        tema_frase: tema.trim(),
        idempotency_key: chave.current,
      });
      setAvaliacao(data.avaliacao);
      setRedacaoId(data.redacao.redacao_id);
      setFeedback(null);
      if (typeof data.sparks_balance === "number") setSaldo(data.sparks_balance);
      recarregar();
    } catch (err) {
      setErro(errMsg(err, "Não foi possível corrigir agora. Tente de novo em alguns minutos."));
    } finally {
      setEnviando(false);
    }
  };

  const pedirFeedback = async () => {
    setConfirmandoFeedback(false);
    if (!redacaoId) return;
    setGerandoFeedback(true);
    try {
      const { data } = await api.post(`/redacao/${redacaoId}/feedback`);
      setFeedback(data.feedback);
      if (typeof data.sparks_balance === "number") setSaldo(data.sparks_balance);
      recarregar();
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível escrever a devolutiva agora."));
    } finally {
      setGerandoFeedback(false);
    }
  };

  const abrirDoHistorico = useCallback(async (id) => {
    try {
      const { data } = await api.get(`/redacao/${id}`);
      setAvaliacao(data.avaliacao);
      setRedacaoId(id);
      setFeedback(data.feedback || null);
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível abrir esta redação."));
    }
  }, []);

  const escreverOutra = () => {
    setAvaliacao(null);
    setRedacaoId(null);
    setFeedback(null);
    setTexto("");
    setTema("");
    setErro(null);
    chave.current = novaChave();
  };

  const faltam = Math.max(0, MIN_CARACTERES - texto.trim().length);
  const semTema = !tema.trim();
  const custo = precos.custo_correcao ?? CUSTO_CORRECAO_PADRAO;
  const custoFeedback = precos.custo_feedback ?? CUSTO_FEEDBACK_PADRAO;
  const semSaldo = saldo != null && saldo < custo;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-3xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-3">Redação</div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white" data-testid="redacao-title">
          {avaliacao ? "Sua correção." : "Escreva. Nós corrigimos."}
        </h1>
        {!avaliacao && (
          <p className="mt-3 text-white/60 max-w-lg">
            Correção pelas cinco competências do ENEM, com os critérios oficiais. Custa{" "}
            <strong className="text-white/80">{custo} Sparks</strong> — e a devolutiva escrita da
            Mentis, se você quiser, é uma escolha separada depois de ver a nota.
          </p>
        )}

        <div className="mt-10">
          {avaliacao ? (
            <Resultado
              avaliacao={avaliacao}
              feedback={feedback}
              custoFeedback={custoFeedback}
              saldo={saldo}
              gerandoFeedback={gerandoFeedback}
              aoPedirFeedback={() => setConfirmandoFeedback(true)}
              aoEscreverOutra={escreverOutra}
            />
          ) : (
            <form
              onSubmit={(e) => { e.preventDefault(); setConfirmando(true); }}
              className="card-sapiens rounded-2xl p-6 md:p-8 space-y-5"
            >
              <div>
                <label className="text-xs font-medium text-zinc-500 mb-1.5 block">
                  Tema proposto <span className="text-zinc-400">(obrigatório)</span>
                </label>
                <input
                  required
                  value={tema}
                  onChange={(e) => setTema(e.target.value)}
                  maxLength={1000}
                  placeholder="Ex.: Desafios para a valorização de comunidades e povos tradicionais no Brasil"
                  className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none"
                  data-testid="redacao-tema"
                />
                <div className="mt-1.5 text-xs text-zinc-400">
                  Sem o tema, a Competência II (200 pontos) não tem contra o que ser medida.
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-500 mb-1.5 block">Sua redação</label>
                <textarea
                  required
                  value={texto}
                  onChange={(e) => setTexto(e.target.value)}
                  rows={16}
                  maxLength={20000}
                  placeholder="Digite ou cole o texto da sua redação aqui..."
                  className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm leading-relaxed focus:border-sapiens-accent outline-none resize-y"
                  data-testid="redacao-texto"
                />
                <div className="mt-1.5 flex items-center justify-between text-xs text-zinc-400">
                  <span>{texto.trim().length} caracteres</span>
                  {faltam > 0 && <span>Faltam {faltam} para enviar</span>}
                </div>
              </div>

              {erro && <div className="text-sm text-rose-600" data-testid="redacao-erro">{erro}</div>}

              <button
                type="submit"
                disabled={enviando || faltam > 0 || semTema || semSaldo}
                className="pill btn-sapiens inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-medium disabled:opacity-40"
                data-testid="redacao-enviar"
              >
                {enviando
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Corrigindo...</>
                  : <><PenLine className="w-4 h-4" /> Corrigir por {custo} Sparks</>}
              </button>
              {semSaldo && (
                <div className="text-xs text-rose-600" data-testid="redacao-sem-saldo">
                  Saldo insuficiente ({saldo} / {custo} Sparks).
                </div>
              )}
            </form>
          )}
        </div>

        {historico?.length > 0 && !avaliacao && (
          <div className="mt-10">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-white/50 mb-3">
              Redações anteriores
            </div>
            <div className="space-y-2">
              {historico.map(({ redacao, avaliacao: av, tem_feedback }) => (
                <button
                  key={redacao.redacao_id}
                  onClick={() => abrirDoHistorico(redacao.redacao_id)}
                  className="card-sapiens rounded-xl p-4 w-full text-left flex items-center justify-between gap-4"
                  data-testid={`redacao-historico-${redacao.redacao_id}`}
                >
                  <div className="min-w-0">
                    <div className="text-sm text-zinc-800 truncate">
                      {redacao.tema_frase || redacao.texto.slice(0, 70) + "..."}
                    </div>
                    <div className="text-xs text-zinc-400 mt-0.5 flex items-center gap-2">
                      <span>{new Date(redacao.created_at).toLocaleDateString("pt-BR")}</span>
                      {tem_feedback && (
                        <span className="inline-flex items-center gap-1 text-sapiens-accent">
                          <Sparkles className="w-3 h-3" /> com devolutiva
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="font-display font-extrabold text-xl tracking-tight text-zinc-950 shrink-0">
                    {av ? av.nota_total : "—"}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <Dialog open={confirmando} onOpenChange={(v) => !v && setConfirmando(false)}>
        <DialogContent className="rounded-2xl" data-testid="redacao-confirmar-correcao">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight">Corrigir esta redação?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-zinc-600 leading-relaxed">
            Isto custa <strong>{custo} Sparks</strong>
            {saldo != null && <> — seu saldo passa de {saldo} para <strong>{saldo - custo}</strong></>}.
            {" "}Você recebe a nota das cinco competências e a nota geral. Se algo der errado no meio,
            os Sparks voltam automaticamente.
          </p>
          <DialogFooter>
            <button
              onClick={() => setConfirmando(false)}
              className="pill inline-flex items-center justify-center px-5 py-2.5 rounded-full text-sm font-medium border border-zinc-200 text-zinc-700 hover:border-zinc-300"
              data-testid="redacao-cancelar-correcao"
            >
              Cancelar
            </button>
            <button
              onClick={enviar}
              className="pill btn-sapiens inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium"
              data-testid="redacao-confirmar-btn"
            >
              <Zap className="w-4 h-4" /> Corrigir por {custo} Sparks
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmandoFeedback} onOpenChange={(v) => !v && setConfirmandoFeedback(false)}>
        <DialogContent className="rounded-2xl" data-testid="redacao-confirmar-feedback">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight">Pedir a devolutiva da Mentis?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-zinc-600 leading-relaxed">
            Isto custa <strong>{custoFeedback} Sparks</strong>
            {saldo != null && <> — seu saldo passa de {saldo} para <strong>{saldo - custoFeedback}</strong></>}.
            {" "}A devolutiva fica salva nesta redação: você pode reler quantas vezes quiser, sem pagar de novo.
          </p>
          <DialogFooter>
            <button
              onClick={() => setConfirmandoFeedback(false)}
              className="pill inline-flex items-center justify-center px-5 py-2.5 rounded-full text-sm font-medium border border-zinc-200 text-zinc-700 hover:border-zinc-300"
              data-testid="redacao-cancelar-feedback"
            >
              Cancelar
            </button>
            <button
              onClick={pedirFeedback}
              className="pill btn-sapiens inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium"
              data-testid="redacao-confirmar-feedback-btn"
            >
              <Sparkles className="w-4 h-4" /> Pedir por {custoFeedback} Sparks
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
