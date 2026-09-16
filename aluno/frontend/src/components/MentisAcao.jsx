import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { CalendarDays, Loader2, ArrowRight } from "lucide-react";
import { api, errMsg } from "../lib/api";
import MentisAcaoQuestoes from "./MentisAcaoQuestoes";
import MentisAcaoIr from "./MentisAcaoIr";

/**
 * O botão que acompanha uma resposta da Mentis quando ela decide que o próximo
 * passo é uma AÇÃO, e não mais conversa.
 *
 * Dispatcher e não um componente só: cada ação tem custo e destino próprios, e
 * o `MentisWidget` e a página `/mentis` renderizam as duas do mesmo jeito sem
 * precisar saber quais existem.
 *
 * Regra que vale para todas: clicar nunca é silencioso. O custo aparece no
 * botão antes de gastar — e quando não há custo, o botão diz isso também.
 */

function AcaoCronograma() {
  const nav = useNavigate();
  const [estado, setEstado] = useState("idle");
  const [erro, setErro] = useState(null);

  // Montar a semana é grátis: a alocação é determinística (ver
  // `cronograma.py`), então não há chamada de modelo para cobrar. O que a
  // Mentis acrescenta ao cronograma é opcional e fica na própria tela.
  const montar = () => {
    setEstado("enviando");
    setErro(null);
    api
      .post("/cronograma/gerar", { com_mentis: false })
      .then(() => nav("/cronograma"))
      .catch((e) => {
        setErro(errMsg(e, "Não consegui montar sua semana agora."));
        setEstado("erro");
      });
  };

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={montar}
        disabled={estado === "enviando"}
        className="pill inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3.5 py-2 text-xs font-medium text-white/80 transition hover:border-white/25 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
        data-testid="mentis-acao-cronograma"
      >
        {estado === "enviando" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CalendarDays className="h-3.5 w-3.5" />}
        Montar minha semana · grátis
        {estado !== "enviando" && <ArrowRight className="h-3 w-3" />}
      </button>
      {erro && <p className="mt-1.5 text-[11px] text-rose-300">{erro}</p>}
    </div>
  );
}

export default function MentisAcao({ acao }) {
  if (!acao) return null;
  if (acao.tipo === "montar_cronograma") return <AcaoCronograma />;
  // "ir" é a ação que faz da Mentis uma camada de navegação, e não só um
  // chat: ela cita uma tela, e o botão leva até lá. Grátis, sempre.
  if (acao.tipo === "ir") return <MentisAcaoIr acao={acao} />;
  return <MentisAcaoQuestoes acao={acao} />;
}
