import { useState } from "react";
import { api, errMsg } from "../lib/api";
import Mentis from "./Mentis";
import { Lightbulb, AlertTriangle, CircleCheck, Loader2, ChevronDown, ChevronRight } from "lucide-react";

/**
 * Intervenção da Mentis — o tratamento da CAUSA RAIZ de um erro.
 *
 * Não confundir com o "Saiba mais" (7 Sparks), que continua existindo e
 * intacto: aquele explica UMA QUESTÃO, este trata UMA DIFICULDADE. O primeiro
 * responde "por que a resposta é essa"; este responde "por que eu erro assim,
 * e como parar".
 *
 * Economia, que aqui é decisão de produto e não detalhe de implementação:
 *
 * - O conteúdo é gerado UMA vez por dificuldade (par erro × processo) e serve
 *   a todos os alunos que tiverem a mesma. São ~15 pares na ontologia vigente,
 *   então o produto inteiro tem algumas dezenas de gerações possíveis, para
 *   sempre.
 * - O que é do aluno não passa por IA: as questões que ELE errou, a
 *   alternativa que marcou e a resolução daqueles itens já vêm montadas de
 *   graça pelo motor. Quem chama passa isso em `evidencia` e a tela junta as
 *   duas metades.
 * - Um clique = uma requisição. O servidor decide sozinho se cobra (primeira
 *   vez) ou não (reabrir, refresh, voltar pelo Painel).
 *
 * Por isso o rótulo do botão diz "na primeira vez" em vez de prometer um
 * preço: mostrar "10 Sparks" a quem já desbloqueou seria mentira, e descobrir
 * quem já desbloqueou custaria uma leitura por render.
 */

const CUSTO = 10; // espelha INTERVENCAO_COST; o servidor é quem cobra de fato

function Secao({ titulo, children }) {
  return (
    <div>
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400 mb-1.5">{titulo}</div>
      {children}
    </div>
  );
}

function Conteudo({ dados, evidencia }) {
  const c = dados.conteudo;
  const previa = dados.previa;
  if (!c) return null;
  return (
    <div className="mt-3 space-y-5">
      <p className="text-sm leading-relaxed text-zinc-700">{c.o_que_acontece}</p>

      <div className="rounded-xl border border-zinc-200 bg-white p-4 space-y-2.5">
        <Secao titulo="Como isso aparece">
          <p className="text-sm text-zinc-700">{c.exemplo.situacao}</p>
        </Secao>
        <div className="border-l-2 border-rose-200 pl-3">
          <div className="text-[11px] font-bold uppercase tracking-wide text-rose-600">O passo em falso</div>
          <p className="text-sm text-zinc-600">{c.exemplo.raciocinio_errado}</p>
        </div>
        <div className="border-l-2 border-emerald-200 pl-3">
          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-700">Onde corrigir</div>
          <p className="text-sm text-zinc-700">{c.exemplo.correcao}</p>
        </div>
      </div>

      <Secao titulo="Treino — use na próxima questão">
        <ol className="space-y-1.5">
          {c.treino.map((t, i) => (
            <li key={i} className="flex gap-2 text-sm text-zinc-700">
              <span className="font-mono-alt text-sapiens-accentDeep shrink-0">{i + 1}.</span>
              <span>{t}</span>
            </li>
          ))}
        </ol>
      </Secao>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl bg-amber-50 border border-amber-100 p-3">
          <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-amber-700 mb-1">
            <AlertTriangle className="w-3.5 h-3.5" /> Sinal de alerta
          </div>
          <p className="text-sm text-amber-900">{c.sinal_de_alerta}</p>
        </div>
        <div className="rounded-xl bg-sky-50 border border-sky-100 p-3">
          <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-sky-700 mb-1">
            <CircleCheck className="w-3.5 h-3.5" /> Antes de marcar, pergunte
          </div>
          <p className="text-sm text-sky-900">{c.checagem}</p>
        </div>
      </div>

      {/* Metade pessoal: vem do motor, sem IA e sem custo. Só aparece quando
          quem usou o componente já tinha essa informação na mão. */}
      {evidencia?.length > 0 && (
        <Secao titulo="Nas suas questões">
          <div className="space-y-1.5">
            {evidencia.slice(0, 4).map((e, i) => (
              <div key={i} className="text-sm text-zinc-600">
                <span className="font-mono-alt text-[11px] text-zinc-400">
                  {[e.banca, e.ano, e.numero ? `nº ${e.numero}` : null].filter(Boolean).join(" · ")}
                </span>
                {e.detalhe && <span className="ml-2">{e.detalhe}</span>}
              </div>
            ))}
          </div>
        </Secao>
      )}

      {previa?.intervencao_nome && (
        <div className="pt-3 border-t border-zinc-100 text-[11px] text-zinc-400">
          Abordagem catalogada: {previa.intervencao_nome}
        </div>
      )}
    </div>
  );
}

