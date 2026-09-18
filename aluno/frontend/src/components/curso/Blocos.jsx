import { useCallback, useEffect, useRef, useState } from "react";
import {
  Check, X, Lightbulb, PlayCircle, Film, ListOrdered, Flame, AlertTriangle, Loader2,
  Table2, Zap, Trophy, Sparkles,
} from "lucide-react";
import TextoRico from "./TextoRico";

/**
 * OS BLOCOS DE CONTEÚDO — um renderizador por tipo, e um registro só.
 *
 * Esta é a peça que faz o sistema de cursos ser um sistema e não um punhado
 * de telas: a estação chega do servidor como uma LISTA DE BLOCOS TIPADOS, e
 * aqui cada tipo sabe se desenhar. Publicar uma estação nova não toca em
 * código nenhum; publicar um TIPO novo de bloco toca em exatamente dois
 * lugares — `RENDERIZADORES`, aqui embaixo, e o validador do servidor
 * (`cursos_conteudo._validar_bloco`).
 *
 * Um tipo que o cliente ainda não conhece não quebra a estação: cai no aviso
 * discreto de "bloco não suportado" e o resto da aula continua. É o que
 * permite publicar conteúdo novo antes de o app de todo mundo ter atualizado.
 *
 * **O que NUNCA chega aqui:** gabarito, dica, feedback e resolução. O servidor
 * corrige e devolve um degrau por tentativa (ver `cursos_conteudo`
 * `.feedback_da_tentativa`). O componente de exercício não sabe a resposta —
 * nem quando está pintando a alternativa certa de verde, porque aí ela já veio
 * na resposta da correção.
 */

// ---------------------------------------------------------------------------
// "Explicar melhor" — a Mentis aprofunda o trecho, por Sparks
// ---------------------------------------------------------------------------
//
// Vive num lugar só e é usado pelos três blocos de LEITURA (texto, tabela,
// exemplo) — exercício e desafio não têm este botão: o que se pede ali é a
// devolutiva da resposta, não uma explicação do enunciado. `aoExplicar` é
// quem faz a chamada de verdade (a tela sabe se é curso ou e-book); aqui só
// se desenha o botão, o carregando e o resultado.

