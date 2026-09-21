import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import {
  Megaphone, Plus, Copy, Wallet, ChevronDown, ChevronRight,
  Sparkles, Search, ExternalLink, Trash2, Ban, RotateCcw,
} from "lucide-react";

function reais(centavos) {
  if (centavos == null) return "—";
  return (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const ROTULO_STATUS = {
  lead: "Pendente", qualificado: "Qualificado", mensagem_pronta: "Mensagem pronta",
  contato: "Contatado", respondeu: "Respondeu", interessado: "Interessado",
  cadastrado: "Cadastrado", ativo: "Afiliado", recusado: "Recusou", removido: "Removido",
};

const RELEVANCIA_ROTULO = { alta: "Alta", media: "Média", baixa: "Baixa" };
const RELEVANCIA_COR = {
  alta: "bg-emerald-50 text-emerald-700 border-emerald-100",
  media: "bg-amber-50 text-amber-700 border-amber-100",
  baixa: "bg-zinc-100 text-zinc-500 border-zinc-200",
};

function dataCurta(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit" });
  } catch {
    return "—";
  }
}

const COR_STATUS = {
  lead: "bg-zinc-100 text-zinc-500 border-zinc-200",
  qualificado: "bg-sky-50 text-sky-700 border-sky-100",
  mensagem_pronta: "bg-indigo-50 text-indigo-700 border-indigo-100",
  contato: "bg-amber-50 text-amber-700 border-amber-100",
  respondeu: "bg-amber-50 text-amber-700 border-amber-100",
  interessado: "bg-violet-50 text-violet-700 border-violet-100",
  cadastrado: "bg-emerald-50 text-emerald-700 border-emerald-100",
  ativo: "bg-emerald-50 text-emerald-700 border-emerald-100",
  recusado: "bg-rose-50 text-rose-600 border-rose-100",
  removido: "bg-rose-50 text-rose-600 border-rose-100",
};

const PROXIMOS_STATUS = {
  lead: ["qualificado", "contato", "recusado"],
  qualificado: ["mensagem_pronta", "contato", "recusado"],
  mensagem_pronta: ["contato", "recusado"],
  contato: ["respondeu", "recusado"],
  respondeu: ["interessado", "recusado"],
  interessado: ["recusado"],
};

const PRIORIDADE_ROTULO = { alta: "Alta", media: "Média", baixa: "Baixa" };
const PRIORIDADE_COR = {
  alta: "bg-rose-50 text-rose-600 border-rose-100",
  media: "bg-amber-50 text-amber-700 border-amber-100",
  baixa: "bg-zinc-100 text-zinc-500 border-zinc-200",
};

// Allowlist de domínio no FRONTEND também — reforço, não a checagem
// autoritativa (essa é no backend, na gravação). Um link que não bate nunca
// vira `<a href>` clicável, só texto.
const DOMINIOS_SEGUROS = ["instagram.com", "www.instagram.com", "chat.whatsapp.com", "wa.me", "t.me", "telegram.me"];

function urlSegura(url) {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") return null;
    if (!DOMINIOS_SEGUROS.includes(parsed.hostname.toLowerCase())) return null;
    return url;
  } catch {
    return null;
  }
}

async function copiar(texto, rotulo) {
  try {
    await navigator.clipboard.writeText(texto);
    toast.success(`${rotulo} copiado.`);
  } catch {
    toast.error("O navegador bloqueou a cópia.");
  }
}

function Etiqueta({ children, className }) {
  return (
    <span className={`inline-flex items-center text-[11px] font-medium border px-2 py-0.5 rounded-full ${className}`}>
      {children}
    </span>
  );
}