export default function IntervencaoMentis({
  erroId,
  processoId,
  causaNome,
  processoNome,
  evidencia,
  sparks,
  onSparks,
  aberta: abertaInicial = false,
  testid = "intervencao",
}) {
  const [aberta, setAberta] = useState(abertaInicial);
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);

  const semSaldo = sparks != null && sparks < CUSTO && !dados;

  const abrir = async () => {
    if (dados) {
      setAberta((v) => !v);
      return;
    }
    setAberta(true);
    setCarregando(true);
    setErro(null);
    try {
      const { data } = await api.post("/mentis/intervencao", { erro_id: erroId, processo_id: processoId });
      setDados(data);
      if (typeof data.sparks_balance === "number" && onSparks) onSparks(data.sparks_balance);
    } catch (e) {
      setErro(errMsg(e, "Não foi possível abrir a intervenção agora."));
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div className="rounded-xl border border-sapiens-navy/10 bg-white/70 p-4" data-testid={testid}>
      <button
        onClick={abrir}
        disabled={carregando || semSaldo}
        data-testid={`${testid}-btn`}
        className="w-full text-left disabled:cursor-not-allowed disabled:opacity-60"
      >
        <div className="flex items-start gap-3">
          <Mentis className="w-5 h-5 shrink-0 mt-0.5" variante="icone" estado={carregando ? "analise" : "neutra"} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="font-display font-bold text-sapiens-navy">Intervenção da Mentis</span>
              {dados && (
                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
                  {dados.cobrado > 0 ? `−${dados.cobrado} Sparks` : "já é sua"}
                </span>
              )}
            </div>
            <p className="mt-0.5 text-xs text-zinc-500">
              {causaNome ? (
                <>Trata a causa: <span className="font-medium text-zinc-700">{causaNome}</span></>
              ) : (
                <>Trata a causa do seu erro, não a questão</>
              )}
              {processoNome && <span className="text-zinc-400"> · {processoNome}</span>}
            </p>
            {!dados && !carregando && (
              <p className="mt-1.5 text-[11px] font-medium text-zinc-400">
                {semSaldo ? `Saldo insuficiente — ${CUSTO} Sparks` : `${CUSTO} Sparks na primeira vez. Depois, sempre sua.`}
              </p>
            )}
          </div>
          <span className="shrink-0 text-zinc-400 pt-0.5">
            {carregando ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : aberta && dados ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </span>
        </div>
      </button>

      {carregando && (
        <p className="mt-3 flex items-center gap-2 text-xs text-zinc-500">
          <Lightbulb className="w-3.5 h-3.5" /> A Mentis está preparando o tratamento desta dificuldade…
        </p>
      )}
      {erro && <p className="mt-3 text-xs font-medium text-rose-600" data-testid={`${testid}-erro`}>{erro}</p>}
      {aberta && dados && <Conteudo dados={dados} evidencia={evidencia} />}
    </div>
  );
}
