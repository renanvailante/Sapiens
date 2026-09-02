import { useState } from "react";
import { toast } from "sonner";
import {
  Copy,
  Download,
  CheckCircle2,
  RotateCw,
  Pencil,
  Save,
  X,
  ChevronDown,
  ChevronRight,
  ArrowLeft,
  AlertTriangle,
} from "lucide-react";
import api from "@/lib/api";
import JsonViewer from "@/components/JsonViewer";

/**
 * Renderiza um item anotado no **Schema Sapiens 2.2**.
 *
 * Diferenças que mudam o que a tela mostra, não apenas onde ela lê:
 *  - domínios e competências são DERIVADOS dos processos (Constituição §4.4);
 *    a tela exibe de quais processos cada um veio, para que a derivação fique
 *    auditável em vez de parecer uma atribuição independente;
 *  - cada distrator carrega uma CADEIA ORDENADA de erro; o elo de `ordem 1` é a
 *    raiz e é o que determina a intervenção (Error Trace §1.1). A tela marca a
 *    raiz explicitamente — mostrar a cadeia como um conjunto desordenado
 *    perderia exatamente a propriedade que a torna útil;
 *  - o resultado da validação contra o catálogo vem do backend e é exibido:
 *    um item inválido precisa ficar visível para revisão, não silencioso.
 */

const PAPEL_COR = { nuclear: "#002FA7", secundario: "#52525B" };

function Tag({ children, color = "#09090B", testId, title }) {
  return (
    <span
      data-testid={testId}
      title={title}
      className="inline-flex items-center gap-1 font-mono text-[11px] px-2 py-1 border"
      style={{ borderColor: color, color }}
    >
      {children}
    </span>
  );
}

