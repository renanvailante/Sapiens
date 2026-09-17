import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  AlertTriangle, MessageCircleMore, Copy, Check, Users,
  Zap, Bell, ArrowRight, BookOpen, RefreshCw,
} from "lucide-react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import PublicarLinkDaLive from "../components/PublicarLinkDaLive";

/**
 * Admin · Aula ao vivo e cursos.
 *
 * A tela existe para UMA tarefa recorrente de quinta-feira: publicar o link
 * do Meet da edição e falar com quem pagou por ela. Por isso o link fica em
 * cima, o aviso de "tem gente paga e nenhum link publicado" é vermelho, e
 * cada inscrito traz o botão que abre a conversa no WhatsApp — a informação
 * não serve para ser consultada, serve para ser usada.
 *
 * Embaixo ficam os cursos em pré-venda, e ali o número que importa é quem já
 * PAGOU por um curso que ainda não existe: é a dívida assumida com aluno. A
 * fila de quem só quer ser avisado vem ao lado, como evidência de qual dos
 * quatro construir primeiro.
 */

function LinhaDeContato({ pessoa, testid }) {
  return (
    <div
      className="flex flex-wrap items-center gap-3 rounded-xl border border-zinc-100 px-3 py-2.5"
      data-testid={testid}
    >
      <div className="min-w-[9rem] flex-1">
        <div className="truncate text-sm font-medium text-zinc-900">{pessoa.nome || pessoa.user_id}</div>
        <div className="truncate text-xs text-zinc-500">{pessoa.email}</div>
      </div>
      {pessoa.whatsapp_link ? (
        <a
          href={pessoa.whatsapp_link}
          target="_blank"
          rel="noopener noreferrer"
          className="pill inline-flex shrink-0 items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 font-mono-alt text-xs text-emerald-700 hover:bg-emerald-100"
          data-testid={`${testid}-whatsapp`}
        >
          <MessageCircleMore className="h-3.5 w-3.5" /> {pessoa.whatsapp}
        </a>
      ) : (
        <span className="shrink-0 font-mono-alt text-xs text-zinc-300" title="Este aluno não informou WhatsApp">
          sem WhatsApp
        </span>
      )}
    </div>
  );
}

/**
 * O PAINEL DE QUEM PRODUZ O CONTEÚDO.
 *
 * Responde três perguntas que a equipe de conteúdo faz toda semana, e que
 * nenhum outro lugar do produto responde:
 *
 * 1. **O que já está publicado?** Estações, exercícios, vídeos.
 * 2. **A progressão existe de verdade?** A distribuição por nível é o número
 *    que denuncia um curso inteiro escrito no nível 2 — que passa em todas as
 *    outras validações e não ensina ninguém a subir.
 * 3. **O que quebrou?** Curso com qualquer problema de validação sai do ar
 *    inteiro, e é aqui que aparece o motivo exato, arquivo por arquivo.
 *
 * "Recarregar do disco" existe para o ciclo de produção: publicar uma estação,
 * conferir, corrigir. Sem ele, cada vírgula num JSON custaria um deploy para
 * ser conferida.
 */
