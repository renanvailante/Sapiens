import { useEffect, useState } from "react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { Gift, ArrowRight, Zap } from "lucide-react";

/**
 * Admin · Indicações — quem trouxe quem, e quanto isso já custou em Sparks.
 *
 * A tela irmã de `AdminPromoCodes`, mas a pergunta é outra. Cupom é
 * marketing: o admin decide o valor e quer saber quantas contas entraram. A
 * indicação é um programa de comissão: o valor é derivado (metade da primeira
 * compra), e o que o admin precisa saber é quanto do faturamento voltou como
 * Spark — e quantos vínculos ainda não converteram.
 *
 * Por isso as três medidas do topo, e não uma lista só: sem elas, a resposta
 * para "vale a pena?" exigiria somar uma coluna à mão.
 */

function formatarData(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit" });
  } catch {
    return iso;
  }
}

function Pessoa({ ficha }) {
  return (
    <div className="min-w-0">
      <div className="truncate text-sm font-semibold text-zinc-950">{ficha.name || ficha.user_id}</div>
      <div className="truncate text-xs text-zinc-500">{ficha.email || "conta removida"}</div>
    </div>
  );
}

function Medida({ rotulo, valor, dica }) {
  return (
    <div className="card-sapiens rounded-2xl p-5">
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500">{rotulo}</div>
      <div className="mt-2 font-display text-3xl font-extrabold tracking-tighter text-zinc-950">{valor}</div>
      {dica && <div className="mt-1 text-xs text-zinc-500">{dica}</div>}
    </div>
  );
}

export default function AdminIndicacoes() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    api
      .get("/admin/indicacoes")
      .then(({ data }) => setDados(data))
      .catch((e) => setErro(errMsg(e, "Não foi possível carregar as indicações.")));
  }, []);

  const itens = dados?.items || [];

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="mb-3 flex items-center gap-3">
          <Gift className="h-4 w-4 text-sapiens-accent" />
          <div className="secao-olho">Admin · Indicações</div>
        </div>
        <h1 className="titulo-tela" data-testid="admin-indicacoes-title">
          Quem trouxe quem
        </h1>
        <p className="mt-3 max-w-lg text-white/60">
          Cada aluno tem um código pessoal. Quem se cadastra com ele fica ligado a quem indicou, e
          na <strong className="font-semibold text-white/85">primeira compra</strong> do indicado o
          indicador recebe metade dos Sparks daquele pacote — uma vez por amigo.
        </p>

        {erro && <div className="mt-6 card-sapiens rounded-2xl p-6 text-sm text-zinc-600">{erro}</div>}

        {dados && (
          <>
            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              <Medida rotulo="Vínculos" valor={dados.total} dica="contas criadas com um código de aluno" />
              <Medida
                rotulo="Converteram"
                valor={dados.ja_converteram}
                dica="indicados que já fizeram a primeira compra"
              />
              <Medida rotulo="Sparks pagos" valor={dados.sparks_pagos} dica="total creditado a indicadores" />
            </div>

            <div className="mt-6 space-y-3">
              {itens.length === 0 && (
                <div className="card-sapiens rounded-2xl p-8 text-center text-sm text-zinc-500">
                  Nenhuma indicação registrada ainda.
                </div>
              )}
              {itens.map((l, i) => (
                <div
                  key={i}
                  className="card-sapiens flex flex-col gap-4 rounded-2xl p-5 md:flex-row md:items-center"
                  data-testid="admin-indicacao-linha"
                >
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <Pessoa ficha={l.indicador} />
                    <ArrowRight className="h-4 w-4 shrink-0 text-zinc-300" />
                    <Pessoa ficha={l.indicado} />
                  </div>
                  <div className="flex shrink-0 items-center gap-4">
                    <div className="text-right">
                      <div className="font-mono-alt text-xs font-bold tracking-wide text-zinc-500">
                        {l.codigo || "—"}
                      </div>
                      <div className="text-[11px] text-zinc-400">entrou em {formatarData(l.created_at)}</div>
                    </div>
                    {l.premio_em ? (
                      <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700">
                        <Zap className="h-3.5 w-3.5" /> {l.premio_sparks}
                      </span>
                    ) : (
                      <span className="shrink-0 rounded-full border border-zinc-200 bg-zinc-100 px-3 py-1.5 text-xs text-zinc-500">
                        sem compra
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
