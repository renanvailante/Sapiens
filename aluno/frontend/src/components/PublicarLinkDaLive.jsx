import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Radio, Save, Video, AlertTriangle, ArrowRight, Check, Copy } from "lucide-react";
import { api, errMsg } from "../lib/api";

/**
 * O CAMPO DO LINK DO MEET DA SEMANA — a única tarefa recorrente do admin.
 *
 * Toda quinta a aula acontece, e alguém precisa colar ali o link da sala. Se
 * ele não for publicado, um aluno que pagou 200 Sparks fica com uma vaga e
 * sem porta. Por isso este cartão mora em DOIS lugares:
 *
 * · na primeira tela do admin (`/admin`), para a tarefa da semana não
 *   depender de lembrar em qual submenu ela fica;
 * · dentro de `/admin/cursos`, onde está o resto — quem pagou, o WhatsApp de
 *   cada um, o histórico e os cursos.
 *
 * São o mesmo componente de propósito: dois formulários para o mesmo campo
 * acabariam divergindo na validação, e o aviso vermelho ("tem gente paga e
 * nenhum link publicado") só serve se aparecer nos dois.
 *
 * **Quem decide qual edição está sendo publicada é o servidor** (ver
 * `cursos.proxima_live`). A tela nunca calcula "a próxima quinta": às 20h05
 * de uma quinta-feira o navegador e o backend discordariam sobre qual aula
 * está no ar, e o link iria para a semana errada.
 */
export default function PublicarLinkDaLive({ compacto = false, testid = "publicar-live" }) {
  const [live, setLive] = useState(null);
  const [link, setLink] = useState("");
  const [tema, setTema] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [copiado, setCopiado] = useState(false);

  const carregar = useCallback(() => {
    api
      .get("/admin/cursos/live")
      .then(({ data }) => {
        setLive(data);
        setLink(data.link || "");
        setTema(data.tema || "");
      })
      .catch((e) => toast.error(errMsg(e, "Não foi possível ler a edição desta quinta.")));
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

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(live.link);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      toast.error("O navegador bloqueou a cópia.");
    }
  };

  if (!live) return null;

  const quando = live.inicio
    ? new Date(live.inicio).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
    : "—";
  // O único estado que pede ação imediata: gente que já pagou e ainda não tem
  // para onde ir. Vermelho, e com o número de pessoas — "pendente" sozinho não
  // diz que existe alguém esperando.
  const urgente = !live.link_publicado && live.inscritos_count > 0;

  return (
    <form
      onSubmit={publicar}
      className={`card-sapiens rounded-2xl ${compacto ? "p-5" : "p-6"}`}
      data-testid={testid}
    >
      <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">
        <div className="flex min-w-0 w-full flex-1 items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-sapiens-accent to-sapiens-navy text-white">
            <Radio className="h-5 w-5" strokeWidth={1.7} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-display text-lg font-bold tracking-tight text-zinc-950">
              Link do Meet da quinta · {live.edicao || "—"}
            </div>
            <div className="text-sm text-zinc-500">
              {quando} · {live.duracao_minutos} min · {live.inscritos_count}{" "}
              {live.inscritos_count === 1 ? "inscrito" : "inscritos"}
            </div>
          </div>
        </div>
        <span
          className={`shrink-0 rounded-full px-3 py-1 font-mono-alt text-[10px] font-bold uppercase tracking-[0.2em] ${
            live.link_publicado
              ? "bg-emerald-50 text-emerald-700"
              : "bg-amber-50 text-amber-700"
          }`}
          data-testid={`${testid}-estado`}
        >
          {live.link_publicado ? "publicado" : "pendente"}
        </span>
      </div>

      {urgente && (
        <div
          className="mt-4 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800"
          data-testid={`${testid}-alerta`}
        >
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            <strong>{live.inscritos_count} aluno(s) já pagaram</strong> esta edição e ainda não
            existe link. Eles compraram a vaga — o link precisa sair antes de {quando}.
          </span>
        </div>
      )}

      <div className="mt-5 space-y-3">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-500" htmlFor={`${testid}-link`}>
            Link do Google Meet
          </label>
          <input
            id={`${testid}-link`}
            value={link}
            onChange={(e) => setLink(e.target.value)}
            placeholder="https://meet.google.com/abc-defg-hij"
            className="w-full rounded-xl border border-zinc-200 px-4 py-3 text-sm outline-none focus:border-sapiens-accent"
            data-testid={`${testid}-link`}
          />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-500" htmlFor={`${testid}-tema`}>
            Tema desta quinta
          </label>
          <input
            id={`${testid}-tema`}
            value={tema}
            onChange={(e) => setTema(e.target.value)}
            placeholder="Ex.: Funções — as 6 questões que mais caem"
            className="w-full rounded-xl border border-zinc-200 px-4 py-3 text-sm outline-none focus:border-sapiens-accent"
            data-testid={`${testid}-tema`}
          />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2.5">
        <button
          type="submit"
          disabled={salvando}
          className="btn-sapiens inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold disabled:opacity-50"
          data-testid={`${testid}-salvar`}
        >
          <Save className="h-4 w-4" /> {salvando ? "Publicando…" : "Publicar"}
        </button>
        {live.link && (
          <>
            <a
              href={live.link}
              target="_blank"
              rel="noopener noreferrer"
              className="pill inline-flex items-center gap-2 rounded-xl border border-zinc-200 px-4 py-3 text-sm text-zinc-700"
              data-testid={`${testid}-abrir`}
            >
              <Video className="h-4 w-4" /> Abrir a sala
            </a>
            <button
              type="button"
              onClick={copiar}
              className="pill inline-flex items-center gap-2 rounded-xl border border-zinc-200 px-4 py-3 text-sm text-zinc-700"
              data-testid={`${testid}-copiar`}
            >
              {copiado ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copiado ? "Copiado" : "Copiar link"}
            </button>
          </>
        )}
        {compacto && (
          <Link
            to="/admin/cursos"
            className="pill inline-flex items-center gap-1.5 rounded-xl px-3 py-3 text-sm text-zinc-500 hover:text-zinc-900"
            data-testid={`${testid}-painel`}
          >
            Ver quem pagou <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        )}
      </div>

      {live.publicado_em && (
        <div className="mt-3 text-xs text-zinc-500">
          Última publicação:{" "}
          {new Date(live.publicado_em).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
          {live.publicado_por ? ` por ${live.publicado_por}` : ""}
        </div>
      )}
    </form>
  );
}
