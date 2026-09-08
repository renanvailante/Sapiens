import { useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, ArrowRight, Loader2 } from "lucide-react";
import { api, errMsg } from "../lib/api";

/**
 * Botão de ação que acompanha uma resposta da Mentis quando ela decide que
 * praticar uma habilidade específica é o próximo passo. Cobrança explícita e
 * separada da mensagem: clicar aqui NUNCA é silencioso — o custo aparece
 * antes de gastar, como em qualquer outra tela do produto. Reaproveita a
 * mesma rota já usada pelo painel "Praticar mais" do Treino
 * (`POST /treino/habilidade/{hab_id}/gerar`) — nenhuma cobrança nova.
 */
export default function MentisAcaoQuestoes({ acao }) {
  const [estado, setEstado] = useState("idle"); // idle | enviando | pronto | erro
  const [resposta, setResposta] = useState(null);
  const [erro, setErro] = useState(null);

  if (!acao || acao.tipo !== "gerar_questoes") return null;

  const custoTotal = acao.quantidade * acao.custo_por_questao;

  const gerar = () => {
    setEstado("enviando");
    setErro(null);
    const idempotency_key = `mentis-${acao.hab_id}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    api
      .post(`/treino/habilidade/${acao.hab_id}/gerar`, {
        quantidade: acao.quantidade,
        dificuldade: "MEDIO",
        idempotency_key,
      })
      .then(({ data }) => {
        setResposta(data);
        setEstado(data.status === "ok" ? "pronto" : "erro");
        if (data.status !== "ok") setErro(data.mensagem);
      })
      .catch((e) => {
        setErro(errMsg(e, "Não foi possível gerar as questões agora."));
        setEstado("erro");
      });
  };

  if (estado === "pronto" && resposta) {
    return (
      <Link
        to={`/minhas-questoes?hab_id=${acao.hab_id}`}
        className="pill mt-2 inline-flex items-center gap-1.5 rounded-full bg-emerald-400/10 border border-emerald-400/30 px-3.5 py-2 text-xs font-medium text-emerald-200 hover:bg-emerald-400/15"
        data-testid="mentis-acao-ver-questoes"
      >
        {resposta.quantidade} questões prontas — fazer agora <ArrowRight className="w-3.5 h-3.5" />
      </Link>
    );
  }

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={gerar}
        disabled={estado === "enviando"}
        className="pill inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3.5 py-2 text-xs font-medium text-white/80 transition hover:border-white/25 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
        data-testid="mentis-acao-gerar-questoes"
      >
        {estado === "enviando" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
        Gerar {acao.quantidade} questões · {custoTotal} Sparks
      </button>
      {erro && <p className="mt-1.5 text-[11px] text-rose-300">{erro}</p>}
    </div>
  );
}