function LinhaDeInfluencer({ item, aoAtualizar, aoRemover }) {
  const [aberto, setAberto] = useState(false);
  const [ativando, setAtivando] = useState(false);
  const [emailLogin, setEmailLogin] = useState("");
  const [percentual, setPercentual] = useState("30");
  const [sparks, setSparks] = useState("300");
  const [kit, setKit] = useState(null);
  const [gerandoMensagem, setGerandoMensagem] = useState(false);
  const [observacao, setObservacao] = useState(item.observacao || "");
  const [salvandoObs, setSalvandoObs] = useState(false);

  const mudarStatus = async (novoStatus) => {
    try {
      const { data } = await api.patch(`/admin/influencers/${item.influencer_id}`, { status: novoStatus });
      aoAtualizar({ ...item, ...data });
      toast.success(`Status: ${ROTULO_STATUS[novoStatus] || novoStatus}.`);
    } catch (e) {
      toast.error(errMsg(e, "Falha ao mudar status."));
    }
  };

  const ativar = async () => {
    setAtivando(true);
    try {
      const { data } = await api.post(`/admin/influencers/${item.influencer_id}/ativar`, {
        email_login: emailLogin.trim(),
        percentual_comissao: (parseFloat(percentual) || 30) / 100,
        sparks_boas_vindas: parseInt(sparks, 10) || 300,
      });
      aoAtualizar({ ...item, ...data });
      toast.success(`Ativado! Código ${data.codigo}.`);
    } catch (e) {
      toast.error(errMsg(e, "Falha ao ativar influencer."));
    } finally {
      setAtivando(false);
    }
  };

  const carregarKit = async () => {
    try {
      const { data } = await api.get(`/admin/influencers/${item.influencer_id}/kit`);
      setKit(data);
    } catch (e) {
      toast.error(errMsg(e, "Falha ao gerar o kit."));
    }
  };

  const marcarPago = async () => {
    try {
      const { data } = await api.post(`/admin/influencers/${item.influencer_id}/comissao/pagar`, {});
      toast.success(`${data.marcados} lançamento(s) marcado(s) como pago.`);
      aoAtualizar({ ...item, comissao_paga_cents: (item.comissao_paga_cents || 0) + (item.comissao_acumulada_cents || 0), comissao_acumulada_cents: 0 });
    } catch (e) {
      toast.error(errMsg(e, "Falha ao marcar comissão paga."));
    }
  };

  const gerarMensagemIA = async () => {
    setGerandoMensagem(true);
    try {
      const { data } = await api.post(`/admin/influencers/${item.influencer_id}/mensagem-ia`);
      aoAtualizar({
        ...item, mensagem_gerada: data.mensagem, mensagem_origem: data.origem,
        status: "mensagem_pronta",
      });
      // `aviso` chega quando a IA estava sem cota e o texto saiu do molde
      // determinístico. Dizer isso importa: um texto de molde apresentado como
      // personalizado é pior que um erro — o admin mandaria como está.
      if (data.aviso) toast.warning(data.aviso);
      else toast.success("Mensagem gerada.");
    } catch (e) {
      toast.error(errMsg(e, "Falha ao gerar mensagem."));
    } finally {
      setGerandoMensagem(false);
    }
  };

  const salvarObservacao = async () => {
    setSalvandoObs(true);
    try {
      await api.patch(`/admin/influencers/${item.influencer_id}`, { observacao });
      aoAtualizar({ ...item, observacao });
      toast.success("Observação salva.");
    } catch (e) {
      toast.error(errMsg(e, "Falha ao salvar observação."));
    } finally {
      setSalvandoObs(false);
    }
  };

  const descartar = async () => {
    try {
      await api.patch(`/admin/influencers/${item.influencer_id}`, { descartado: !item.descartado });
      aoAtualizar({ ...item, descartado: !item.descartado });
      toast.success(item.descartado ? "Lead restaurado." : "Lead descartado.");
    } catch (e) {
      toast.error(errMsg(e, "Falha ao descartar."));
    }
  };

  const remover = async () => {
    if (!window.confirm(`Apagar "${item.nome}" definitivamente? Isso não pode ser desfeito.`)) return;
    try {
      await api.delete(`/admin/influencers/${item.influencer_id}`);
      toast.success("Removido.");
      aoRemover(item.influencer_id);
    } catch (e) {
      toast.error(errMsg(e, "Falha ao remover — se já tem comissão lançada, use 'Recusou' em vez de apagar."));
    }
  };

  const link = item.link ? `${window.location.origin}${item.link}` : null;
  const fonte = urlSegura(item.url);
  const ehDaIA = item.origem === "pesquisa_ia";

  return (
    <div className={`card-sapiens rounded-2xl p-5 ${item.descartado ? "opacity-50" : ""}`} data-testid={`admin-inf-row-${item.influencer_id}`}>
      {/* Colunas do CRM: Lead · Plataforma · Nicho · Audiência · Relevância ·
          Prioridade · URL · Status · Última ação — em grid, não <table>, pra
          usar o mesmo componente de card do resto do Admin (ver AdminInfluencers.jsx). */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-4 lg:grid-cols-8">
        <div className="col-span-2 sm:col-span-2 lg:col-span-2">
          <div className="text-[10px] uppercase tracking-wide text-zinc-400">Lead</div>
          <div className="font-display font-bold text-zinc-950 truncate">{item.nome}</div>
          {item.username && <div className="text-[11px] text-zinc-400">@{item.username.replace(/^@/, "")}</div>}
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-zinc-400">Plataforma</div>
          <div className="text-xs text-zinc-700 capitalize">{item.plataforma || "—"}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-zinc-400">Nicho</div>
          <div className="text-xs text-zinc-700 truncate">{item.nicho || "—"}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-zinc-400">Audiência</div>
          <div className="text-xs text-zinc-700">{item.tamanho_aproximado ? `~${item.tamanho_aproximado.toLocaleString("pt-BR")}` : "—"}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-zinc-400">Relevância</div>
          {item.confianca ? (
            <Etiqueta className={RELEVANCIA_COR[item.confianca] || RELEVANCIA_COR.baixa}>{RELEVANCIA_ROTULO[item.confianca] || item.confianca}</Etiqueta>
          ) : <span className="text-xs text-zinc-400">—</span>}
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-zinc-400">Prioridade</div>
          {item.prioridade ? (
            <Etiqueta className={PRIORIDADE_COR[item.prioridade] || PRIORIDADE_COR.baixa}>{PRIORIDADE_ROTULO[item.prioridade] || item.prioridade}</Etiqueta>
          ) : <span className="text-xs text-zinc-400">—</span>}
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-zinc-400">URL</div>
          {fonte ? (
            <a href={fonte} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-sapiens-accent hover:underline">
              <ExternalLink className="w-3 h-3" /> Abrir
            </a>
          ) : item.url ? (
            <span className="text-xs text-zinc-400" title={item.url}>não verificada</span>
          ) : <span className="text-xs text-zinc-400">—</span>}
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-zinc-400">Status</div>
          <Etiqueta className={COR_STATUS[item.status] || COR_STATUS.lead}>{ROTULO_STATUS[item.status] || item.status}</Etiqueta>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-zinc-400">Última ação</div>
          <div className="text-xs text-zinc-700">{dataCurta(item.updated_at)}</div>
        </div>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2">
        {ehDaIA && <Etiqueta className="bg-sapiens-accent/10 text-sapiens-accent border-sapiens-accent/30">Pesquisador IA</Etiqueta>}
        {item.codigo && <span className="font-mono-alt text-xs text-zinc-500 tracking-wide">{item.codigo}</span>}
        {item.contato && <span className="text-xs text-zinc-400">{item.contato}</span>}
      </div>

      {/* Mensagem personalizada — coluna própria do CRM pedido: prévia +
          cópia direto na linha, sem precisar abrir o card. */}
      {item.mensagem_gerada && (
        <div className="mt-2 flex items-start gap-2 rounded-lg border border-zinc-100 px-3 py-2">
          <p className="min-w-0 flex-1 truncate text-xs text-zinc-600" title={item.mensagem_gerada}>
            <span className="text-zinc-400">Mensagem: </span>{item.mensagem_gerada}
          </p>
          <button onClick={() => copiar(item.mensagem_gerada, "Mensagem")} className="shrink-0 text-zinc-400 hover:text-zinc-900" data-testid={`admin-inf-copiar-mensagem-linha-${item.influencer_id}`}>
            <Copy className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {item.status === "ativo" && (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="rounded-xl border border-zinc-100 px-3 py-2">
            <div className="text-[10px] uppercase text-zinc-400">Alunos</div>
            <div className="font-display font-bold text-zinc-950">{item.alunos_atribuidos ?? 0}</div>
          </div>
          <div className="rounded-xl border border-zinc-100 px-3 py-2">
            <div className="text-[10px] uppercase text-zinc-400">Faturamento</div>
            <div className="font-display font-bold text-zinc-950">{reais(item.faturamento_atribuido_cents)}</div>
          </div>
          <div className="rounded-xl border border-zinc-100 px-3 py-2">
            <div className="text-[10px] uppercase text-zinc-400">Comissão acumulada</div>
            <div className="font-display font-bold text-emerald-700">{reais(item.comissao_acumulada_cents)}</div>
          </div>
          <div className="rounded-xl border border-zinc-100 px-3 py-2">
            <div className="text-[10px] uppercase text-zinc-400">Já paga</div>
            <div className="font-display font-bold text-zinc-500">{reais(item.comissao_paga_cents)}</div>
          </div>
        </div>
      )}

      {item.status === "ativo" && link && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button onClick={() => copiar(link, "Link")} className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-900" data-testid={`admin-inf-copiar-link-${item.influencer_id}`}>
            <Copy className="w-3 h-3" /> Copiar link
          </button>
          <button onClick={() => copiar(item.codigo, "Código")} className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-900">
            <Copy className="w-3 h-3" /> Copiar código
          </button>
          {(item.comissao_acumulada_cents || 0) > 0 && (
            <button onClick={marcarPago} className="pill inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 border border-emerald-400/30 px-3 py-1.5 text-xs font-medium text-emerald-700" data-testid={`admin-inf-marcar-pago-${item.influencer_id}`}>
              <Wallet className="w-3 h-3" /> Marcar comissão como paga
            </button>
          )}
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button onClick={() => setAberto((v) => !v)} className="inline-flex items-center gap-1 text-xs font-medium text-zinc-500 hover:text-zinc-900">
          {aberto ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          {item.status === "ativo" ? "Kit de divulgação" : "Ações"}
        </button>
      </div>

      {aberto && (
        <div className="mt-3 space-y-3">
          {ehDaIA && (item.foco || item.tipo_audiencia || item.potencial_parceria || item.justificativa_ia || (item.sinais_publicos_relevancia || []).length > 0) && (
            <div className="rounded-xl border border-zinc-100 p-3 space-y-1 text-xs text-zinc-600">
              {item.foco && <div><span className="text-zinc-400">Foco:</span> {item.foco}</div>}
              {item.tipo_audiencia && <div><span className="text-zinc-400">Tipo de audiência:</span> {item.tipo_audiencia}</div>}
              {item.localizacao && <div><span className="text-zinc-400">Localização:</span> {item.localizacao}</div>}
              {item.potencial_parceria && <div><span className="text-zinc-400">Potencial de parceria:</span> {item.potencial_parceria}</div>}
              {(item.sinais_publicos_relevancia || []).length > 0 && (
                <div><span className="text-zinc-400">Sinais públicos:</span> {item.sinais_publicos_relevancia.join("; ")}</div>
              )}
              {item.justificativa_ia && <div><span className="text-zinc-400">Justificativa da IA:</span> {item.justificativa_ia}</div>}
            </div>
          )}

          {item.status !== "ativo" && item.status !== "cadastrado" && (
            <div className="flex flex-wrap gap-2">
              {(PROXIMOS_STATUS[item.status] || []).map((s) => (
                <button key={s} onClick={() => mudarStatus(s)} className="pill rounded-full border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-900" data-testid={`admin-inf-status-${item.influencer_id}-${s}`}>
                  → {ROTULO_STATUS[s]}
                </button>
              ))}
            </div>
          )}

          {item.status !== "ativo" && item.status !== "cadastrado" && (
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                {!item.mensagem_gerada ? (
                  <button onClick={gerarMensagemIA} disabled={gerandoMensagem} className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-600 disabled:opacity-50" data-testid={`admin-inf-gerar-mensagem-${item.influencer_id}`}>
                    <Sparkles className="w-3 h-3" /> {gerandoMensagem ? "Gerando…" : "Gerar mensagem (IA)"}
                  </button>
                ) : (
                  <button onClick={gerarMensagemIA} disabled={gerandoMensagem} className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-600 disabled:opacity-50">
                    <Sparkles className="w-3 h-3" /> {gerandoMensagem ? "Gerando…" : "Gerar outra"}
                  </button>
                )}
              </div>
              {item.mensagem_gerada && (
                <div className="rounded-xl border border-zinc-100 p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase text-zinc-400">
                      Mensagem
                      {item.mensagem_origem === "modelo" && (
                        <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[9px] font-semibold text-amber-800">
                          modelo padrão
                        </span>
                      )}
                    </span>
                    <button onClick={() => copiar(item.mensagem_gerada, "Mensagem")} className="text-zinc-400 hover:text-zinc-900" data-testid={`admin-inf-copiar-mensagem-${item.influencer_id}`}>
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <p className="mt-1 text-xs text-zinc-600 whitespace-pre-wrap">{item.mensagem_gerada}</p>
                  {item.mensagem_origem === "modelo" && (
                    <p className="mt-1.5 text-[10px] text-amber-700">
                      Não foi personalizada por IA (cota esgotada) — vale editar antes de enviar.
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {(item.status === "interessado" || item.status === "cadastrado") && !item.codigo && (
            <div className="rounded-xl border border-zinc-100 p-4 space-y-2">
              <div className="text-xs font-medium text-zinc-500">Ativar como afiliado</div>
              <input value={emailLogin} onChange={(e) => setEmailLogin(e.target.value)} placeholder="e-mail que faz login no painel" className="w-full border border-zinc-200 rounded-lg px-3 py-2 text-sm" data-testid={`admin-inf-email-${item.influencer_id}`} />
              <div className="flex gap-2">
                <input value={percentual} onChange={(e) => setPercentual(e.target.value)} type="number" placeholder="30" className="w-24 border border-zinc-200 rounded-lg px-3 py-2 text-sm" />
                <span className="self-center text-xs text-zinc-400">% de comissão</span>
                <input value={sparks} onChange={(e) => setSparks(e.target.value)} type="number" placeholder="300" className="w-24 border border-zinc-200 rounded-lg px-3 py-2 text-sm" />
                <span className="self-center text-xs text-zinc-400">Sparks de boas-vindas</span>
              </div>
              <button onClick={ativar} disabled={ativando || !emailLogin.trim()} className="btn-sapiens rounded-xl px-4 py-2 text-sm font-semibold disabled:opacity-50" data-testid={`admin-inf-ativar-${item.influencer_id}`}>
                {ativando ? "Ativando…" : "Ativar"}
              </button>
            </div>
          )}

          {item.status === "ativo" && (
            <div className="space-y-2">
              {!kit && (
                <button onClick={carregarKit} className="pill rounded-full border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-600" data-testid={`admin-inf-gerar-kit-${item.influencer_id}`}>
                  Gerar materiais
                </button>
              )}
              {kit && (
                <div className="grid gap-2 sm:grid-cols-2">
                  {[["Mensagem", kit.mensagem], ["Legenda", kit.legenda], ["Story", kit.story], ["Roteiro", kit.roteiro_reel]].map(([rotulo, texto]) => (
                    <div key={rotulo} className="rounded-xl border border-zinc-100 p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase text-zinc-400">{rotulo}</span>
                        <button onClick={() => copiar(texto, rotulo)} className="text-zinc-400 hover:text-zinc-900"><Copy className="w-3.5 h-3.5" /></button>
                      </div>
                      <p className="mt-1 text-xs text-zinc-600 whitespace-pre-wrap">{texto}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="space-y-1">
            <div className="text-[10px] uppercase text-zinc-400">Observação</div>
            <textarea value={observacao} onChange={(e) => setObservacao(e.target.value)} rows={2}
              placeholder="Nota livre do admin — nunca da IA" className="w-full border border-zinc-200 rounded-lg px-3 py-2 text-xs"
              data-testid={`admin-inf-observacao-${item.influencer_id}`} />
            <button onClick={salvarObservacao} disabled={salvandoObs} className="pill rounded-full border border-zinc-200 px-3 py-1 text-[11px] font-medium text-zinc-600 disabled:opacity-50">
              {salvandoObs ? "Salvando…" : "Salvar observação"}
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-zinc-100">
            <button onClick={descartar} className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-500 hover:text-zinc-900">
              {item.descartado ? <RotateCcw className="w-3 h-3" /> : <Ban className="w-3 h-3" />}
              {item.descartado ? "Restaurar" : "Descartar"}
            </button>
            {!item.codigo && (
              <button onClick={remover} className="pill inline-flex items-center gap-1.5 rounded-full border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50" data-testid={`admin-inf-remover-${item.influencer_id}`}>
                <Trash2 className="w-3 h-3" /> Remover definitivamente
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** Relatório da última rodada.
 *
 * Existe por causa de um bug de 2026-09-21: a rodada devolvia "0/40 leads
 * novos encontrados (fontes públicas não renderam mais candidatos)" enquanto
 * a causa real era um 429 de quota na busca. O admin lia "não tem ninguém lá
 * fora" quando a verdade era "a busca não aconteceu". Por isso o painel mostra
 * SEMPRE as fontes e os erros técnicos — um zero sem causa visível é o que
 * não pode voltar a acontecer.
 */
function RelatorioDaRodada({ resumo }) {
  if (!resumo) return null;
  const fontes = resumo.fontes || [];
  const descartes = Object.entries(resumo.descartes || {});
  const erros = resumo.erros_tecnicos || [];
  const porFonte = fontes.reduce((acc, f) => {
    const chave = f.provedor || "-";
    acc[chave] = acc[chave] || { ok: 0, vazio: 0, erro: 0, resultados: 0 };
    acc[chave][f.estado === "cache" ? "ok" : f.estado] = (acc[chave][f.estado === "cache" ? "ok" : f.estado] || 0) + 1;
    acc[chave].resultados += Number(f.resultados || 0);
    return acc;
  }, {});

  return (
    <div className="mt-4 rounded-xl border border-zinc-200 bg-zinc-50/60 p-4 text-xs text-zinc-600">
      <div className="font-semibold text-zinc-900">
        Última rodada · {resumo.total_novos ?? 0} lead(s) novo(s) · {Math.round((resumo.duracao_ms || 0) / 1000)}s
      </div>

      <div className="mt-3 font-medium text-zinc-700">Fontes usadas</div>
      <ul className="mt-1 space-y-0.5">
        {Object.entries(porFonte).map(([provedor, c]) => (
          <li key={provedor}>
            <span className="font-mono">{provedor}</span> — {c.resultados} resultado(s) em {c.ok || 0} consulta(s) OK
            {c.vazio ? `, ${c.vazio} sem resultado` : ""}
            {c.erro ? <span className="text-amber-700">, {c.erro} com falha</span> : ""}
          </li>
        ))}
        {!fontes.length && <li>nenhuma fonte foi consultada nesta rodada.</li>}
      </ul>

      {!!descartes.length && (
        <>
          <div className="mt-3 font-medium text-zinc-700">Descartados e por quê</div>
          <ul className="mt-1 space-y-0.5">
            {descartes.map(([motivo, quantos]) => (
              <li key={motivo}>
                {quantos}× <span className="font-mono">{motivo.replace(/_/g, " ")}</span>
              </li>
            ))}
          </ul>
        </>
      )}

      {!!erros.length && (
        <>
          <div className="mt-3 font-medium text-amber-800">Erros técnicos (não são “nada encontrado”)</div>
          <ul className="mt-1 space-y-0.5 text-amber-800">
            {erros.map((e) => <li key={e} className="break-words">{e}</li>)}
          </ul>
        </>
      )}
    </div>
  );
}

function PesquisadorIA({ aoConcluir }) {
  const [pesquisando, setPesquisando] = useState(false);
  const [resumo, setResumo] = useState(null);

  const pesquisar = async (limiteTotal) => {
    setPesquisando(true);
    try {
      const corpo = limiteTotal ? { limite_total: limiteTotal } : {};
      const { data } = await api.post("/admin/influencers/pesquisar", corpo);
      setResumo(data);
      const total = data.total_novos ?? 0;
      const houveFalha = (data.erros_tecnicos || []).length > 0;
      if (total > 0) {
        toast.success(`${total} lead(s) novo(s) encontrado(s).`);
      } else if (houveFalha) {
        toast.error("Nenhum lead novo — e houve falha de fonte nesta rodada. Veja os erros técnicos abaixo.");
      } else {
        toast.info("Rodada concluída — nenhum lead novo (tudo já estava no CRM).");
      }
      (data.avisos || []).forEach((aviso) => toast.warning(aviso));
      aoConcluir();
    } catch (e) {
      toast.error(errMsg(e, "Falha ao pesquisar. Se você acabou de rodar, aguarde antes de tentar de novo (limite de uso)."));
    } finally {
      setPesquisando(false);
    }
  };

  return (
    <div className="mt-8 card-sapiens rounded-2xl p-6">
      <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
        <Sparkles className="w-4 h-4 text-sapiens-accent" /> Pesquisador IA de Aquisição
      </div>
      <p className="mt-2 text-xs text-zinc-500 max-w-xl">
        Busca pública real (Instagram, YouTube, TikTok, blogs e páginas públicas) e traz cada
        lead com a fonte que comprova a descoberta — a URL nunca é escrita pela IA, sempre vem
        de uma busca ou de uma página pública que cita o perfil. Nunca faz login, nunca entra em
        grupo, nunca envia mensagem: o texto de abordagem é gerado sob demanda e copiado à mão.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button onClick={() => pesquisar(10)} disabled={pesquisando} className="rounded-xl border border-zinc-300 px-4 py-2.5 text-sm font-semibold text-zinc-700 disabled:opacity-50" data-testid="admin-inf-pesquisar-ia-10">
          {pesquisando ? "Pesquisando…" : "Rodada pequena (10 leads)"}
        </button>
        <button onClick={() => pesquisar(null)} disabled={pesquisando} className="btn-sapiens rounded-xl px-5 py-2.5 text-sm font-semibold disabled:opacity-50" data-testid="admin-inf-pesquisar-ia">
          {pesquisando ? "Pesquisando… (pode levar alguns minutos)" : "Rodada completa"}
        </button>
      </div>
      <RelatorioDaRodada resumo={resumo} />
    </div>
  );
}

export default function AdminInfluencers() {
  const [items, setItems] = useState([]);
  const [resumo, setResumo] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [filtro, setFiltro] = useState("");
  const [plataformaFiltro, setPlataformaFiltro] = useState("");
  const [nichoFiltro, setNichoFiltro] = useState("");
  const [nichosConhecidos, setNichosConhecidos] = useState([]);
  const [prioridadeFiltro, setPrioridadeFiltro] = useState("");
  const [busca, setBusca] = useState("");
  const [buscaDebounced, setBuscaDebounced] = useState("");
  const [incluirDescartados, setIncluirDescartados] = useState(false);
  const [pagina, setPagina] = useState(0);
  const [temMais, setTemMais] = useState(false);
  const [nome, setNome] = useState("");
  const [contato, setContato] = useState("");
  const [plataforma, setPlataforma] = useState("");
  const [nicho, setNicho] = useState("");
  const [tamanho, setTamanho] = useState("");
  const [criando, setCriando] = useState(false);
  const LIMITE_PAGINA = 30;

  useEffect(() => {
    const t = setTimeout(() => setBuscaDebounced(busca.trim()), 350);
    return () => clearTimeout(t);
  }, [busca]);

  const carregar = useCallback((paginaAlvo = 0) => {
    const params = new URLSearchParams();
    if (filtro) params.set("status", filtro);
    if (plataformaFiltro) params.set("plataforma", plataformaFiltro);
    if (nichoFiltro) params.set("nicho", nichoFiltro);
    if (prioridadeFiltro) params.set("prioridade", prioridadeFiltro);
    if (buscaDebounced) params.set("busca", buscaDebounced);
    if (incluirDescartados) params.set("incluir_descartados", "true");
    params.set("skip", String(paginaAlvo * LIMITE_PAGINA));
    params.set("limit", String(LIMITE_PAGINA));

    Promise.all([
      api.get(`/admin/influencers?${params.toString()}`).then(({ data }) => data),
      api.get("/admin/influencers/resumo").then(({ data }) => data),
    ]).then(([lista, res]) => {
      const novos = lista.items || [];
      setItems((prev) => (paginaAlvo === 0 ? novos : [...prev, ...novos]));
      setTemMais(novos.length >= LIMITE_PAGINA);
      setResumo(res);
      setPagina(paginaAlvo);
      setLoaded(true);
      // Lista de nichos conhecidos cresce por união, nunca por substituição —
      // senão filtrar por um nicho faria as OUTRAS opções somem do próprio
      // seletor que as oferece.
      setNichosConhecidos((prev) => {
        const vistos = new Set(prev);
        novos.forEach((i) => { if (i.nicho) vistos.add(i.nicho); });
        return Array.from(vistos).sort((a, b) => a.localeCompare(b, "pt-BR"));
      });
    }).catch((e) => {
      toast.error(errMsg(e, "Falha ao carregar influencers."));
      setLoaded(true);
    });
  }, [filtro, plataformaFiltro, nichoFiltro, prioridadeFiltro, buscaDebounced, incluirDescartados]);

  useEffect(() => { carregar(0); }, [carregar]);

  const criar = async (e) => {
    e.preventDefault();
    if (!nome.trim()) {
      toast.error("Informe o nome.");
      return;
    }
    setCriando(true);
    try {
      await api.post("/admin/influencers", {
        nome: nome.trim(),
        contato: contato.trim() || undefined,
        plataforma: plataforma.trim() || undefined,
        nicho: nicho.trim() || undefined,
        tamanho_aproximado: tamanho ? parseInt(tamanho, 10) : undefined,
        origem: "prospecção manual",
      });
      setNome(""); setContato(""); setPlataforma(""); setNicho(""); setTamanho("");
      toast.success("Lead criado.");
      carregar(0);
    } catch (e2) {
      toast.error(errMsg(e2, "Falha ao criar lead."));
    } finally {
      setCriando(false);
    }
  };

  const atualizarItem = (novo) => {
    setItems((prev) => prev.map((i) => (i.influencer_id === novo.influencer_id ? novo : i)));
  };

  const removerItem = (influencerId) => {
    setItems((prev) => prev.filter((i) => i.influencer_id !== influencerId));
  };

  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="flex items-center gap-3 mb-3">
          <Megaphone className="w-4 h-4 text-sapiens-accent" />
          <div className="secao-olho">Admin · Influencers</div>
        </div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-white" data-testid="admin-inf-title">
          Programa de influencers
        </h1>
        <p className="mt-3 text-white/60 max-w-lg">
          Prospecção, ativação e comissão dos parceiros. 300 Sparks de boas-vindas pra quem entra pelo
          código, 30% de comissão recorrente pra quem indicou — os dois configuráveis por influencer.
        </p>

        {resumo && (
          <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="card-sapiens rounded-2xl p-4">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Total</div>
              <div className="mt-1 font-display text-2xl font-extrabold text-zinc-950">{resumo.total}</div>
            </div>
            <div className="card-sapiens rounded-2xl p-4">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Afiliados</div>
              <div className="mt-1 font-display text-2xl font-extrabold text-zinc-950">{resumo.ativos}</div>
            </div>
            <div className="card-sapiens rounded-2xl p-4">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Comissão a pagar</div>
              <div className="mt-1 font-display text-2xl font-extrabold text-emerald-700">{reais(resumo.comissao_acumulada_total_cents)}</div>
            </div>
            <div className="card-sapiens rounded-2xl p-4">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Já pago</div>
              <div className="mt-1 font-display text-2xl font-extrabold text-zinc-500">{reais(resumo.comissao_paga_total_cents)}</div>
            </div>
          </div>
        )}

        <PesquisadorIA aoConcluir={() => carregar(0)} />

        <form onSubmit={criar} className="mt-6 card-sapiens rounded-2xl p-6 space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900"><Plus className="w-4 h-4" /> Novo lead manual</div>
          <div className="grid gap-2 sm:grid-cols-2">
            <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Nome" className="border border-zinc-200 rounded-xl px-4 py-2.5 text-sm" data-testid="admin-inf-input-nome" />
            <input value={contato} onChange={(e) => setContato(e.target.value)} placeholder="Contato (WhatsApp, e-mail, @)" className="border border-zinc-200 rounded-xl px-4 py-2.5 text-sm" />
            <input value={plataforma} onChange={(e) => setPlataforma(e.target.value)} placeholder="Plataforma (instagram, tiktok...)" className="border border-zinc-200 rounded-xl px-4 py-2.5 text-sm" />
            <input value={nicho} onChange={(e) => setNicho(e.target.value)} placeholder="Nicho" className="border border-zinc-200 rounded-xl px-4 py-2.5 text-sm" />
            <input value={tamanho} onChange={(e) => setTamanho(e.target.value)} type="number" placeholder="Seguidores (aprox.)" className="border border-zinc-200 rounded-xl px-4 py-2.5 text-sm" />
          </div>
          <button type="submit" disabled={criando} className="btn-sapiens rounded-xl px-5 py-2.5 text-sm font-semibold disabled:opacity-50" data-testid="admin-inf-criar-lead">
            {criando ? "Criando…" : "Criar lead"}
          </button>
        </form>

        <div className="mt-6 space-y-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
            <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por nome, nicho, @ ou contato"
              className="w-full border border-zinc-200 rounded-xl pl-8 pr-4 py-2.5 text-sm" data-testid="admin-inf-busca" />
          </div>

          <div className="flex flex-wrap gap-2">
            {["", "lead", "qualificado", "mensagem_pronta", "contato", "respondeu", "interessado", "cadastrado", "ativo", "recusado"].map((s) => (
              <button key={s} onClick={() => setFiltro(s)} className={`pill rounded-full px-3 py-1.5 text-xs font-medium border ${filtro === s ? "bg-sapiens-accent/15 border-sapiens-accent/40 text-sapiens-accent" : "border-zinc-200 text-zinc-500"}`}>
                {s === "" ? "Todos" : ROTULO_STATUS[s]}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <select value={plataformaFiltro} onChange={(e) => setPlataformaFiltro(e.target.value)} className="border border-zinc-200 rounded-full px-3 py-1.5 text-xs font-medium text-zinc-600" data-testid="admin-inf-filtro-plataforma">
              <option value="">Toda plataforma</option>
              <option value="instagram">Instagram</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="telegram">Telegram</option>
              <option value="tiktok">TikTok</option>
              <option value="youtube">YouTube</option>
            </select>
            <select value={nichoFiltro} onChange={(e) => setNichoFiltro(e.target.value)} className="border border-zinc-200 rounded-full px-3 py-1.5 text-xs font-medium text-zinc-600" data-testid="admin-inf-filtro-nicho">
              <option value="">Todo nicho</option>
              {nichosConhecidos.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
            <select value={prioridadeFiltro} onChange={(e) => setPrioridadeFiltro(e.target.value)} className="border border-zinc-200 rounded-full px-3 py-1.5 text-xs font-medium text-zinc-600" data-testid="admin-inf-filtro-prioridade">
              <option value="">Toda prioridade</option>
              <option value="alta">Prioridade alta</option>
              <option value="media">Prioridade média</option>
              <option value="baixa">Prioridade baixa</option>
            </select>
            <label className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-500 px-2">
              <input type="checkbox" checked={incluirDescartados} onChange={(e) => setIncluirDescartados(e.target.checked)} />
              Incluir descartados
            </label>
          </div>
        </div>

        <div className="mt-4 space-y-3">
          {loaded && items.length === 0 && (
            <div className="card-sapiens rounded-2xl p-8 text-center text-zinc-500 text-sm">
              Nenhum influencer/lead neste filtro.
            </div>
          )}
          {items.map((item) => (
            <LinhaDeInfluencer key={item.influencer_id} item={item} aoAtualizar={atualizarItem} aoRemover={removerItem} />
          ))}
        </div>

        {temMais && (
          <div className="mt-4 flex justify-center">
            <button onClick={() => carregar(pagina + 1)} className="pill rounded-full border border-zinc-200 px-5 py-2 text-xs font-medium text-zinc-500 hover:text-zinc-900">
              Carregar mais
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
