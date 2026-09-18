import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { toast } from "sonner";
import { useCarregamento } from "../hooks/useCarregamento";
import { COMPETENCIAS_REDACAO } from "../constants/redacao";
import CardDeMelhora from "../components/CardDeMelhora";
import { criarPortao, novaChave } from "../lib/idempotencia";
import {
  PenLine, Loader2, AlertTriangle, Sparkles, Zap, Camera, BookOpen, Check,
  ChevronDown, X,
} from "lucide-react";

const MIN_CARACTERES = 200;

// Espelham `redacao_routes.CORRECAO_COST` / `FEEDBACK_COST` /
// `DIGITALIZACAO_COST`. São só o valor exibido enquanto `GET /redacao/precos`
// não responde — quem cobra é o servidor, e é a resposta dele que manda na
// tela.
const CUSTO_CORRECAO_PADRAO = 120;
const CUSTO_FEEDBACK_PADRAO = 90;
const CUSTO_DIGITALIZACAO_PADRAO = 25;

// Teto do arquivo que o navegador aceita ANTES de virar base64 (que cresce
// ~33%). Espelha `redacao_routes.DIGITALIZACAO_MAX_BYTES`, com folga: recusar
// aqui poupa o aluno de esperar um upload que o servidor vai rejeitar.
const FOTO_MAX_BYTES = 6_000_000;

// As cinco competências do ENEM, 0–200 cada. Os rótulos são os oficiais,
// encurtados para caber na tela; o corretor devolve só o `id`.
const COMPETENCIAS = COMPETENCIAS_REDACAO;

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

/**
 * A COLETÂNEA DE TEMAS.
 *
 * O campo "Tema proposto (obrigatório)" começava vazio, e um campo vazio é o
 * degrau que faz a maioria não escrever nada: quem quer treinar redação
 * raramente tem uma frase temática na mão, e sair do Sapiens para procurar uma
 * é sair do Sapiens.
 *
 * O catálogo vem inteiro do servidor (`GET /redacao/temas`, custo zero — é
 * constante de módulo), agrupado por eixo. Escolher um tema preenche a frase
 * temática e anexa os textos motivadores à submissão; digitar um tema à mão
 * continua funcionando exatamente como antes, e custa o mesmo.
 */
