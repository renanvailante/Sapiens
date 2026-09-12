import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import {
  ShieldCheck, Boxes, ClipboardCheck, FlaskConical, Check, X, Loader2, CircleAlert, TriangleAlert,
} from "lucide-react";

/**
 * Curadoria — a tela da Fase 0, que é o pré-requisito de todas as outras.
 *
 * Três abas, nesta ordem porque é a ordem em que se decide:
 *
 *  1. **Oferta** — quantos itens existem por processo, em quantos contextos.
 *     Reprovado aqui significa que reteste sobre aquele processo mede memória
 *     do item, não estabilização da habilidade. É bloqueante para abrir escopo.
 *  2. **Revisão** — o elo de ordem 1, item a item. Confirmar aqui é o ÚNICO
 *     caminho legítimo para religar o portão de crença e sair do perfil
 *     provisório em que produção roda desde 2026-09-04.
 *  3. **Lab** — o que o autorrelato do aluno e o comportamento das
 *     intervenções sugerem que está mal anotado. O Lab PROPÕE; quem revisa é a
 *     pessoa, na aba 2.
 */

const ABAS = [
  { id: "oferta", rotulo: "Oferta de itens", icone: Boxes },
  { id: "revisao", rotulo: "Revisão humana", icone: ClipboardCheck },
  { id: "lab", rotulo: "Sapiens Lab", icone: FlaskConical },
];

