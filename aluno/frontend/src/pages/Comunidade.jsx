import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import Nav from "../components/Nav";
import { api, errMsg } from "../lib/api";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import {
  Users, MessageCircle, CheckCircle2, ArrowUp, Sparkles, Loader2, PenLine, Filter,
} from "lucide-react";

/**
 * O mural de dúvidas.
 *
 * Perguntar é de graça, sempre — cobrar de quem está travado num exercício é
 * cobrar no pior momento, e mataria o mural na primeira semana. Quem responde
 * ganha XP; quem tem a resposta MARCADA como a que resolveu ganha Sparks.
 *
 * O filtro "Sem resposta" é o primeiro da lista de propósito: o problema de
 * um mural jovem não é falta de leitor, é dúvida que fica sem ninguém. Pôr
 * essa fila na frente é o que transforma quem entrou para perguntar em quem
 * fica para responder.
 */

const FILTROS = [
  { id: "sem_resposta", rotulo: "Sem resposta" },
  { id: "recentes", rotulo: "Recentes" },
  { id: "resolvidas", rotulo: "Resolvidas" },
  { id: "minhas", rotulo: "Minhas" },
];

export function tempoRelativo(iso) {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return "agora";
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} h`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d} d`;
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

function CardDeDuvida({ duvida }) {
  const destacada = duvida.destacada_ate && duvida.destacada_ate > new Date().toISOString();
  return (
    <Link
      to={`/comunidade/${duvida.duvida_id}`}
      className="lift card-sapiens block rounded-2xl p-5"
      data-testid={`duvida-${duvida.duvida_id}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono-alt rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-[10px] uppercase tracking-[0.18em] text-white/50">
          {duvida.area}
        </span>
        {destacada && (
          <span className="pill inline-flex items-center gap-1 rounded-full border border-amber-400/25 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-200">
            <Sparkles className="h-3 w-3" /> Destaque
          </span>
        )}
        {duvida.resolvida && (
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/25 bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-200">
            <CheckCircle2 className="h-3 w-3" /> Resolvida
          </span>
        )}
        {duvida.status === "em_revisao" && (
          <span className="rounded-full border border-amber-400/25 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-200">
            Em revisão pela equipe
          </span>
        )}
      </div>

      <h3 className="mt-2.5 font-display text-lg font-bold leading-snug tracking-tight text-zinc-950">
        {duvida.titulo}
      </h3>
      <p className="mt-1 line-clamp-2 text-sm text-zinc-500">{duvida.corpo}</p>

      <div className="mt-3 flex items-center gap-4 text-xs text-white/40">
        <span>{duvida.autor_nome}</span>
        <span>{tempoRelativo(duvida.created_at)}</span>
        <span className="inline-flex items-center gap-1">
          <MessageCircle className="h-3 w-3" /> {duvida.respostas}
        </span>
        {duvida.votos > 0 && (
          <span className="inline-flex items-center gap-1">
            <ArrowUp className="h-3 w-3" /> {duvida.votos}
          </span>
        )}
      </div>
    </Link>
  );
}

function FormularioDeDuvida({ areas, aoPublicar }) {
  const [aberto, setAberto] = useState(false);
  const [area, setArea] = useState("Matemática");
  const [titulo, setTitulo] = useState("");
  const [corpo, setCorpo] = useState("");
  const [enviando, setEnviando] = useState(false);

  const valido = titulo.trim().length >= 8 && corpo.trim().length >= 10;

  const enviar = async (e) => {
    e.preventDefault();
    if (!valido || enviando) return;
    setEnviando(true);
    try {
      await api.post("/comunidade/duvidas", { area, titulo: titulo.trim(), corpo: corpo.trim() });
      setTitulo("");
      setCorpo("");
      setAberto(false);
      toast.success("Sua dúvida está no mural.");
      aoPublicar();
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível publicar agora."));
    } finally {
      setEnviando(false);
    }
  };

  if (!aberto) {
    return (
      <button
        onClick={() => setAberto(true)}
        className="cta-calor lift flex w-full items-center gap-3 rounded-2xl p-5 text-left"
        data-testid="comunidade-abrir-formulario"
      >
        <PenLine className="h-5 w-5 shrink-0" />
        <div>
          <p className="font-display text-lg font-bold tracking-tight">Publicar uma dúvida</p>
          <p className="text-sm opacity-70">De graça, sempre. Alguém da comunidade responde.</p>
        </div>
      </button>
    );
  }

  return (
    <form onSubmit={enviar} className="card-sapiens rounded-2xl p-5" data-testid="comunidade-formulario">
      <label className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">Área</label>
      <select
        value={area}
        onChange={(e) => setArea(e.target.value)}
        className="mt-1.5 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-sapiens-accent"
        data-testid="comunidade-area"
      >
        {areas.map((a) => (
          <option key={a} value={a} className="bg-[#0B1526]">{a}</option>
        ))}
      </select>

      <label className="font-mono-alt mt-4 block text-[10px] uppercase tracking-[0.3em] text-zinc-400">
        Sua dúvida em uma frase
      </label>
      <input
        value={titulo}
        onChange={(e) => setTitulo(e.target.value)}
        maxLength={160}
        placeholder="Ex.: Por que essa integral vira ln?"
        className="mt-1.5 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-base text-white placeholder:text-white/25 outline-none focus:border-sapiens-accent"
        data-testid="comunidade-titulo"
      />

      <label className="font-mono-alt mt-4 block text-[10px] uppercase tracking-[0.3em] text-zinc-400">
        Conte o que você já tentou
      </label>
      <textarea
        value={corpo}
        onChange={(e) => setCorpo(e.target.value)}
        maxLength={4000}
        rows={5}
        placeholder="Quanto mais específico, melhor a resposta que você recebe. Diga onde você travou."
        className="mt-1.5 w-full resize-y rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-base text-white placeholder:text-white/25 outline-none focus:border-sapiens-accent"
        data-testid="comunidade-corpo"
      />

      <div className="mt-4 flex items-center gap-2">
        <button
          type="submit"
          disabled={!valido || enviando}
          className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium disabled:opacity-50"
          data-testid="comunidade-publicar"
        >
          {enviando && <Loader2 className="h-4 w-4 animate-spin" />} Publicar
        </button>
        <button
          type="button"
          onClick={() => setAberto(false)}
          className="rounded-full px-4 py-2.5 text-sm text-white/60 hover:text-white"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}

export default function Comunidade() {
  const [dados, setDados] = useState({ items: [], total: 0, areas: [] });
  const [filtro, setFiltro] = useState("sem_resposta");
  const [area, setArea] = useState("");
  const [carregando, setCarregando] = useState(true);

  useDeclararContextoMentis("No mural de dúvidas da comunidade.");

  const carregar = useCallback(() => {
    setCarregando(true);
    const params = new URLSearchParams({ filtro });
    if (area) params.set("area", area);
    api
      .get(`/comunidade?${params}`)
      .then(({ data }) => setDados(data))
      .catch(() => setDados({ items: [], total: 0, areas: [] }))
      .finally(() => setCarregando(false));
  }, [filtro, area]);

  useEffect(carregar, [carregar]);

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-3xl px-6 py-12 md:px-10">
        <div className="font-mono-alt mb-3 flex items-center gap-2 text-xs uppercase tracking-[0.35em] text-white/50">
          <Users className="h-3.5 w-3.5" /> Comunidade
        </div>
        <h1
          className="font-display text-4xl font-extrabold tracking-tighter text-white md:text-5xl"
          data-testid="comunidade-title"
        >
          Ninguém trava sozinho.
        </h1>
        <p className="mt-3 max-w-xl text-white/60">
          Publique sua dúvida e responda a de outro aluno. Quando alguém marca a sua resposta como a
          que resolveu, você ganha Sparks — explicar é o estudo que mais rende.
        </p>

        <div className="mt-8">
          <FormularioDeDuvida areas={dados.areas.length ? dados.areas : ["Matemática"]} aoPublicar={carregar} />
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-2">
          {FILTROS.map((f) => (
            <button
              key={f.id}
              onClick={() => setFiltro(f.id)}
              className={`pill rounded-full px-3.5 py-1.5 text-xs transition-colors ${
                filtro === f.id
                  ? "border border-sapiens-accent/50 bg-sapiens-accent/20 text-white"
                  : "border border-white/10 bg-white/5 text-white/60 hover:text-white"
              }`}
              data-testid={`comunidade-filtro-${f.id}`}
            >
              {f.rotulo}
            </button>
          ))}
          <span className="ml-auto inline-flex items-center gap-1.5">
            <Filter className="h-3 w-3 text-white/30" />
            <select
              value={area}
              onChange={(e) => setArea(e.target.value)}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/70 outline-none"
              data-testid="comunidade-filtro-area"
            >
              <option value="" className="bg-[#0B1526]">Todas as áreas</option>
              {dados.areas.map((a) => (
                <option key={a} value={a} className="bg-[#0B1526]">{a}</option>
              ))}
            </select>
          </span>
        </div>

        <div className="mt-4 space-y-3">
          {carregando ? (
            <div className="flex items-center gap-2 py-8 text-white/50">
              <Loader2 className="h-4 w-4 animate-spin" /> Carregando…
            </div>
          ) : dados.items.length === 0 ? (
            <div className="card-sapiens rounded-2xl p-6" data-testid="comunidade-vazio">
              <p className="text-sm text-zinc-500">
                {filtro === "sem_resposta"
                  ? "Nenhuma dúvida esperando resposta agora. Boa hora para publicar a sua."
                  : "Nada por aqui ainda."}
              </p>
            </div>
          ) : (
            dados.items.map((d) => <CardDeDuvida key={d.duvida_id} duvida={d} />)
          )}
        </div>
      </div>
    </div>
  );
}
