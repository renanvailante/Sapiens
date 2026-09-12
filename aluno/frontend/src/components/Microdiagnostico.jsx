import { useState } from "react";
import { api } from "../lib/api";
import { CircleHelp, Check } from "lucide-react";

/**
 * Microdiagnóstico (Fase 3) — a única pergunta que o Sapiens faz ao aluno.
 *
 * Dois alunos marcam a alternativa C pelo mesmo motivo aparente e por processos
 * completamente diferentes. Até aqui o motor inferia a causa de
 * `distratores[].erros_esperados[]` — a hipótese do ANOTADOR sobre quem marca
 * aquele distrator. Ninguém perguntava ao aluno.
 *
 * Três decisões que este componente carrega, e que não são de interface:
 *
 *  - **Alternativas fechadas, nunca texto livre.** Texto livre exigiria um
 *    modelo para classificar, e um classificador produzindo vínculo causal
 *    fora do catálogo é a mesma regra violada por outra porta.
 *  - **Um toque, e acabou.** A resposta vai embora sozinha; não há botão de
 *    confirmar, não há segunda tela.
 *  - **Pular é indistinguível de não ter recebido.** Quem ignora não é
 *    lembrado, não é contado e não é perguntado de novo por causa disso — a
 *    tela simplesmente não chama a rota.
 *
 * O que o aluno responde aqui NUNCA vira causa do erro dele: entra em campo
 * próprio, com produtor próprio, e serve para descobrir anotação ruim.
 */
export default function Microdiagnostico({ pergunta, onRespondido }) {
  const [escolhida, setEscolhida] = useState(null);
  const [oculto, setOculto] = useState(false);

  if (!pergunta || oculto) return null;

  const responder = async (opcao) => {
    if (escolhida) return;
    setEscolhida(opcao.id);
    onRespondido?.(opcao.id);
    try {
      await api.post("/revisao/microdiagnostico", {
        event_id: pergunta.event_id,
        opcao: opcao.id,
        par: pergunta.par,
      });
    } catch {
      // Silencioso: o valor deste dado é estatístico, e um erro de rede não
      // pode virar um alerta na cara de quem está no meio de uma prova.
    }
  };

  return (
    <div className="mt-4 rounded-2xl border border-zinc-200 bg-white/70 p-4" data-testid="microdiagnostico">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-400">
          <CircleHelp className="h-3.5 w-3.5" /> {pergunta.pergunta}
        </div>
        {!escolhida && (
          <button
            type="button"
            onClick={() => setOculto(true)}
            className="shrink-0 text-[11px] text-zinc-400 underline-offset-2 hover:underline"
            data-testid="microdiagnostico-pular"
          >
            pular
          </button>
        )}
      </div>

      {escolhida ? (
        <div className="mt-2 flex items-center gap-1.5 text-sm text-emerald-700" data-testid="microdiagnostico-ok">
          <Check className="h-4 w-4" /> Anotado. Isso ajuda a melhorar as questões.
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          {pergunta.opcoes.map((o) => (
            <button
              key={o.id}
              type="button"
              onClick={() => responder(o)}
              className="pill rounded-full border border-zinc-200 px-3.5 py-2 text-xs font-medium text-zinc-600 transition hover:border-sapiens-accent hover:text-sapiens-navy"
              data-testid={`microdiagnostico-${o.id}`}
            >
              {o.rotulo}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