function ExplicarMelhor({ blocoId, aoExplicar }) {
  const [pedindo, setPedindo] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");

  if (!aoExplicar) return null;

  const pedir = async () => {
    setPedindo(true);
    setErro("");
    try {
      const r = await aoExplicar(blocoId);
      if (r) setResultado(r);
    } catch {
      setErro("Não foi possível pedir a explicação agora. Tente de novo em instantes.");
    } finally {
      setPedindo(false);
    }
  };

  if (resultado) {
    return (
      <div className="mt-4 rounded-2xl bg-sky-50/70 p-4 ring-1 ring-sky-200/70" data-testid={`explicacao-${blocoId}`}>
        <div className="secao-olho flex items-center gap-1.5 text-sky-700/80">
          <Sparkles className="h-3 w-3" /> A Mentis explica melhor
        </div>
        <div className="mt-2 space-y-2 text-sm text-zinc-700">
          {resultado.paragrafos.map((p, i) => <p key={i}><TextoRico markdown={p} /></p>)}
        </div>
      </div>
    );
  }

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={pedir}
        disabled={pedindo}
        className="chip inline-flex items-center gap-1.5 disabled:opacity-60"
        data-testid={`explicar-${blocoId}`}
      >
        {pedindo ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
        {pedindo ? "A Mentis está lendo…" : "Pedir para a Mentis explicar melhor"}
      </button>
      {erro && <p className="mt-1.5 text-xs text-amber-600">{erro}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Texto
// ---------------------------------------------------------------------------

const VARIANTES = {
  padrao: { classe: "leitura-clara", icone: null },
  destaque: { classe: "leitura-clara ring-1 ring-sky-400/50", icone: Flame },
  atencao: { classe: "leitura-clara ring-1 ring-amber-400/60", icone: AlertTriangle },
};

function BlocoTexto({ bloco, aoExplicar }) {
  const variante = VARIANTES[bloco.variante] || VARIANTES.padrao;
  const Icone = variante.icone;
  return (
    <section className={`${variante.classe} rounded-3xl p-5 md:p-7 text-zinc-800`} data-testid={`bloco-${bloco.bloco_id}`}>
      {bloco.titulo && (
        <h2 className="mb-3 flex items-center gap-2 font-display text-lg font-extrabold tracking-tight text-zinc-950">
          {Icone && <Icone className="h-4 w-4 text-sky-600" />}
          {bloco.titulo}
        </h2>
      )}
      <TextoRico markdown={bloco.markdown} />
      <ExplicarMelhor blocoId={bloco.bloco_id} aoExplicar={aoExplicar} />
    </section>
  );
}

// ---------------------------------------------------------------------------
// Tabela
// ---------------------------------------------------------------------------

/**
 * Existe porque o subconjunto de markdown do curso não tem tabela — e a regra
 * do contrato é que o que passa do subconjunto vira um TIPO DE BLOCO, com
 * renderizador e validação próprios, em vez de um parser mais esperto.
 *
 * No celular a tabela rola na horizontal dentro do próprio bloco. A
 * alternativa (quebrar em cartões empilhados) perde justamente o que faz uma
 * tabela ser tabela: comparar a mesma coluna entre linhas.
 */
function BlocoTabela({ bloco, aoExplicar }) {
  return (
    <section
      className="leitura-clara rounded-3xl p-5 text-zinc-800 md:p-7"
      data-testid={`bloco-${bloco.bloco_id}`}
      // "Lembrar-me com a Mentis" sobre um OBJETO (ver `LembrarComAMentis`).
      // Uma tabela é o caso que a seleção de texto não resolve: arrastar por
      // cima dela devolve as células embaralhadas numa linha só, que não é o
      // que o aluno quis marcar. O atributo diz o que o objeto É, e o toque
      // longo (ou clique-direito) marca a tabela inteira.
      data-lembrar={`Tabela${bloco.titulo ? `: ${bloco.titulo}` : ""}`}
      data-lembrar-ref={`curso:bloco:${bloco.bloco_id}`}
    >
      {bloco.titulo && (
        <h2 className="mb-3 flex items-center gap-2 font-display text-lg font-extrabold tracking-tight text-zinc-950">
          <Table2 className="h-4 w-4 text-sky-600" />
          {bloco.titulo}
        </h2>
      )}
      <div className="-mx-1 overflow-x-auto px-1">
        <table className="w-full min-w-[22rem] border-collapse text-sm">
          <thead>
            <tr>
              {(bloco.colunas || []).map((coluna, i) => (
                <th
                  key={i}
                  scope="col"
                  className="border-b-2 border-zinc-300 px-3 py-2 text-left font-display text-[13px] font-bold tracking-tight text-zinc-900"
                >
                  <TextoRico markdown={coluna} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(bloco.linhas || []).map((linha, i) => (
              <tr key={i} className={i % 2 ? "bg-zinc-50" : undefined}>
                {linha.map((celula, j) => (
                  <td key={j} className="border-b border-zinc-200 px-3 py-2 align-top text-zinc-700">
                    <TextoRico markdown={celula} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ExplicarMelhor blocoId={bloco.bloco_id} aoExplicar={aoExplicar} />
    </section>
  );
}

// ---------------------------------------------------------------------------
// Exemplo resolvido
// ---------------------------------------------------------------------------

function BlocoExemplo({ bloco, aoExplicar }) {
  return (
    <section
      className="leitura-clara rounded-3xl p-5 md:p-7 text-zinc-800"
      data-testid={`bloco-${bloco.bloco_id}`}
      // Idem à tabela: um exemplo resolvido é um objeto (enunciado + passos),
      // e marcá-lo inteiro é mais útil que marcar um passo solto.
      data-lembrar={`Exemplo resolvido${bloco.titulo ? `: ${bloco.titulo}` : ""}`}
      data-lembrar-ref={`curso:bloco:${bloco.bloco_id}`}
    >
      <div className="secao-olho flex items-center gap-1.5 text-sky-700/80">
        <ListOrdered className="h-3 w-3" /> Exemplo resolvido
      </div>
      <div className="mt-3 font-medium text-zinc-950">
        <TextoRico markdown={bloco.enunciado} />
      </div>

      <ol className="mt-5 space-y-4">
        {(bloco.passos || []).map((passo, i) => (
          <li key={i} className="flex gap-3">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sky-100 font-mono-alt text-xs font-bold text-sky-700">
              {i + 1}
            </span>
            <div className="min-w-0">
              <TextoRico markdown={passo.texto} />
              {/* O "por que este passo". É o que separa um exemplo resolvido de
                  uma conta copiada — e por isso tem peso visual próprio. */}
              {passo.comentario && (
                <p className="mt-1.5 border-l-2 border-sky-300 pl-2.5 text-sm italic text-zinc-500">
                  {passo.comentario}
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>

      {bloco.fecho && (
        <div className="mt-5 rounded-2xl bg-sky-50 p-4 text-sm text-sky-900">
          <TextoRico markdown={bloco.fecho} />
        </div>
      )}
      <ExplicarMelhor blocoId={bloco.bloco_id} aoExplicar={aoExplicar} />
    </section>
  );
}

// ---------------------------------------------------------------------------
// Vídeo
// ---------------------------------------------------------------------------

function urlDoVideo(bloco) {
  const ref = String(bloco.ref || "");
  if (bloco.provedor === "youtube") {
    // Aceita id puro ou URL completa — quem escreve o conteúdo cola o que tem
    // à mão, e exigir a forma canônica só produziria erro de digitação.
    const id = ref.match(/(?:v=|youtu\.be\/|embed\/)([\w-]{6,})/)?.[1] || ref;
    return `https://www.youtube-nocookie.com/embed/${id}`;
  }
  if (bloco.provedor === "vimeo") {
    const id = ref.match(/(\d{6,})/)?.[1] || ref;
    return `https://player.vimeo.com/video/${id}`;
  }
  return ref;
}

function BlocoVideo({ bloco, onVisto }) {
  // Vídeo sem `ref` nem chega ao cliente (o servidor o omite); esta guarda é
  // para o caso de o cliente estar à frente do servidor numa publicação.
  if (!bloco.ref) return null;

  const fonte = urlDoVideo(bloco);
  return (
    <section className="superficie rounded-3xl p-4 md:p-5" data-testid={`bloco-${bloco.bloco_id}`}>
      <div className="mb-3 flex items-center gap-2">
        <Film className="h-4 w-4 text-white/45" />
        <h2 className="font-display text-base font-bold tracking-tight text-white">{bloco.titulo}</h2>
        <span className="chip ml-auto text-[11px]">Opcional</span>
      </div>

      {bloco.provedor === "arquivo" ? (
        <video
          src={fonte}
          controls
          className="w-full rounded-2xl"
          onPlay={onVisto}
          data-testid={`video-${bloco.bloco_id}`}
        />
      ) : (
        <div className="relative w-full overflow-hidden rounded-2xl" style={{ aspectRatio: "16 / 9" }}>
          <iframe
            src={fonte}
            title={bloco.titulo}
            className="absolute inset-0 h-full w-full"
            allow="accelerometer; clipboard-write; encrypted-media; picture-in-picture"
            allowFullScreen
            onLoad={onVisto}
            data-testid={`video-${bloco.bloco_id}`}
          />
        </div>
      )}

      {bloco.resumo && <p className="mt-3 text-sm text-white/55">{bloco.resumo}</p>}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Exercício e desafio
// ---------------------------------------------------------------------------

const LETRAS = "ABCDEFGH";

function BlocoExercicio({ bloco, progresso, aoResponder }) {
  const desafio = bloco.tipo === "desafio";
  const [escolha, setEscolha] = useState("");
  const [texto, setTexto] = useState("");
  const [resultado, setResultado] = useState(null);
  const [enviando, setEnviando] = useState(false);
  // Pediu para responder de novo um exercício que já tinha acertado.
  //
  // Precisa ser estado PRÓPRIO, e é aqui que morava o bug: a trava era
  // `jaAcertou && !resultado`, e o botão "Responder de novo" só limpava
  // `resultado` — que já era nulo. A condição continuava verdadeira, os campos
  // continuavam desabilitados e o exercício ficava trancado para sempre.
  // Quem tinha acertado numa visita anterior (ou só recarregou a página) não
  // conseguia responder mais nada naquela questão.
  const [refazendo, setRefazendo] = useState(false);
  // Conta a partir do PRIMEIRO TOQUE no exercício, não da abertura da página:
  // a estação inteira é renderizada de uma vez, e cronometrar a partir do
  // `mount` mediria quanto tempo o aluno levou para chegar até aqui.
  const inicio = useRef(null);

  const jaAcertou = Boolean(progresso?.acertou);
  const travado = jaAcertou && !resultado && !refazendo;

  const tocar = useCallback(() => {
    if (inicio.current === null) inicio.current = Date.now();
  }, []);

  const enviar = useCallback(async (resposta) => {
    if (enviando || resposta === "" || resposta === null || resposta === undefined) return;
    setEnviando(true);
    const decorrido = inicio.current ? (Date.now() - inicio.current) / 1000 : null;
    try {
      const r = await aoResponder(bloco.bloco_id, resposta, decorrido, bloco.formato === "dissertativo");
      setResultado(r);
      // Errou: o cronômetro recomeça para a próxima tentativa ser medida
      // sozinha, senão a segunda tentativa herda o tempo da primeira.
      inicio.current = r?.acertou ? null : Date.now();
    } finally {
      setEnviando(false);
    }
  }, [aoResponder, bloco.bloco_id, bloco.formato, enviando]);

  const cor = desafio ? "text-amber-600" : "text-sky-700/80";

  return (
    <section
      className="leitura-clara rounded-3xl p-5 md:p-7 text-zinc-800"
      data-testid={`bloco-${bloco.bloco_id}`}
      onFocusCapture={tocar}
      onPointerDown={tocar}
    >
      <div className={`secao-olho flex items-center gap-1.5 ${cor}`}>
        {desafio ? <Flame className="h-3 w-3" /> : null}
        {desafio ? "Desafio" : `Exercício · nível ${bloco.nivel}`}
        {bloco.opcional && <span className="ml-1 opacity-60">· opcional</span>}
        {jaAcertou && (
          <span className="ml-auto inline-flex items-center gap-1 normal-case tracking-normal text-emerald-600">
            <Check className="h-3 w-3" /> Você já acertou
          </span>
        )}
      </div>

      <div className="mt-3 font-medium text-zinc-950">
        <TextoRico markdown={bloco.enunciado} />
      </div>

      {bloco.formato === "multipla_escolha" ? (
        <div className="mt-5 grid gap-2">
          {(bloco.alternativas || []).map((alt, i) => {
            const certa = resultado?.gabarito === alt.id;
            const erradaEscolhida = resultado && !resultado.acertou && escolha === alt.id;
            const estado = certa ? "certa" : erradaEscolhida ? "errada" : escolha === alt.id ? "escolhida" : "livre";
            return (
              <button
                key={alt.id}
                type="button"
                data-estado={estado}
                data-testid={`alt-${bloco.bloco_id}-${alt.id}`}
                disabled={enviando || travado}
                className={`alternativa ${escolha === alt.id && !resultado ? "select-pop" : ""}`}
                onClick={() => { setEscolha(alt.id); setResultado(null); enviar(alt.id); }}
              >
                <span className="alternativa-letra">
                  {certa ? <Check className="h-4 w-4" /> : erradaEscolhida ? <X className="h-4 w-4" /> : LETRAS[i]}
                </span>
                <span className="text-zinc-700">{alt.texto}</span>
              </button>
            );
          })}
        </div>
      ) : bloco.formato === "dissertativo" ? (
        <Dissertativa
          bloco={bloco}
          travado={travado}
          enviando={enviando}
          resultado={resultado}
          texto={texto}
          aoEscrever={(v) => { setTexto(v); setResultado(null); }}
          aoEnviar={() => enviar(texto)}
        />
      ) : (
        <form
          className="mt-5 flex flex-col items-stretch gap-2 sm:flex-row sm:items-center sm:flex-wrap"
          onSubmit={(e) => { e.preventDefault(); enviar(texto); }}
        >
          <input
            value={texto}
            onChange={(e) => { setTexto(e.target.value); setResultado(null); }}
            inputMode={bloco.formato === "numerico" ? "decimal" : "text"}
            placeholder={bloco.formato === "numerico" ? "Sua resposta" : "Escreva sua resposta"}
            disabled={enviando || travado}
            data-testid={`campo-${bloco.bloco_id}`}
            className="min-w-0 flex-1 rounded-2xl border border-zinc-300 bg-white px-4 py-3 text-base text-zinc-900 outline-none focus:border-sky-500"
          />
          {bloco.unidade && <span className="text-sm text-zinc-500">{bloco.unidade}</span>}
          <button
            type="submit"
            disabled={enviando || travado || !texto.trim()}
            className="pill btn-sapiens inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold disabled:opacity-50 sm:w-auto"
            data-testid={`responder-${bloco.bloco_id}`}
          >
            {enviando ? <Loader2 className="h-4 w-4 animate-spin" /> : null} Responder
          </button>
        </form>
      )}

      <Devolutiva resultado={resultado} />

      {travado && (
        <button
          type="button"
          onClick={() => {
            setRefazendo(true);
            setResultado(null);
            setEscolha("");
            setTexto("");
            inicio.current = Date.now();
          }}
          className="mt-4 text-xs font-semibold text-sky-700 underline underline-offset-2"
          data-testid={`refazer-${bloco.bloco_id}`}
        >
          Responder de novo
        </button>
      )}
    </section>
  );
}

/**
 * A QUESTÃO QUE SE RESPONDE ESCREVENDO.
 *
 * Duas coisas aqui não são decoração:
 *
 * 1. **A régua aparece ANTES de escrever.** Os critérios são o que a Mentis
 *    vai olhar, e escondê-los transformaria a questão num jogo de adivinhar o
 *    que o corretor quer. Quem sabe o que vai ser cobrado escreve melhor — e
 *    a devolutiva, depois, é sobre a mesma lista.
 * 2. **O preço é dito antes do clique, e vem do servidor.** O número não é
 *    escrito aqui: chega no bloco (`custo_correcao`), porque preço é decisão
 *    de produto e um número chumbado no JS vira mentira no dia em que ele
 *    mudar.
 */
function Dissertativa({ bloco, travado, enviando, resultado, texto, aoEscrever, aoEnviar }) {
  const custo = bloco.custo_correcao;
  const criterios = bloco.criterios || [];
  const julgados = resultado?.criterios || [];

  return (
    <form
      className="mt-5"
      onSubmit={(e) => { e.preventDefault(); aoEnviar(); }}
      data-testid={`dissertativa-${bloco.bloco_id}`}
    >
      {criterios.length > 0 && (
        <div className="rounded-2xl bg-sky-50/70 p-4 ring-1 ring-sky-200/70">
          <div className="secao-olho text-sky-700/80">O que a correção vai olhar</div>
          <ul className="mt-2 space-y-1.5">
            {criterios.map((c, i) => {
              const julgado = julgados[i];
              return (
                <li key={i} className="flex gap-2 text-sm text-zinc-700">
                  {julgado ? (
                    julgado.atendido
                      ? <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                      : <X className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  ) : (
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-sky-400" />
                  )}
                  <span>
                    {c}
                    {julgado?.comentario && (
                      <em className="mt-0.5 block not-italic text-[13px] text-zinc-500">
                        {julgado.comentario}
                      </em>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <textarea
        value={texto}
        onChange={(e) => aoEscrever(e.target.value)}
        rows={7}
        maxLength={4000}
        disabled={enviando || travado}
        placeholder="Escreva sua resposta com suas palavras…"
        data-testid={`campo-${bloco.bloco_id}`}
        className="mt-3 w-full rounded-2xl border border-zinc-300 bg-white px-4 py-3 text-base leading-relaxed text-zinc-900 outline-none focus:border-sky-500"
      />

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={enviando || travado || !texto.trim()}
          className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold disabled:opacity-50"
          data-testid={`responder-${bloco.bloco_id}`}
        >
          {enviando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
          {enviando ? "A Mentis está lendo…" : "Enviar para a Mentis"}
          {custo ? <span className="opacity-80">· {custo} Sparks</span> : null}
        </button>
        <span className="text-[12px] text-zinc-500">
          {texto.trim().length > 0 ? `${texto.trim().length} caracteres` : "Até 4.000 caracteres."}
        </span>
      </div>

      {resultado?.devolutiva && (
        <div className="mt-4 rounded-2xl bg-white/70 p-4 ring-1 ring-zinc-200" data-testid="devolutiva-mentis">
          <div className="secao-olho text-zinc-500">
            A Mentis leu sua resposta
            {typeof resultado.atendidos === "number" && (
              <span className="ml-1 normal-case tracking-normal">
                · {resultado.atendidos} de {resultado.total} critérios
              </span>
            )}
          </div>
          <div className="mt-2 text-sm text-zinc-700"><TextoRico markdown={resultado.devolutiva} /></div>
          {resultado.proximo_passo && (
            <p className="mt-2 flex gap-2 text-sm text-zinc-700">
              <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
              <span>{resultado.proximo_passo}</span>
            </p>
          )}
        </div>
      )}
    </form>
  );
}

/**
 * O que ENTROU no saldo com esta resposta — nunca o que a questão "vale".
 *
 * O número vem do servidor, que é quem creditou; refazer um exercício já pago
 * devolve zero e aqui não aparece nada. Anunciar "+1 Spark" sem crédito é a
 * forma mais rápida de fazer o aluno desconfiar do saldo inteiro.
 */
function Recompensa({ ganho }) {
  if (!ganho || (!ganho.sparks && !ganho.xp)) return null;
  return (
    <span className="ml-auto flex items-center gap-2 font-mono-alt text-[11px] font-bold" data-testid="recompensa">
      {ganho.sparks > 0 && (
        <span className="premio-pop inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-amber-800">
          <Zap className="h-3 w-3" /> +{ganho.sparks}
        </span>
      )}
      {ganho.xp > 0 && (
        <span className="premio-pop inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-violet-800">
          <Trophy className="h-3 w-3" /> +{ganho.xp} XP
        </span>
      )}
    </span>
  );
}

/** A devolutiva do servidor. Cada campo só existe quando foi conquistado —
 *  a tela não decide o que revelar, ela desenha o que chegou. */
function Devolutiva({ resultado }) {
  if (!resultado) return null;
  const certo = resultado.acertou;
  return (
    <div
      className={`mt-4 rounded-2xl p-4 text-sm ${certo ? "bg-emerald-50 text-emerald-900" : "bg-amber-50 text-amber-900"}`}
      data-testid="devolutiva"
      role="status"
    >
      <div className="flex flex-wrap items-center gap-2 font-semibold">
        {certo ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
        {certo ? "Isso mesmo." : `Ainda não — tentativa ${resultado.tentativa}.`}
        <Recompensa ganho={resultado.recompensa} />
      </div>

      {resultado.dica && (
        <p className="mt-2 flex gap-2">
          <Lightbulb className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{resultado.dica}</span>
        </p>
      )}
      {resultado.comentario && (
        <div className="mt-2"><TextoRico markdown={resultado.comentario} /></div>
      )}
      {resultado.solucao && (
        <div className="mt-3 border-t border-current/15 pt-3">
          <div className="secao-olho mb-1.5 text-current opacity-70">Como se resolve</div>
          <TextoRico markdown={resultado.solucao} />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// O registro
// ---------------------------------------------------------------------------

const RENDERIZADORES = {
  texto: BlocoTexto,
  tabela: BlocoTabela,
  exemplo: BlocoExemplo,
  video: BlocoVideo,
  exercicio: BlocoExercicio,
  desafio: BlocoExercicio,
};

export default function Bloco({ bloco, progresso, aoResponder, aoVer, aoExplicar }) {
  const Renderizador = RENDERIZADORES[bloco.tipo];

  // Um bloco de leitura conta como visto quando entra na tela. Exercício não:
  // o sinal dele é a resposta, e marcar "visto" ao rolar por cima
  // confundiria "passou o olho" com "fez".
  const alvo = useRef(null);
  const leitura = bloco.tipo === "texto" || bloco.tipo === "exemplo" || bloco.tipo === "tabela";
  useEffect(() => {
    if (!leitura || !alvo.current || typeof IntersectionObserver === "undefined") return undefined;
    const observador = new IntersectionObserver(
      ([entrada]) => {
        if (entrada.isIntersecting) {
          aoVer?.(bloco.bloco_id);
          observador.disconnect();
        }
      },
      { threshold: 0.4 },
    );
    observador.observe(alvo.current);
    return () => observador.disconnect();
  }, [leitura, bloco.bloco_id, aoVer]);

  if (!Renderizador) {
    // Tipo que este cliente ainda não conhece. Não quebra a aula: some com um
    // aviso, e o resto da estação continua funcionando.
    return (
      <div className="superficie rounded-2xl p-4 text-sm text-white/45" data-testid="bloco-desconhecido">
        <PlayCircle className="mr-2 inline h-4 w-4" />
        Este trecho precisa de uma versão mais nova do app. Atualize a página para vê-lo.
      </div>
    );
  }

  return (
    <div ref={alvo}>
      <Renderizador
        bloco={bloco}
        progresso={progresso}
        aoResponder={aoResponder}
        aoExplicar={aoExplicar}
        onVisto={() => aoVer?.(bloco.bloco_id)}
      />
    </div>
  );
}
