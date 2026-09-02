import { useState } from "react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import EstadoDeErro from "../components/EstadoDeErro";
import { useCarregamento } from "../hooks/useCarregamento";
import { PenLine, Loader2, AlertTriangle, ChevronLeft } from "lucide-react";

const MIN_CARACTERES = 200;

// As cinco competências do ENEM, 0–200 cada. Os rótulos são os oficiais,
// encurtados para caber na tela; o corretor devolve só o `id`.
const COMPETENCIAS = {
  "COMP-I": "Domínio da norma culta",
  "COMP-II": "Compreensão do tema",
  "COMP-III": "Seleção e organização de argumentos",
  "COMP-IV": "Mecanismos linguísticos (coesão)",
  "COMP-V": "Proposta de intervenção",
};

function BarraCompetencia({ comp }) {
  const pontos = comp.nivel_pontos;
  const naoConfirmado = comp.nivel_candidato_nao_confirmado;
  const exibido = pontos ?? naoConfirmado ?? 0;
  const pct = Math.round((exibido / 200) * 100);

  return (
    <div data-testid={`redacao-comp-${comp.id}`}>
      <div className="flex items-baseline justify-between text-sm mb-1">
        <span className="text-zinc-700">{COMPETENCIAS[comp.id] || comp.id}</span>
        <span className="font-mono-alt font-bold text-zinc-900">
          {exibido}
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
          Estimativa não confirmada — este critério precisa de revisão humana.
        </div>
      )}
      {comp.cap_aplicado && (
        <div className="mt-1 text-[11px] text-zinc-500">Teto aplicado por outro critério da redação.</div>
      )}
    </div>
  );
}

function Resultado({ avaliacao, aoEscreverOutra }) {
  const anulada = avaliacao.estado_geral === "ANULADA";

  return (
    <div className="space-y-4" data-testid="redacao-resultado">
      <div className={`card-sapiens rounded-2xl p-8 text-center ${anulada ? "border-rose-200" : ""}`}>
        <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">
          {anulada ? "Redação anulada" : "Nota estimada"}
        </div>
        <div className="mt-2 font-display text-6xl font-extrabold tracking-tighter text-zinc-950">
          {avaliacao.nota_total}
          <span className="text-zinc-300 text-3xl">/1000</span>
        </div>
        {avaliacao.necessita_revisao_humana && (
          <div className="mt-4 inline-flex items-start gap-2 text-left rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-900">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>
              Esta é uma <strong>estimativa</strong>. Parte dos critérios não pôde ser decidida com
              segurança automaticamente — a nota real de um corretor humano pode ser diferente.
            </span>
          </div>
        )}
      </div>

      {avaliacao.gatilhos_disparados?.length > 0 && (
        <div className="card-sapiens rounded-2xl p-6" data-testid="redacao-gatilhos">
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-rose-700 mb-3">
            Motivos de anulação identificados
          </div>
          <ul className="space-y-1.5 text-sm text-zinc-700">
            {avaliacao.gatilhos_disparados.map((g, i) => (
              <li key={i}>· {g.descricao || g.nome || g.id}</li>
            ))}
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

      {avaliacao.tangenciamento_detectado && (
        <div className="card-sapiens rounded-2xl p-6 text-sm text-zinc-700">
          <strong className="text-zinc-900">Tangenciamento do tema.</strong> O texto passa perto do
          tema proposto, mas não o enfrenta diretamente — no ENEM isso limita a nota das
          competências II e III.
        </div>
      )}

      <button
        onClick={aoEscreverOutra}
        className="pill btn-sapiens inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-medium"
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
  const [avaliacao, setAvaliacao] = useState(null);
  const [erro, setErro] = useState(null);

  const { dados: historico, recarregar } = useCarregamento(
    async () => (await api.get("/redacao")).data.items || [],
    [],
  );

  const enviar = async (e) => {
    e.preventDefault();
    setEnviando(true);
    setErro(null);
    try {
      const { data } = await api.post("/redacao", {
        texto,
        tema_frase: tema.trim() || null,
      });
      setAvaliacao(data.avaliacao);
      recarregar();
    } catch (err) {
      setErro(errMsg(err, "Não foi possível corrigir agora. Tente de novo em alguns minutos."));
    } finally {
      setEnviando(false);
    }
  };

  const escreverOutra = () => {
    setAvaliacao(null);
    setTexto("");
    setTema("");
  };

  const faltam = Math.max(0, MIN_CARACTERES - texto.trim().length);

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
            Correção pelas cinco competências do ENEM, com os critérios oficiais. A maior parte da
            análise roda localmente — só o que fica em dúvida vai para a IA.
          </p>
        )}

        <div className="mt-10">
          {avaliacao ? (
            <Resultado avaliacao={avaliacao} aoEscreverOutra={escreverOutra} />
          ) : (
            <form onSubmit={enviar} className="card-sapiens rounded-2xl p-6 md:p-8 space-y-5">
              <div>
                <label className="text-xs font-medium text-zinc-500 mb-1.5 block">
                  Tema proposto <span className="text-zinc-400">(opcional, mas melhora muito a análise)</span>
                </label>
                <input
                  value={tema}
                  onChange={(e) => setTema(e.target.value)}
                  maxLength={1000}
                  placeholder="Ex.: Desafios para a valorização de comunidades e povos tradicionais no Brasil"
                  className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none"
                  data-testid="redacao-tema"
                />
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
                disabled={enviando || faltam > 0}
                className="pill btn-sapiens inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-medium disabled:opacity-40"
                data-testid="redacao-enviar"
              >
                {enviando
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Corrigindo...</>
                  : <><PenLine className="w-4 h-4" /> Corrigir minha redação</>}
              </button>
            </form>
          )}
        </div>

        {historico?.length > 0 && !avaliacao && (
          <div className="mt-10">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-white/50 mb-3">
              Redações anteriores
            </div>
            <div className="space-y-2">
              {historico.map(({ redacao, avaliacao: av }) => (
                <button
                  key={redacao.redacao_id}
                  onClick={() => av && setAvaliacao(av)}
                  className="card-sapiens rounded-xl p-4 w-full text-left flex items-center justify-between gap-4"
                  data-testid={`redacao-historico-${redacao.redacao_id}`}
                >
                  <div className="min-w-0">
                    <div className="text-sm text-zinc-800 truncate">
                      {redacao.tema_frase || redacao.texto.slice(0, 70) + "..."}
                    </div>
                    <div className="text-xs text-zinc-400 mt-0.5">
                      {new Date(redacao.created_at).toLocaleDateString("pt-BR")}
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
    </div>
  );
}