function Selo({ ok, sim = "Aprovado", nao = "Reprovado" }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
        ok ? "border-emerald-100 bg-emerald-50 text-emerald-700" : "border-amber-100 bg-amber-50 text-amber-700"
      }`}
    >
      {ok ? <Check className="h-3 w-3" /> : <TriangleAlert className="h-3 w-3" />}
      {ok ? sim : nao}
    </span>
  );
}

function Vazio({ texto }) {
  return <p className="mt-6 text-sm text-white/50">{texto}</p>;
}

// ---------------------------------------------------------------- Oferta

function Oferta() {
  const [dados, setDados] = useState(null);
  useEffect(() => {
    api
      .get("/admin/curadoria/oferta")
      .then(({ data }) => setDados(data))
      .catch((e) => toast.error(errMsg(e, "Falha ao ler o relatório de oferta.")));
  }, []);

  if (!dados) return <Vazio texto="Lendo o acervo..." />;

  return (
    <div className="mt-6 space-y-4" data-testid="curadoria-oferta">
      <div className="card-sapiens rounded-2xl p-5">
        <p className="font-display text-lg font-bold tracking-tight text-zinc-950">{dados.veredito}</p>
        <div className="mt-3 flex flex-wrap gap-6 text-sm text-zinc-600">
          <span>{dados.acervo.itens} itens no acervo</span>
          <span>{dados.acervo.revisados} revisados</span>
          <span>{dados.acervo.aptos_para_crenca} aptos para crença</span>
          <span>portão: <strong className="text-zinc-800">{dados.portao}</strong></span>
        </div>
        <p className="mt-3 text-xs leading-relaxed text-zinc-500">
          Um processo entra nas Fases 1/2/5 com pelo menos {dados.criterio.min_itens} itens e{" "}
          {dados.criterio.min_contextos} contextos distintos. Abaixo disso, a fila repete as mesmas
          questões e o reteste vira teste de memória.
        </p>
      </div>

      {dados.processos.map((p) => (
        <div key={p.processo_id} className="card-sapiens rounded-2xl p-5" data-testid={`oferta-${p.processo_id}`}>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="font-display font-bold text-zinc-950">{p.processo_nome}</div>
              <div className="font-mono-alt text-[10px] uppercase tracking-wide text-zinc-400">{p.processo_id}</div>
            </div>
            <Selo ok={p.apto_para_fase_1} />
          </div>
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-zinc-600">
            <span>{p.itens} itens</span>
            <span>{p.com_cadeia_raiz} com cadeia raiz</span>
            <span>{p.com_intervencao} com intervenção anotada</span>
            <span>{p.contextos_distintos} contexto(s)</span>
            <span>{p.revisados} revisado(s)</span>
          </div>
          {p.motivos.length > 0 && (
            <ul className="mt-3 space-y-1">
              {p.motivos.map((m, i) => (
                <li key={i} className="flex items-start gap-1.5 text-xs text-amber-700">
                  <CircleAlert className="mt-0.5 h-3 w-3 shrink-0" /> {m}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------- Revisão humana

function Revisao() {
  const [dados, setDados] = useState(null);
  const [ocupado, setOcupado] = useState(null);

  const carregar = () =>
    api
      .get("/admin/curadoria/fila")
      .then(({ data }) => setDados(data))
      .catch((e) => toast.error(errMsg(e, "Falha ao carregar a fila de revisão.")));

  useEffect(() => { carregar(); }, []);

  const revisar = async (itemId, aprovado) => {
    setOcupado(itemId);
    try {
      await api.post(`/admin/curadoria/itens/${encodeURIComponent(itemId)}/revisar`, { aprovado });
      toast.success(aprovado ? "Elo confirmado — o item passa a alimentar crença." : "Revisão registrada.");
      await carregar();
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível registrar a revisão."));
    } finally {
      setOcupado(null);
    }
  };

  if (!dados) return <Vazio texto="Carregando a fila..." />;
  if (dados.pares.length === 0) return <Vazio texto="Nada pendente. Todo item com cadeia anotada já foi revisado." />;

  return (
    <div className="mt-6 space-y-6" data-testid="curadoria-revisao">
      <div className="card-sapiens rounded-2xl p-5">
        <p className="text-sm leading-relaxed text-zinc-600">
          A pergunta é uma só: <strong className="text-zinc-800">este elo raiz se sustenta?</strong> Não é
          revisão de gabarito nem de enunciado. Confirmar grava{" "}
          <code className="font-mono-alt text-xs">apto_para_camada_de_crenca</code> no item — é o que faz o
          erro de um aluno naquela questão poder mover o perfil dele.
        </p>
        <div className="mt-3 text-xs text-zinc-500">
          {dados.itens_pendentes} pendente(s) de {dados.total_no_acervo} no acervo · portão:{" "}
          <strong className="text-zinc-700">{dados.portao}</strong>
        </div>
      </div>

      {dados.pares.map((g) => (
        <div key={g.par} data-testid={`revisao-par-${g.par}`}>
          <div className="mb-2 flex flex-wrap items-baseline gap-2">
            <span className="font-display text-lg font-bold tracking-tight text-white">{g.erro_nome}</span>
            <span className="text-sm text-white/50">em {g.processo_nome}</span>
            <span className="font-mono-alt text-[10px] uppercase tracking-wide text-white/30">{g.par}</span>
          </div>
          <div className="space-y-3">
            {g.itens.map((it) => (
              <div key={it.item_id} className="card-sapiens rounded-2xl p-5" data-testid={`revisao-item-${it.item_id}`}>
                <div className="font-mono-alt text-[10px] uppercase tracking-wide text-zinc-400">
                  {it.fonte.banca} {it.fonte.ano} · {it.fonte.prova} · questão {it.fonte.numero}
                  {it.fonte.tema ? ` · ${it.fonte.tema}` : ""}
                </div>
                {it.enunciado && (
                  <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-zinc-600">{it.enunciado}</p>
                )}
                <div className="mt-3 rounded-xl border border-zinc-200 bg-white/70 p-3">
                  <div className="text-xs font-bold text-zinc-700">
                    Alternativa {it.alternativa}
                    {it.explicacao_do_distrator ? ` — ${it.explicacao_do_distrator}` : ""}
                  </div>
                  <ol className="mt-2 space-y-1">
                    {it.cadeia.map((e, i) => (
                      <li key={i} className="text-xs text-zinc-600">
                        <span className={`font-mono-alt ${e.papel === "raiz" ? "text-rose-600" : "text-zinc-400"}`}>
                          {e.papel}
                        </span>{" "}
                        · {e.erro_nome} em {e.processo_nome} · confiança {e.confianca}
                      </li>
                    ))}
                  </ol>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    disabled={ocupado === it.item_id}
                    onClick={() => revisar(it.item_id, true)}
                    className="pill btn-sapiens inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-medium disabled:opacity-40"
                    data-testid={`revisao-aprovar-${it.item_id}`}
                  >
                    {ocupado === it.item_id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                    O elo raiz se sustenta
                  </button>
                  <button
                    type="button"
                    disabled={ocupado === it.item_id}
                    onClick={() => revisar(it.item_id, false)}
                    className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-4 py-2 text-xs font-medium text-zinc-600 hover:border-zinc-300 disabled:opacity-40"
                    data-testid={`revisao-rejeitar-${it.item_id}`}
                  >
                    <X className="h-3.5 w-3.5" /> Não se sustenta
                  </button>
                  {it.revisado && <Selo ok={it.apto} sim="Apto" nao="Revisado, não apto" />}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------- Lab

function Lab() {
  const [dados, setDados] = useState(null);
  const [relato, setRelato] = useState(null);

  useEffect(() => {
    api.get("/admin/curadoria/lab").then(({ data }) => setDados(data)).catch(() => setDados({ pares: [] }));
    api.get("/admin/curadoria/concordancia").then(({ data }) => setRelato(data)).catch(() => setRelato(null));
  }, []);

  if (!dados) return <Vazio texto="Cruzando traços, autorrelatos e retestes..." />;

  return (
    <div className="mt-6 space-y-4" data-testid="curadoria-lab">
      <div className="card-sapiens rounded-2xl p-5">
        <p className="font-display text-lg font-bold tracking-tight text-zinc-950">{dados.veredito}</p>
        <p className="mt-2 text-xs leading-relaxed text-zinc-500">
          O alvo é o {dados.alvo}. O Lab propõe revisão e nunca altera a ontologia — o que sai daqui
          entra na aba de revisão humana, item a item.
        </p>
      </div>

      {dados.pares.length === 0 && <Vazio texto="Ainda não há evidência agregada suficiente." />}

      {dados.pares.map((p) => (
        <div key={p.par} className="card-sapiens rounded-2xl p-5" data-testid={`lab-${p.par}`}>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="font-display font-bold text-zinc-950">
                {p.erro_nome} <span className="font-normal text-zinc-500">em {p.processo_nome}</span>
              </div>
              <div className="font-mono-alt text-[10px] uppercase tracking-wide text-zinc-400">{p.par}</div>
            </div>
            {p.sinais.length > 0 && <Selo ok={false} nao="Revisar anotação" />}
          </div>
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-zinc-600">
            <span>{p.alunos} aluno(s)</span>
            <span>{p.raizes} raiz(es)</span>
            <span>{p.intervencoes_mostradas} intervenção(ões), {p.dispensas} dispensada(s)</span>
            <span>{p.retestes_ok}/{p.retestes} reteste(s) ok</span>
            {p.autorrelatos > 0 && <span>{p.autorrelatos} autorrelato(s)</span>}
          </div>
          {p.sinais.map((s, i) => (
            <p key={i} className="mt-2 flex items-start gap-1.5 text-sm leading-relaxed text-amber-800">
              <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {s.texto}
            </p>
          ))}
          {!p.amostra_suficiente && p.sinais.length > 0 && (
            <p className="mt-2 text-xs text-zinc-500">
              Amostra ainda pequena ({dados.criterio.min_alunos} alunos e {dados.criterio.min_observacoes}{" "}
              observações são o mínimo) — o sinal aparece, mas o par não entra na fila de revisão.
            </p>
          )}
        </div>
      ))}

      {relato?.pares?.length > 0 && (
        <div className="card-sapiens rounded-2xl p-5" data-testid="lab-concordancia">
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-400">
            Autorrelato × raiz atribuída
          </div>
          <div className="mt-3 space-y-2">
            {relato.pares.map((l) => (
              <div key={l.par} className="flex flex-wrap items-center gap-3 text-xs text-zinc-600">
                <span className="font-mono-alt text-zinc-500">{l.par}</span>
                <span>{l.total} relato(s)</span>
                <span>{Math.round(l.fracao_contradicao * 100)}% dizem ter chutado</span>
                {l.suspeita_de_anotacao && <Selo ok={false} nao="Suspeita" />}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function AdminCuradoria() {
  const [aba, setAba] = useState("oferta");

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-4xl px-6 py-12 md:px-10">
        <div className="mb-3 flex items-center gap-3">
          <ShieldCheck className="h-4 w-4 text-sapiens-accent" />
          <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50">Admin · Curadoria</div>
        </div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-white" data-testid="admin-curadoria-title">
          Destravar a evidência
        </h1>
        <p className="mt-3 max-w-xl text-white/60">
          Enquanto o corpus não tiver revisão humana, todo perfil de aluno sai marcado como provisório e
          o produto só pode levantar hipótese. Esta tela é o caminho de saída.
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          {ABAS.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => setAba(a.id)}
              className={`pill inline-flex items-center gap-1.5 rounded-full border px-4 py-2 text-xs font-medium transition ${
                aba === a.id
                  ? "border-sapiens-accent bg-sapiens-accentSoft text-sapiens-navy"
                  : "border-white/15 text-white/60 hover:border-white/30"
              }`}
              data-testid={`curadoria-aba-${a.id}`}
            >
              <a.icone className="h-3.5 w-3.5" /> {a.rotulo}
            </button>
          ))}
        </div>

        {aba === "oferta" && <Oferta />}
        {aba === "revisao" && <Revisao />}
        {aba === "lab" && <Lab />}
      </div>
    </div>
  );
}