function Section({ title, count, children, testId, hint }) {
  return (
    <div className="border border-border bg-white" data-testid={testId}>
      <div className="px-5 py-3 border-b border-border flex items-center justify-between gap-3">
        <div>
          <div className="overline text-muted-foreground">{title}</div>
          {hint && <div className="text-[11px] text-muted-foreground mt-0.5">{hint}</div>}
        </div>
        <div className="font-mono text-xs text-muted-foreground shrink-0">{count}</div>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function Confianca({ valor }) {
  if (valor === null || valor === undefined) return <span className="text-muted-foreground">—</span>;
  // Bins do Error Trace §5: alta 0.7 / media 0.4 / baixa 0.15.
  const n = typeof valor === "number" ? valor : NaN;
  const rotulo = Number.isNaN(n) ? String(valor) : n >= 0.7 ? "alta" : n >= 0.4 ? "media" : "baixa";
  const cor = { alta: "#059669", media: "#B45309", baixa: "#71717A" }[rotulo] || "#71717A";
  return (
    <span className="font-mono text-[11px]" style={{ color: cor }}>
      {rotulo}
      {!Number.isNaN(n) && ` (${n})`}
    </span>
  );
}

export default function PipelineResult({ data, onReset, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState("");
  const [busy, setBusy] = useState(false);
  const [openProc, setOpenProc] = useState({});

  // `item` é a chave canônica; `pipeline` é a forma anterior, lida para não
  // quebrar a visualização de documentos gerados antes da migração.
  const item = data.item || data.pipeline || {};
  const questao = item.questao || {};
  const fonte = item.fonte || {};
  const ec = item.estrutura_cognitiva || {};
  const processos = ec.processos || [];
  const distratores = item.distratores || [];
  const validacao = data.validacao;

  const correta = (questao.alternativas || []).find((a) => a.correta === true)?.letra;
  const jsonStr = JSON.stringify(item, null, 2);

  const copyJson = async () => {
    await navigator.clipboard.writeText(jsonStr);
    toast.success("JSON copiado.");
  };
  const downloadJson = () => {
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${item.item_id || data.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Download iniciado.");
  };
  const validateJson = () => {
    if (validacao && validacao.valid === false) {
      toast.error(`Inválido contra o catálogo: ${validacao.errors.length} erro(s). Veja abaixo.`);
      return;
    }
    if (validacao && validacao.warnings?.length) {
      toast.warning(`Válido, com ${validacao.warnings.length} aviso(s).`);
      return;
    }
    if (validacao && validacao.valid) {
      toast.success(`Válido contra a ontologia ${item.ontology_version}.`);
      return;
    }
    toast.info("Este item ainda não foi validado pelo servidor.");
  };

  const regenerate = async () => {
    setBusy(true);
    try {
      const r = await api.post(`/pipeline/${data.id}/regenerate`);
      onUpdate(r.data);
      toast.success("Item reanotado.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Falha ao regenerar.");
    } finally {
      setBusy(false);
    }
  };

  const startEdit = () => {
    setEditText(jsonStr);
    setEditing(true);
  };
  const saveEdit = async () => {
    setBusy(true);
    try {
      const parsed = JSON.parse(editText);
      const r = await api.put(`/pipeline/${data.id}`, { item: parsed });
      onUpdate(r.data);
      setEditing(false);
      toast.success("Item atualizado manualmente.");
    } catch (e) {
      toast.error("Falha: " + (e?.response?.data?.detail || e.message));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-2 space-y-6" data-testid="pipeline-result">
      <button
        onClick={onReset}
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        data-testid="new-pipeline-btn"
      >
        <ArrowLeft className="h-4 w-4" /> Gerar outra questão
      </button>

      {validacao && validacao.valid === false && (
        <div className="border-2 border-rose-600 bg-rose-50 p-4" data-testid="validacao-erros">
          <div className="flex items-center gap-2 font-bold text-rose-800">
            <AlertTriangle className="h-4 w-4" />
            Item fora do contrato — {validacao.errors.length} violação(ões)
          </div>
          <p className="mt-1 text-xs text-rose-900">
            O item foi armazenado assim mesmo, para revisão humana. Ele não pode
            alimentar o estado de nenhum estudante enquanto não for revisado.
          </p>
          <ul className="mt-2 list-disc pl-5 text-sm text-rose-900 space-y-1">
            {validacao.errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}
      {validacao?.warnings?.length > 0 && (
        <div className="border border-amber-500 bg-amber-50 p-4" data-testid="validacao-avisos">
          <div className="font-bold text-amber-800 text-sm">
            {validacao.warnings.length} aviso(s) de anotação
          </div>
          <ul className="mt-2 list-disc pl-5 text-sm text-amber-900 space-y-1">
            {validacao.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Header block */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-0 border border-border bg-white">
        <div className="lg:col-span-8 p-6 border-b lg:border-b-0 lg:border-r border-border">
          <div className="overline text-muted-foreground">Questão detectada</div>
          <div className="mt-2 text-xl font-bold" data-testid="questao-tema">
            {fonte.tema || "Tema não identificado"}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            <span data-testid="questao-disciplina">{fonte.disciplina || "—"}</span>
            {fonte.banca && <> · <span>{fonte.banca}</span></>}
            {fonte.ano && <> · <span>{fonte.ano}</span></>}
            {fonte.prova && <> · <span>{fonte.prova}</span></>}
            {fonte.numero && <> · <span>nº {fonte.numero}</span></>}
          </div>
          <p
            className="mt-4 text-sm leading-relaxed whitespace-pre-wrap"
            data-testid="questao-enunciado"
          >
            {questao.enunciado || "—"}
          </p>
          {questao.alternativas?.length > 0 && (
            <ul className="mt-4 space-y-1" data-testid="alternativas-list">
              {questao.alternativas.map((a) => (
                <li
                  key={a.letra}
                  className={`flex gap-3 text-sm py-1 px-2 border-l-2 ${
                    a.correta === true
                      ? "border-emerald-600 bg-emerald-50"
                      : "border-transparent"
                  }`}
                >
                  <span className="font-mono font-bold w-6">{a.letra})</span>
                  <span>{a.texto}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="lg:col-span-4 p-6 space-y-4">
          <div>
            <div className="overline text-muted-foreground">Resposta correta</div>
            <div
              className="mt-1 text-3xl font-black text-emerald-700 font-mono"
              data-testid="resposta-correta"
            >
              {correta || "—"}
            </div>
          </div>
          <div>
            <div className="overline text-muted-foreground">Confiança global</div>
            <div className="mt-1 text-sm">
              <Confianca valor={item.qualidade?.confianca_global} />
            </div>
          </div>
          <div>
            <div className="overline text-muted-foreground">Ontologia · Schema</div>
            <div className="mt-1 font-mono text-xs" data-testid="versoes">
              {item.ontology_version || "—"} · v{item.schema_version || "—"}
            </div>
          </div>
          <div>
            <div className="overline text-muted-foreground">item_id</div>
            <div className="mt-1 font-mono text-[11px] break-all" data-testid="item-id">
              {item.item_id || "—"}
            </div>
          </div>
          <div className="pt-2 flex flex-wrap gap-2">
            <ActionBtn onClick={copyJson} icon={Copy} label="Copiar" testId="btn-copy" />
            <ActionBtn onClick={downloadJson} icon={Download} label="Baixar" testId="btn-download" />
            <ActionBtn onClick={validateJson} icon={CheckCircle2} label="Validar" testId="btn-validate" />
            <ActionBtn onClick={regenerate} icon={RotateCw} label="Regenerar" disabled={busy} testId="btn-regenerate" />
            <ActionBtn onClick={editing ? () => setEditing(false) : startEdit} icon={editing ? X : Pencil} label={editing ? "Cancelar" : "Editar"} testId="btn-edit" />
          </div>
        </div>
      </div>

      {/* Incerteza — sinal estruturado, exigido pelo Manual §12 regra 2 */}
      {item.incerteza?.marcadores?.length > 0 && (
        <Section
          title="Incerteza registrada"
          count={item.incerteza.marcadores.length}
          testId="section-incerteza"
          hint="Vocabulário fechado do Schema 2.2. Alimenta a fila de revisão de granularidade."
        >
          <div className="flex flex-wrap gap-2">
            {item.incerteza.marcadores.map((m) => (
              <Tag key={m} color="#B45309" testId={`tag-inc-${m}`}>{m}</Tag>
            ))}
          </div>
          {item.incerteza.detalhe && (
            <p className="mt-3 text-sm text-muted-foreground">{item.incerteza.detalhe}</p>
          )}
          {item.incerteza.requer_arbitragem && (
            <p className="mt-2 text-xs font-bold text-amber-800">
              Requer arbitragem de governança.
            </p>
          )}
        </Section>
      )}

      {/* Derivados */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Section
          title="Domínios"
          count={ec.dominios?.length ?? 0}
          testId="section-dominios"
          hint="Derivados por união dos processos — nunca atribuídos à parte."
        >
          <ul className="space-y-2">
            {(ec.dominios || []).map((d) => (
              <li key={d.id} className="flex items-center gap-3 flex-wrap">
                <Tag color="#002FA7" testId={`tag-dom-${d.id}`}>{d.id}</Tag>
                <span className="font-mono text-[11px] text-muted-foreground">
                  peso {d.peso_no_item ?? "—"}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  de {(d.derivado_de || []).join(", ") || "—"}
                </span>
              </li>
            ))}
            {(ec.dominios || []).length === 0 && (
              <li className="text-xs text-muted-foreground">Nenhum domínio derivado.</li>
            )}
          </ul>
        </Section>

        <Section
          title="Competências"
          count={ec.competencias?.length ?? 0}
          testId="section-competencias"
          hint="Agrupamento recalculável a partir dos processos."
        >
          <ul className="space-y-2">
            {(ec.competencias || []).map((c) => (
              <li key={c.id} className="flex items-center gap-3 flex-wrap">
                <Tag color="#059669" testId={`tag-comp-${c.id}`}>{c.id}</Tag>
                <span className="font-mono text-[11px] text-muted-foreground">
                  peso {c.peso_no_item ?? "—"}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  de {(c.derivado_de || []).join(", ") || "—"}
                </span>
              </li>
            ))}
            {(ec.competencias || []).length === 0 && (
              <li className="text-xs text-muted-foreground">Nenhuma competência derivada.</li>
            )}
          </ul>
        </Section>
      </div>

      {/* Processos cognitivos */}
      <Section
        title="Processos Cognitivos"
        count={processos.length}
        testId="section-processos"
        hint="No máximo 2 com peso (Manual §4). Pesos somam 1.0."
      >
        <ul>
          {processos.map((p, i) => {
            const isOpen = openProc[p.id + i];
            const papelColor = PAPEL_COR[p.papel] || "#09090B";
            return (
              <li key={p.id + i} className="border-b border-border last:border-b-0 py-3">
                <div className="flex items-center gap-3 flex-wrap">
                  <Tag color={papelColor} testId={`tag-proc-${p.id}`}>{p.id}</Tag>
                  <span
                    className="font-mono text-[10px] uppercase tracking-widest"
                    style={{ color: papelColor }}
                  >
                    {p.papel || "—"}
                  </span>
                  <span className="font-mono text-[11px] text-muted-foreground">
                    peso {p.peso_no_item ?? "—"}
                  </span>
                  <Confianca valor={p.confianca} />
                  <button
                    data-testid={`proc-justify-${p.id}`}
                    onClick={() => setOpenProc((s) => ({ ...s, [p.id + i]: !isOpen }))}
                    className="ml-auto flex items-center gap-1 text-xs underline text-muted-foreground"
                  >
                    {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                    {isOpen ? "Ocultar evidências" : "Mostrar evidências"}
                  </button>
                </div>
                {p.habilidades?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2 pl-1">
                    {p.habilidades.map((h) => (
                      <Tag
                        key={h.id}
                        color={h.aproximado ? "#B45309" : "#52525B"}
                        testId={`tag-hab-${h.id}`}
                        title={h.aproximado ? "Encaixe aproximado (Manual §6, regra 4)" : undefined}
                      >
                        {h.id}{h.aproximado ? " ~" : ""}
                      </Tag>
                    ))}
                  </div>
                )}
                {isOpen && (
                  <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4 pl-1 border-l-2 ml-2" style={{ borderColor: papelColor }}>
                    <Justify title="Trechos do enunciado" items={p.evidencias?.trechos} />
                    <Justify title="Figuras usadas" items={p.evidencias?.figuras} />
                    <Justify title="Justificativa" text={p.justificativa} />
                  </div>
                )}
              </li>
            );
          })}
          {processos.length === 0 && (
            <li className="text-xs text-muted-foreground">
              Nenhum processo cognitivo identificado.
            </li>
          )}
        </ul>
      </Section>

      {/* Distratores — cadeia ORDENADA */}
      <Section
        title="Distratores"
        count={distratores.length}
        testId="section-distratores"
        hint="Cadeia ordenada: o elo 1 é a raiz e determina a intervenção (Error Trace §1.1)."
      >
        <ul className="space-y-5">
          {distratores.map((d, i) => (
            <li key={i} className="flex items-start gap-4">
              <span className="font-mono font-bold text-lg w-6 shrink-0">{d.alternativa}</span>
              <div className="flex-1 min-w-0">
                <ol className="space-y-2">
                  {[...(d.erros_esperados || [])]
                    .sort((a, b) => (a.ordem ?? 99) - (b.ordem ?? 99))
                    .map((elo, j) => (
                      <li key={j} className="flex items-center gap-2 flex-wrap">
                        <span
                          className={`font-mono text-[10px] px-1.5 py-0.5 ${
                            elo.ordem === 1
                              ? "bg-rose-600 text-white font-bold"
                              : "bg-zinc-200 text-zinc-700"
                          }`}
                          title={elo.ordem === 1 ? "Raiz da cadeia" : "Elo decorrente"}
                        >
                          {elo.ordem === 1 ? "RAIZ" : `→ ${elo.ordem}`}
                        </span>
                        <Tag color="#E11D48" testId={`tag-err-${d.alternativa}-${elo.ordem}`}>
                          {elo.erro}
                        </Tag>
                        <span className="font-mono text-[11px] text-muted-foreground">
                          em {elo.processo_afetado}
                        </span>
                        <Confianca valor={elo.confianca} />
                        {elo.mecanismo && (
                          <Tag color="#7C3AED" title="Eixo do mecanismo — provisório (Error Trace §4)">
                            {elo.mecanismo}
                          </Tag>
                        )}
                      </li>
                    ))}
                  {(d.erros_esperados || []).length === 0 && (
                    <li className="text-xs text-muted-foreground">Cadeia de erro não anotada.</li>
                  )}
                </ol>
                {d.explicacao && (
                  <p className="mt-2 text-sm text-muted-foreground">{d.explicacao}</p>
                )}
              </div>
            </li>
          ))}
          {distratores.length === 0 && (
            <li className="text-xs text-muted-foreground">Nenhum distrator anotado.</li>
          )}
        </ul>
      </Section>

      {/* Intervenções */}
      {item.intervencoes?.length > 0 && (
        <Section
          title="Intervenções"
          count={item.intervencoes.length}
          testId="section-intervencoes"
          hint="Selecionadas a partir do elo de ordem 1, nunca da manifestação de superfície."
        >
          <ul className="space-y-3">
            {item.intervencoes.map((it, i) => (
              <li key={i} className="flex items-start gap-3 flex-wrap">
                <Tag color="#0891B2" testId={`tag-int-${it.id}`}>{it.id}</Tag>
                <span className="font-mono text-[11px] text-muted-foreground">
                  gatilho: {it.gatilho?.erro || "—"} em {it.gatilho?.processo || "—"}
                </span>
                {it.acao && <p className="w-full text-sm text-muted-foreground">{it.acao}</p>}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Full JSON */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="overline text-muted-foreground">JSON completo (Schema 2.2)</div>
          {editing && (
            <button
              data-testid="btn-save-edit"
              onClick={saveEdit}
              disabled={busy}
              className="flex items-center gap-2 bg-primary text-white px-3 py-1.5 text-xs font-bold hover:bg-foreground disabled:opacity-50"
            >
              <Save className="h-3 w-3" /> Salvar edição
            </button>
          )}
        </div>
        {editing ? (
          <textarea
            data-testid="json-editor"
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            className="w-full h-[500px] font-mono text-[12.5px] bg-white border border-border p-4"
          />
        ) : (
          <JsonViewer data={item} testId="pipeline-json" />
        )}
      </div>
    </div>
  );
}

function ActionBtn({ onClick, icon: Icon, label, disabled, testId }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className="flex items-center gap-1.5 border border-border bg-white px-3 py-1.5 text-xs font-medium hover:bg-foreground hover:text-white disabled:opacity-50"
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}

function Justify({ title, items, text }) {
  const hasItems = Array.isArray(items) && items.length > 0;
  return (
    <div className="pl-3">
      <div className="overline text-muted-foreground mb-1">{title}</div>
      {hasItems ? (
        <ul className="list-disc pl-5 text-sm space-y-1">
          {items.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      ) : text ? (
        <p className="text-sm">{text}</p>
      ) : (
        <p className="text-xs text-muted-foreground">Não informado.</p>
      )}
    </div>
  );
}
