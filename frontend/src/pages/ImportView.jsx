import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useFilters } from "@/layout/AppLayout";
import { Panel, SemDado } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

const SAMPLE = `{
  "turma": "9º C",
  "periodo": "2025.2",
  "versao_taxonomia": "Taxonomia Sapiens v0.9 (Experimental)",
  "data_processamento": "2025-08-20T10:00:00Z",
  "modelo_analise": "sapiens-cognitive-v1.2",
  "ano_escolar": "9º ano",
  "banca": "Simulado Sapiens",
  "prova": "Prova bimestral 2025.2",
  "alunos": [
    {
      "aluno_id": "A101",
      "nome": "João Pereira",
      "erros_por_no": [
        {"no_id":"MAT.NUM.01","no_label":"Interpretação de números racionais","disciplina":"Matemática","taxa_erro":0.42,"num_questoes":6}
      ]
    }
  ]
}`;

export default function ImportView() {
  const { refreshFilters } = useFilters();
  const [text, setText] = useState("");
  const [imports, setImports] = useState([]);
  const [busy, setBusy] = useState(false);

  const loadImports = async () => {
    try {
      const { data } = await api.get("/imports");
      setImports(data || []);
    } catch (_) {
      // ignore
    }
  };

  useEffect(() => { loadImports(); }, []);

  const onFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const t = await f.text();
    setText(t);
  };

  const submit = async () => {
    let payload;
    try {
      payload = JSON.parse(text);
    } catch {
      toast.error("JSON inválido");
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post("/imports", payload);
      toast.success(`Importado: turma ${data.turma} · ${data.periodo}`);
      setText("");
      await loadImports();
      await refreshFilters();
    } catch (e) {
      toast.error(e.response?.data?.detail?.toString() || "Falha ao importar");
    } finally {
      setBusy(false);
    }
  };

  const deleteImport = async (id) => {
    if (!window.confirm("Remover este import?")) return;
    await api.delete(`/imports/${id}`);
    await loadImports();
    await refreshFilters();
    toast.success("Removido");
  };

  return (
    <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="import-view">
      <Panel title="Importar dados processados" subtitle="Cole ou carregue o JSON produzido pelo sistema Sapiens">
        <div className="space-y-3">
          <input
            data-testid="import-file-input"
            type="file"
            accept="application/json,.json"
            onChange={onFile}
            className="block text-sm"
          />
          <div className="flex gap-2 items-center">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setText(SAMPLE)}
              data-testid="import-sample-btn"
            >
              Usar exemplo
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setText("")}
              data-testid="import-clear-btn"
            >
              Limpar
            </Button>
          </div>
          <Textarea
            data-testid="import-json-textarea"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Cole aqui o JSON…"
            rows={16}
            className="font-mono text-xs"
          />
          <Button
            data-testid="import-submit-btn"
            disabled={busy || !text.trim()}
            onClick={submit}
            className="bg-[hsl(214_100%_34%)] text-white hover:bg-[hsl(214_100%_28%)]"
          >
            {busy ? "Enviando…" : "Importar"}
          </Button>
          <p className="text-[11px] text-muted-foreground">
            Os dados não são editáveis após importação. Campos ausentes serão exibidos como &quot;Sem dado&quot;.
          </p>
        </div>
      </Panel>

      <Panel title="Imports registrados" subtitle={`${imports.length} snapshots armazenados`}>
        <div className="border border-border">
          <table className="sapiens-table">
            <thead>
              <tr>
                <th>Turma</th>
                <th>Período</th>
                <th>Versão</th>
                <th>Ingerido em</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {imports.length === 0 && (
                <tr><td colSpan={5}><SemDado label="Nenhum import" /></td></tr>
              )}
              {imports.map((i) => (
                <tr key={i.import_id}>
                  <td>{i.turma || <SemDado />}</td>
                  <td>{i.periodo || <SemDado />}</td>
                  <td className="text-xs font-mono">{i.versao_taxonomia || <SemDado />}</td>
                  <td className="text-xs font-mono">{i._ingested_at?.slice(0, 19).replace("T", " ") || <SemDado />}</td>
                  <td className="num">
                    <button
                      onClick={() => deleteImport(i.import_id)}
                      data-testid={`delete-import-${i.import_id}`}
                      className="text-xs text-destructive underline"
                    >
                      remover
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