function Coletanea({ temas, eixos, escolhido, editado, aoEscolher, aoLimpar }) {
  const [aberta, setAberta] = useState(false);
  const porId = useMemo(
    () => Object.fromEntries((temas || []).map((t) => [t.tema_id, t])),
    [temas],
  );

  if (!temas?.length) return null;

  if (escolhido) {
    return (
      <div
        className="rounded-2xl border border-[#4FD9FF]/30 bg-[#4FD9FF]/[0.07] p-4"
        data-testid="redacao-tema-escolhido"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-[#7FD8FF]">
              {escolhido.eixo_titulo}
            </div>
            <div className="mt-1 text-sm font-semibold leading-snug text-zinc-950">
              {escolhido.frase}
            </div>
          </div>
          <button
            type="button"
            onClick={aoLimpar}
            className="shrink-0 rounded-full p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
            aria-label="Escolher outro tema"
            data-testid="redacao-tema-trocar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {/* O aluno escolheu um tema e DEPOIS reescreveu a frase no campo
            abaixo. Os textos motivadores deixam de valer nesse caso (eles são
            a coletânea daquele tema, não desta frase) e a submissão já não os
            manda — isto é só a tela dizendo o que ela está fazendo, em vez de
            mostrar duas frases diferentes sem explicar a diferença. */}
        {editado && (
          <p className="mt-2.5 text-xs leading-relaxed text-amber-700">
            Você reescreveu o tema no campo abaixo. Vale o que está escrito lá — os textos
            motivadores deste tema não entram mais na correção.
          </p>
        )}
        <details className="mt-3">
          <summary className="cursor-pointer text-xs font-medium text-sapiens-accentDeep">
            Ver os {escolhido.textos_motivadores.length} textos motivadores
          </summary>
          <div className="mt-3 space-y-3 border-l-2 border-[#4FD9FF]/30 pl-3">
            {escolhido.textos_motivadores.map((t) => (
              <div key={t.rotulo}>
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
                  {t.rotulo} · {t.fonte}
                </div>
                <p className="mt-1 text-xs leading-relaxed text-zinc-600">{t.texto}</p>
              </div>
            ))}
          </div>
        </details>
      </div>
    );
  }

  return (
    <div data-testid="redacao-coletanea">
      <button
        type="button"
        onClick={() => setAberta((v) => !v)}
        aria-expanded={aberta}
        className="flex w-full items-center gap-2.5 rounded-2xl border border-zinc-200 px-4 py-3 text-left text-sm font-medium text-zinc-700 hover:border-sapiens-accent"
        data-testid="redacao-abrir-coletanea"
      >
        <BookOpen className="h-4 w-4 shrink-0 text-sapiens-accent" />
        <span className="flex-1">Escolher um tema da nossa coletânea</span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-zinc-400 transition-transform ${aberta ? "rotate-180" : ""}`}
        />
      </button>

      {aberta && (
        <div className="mt-2 space-y-4 rounded-2xl border border-zinc-200 p-4">
          {eixos.map((eixo) => (
            <div key={eixo.eixo_id}>
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-400">
                {eixo.titulo}
              </div>
              <div className="mt-1.5 space-y-1">
                {eixo.temas.map((id) => porId[id]).filter(Boolean).map((t) => (
                  <button
                    key={t.tema_id}
                    type="button"
                    onClick={() => { aoEscolher(t); setAberta(false); }}
                    className="flex w-full items-start gap-2.5 rounded-xl px-3 py-2.5 text-left hover:bg-zinc-50"
                    data-testid={`redacao-tema-${t.tema_id}`}
                  >
                    <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-300" />
                    <span className="min-w-0">
                      <span className="block text-sm font-medium text-zinc-900">{t.titulo}</span>
                      <span className="mt-0.5 block text-xs leading-snug text-zinc-500">
                        {t.resumo}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
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
        <div className="secao-olho">
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
          <div className="secao-olho">
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
            <strong className="text-zinc-900">Isto é opcional e é outra compra.</strong> A sua
            correção nas cinco competências, acima, já está paga e é sua. Se quiser, a Mentis lê
            esta redação e escreve uma devolutiva completa: o que ficou bom, o que ficou ruim,
            onde e como melhorar, e o que mais derrubou a sua nota — citando trechos do seu
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
  // A coletânea e o tema escolhido nela. `temaEscolhido` é o objeto inteiro
  // (frase + textos motivadores), porque os motivadores viajam junto na
  // submissão — é o que dá à Competência II algo além da frase para medir.
  const [coletanea, setColetanea] = useState({ temas: [], eixos: [] });
  const [temaEscolhido, setTemaEscolhido] = useState(null);
  const [digitalizando, setDigitalizando] = useState(false);
  const [confirmandoFoto, setConfirmandoFoto] = useState(null);
  const arquivoRef = useRef(null);
  const portaoDaFoto = useRef(criarPortao("ocr"));
  const portaoDaCorrecao = useRef(criarPortao("red"));
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
    custo_digitalizacao: CUSTO_DIGITALIZACAO_PADRAO,
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
    // A coletânea é constante do servidor: uma leitura por abertura de tela,
    // sem Firestore e sem Mongo. Se falhar, a tela continua de pé com o campo
    // de tema digitado — o catálogo é um atalho, não um pré-requisito.
    api
      .get("/redacao/temas")
      .then(({ data }) => { if (ativo) setColetanea({ temas: data.temas || [], eixos: data.eixos || [] }); })
      .catch(() => {});
    api
      .get("/firestore/students/me/sparks")
      .then(({ data }) => { if (ativo) setSaldo(data.sparks_balance); })
      .catch(() => {});
    return () => { ativo = false; };
  }, []);

  /** O arquivo escolhido vira data URL e abre a confirmação da cobrança. A
   *  leitura é local: nada sai do aparelho antes de o aluno confirmar. */
  const escolherFoto = (e) => {
    const arquivo = e.target.files?.[0];
    e.target.value = ""; // permite reescolher o MESMO arquivo depois de um erro
    if (!arquivo) return;
    if (!arquivo.type?.startsWith("image/")) {
      toast.error("Escolha uma foto da folha (JPG ou PNG).");
      return;
    }
    if (arquivo.size > FOTO_MAX_BYTES) {
      toast.error("Foto muito grande. Tire em qualidade normal, sem ampliar.");
      return;
    }
    const leitor = new FileReader();
    leitor.onload = () => setConfirmandoFoto(String(leitor.result || ""));
    leitor.onerror = () => toast.error("Não consegui abrir essa foto.");
    leitor.readAsDataURL(arquivo);
  };

  const digitalizar = async () => {
    // Mesma trava do cronograma: a `ref` barra o segundo toque no mesmo
    // instante, e a chave só troca quando a foto foi lida — tentar de novo
    // depois de um erro de rede é a mesma foto, e o servidor precisa
    // reconhecê-la como tal em vez de cobrar outra vez.
    if (!portaoDaFoto.current.entrar()) return;
    const imagem = confirmandoFoto;
    setConfirmandoFoto(null);
    if (!imagem) { portaoDaFoto.current.sair(); return; }
    setDigitalizando(true);
    try {
      const { data } = await api.post("/redacao/digitalizar", {
        imagem_base64: imagem,
        idempotency_key: portaoDaFoto.current.chave,
      });
      portaoDaFoto.current.concluir();
      // O texto ENTRA no campo — não substitui em silêncio o que já estava
      // escrito. Quem já tinha texto recebe o reconhecido no fim, e decide.
      setTexto((atual) => (atual.trim() ? `${atual.trim()}\n\n${data.texto}` : data.texto));
      if (typeof data.sparks_balance === "number") setSaldo(data.sparks_balance);
      toast.success("Pronto. Revise o texto antes de mandar corrigir — o reconhecimento erra.");
    } catch (err) {
      toast.error(errMsg(err, "Não consegui ler a foto agora."));
    } finally {
      portaoDaFoto.current.sair();
      setDigitalizando(false);
    }
  };

  const enviar = async () => {
    // A chave da correção já era estável por tentativa (`chave.current`), mas
    // faltava a trava do toque duplo: dois cliques no "Corrigir" mandavam duas
    // requisições com a MESMA chave, e a segunda respondia 409 ("já está sendo
    // processada") em cima de uma correção que estava dando certo — erro na
    // tela de quem não errou nada.
    if (!portaoDaCorrecao.current.entrar()) return;
    setConfirmando(false);
    setEnviando(true);
    setErro(null);
    try {
      const { data } = await api.post("/redacao", {
        texto,
        tema_frase: tema.trim(),
        // Só quando o tema veio da coletânea E a frase não foi editada depois:
        // mandar os motivadores de um tema junto de outra frase seria dar ao
        // corretor um contexto que não é o do texto avaliado.
        textos_motivadores:
          temaEscolhido && temaEscolhido.frase === tema.trim()
            ? temaEscolhido.textos_motivadores.map((t) => t.texto)
            : [],
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
      portaoDaCorrecao.current.sair();
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
    setTemaEscolhido(null);
    setErro(null);
    chave.current = novaChave();
  };

  const faltam = Math.max(0, MIN_CARACTERES - texto.trim().length);
  const semTema = !tema.trim();
  const custo = precos.custo_correcao ?? CUSTO_CORRECAO_PADRAO;
  const custoFeedback = precos.custo_feedback ?? CUSTO_FEEDBACK_PADRAO;
  const custoDigitalizacao = precos.custo_digitalizacao ?? CUSTO_DIGITALIZACAO_PADRAO;
  const semSaldo = saldo != null && saldo < custo;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-3xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="secao-olho">Redação</div>
        <h1 className="titulo-tela" data-testid="redacao-title">
          {avaliacao ? "Sua correção." : "Escreva. A Mentis corrige como o ENEM corrige."}
        </h1>
        {!avaliacao && (
          <div className="mt-3 max-w-lg space-y-2 text-white/60">
            {/* As duas compras, ditas separadamente e nesta ordem. O que se
                compra por {custo} Sparks é a NOTA; a devolutiva da Mentis é
                outra coisa, custa outro preço e é pedida depois — nunca vem
                junta nem "inclusa". */}
            <p>
              <strong className="text-white/85">
                Correção nas cinco competências do ENEM, com os critérios oficiais.
              </strong>{" "}
              Nota de 0 a 200 em cada uma, mais a nota geral. Custa{" "}
              <strong className="text-white/80">{custo} Sparks</strong>.
            </p>
            <p className="text-sm text-white/45">
              A devolutiva escrita da Mentis é separada: você só decide se quer depois de
              ver a nota, e ela custa {custoFeedback} Sparks à parte.
            </p>
          </div>
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
              <div className="space-y-3">
                <Coletanea
                  temas={coletanea.temas}
                  eixos={coletanea.eixos}
                  escolhido={temaEscolhido}
                  editado={Boolean(temaEscolhido) && temaEscolhido.frase !== tema.trim()}
                  aoEscolher={(t) => { setTemaEscolhido(t); setTema(t.frase); }}
                  aoLimpar={() => { setTemaEscolhido(null); setTema(""); }}
                />
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
              </div>

              <div>
                <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
                  <label className="text-xs font-medium text-zinc-500">Sua redação</label>
                  {/* ESCREVI NO PAPEL. Quem treina redação escreve à mão, na
                      folha oficial, porque é assim que a prova é — e depois
                      abandona a correção em vez de digitar 30 linhas. O botão
                      abre a câmera no celular (`capture`) e a galeria no
                      desktop. O texto reconhecido entra no campo abaixo para
                      ser REVISADO; corrigir continua sendo outra compra. */}
                  <button
                    type="button"
                    onClick={() => arquivoRef.current?.click()}
                    disabled={digitalizando}
                    className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-600 hover:border-sapiens-accent hover:text-zinc-900 disabled:opacity-50"
                    data-testid="redacao-foto"
                  >
                    {digitalizando ? (
                      <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Lendo a foto…</>
                    ) : (
                      <><Camera className="h-3.5 w-3.5" /> Escrevi no papel · {custoDigitalizacao} Sparks</>
                    )}
                  </button>
                  <input
                    ref={arquivoRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={escolherFoto}
                    className="hidden"
                    data-testid="redacao-foto-input"
                  />
                </div>
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

      {/* A cobrança da digitalização, dita antes de acontecer — a mesma regra
          das outras duas compras desta tela. */}
      <Dialog open={Boolean(confirmandoFoto)} onOpenChange={(v) => !v && setConfirmandoFoto(null)}>
        <DialogContent className="rounded-2xl" data-testid="redacao-confirmar-foto">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight">
              Digitalizar esta foto?
            </DialogTitle>
          </DialogHeader>
          {confirmandoFoto && (
            <img
              src={confirmandoFoto}
              alt="A foto da sua redação"
              className="max-h-56 w-full rounded-xl border border-zinc-200 object-contain"
            />
          )}
          <p className="text-sm text-zinc-600 leading-relaxed">
            Isto custa <strong>{custoDigitalizacao} Sparks</strong>
            {saldo != null && <> — seu saldo passa de {saldo} para <strong>{saldo - custoDigitalizacao}</strong></>}.
            {" "}Ela vira texto no campo abaixo, para você revisar. <strong>Não é a correção</strong>:
            corrigir continua custando {custo} Sparks, e só quando você mandar.
            {" "}Se a foto sair ilegível, os Sparks voltam.
          </p>
          <DialogFooter>
            <button
              onClick={() => setConfirmandoFoto(null)}
              className="pill inline-flex items-center justify-center px-5 py-2.5 rounded-full text-sm font-medium border border-zinc-200 text-zinc-700 hover:border-zinc-300"
              data-testid="redacao-cancelar-foto"
            >
              Cancelar
            </button>
            <button
              onClick={digitalizar}
              className="pill btn-sapiens inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium"
              data-testid="redacao-confirmar-foto-btn"
            >
              <Camera className="w-4 h-4" /> Digitalizar por {custoDigitalizacao} Sparks
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
