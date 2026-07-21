import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Panel, SemDado, EmptyState } from "@/components/common";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function TaxonomiaView() {
  const [versoes, setVersoes] = useState([]);
  const [versao, setVersao] = useState("");
  const [tree, setTree] = useState([]);
  const [selected, setSelected] = useState(null);
  const [openDisc, setOpenDisc] = useState({});

  useEffect(() => {
    api.get("/taxonomia").then(({ data }) => {
      setVersoes(data.versoes_disponiveis || []);
      setVersao(data.versoes_disponiveis?.slice(-1)[0] || "");
    });
  }, []);

  useEffect(() => {
    if (!versao) return;
    api.get("/taxonomia", { params: { versao } })
      .then(({ data }) => {
        setTree(data.arvore || []);
        const initOpen = {};
        (data.arvore || []).forEach((d, i) => { initOpen[d.disciplina] = i === 0; });
        setOpenDisc(initOpen);
        setSelected(null);
      });
  }, [versao]);

  return (
    <div className="p-6 space-y-4" data-testid="taxonomia-view">
      <div className="flex items-center gap-3">
        <span className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">Versão da taxonomia</span>
        <Select value={versao} onValueChange={setVersao}>
          <SelectTrigger data-testid="taxonomia-versao-select" className="h-8 min-w-[300px] text-xs">
            <SelectValue placeholder="Selecione uma versão" />
          </SelectTrigger>
          <SelectContent>
            {versoes.map((v) => (
              <SelectItem key={v} value={v}>{v}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <Panel title="Árvore da taxonomia" subtitle="Estrutura derivada dos dados importados">
            {tree.length === 0 ? (
              <EmptyState title="Sem dado" hint="Nenhum dado importado para esta versão." />
            ) : (
              <div className="divide-y divide-border border border-border">
                {tree.map((d) => (
                  <div key={d.disciplina}>
                    <button
                      data-testid={`disc-toggle-${d.disciplina}`}
                      onClick={() => setOpenDisc({ ...openDisc, [d.disciplina]: !openDisc[d.disciplina] })}
                      className="w-full flex items-center justify-between px-3 py-2 hover:bg-[hsl(0_0%_98%)] text-left"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] w-4 text-muted-foreground">
                          {openDisc[d.disciplina] ? "▾" : "▸"}
                        </span>
                        <span className="font-semibold text-sm" style={{ fontFamily: 'Chivo' }}>{d.disciplina}</span>
                        <span className="text-[11px] font-mono text-muted-foreground">{d.nos.length} nós</span>
                      </div>
                    </button>
                    {openDisc[d.disciplina] && (
                      <div>
                        {d.nos.map((n) => (
                          <button
                            key={n.no_id}
                            data-testid={`no-item-${n.no_id}`}
                            onClick={() => setSelected({ ...n, disciplina: d.disciplina })}
                            className={
                              "w-full flex items-center justify-between px-8 py-1.5 text-left text-sm border-t border-border " +
                              (selected?.no_id === n.no_id
                                ? "bg-[hsl(214_100%_34%)] text-white"
                                : "hover:bg-[hsl(0_0%_98%)]")
                            }
                          >
                            <div className="flex-1 min-w-0">
                              <div className="truncate">{n.no_label}</div>
                              <div className={"text-[10px] font-mono " + (selected?.no_id === n.no_id ? "text-white/70" : "text-muted-foreground")}>
                                {n.no_id}
                              </div>
                            </div>
                            <div className={"text-[11px] font-mono ml-2 " + (selected?.no_id === n.no_id ? "text-white/80" : "text-muted-foreground")}>
                              {n.num_questoes}q · {n.num_alunos}a
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>

        <div>
          <Panel title="Detalhes do nó">
            {!selected ? (
              <div className="text-sm text-muted-foreground">Clique em um nó da árvore para ver detalhes.</div>
            ) : (
              <div className="space-y-3">
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Nó</div>
                  <div className="text-lg tracking-tight" style={{ fontFamily: 'Chivo' }}>{selected.no_label}</div>
                  <div className="text-[11px] font-mono text-muted-foreground">{selected.no_id}</div>
                </div>
                <Detail label="Disciplina" value={selected.disciplina} />
                <Detail label="Versão taxonomia" value={versao} mono />
                <Detail label="Nº de questões (soma)" value={selected.num_questoes} />
                <Detail label="Nº de alunos com este nó" value={selected.num_alunos} />
                <div className="text-[11px] text-muted-foreground border-t pt-3 border-border">
                  IDs, descrições e hierarquia podem mudar entre versões. Não compare turmas de versões diferentes sem cautela.
                </div>
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value, mono }) {
  return (
    <div>
      <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className={"text-sm " + (mono ? "font-mono" : "")}>
        {value == null || value === "" ? <SemDado /> : value}
      </div>
    </div>
  );
}
