import { useEffect, useMemo, useState } from "react";
import { Sparkles, Loader2, ArrowRight, ChevronDown } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { avisarSparksMudou } from "./Nav";

/**
 * Gerar questões novas — agora com endereço.
 *
 * A ferramenta existia, mas só dentro do briefing de uma habilidade do mapa
 * (`TreinoHabilidades`) ou como botão de uma resposta da Mentis. Quem abria
 * "Minhas questões" via uma lista vazia e uma frase mandando procurar em
 * OUTRA tela — a definição de ferramenta escondida.
 *
 * Nada de novo por baixo: mesma rota
 * (`POST /treino/habilidade/{hab_id}/gerar`), mesmo preço servido por
 * `/treino/precos`, mesma chave de idempotência. A única coisa que este
 * componente acrescenta é o seletor da habilidade — que antes vinha implícito
 * do lugar de onde o botão era clicado.
 *
 * Regra que não muda: o custo total aparece NO botão, antes do clique.
 */
export default function GerarQuestoesPainel({ habIdInicial, aoGerar }) {
  const [habilidades, setHabilidades] = useState([]);
  const [habId, setHabId] = useState(habIdInicial || "");
  const [quantidade, setQuantidade] = useState(5);
  const [custoPorQuestao, setCustoPorQuestao] = useState(null);
  const [estado, setEstado] = useState("idle");
  const [erro, setErro] = useState(null);
  const [resposta, setResposta] = useState(null);

  useEffect(() => {
    api.get("/treino/habilidades").then(({ data }) => setHabilidades(data.habilidades || [])).catch(() => {});
    api.get("/treino/precos").then(({ data }) => setCustoPorQuestao(data.custo_por_questao)).catch(() => {});
  }, []);

  // Sugestão de ponto de partida: a habilidade mais fraca com amostra. É a
  // mesma ordem que o Painel usa para as missões — não uma segunda opinião.
  const sugeridas = useMemo(() => {
    const fracas = habilidades
      .filter((h) => h.respondidas > 0 && h.classificacao !== "forte")
      .sort((a, b) => (a.percentual ?? 100) - (b.percentual ?? 100));
    return [...fracas, ...habilidades.filter((h) => !h.respondidas)];
  }, [habilidades]);

  useEffect(() => {
    if (!habId && sugeridas.length) setHabId(sugeridas[0].hab_id);
  }, [sugeridas, habId]);

  const custoTotal = custoPorQuestao != null ? custoPorQuestao * quantidade : null;

  const gerar = () => {
    if (!habId) return;
    setEstado("enviando");
    setErro(null);
    const idempotency_key = `minhas-${habId}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    api
      .post(`/treino/habilidade/${habId}/gerar`, { quantidade, dificuldade: "MEDIO", idempotency_key })
      .then(({ data }) => {
        setResposta(data);
        setEstado(data.status === "ok" ? "pronto" : "erro");
        if (data.status !== "ok") setErro(data.mensagem);
        // O saldo mudou sem trocar de rota: sem este aviso o chip da barra
        // continuaria exibindo o valor de antes da cobrança.
        avisarSparksMudou();
        if (data.status === "ok") aoGerar?.(data);
      })
      .catch((e) => {
        setErro(errMsg(e, "Não foi possível gerar as questões agora."));
        setEstado("erro");
      });
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5" data-testid="gerar-questoes">
      <div className="flex items-center gap-2 font-display text-base font-bold text-white">
        <Sparkles className="h-4 w-4 text-[#7FD8FF]" /> Gerar questões sobre um ponto
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
        <label className="block text-xs">
          <span className="mb-1.5 block text-white/45">Habilidade</span>
          <span className="relative block">
            <select
              value={habId}
              onChange={(e) => setHabId(e.target.value)}
              className="w-full appearance-none rounded-xl border border-white/12 bg-white/5 px-3.5 py-2.5 pr-9 text-sm text-white outline-none focus:border-[#4FD9FF]/60"
              data-testid="gerar-questoes-hab"
            >
              {sugeridas.map((h) => (
                <option key={h.hab_id} value={h.hab_id}>
                  {h.nome}
                  {h.respondidas ? ` · ${Math.round(h.percentual ?? 0)}%` : " · nova"}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/35" />
          </span>
        </label>

        <label className="block text-xs">
          <span className="mb-1.5 block text-white/45">Quantidade</span>
          <input
            type="number"
            min={1}
            max={10}
            value={quantidade}
            onChange={(e) => setQuantidade(Math.max(1, Math.min(10, Number(e.target.value) || 1)))}
            className="w-20 rounded-xl border border-white/12 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-[#4FD9FF]/60"
            data-testid="gerar-questoes-quantidade"
          />
        </label>

        <button
          type="button"
          onClick={gerar}
          disabled={estado === "enviando" || !habId || custoTotal == null}
          className="pill btn-sapiens inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-medium disabled:opacity-50"
          data-testid="gerar-questoes-enviar"
        >
          {estado === "enviando" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {custoTotal == null ? "Gerar" : `Gerar · ${custoTotal} Sparks`}
        </button>
      </div>

      {custoPorQuestao != null && (
        <p className="mt-2.5 text-[11px] text-white/35">
          {custoPorQuestao} Sparks por questão. Você só paga pelas que forem entregues.
        </p>
      )}

      {erro && <p className="mt-2.5 text-xs text-rose-300" data-testid="gerar-questoes-erro">{erro}</p>}

      {estado === "pronto" && resposta && (
        <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-emerald-300" data-testid="gerar-questoes-ok">
          {resposta.quantidade} questões prontas, logo abaixo <ArrowRight className="h-3 w-3" />
        </p>
      )}
    </div>
  );
}
