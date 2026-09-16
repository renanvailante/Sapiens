import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  Radio, Video, Save, AlertTriangle, MessageCircleMore, Copy, Check, Users,
  Zap, Bell, ArrowRight,
} from "lucide-react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";

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

function formatarData(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

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

export default function AdminCursos() {
  const [dados, setDados] = useState(null);
  const [link, setLink] = useState("");
  const [tema, setTema] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const [aberto, setAberto] = useState(null);

  const carregar = useCallback(() => {
    api
      .get("/admin/cursos")
      .then(({ data }) => {
        setDados(data);
        setLink(data.live?.link || "");
        setTema(data.live?.tema || "");
      })
      .catch((e) => toast.error(errMsg(e, "Não foi possível carregar o painel de cursos.")));
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const publicar = async (e) => {
    e.preventDefault();
    setSalvando(true);
    try {
      await api.put("/admin/cursos/live", { link: link.trim(), tema: tema.trim() });
      toast.success("Edição publicada. Quem pagou já vê o link.");
      carregar();
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível publicar."));
    } finally {
      setSalvando(false);
    }
  };

  const live = dados?.live || {};
  const inscritos = dados?.inscritos || [];
  const semLinkComGentePaga = !live.link_publicado && inscritos.length > 0;

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
      <div className="mx-auto max-w-5xl px-6 py-12 md:px-10">
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

        {semLinkComGentePaga && (
          <div
            className="mt-4 flex items-start gap-2 rounded-2xl border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-100"
            data-testid="admin-cursos-alerta"
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              <strong>{inscritos.length} aluno(s) já pagaram</strong> a edição de {live.edicao} e
              ainda não existe link publicado. Eles compraram a vaga — o link precisa sair antes
              de {formatarData(live.inicio)}.
            </span>
          </div>
        )}

        {/* Publicação */}
        <form onSubmit={publicar} className="card-sapiens mt-6 rounded-2xl p-6" data-testid="admin-cursos-form">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-sapiens-accent to-sapiens-navy text-white">
              <Radio className="h-5 w-5" strokeWidth={1.7} />
            </div>
            <div>
              <div className="font-display text-lg font-bold tracking-tight text-zinc-950">
                Publicar a edição de {live.edicao || "—"}
              </div>
              <div className="text-sm text-zinc-500">
                {live.inicio ? formatarData(live.inicio) : "—"} · {live.apresentador}
              </div>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-500" htmlFor="admin-cursos-link">
                Link do Google Meet
              </label>
              <input
                id="admin-cursos-link"
                value={link}
                onChange={(e) => setLink(e.target.value)}
                placeholder="https://meet.google.com/abc-defg-hij"
                className="w-full rounded-xl border border-zinc-200 px-4 py-3 text-sm outline-none focus:border-sapiens-accent"
                data-testid="admin-cursos-link"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-500" htmlFor="admin-cursos-tema">
                Tema desta quinta
              </label>
              <input
                id="admin-cursos-tema"
                value={tema}
                onChange={(e) => setTema(e.target.value)}
                placeholder="Ex.: Funções — as 6 questões que mais caem"
                className="w-full rounded-xl border border-zinc-200 px-4 py-3 text-sm outline-none focus:border-sapiens-accent"
                data-testid="admin-cursos-tema"
              />
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={salvando}
              className="btn-sapiens inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold disabled:opacity-50"
              data-testid="admin-cursos-salvar"
            >
              <Save className="h-4 w-4" /> {salvando ? "Publicando…" : "Publicar"}
            </button>
            {live.link && (
              <a
                href={live.link}
                target="_blank"
                rel="noopener noreferrer"
                className="pill inline-flex items-center gap-2 rounded-xl border border-zinc-200 px-4 py-3 text-sm text-zinc-700 hover:bg-white/10"
              >
                <Video className="h-4 w-4" /> Abrir a sala
              </a>
            )}
            {live.publicado_em && (
              <span className="text-xs text-zinc-500">
                Última publicação: {formatarData(live.publicado_em)} por {live.publicado_por}
              </span>
            )}
          </div>
        </form>

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