function PainelDeConteudo() {
  const [inventario, setInventario] = useState(null);
  const [recarregando, setRecarregando] = useState(false);

  const carregar = useCallback(() => {
    api
      .get("/admin/cursos/conteudo")
      .then(({ data }) => setInventario(data))
      .catch((e) => toast.error(errMsg(e, "Não foi possível ler o inventário de conteúdo.")));
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const recarregar = async () => {
    setRecarregando(true);
    try {
      const { data } = await api.post("/admin/cursos/conteudo/recarregar");
      setInventario(data);
      toast.success(
        data.problemas_totais
          ? `Recarregado com ${data.problemas_totais} problema(s).`
          : "Conteúdo recarregado do disco.",
      );
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível recarregar."));
    } finally {
      setRecarregando(false);
    }
  };

  if (!inventario) return null;

  return (
    <section className="mt-10" data-testid="admin-cursos-conteudo">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 font-display text-xl font-bold tracking-tight text-white">
            <BookOpen className="h-4 w-4 text-[#7FD8FF]" /> Conteúdo publicado
          </h2>
          <p className="mt-1 font-mono-alt text-[10px] uppercase tracking-[0.2em] text-white/30">
            schema {inventario.schema_version} · {inventario.raiz}
          </p>
        </div>
        <button
          onClick={recarregar}
          disabled={recarregando}
          className="pill inline-flex items-center gap-1.5 rounded-full border border-white/15 px-4 py-2.5 text-xs font-medium text-white/70 hover:text-white disabled:opacity-50"
          data-testid="admin-cursos-recarregar"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${recarregando ? "animate-spin" : ""}`} />
          Recarregar do disco
        </button>
      </div>

      <div className="space-y-2">
        {inventario.cursos.map((c) => (
          <div key={c.curso_id} className="card-sapiens rounded-2xl p-4" data-testid={`conteudo-${c.curso_id}`}>
            <div className="flex flex-wrap items-center gap-3">
              <div className="min-w-0 flex-1">
                <div className="truncate font-display font-semibold text-zinc-900">{c.curso_id}</div>
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
                  {c.publicado ? `versão ${c.versao} · ${c.trilhas?.length || 0} trilha(s)` : "sem conteúdo"}
                </div>
              </div>
              {c.publicado ? (
                <>
                  <Medida n={c.estacoes} rotulo="estações" />
                  <Medida n={c.exercicios} rotulo="exercícios" />
                  <Medida n={c.desafios} rotulo="desafios" />
                  {c.videos_pendentes > 0 && (
                    <Medida n={c.videos_pendentes} rotulo="vídeos a gravar" alerta />
                  )}
                </>
              ) : (
                <span className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-amber-600">
                  {c.problemas?.length ? "fora do ar" : "em produção"}
                </span>
              )}
            </div>

            {/* A progressão, em barras. Um curso todo num nível só salta aos
                olhos aqui e em nenhum outro lugar. */}
            {c.publicado && c.exercicios > 0 && (
              <div className="mt-3 flex items-end gap-1.5" title="Exercícios por nível">
                {Object.entries(c.exercicios_por_nivel).map(([nivel, quantos]) => (
                  <div key={nivel} className="flex-1 text-center">
                    <div
                      className="mx-auto w-full rounded-t bg-gradient-to-t from-sky-400 to-violet-400"
                      style={{ height: `${Math.max(3, (quantos / c.exercicios) * 46)}px` }}
                    />
                    <div className="mt-1 font-mono-alt text-[9px] text-zinc-400">
                      N{nivel} · {quantos}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {c.problemas?.length > 0 && (
              <ul className="mt-3 space-y-1.5 border-t border-rose-200 pt-3" data-testid={`problemas-${c.curso_id}`}>
                {c.problemas.map((p, i) => (
                  <li key={i} className="flex gap-2 text-xs text-rose-700">
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span>
                      <code className="font-mono-alt text-rose-900">{p.arquivo}</code> — {p.mensagem}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function Medida({ n, rotulo, alerta = false }) {
  return (
    <div className="shrink-0 text-right">
      <div
        className={`font-display text-xl font-extrabold leading-none tracking-tighter ${
          alerta ? "text-amber-600" : "text-zinc-950"
        }`}
      >
        {n}
      </div>
      <div className="font-mono-alt text-[9px] uppercase tracking-[0.2em] text-zinc-400">{rotulo}</div>
    </div>
  );
}

export default function AdminCursos() {
  const [dados, setDados] = useState(null);
  const [copiado, setCopiado] = useState(false);
  const [aberto, setAberto] = useState(null);

  const carregar = useCallback(() => {
    api
      .get("/admin/cursos")
      .then(({ data }) => setDados(data))
      .catch((e) => toast.error(errMsg(e, "Não foi possível carregar o painel de cursos.")));
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const live = dados?.live || {};
  const inscritos = dados?.inscritos || [];

  /** Todos os números da edição, um por linha — para colar numa lista de
   *  transmissão sem catar um a um. */
  const copiarNumeros = async () => {
    const numeros = inscritos.map((i) => i.whatsapp_e164).filter(Boolean);
    if (numeros.length === 0) {
      toast.error("Nenhum inscrito desta edição informou WhatsApp.");
      return;
    }
    try {
      await navigator.clipboard.writeText(numeros.join("\n"));
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
      toast.success(`${numeros.length} número(s) copiado(s).`);
    } catch {
      toast.error("O navegador bloqueou a cópia.");
    }
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-5xl px-5 py-7 md:px-10 md:py-10">
        <div className="mb-3 font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50">
          Admin · Cursos e live
        </div>
        <h1
          className="font-display text-4xl font-extrabold tracking-tighter text-white"
          data-testid="admin-cursos-title"
        >
          Aula ao vivo de quinta
        </h1>
        <p className="mt-3 max-w-2xl text-white/60">
          Publique o link do Meet e o tema da edição, e fale com quem já pagou. O link só
          chega ao navegador de quem comprou o acesso.
        </p>
        {/* A regra de cobrança escrita onde ela é executada: quem publica o
            link é quem responde ao aluno que perguntar por que pagou de novo. */}
        <p className="mt-2 max-w-2xl text-sm text-white/40">
          A aula custa 200 Sparks <strong className="font-semibold text-white/60">por
          edição</strong> — toda quinta de novo. A única exceção é quem comprou o pacote de
          4.000 Sparks: esses entram em todas sem pagar, e aparecem na lista abaixo com 0
          Sparks.
        </p>

        {/* Estado da edição */}
        <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="card-sapiens rounded-2xl p-4">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Edição</div>
            <div className="mt-1 font-display text-xl font-extrabold tracking-tighter text-zinc-950">
              {live.edicao || "—"}
            </div>
          </div>
          <div className="card-sapiens rounded-2xl p-4">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Inscritos</div>
            <div className="mt-1 font-display text-xl font-extrabold tracking-tighter text-zinc-950">
              {dados?.inscritos_count ?? "—"}
            </div>
          </div>
          <div className="card-sapiens rounded-2xl p-4">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Sparks</div>
            <div className="mt-1 font-display text-xl font-extrabold tracking-tighter text-zinc-950">
              {dados?.receita_sparks ?? "—"}
            </div>
          </div>
          <div className="card-sapiens rounded-2xl p-4">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Link</div>
            <div
              className={`mt-1 font-display text-xl font-extrabold tracking-tighter ${
                live.link_publicado ? "text-emerald-600" : "text-amber-600"
              }`}
            >
              {live.link_publicado ? "publicado" : "pendente"}
            </div>
          </div>
        </div>

        {/* O campo do link, o mesmo componente que abre a primeira tela do
            admin. Duas cópias do mesmo formulário divergiriam na validação, e
            o aviso de "tem gente paga sem link" só vale se for o mesmo nos
            dois lugares. Publicar aqui recarrega o painel abaixo. */}
        <div className="mt-6">
          <PublicarLinkDaLive testid="admin-cursos-form" />
        </div>

        {/* Inscritos da edição */}
        <section className="mt-8" data-testid="admin-cursos-inscritos">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 font-display text-xl font-bold tracking-tight text-white">
              <Users className="h-4 w-4 text-[#7FD8FF]" /> Quem pagou esta edição
            </h2>
            <button
              onClick={copiarNumeros}
              className="pill inline-flex items-center gap-1.5 rounded-full border border-white/15 px-4 py-2 text-xs font-medium text-white/70 hover:text-white"
              data-testid="admin-cursos-copiar-numeros"
            >
              {copiado ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              Copiar os números
            </button>
          </div>

          <div className="card-sapiens rounded-2xl p-4">
            {inscritos.length === 0 ? (
              <div className="py-6 text-center text-sm text-zinc-500">
                Ninguém comprou o acesso desta edição ainda.
              </div>
            ) : (
              <div className="space-y-1.5">
                {inscritos.map((i) => (
                  <LinhaDeContato
                    key={i.user_id}
                    pessoa={i}
                    testid={`admin-cursos-inscrito-${i.user_id}`}
                  />
                ))}
              </div>
            )}
          </div>

          {dados?.historico?.length > 1 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {dados.historico.map((h) => (
                <span
                  key={h.edicao}
                  className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 font-mono-alt text-[11px] text-white/50"
                >
                  <Zap className="h-3 w-3 text-amber-400" /> {h.edicao}: {h.inscritos}
                </span>
              ))}
            </div>
          )}
        </section>

        <PainelDeConteudo />

        {/* Pré-venda dos cursos: quem já pagou, e quem só quer ser avisado */}
        <section className="mt-10" data-testid="admin-cursos-interesse">
          <h2 className="mb-1 flex items-center gap-2 font-display text-xl font-bold tracking-tight text-white">
            <Bell className="h-4 w-4 text-[#7FD8FF]" /> Pré-venda e fila de espera
          </h2>
          <p className="mb-3 max-w-2xl text-sm text-white/50">
            O número em destaque é quem <strong className="font-semibold text-white/80">já
            pagou</strong> por um curso que ainda não existe — é a dívida assumida com
            aluno, não uma métrica. Clique para ver nome e WhatsApp de cada um.
          </p>
          <div className="space-y-2">
            {(dados?.cursos || []).map((c) => {
              const fila = dados?.interessados_por_curso?.[c.curso_id] || [];
              const pagantes = dados?.compradores_por_curso?.[c.curso_id] || [];
              const expandido = aberto === c.curso_id;
              return (
                <div key={c.curso_id} className="card-sapiens rounded-2xl p-4">
                  <button
                    onClick={() => setAberto(expandido ? null : c.curso_id)}
                    className="flex w-full items-center gap-3 text-left"
                    data-testid={`admin-cursos-curso-${c.curso_id}`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-display font-semibold text-zinc-900">{c.titulo}</div>
                      <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-amber-600">
                        {c.status === "em_breve" ? "em breve" : c.status} · {c.custo_sparks} Sparks
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="font-display text-2xl font-extrabold leading-none tracking-tighter text-emerald-700">
                        {c.compradores}
                      </div>
                      <div className="font-mono-alt text-[9px] uppercase tracking-[0.2em] text-zinc-400">
                        pagaram
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="font-display text-2xl font-extrabold leading-none tracking-tighter text-zinc-950">
                        {c.interessados}
                      </div>
                      <div className="font-mono-alt text-[9px] uppercase tracking-[0.2em] text-zinc-400">
                        na fila
                      </div>
                    </div>
                    <ArrowRight
                      className={`h-4 w-4 shrink-0 text-zinc-400 transition-transform ${expandido ? "rotate-90" : ""}`}
                    />
                  </button>
                  {expandido && (
                    <div className="mt-3 space-y-3 border-t border-zinc-100 pt-3">
                      <div>
                        <div className="mb-1.5 font-mono-alt text-[10px] uppercase tracking-[0.25em] text-emerald-700">
                          Já pagaram · {c.sparks_arrecadados} Sparks
                        </div>
                        {pagantes.length === 0 ? (
                          <div className="py-2 text-sm text-zinc-500">Ninguém comprou ainda.</div>
                        ) : (
                          <div className="space-y-1.5">
                            {pagantes.map((p) => (
                              <LinhaDeContato
                                key={p.user_id}
                                pessoa={p}
                                testid={`admin-cursos-comprador-${p.user_id}`}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                      <div>
                        <div className="mb-1.5 font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">
                          Só querem ser avisados
                        </div>
                        {fila.length === 0 ? (
                          <div className="py-2 text-sm text-zinc-500">Ninguém na fila ainda.</div>
                        ) : (
                          <div className="space-y-1.5">
                            {fila.map((p) => (
                              <LinhaDeContato
                                key={p.user_id}
                                pessoa={p}
                                testid={`admin-cursos-interessado-${p.user_id}`}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        <Link
          to="/admin/users"
          className="pill mt-8 inline-flex items-center gap-1.5 rounded-full border border-white/15 px-4 py-2.5 text-xs font-medium text-white/70 hover:text-white"
        >
          Ver todos os alunos e WhatsApps <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
}
