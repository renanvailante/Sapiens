import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import Nav from "../components/Nav";
import { api, errMsg } from "../lib/api";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { Users, MessageCircle, CheckCircle2, ArrowUp, Sparkles, Loader2, PenLine, Filter, Lock } from "lucide-react";

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

function FormularioDeDuvida({ areas, aoPublicar, sala = "geral" }) {
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
      await api.post("/comunidade/duvidas", {
        area, titulo: titulo.trim(), corpo: corpo.trim(), sala,
      });
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
      <label className="secao-olho">Área</label>
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
  // A sala vem da URL para que o link da sala VIP possa ser enviado e
  // favoritado — `?sala=vip` é o endereço dela.
  const [params, setParams] = useSearchParams();
  const sala = params.get("sala") === "vip" ? "vip" : "geral";
  const [souVip, setSouVip] = useState(null);

  useDeclararContextoMentis(
    sala === "vip" ? "Na sala VIP da comunidade." : "No mural de dúvidas da comunidade.",
  );

  // Pergunta ANTES de tentar abrir a sala: assim quem não comprou vê o convite
  // em vez de um 403 no meio da navegação.
  useEffect(() => {
    api.get("/comunidade/vip/acesso")
      .then(({ data }) => setSouVip(Boolean(data.vip)))
      .catch(() => setSouVip(false));
  }, []);

  const trocarSala = (nova) => {
    const p = new URLSearchParams(params);
    if (nova === "vip") p.set("sala", "vip");
    else p.delete("sala");
    setParams(p, { replace: true });
  };

  const carregar = useCallback(() => {
    if (sala === "vip" && souVip === false) {
      setDados({ items: [], total: 0, areas: [] });
      setCarregando(false);
      return;
    }
    setCarregando(true);
    const busca = new URLSearchParams({ filtro });
    if (area) busca.set("area", area);
    if (sala === "vip") busca.set("sala", "vip");
    api
      .get(`/comunidade?${busca}`)
      .then(({ data }) => setDados(data))
      .catch(() => setDados({ items: [], total: 0, areas: [] }))
      .finally(() => setCarregando(false));
  }, [filtro, area, sala, souVip]);

  useEffect(carregar, [carregar]);

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-3xl px-5 py-7 md:px-10 md:py-10">
        <div className="secao-olho flex items-center gap-1.5">
          <Users className="h-3.5 w-3.5" /> Comunidade
        </div>
        <h1
          className="titulo-tela"
          data-testid="comunidade-title"
        >
          Ninguém trava sozinho.
        </h1>
        <p className="mt-3 max-w-xl text-white/60">
          {sala === "vip"
            ? "A sala fechada de quem tem o pacote de 4.000 Sparks. Menos gente, resposta mais rápida — e a equipe lê todas."
            : "Publique sua dúvida e responda a de outro aluno. Quando alguém marca a sua resposta como a que resolveu, você ganha Sparks — explicar é o estudo que mais rende."}
        </p>

        {/* As duas salas. A VIP aparece para todo mundo de propósito: quem
            não tem o direito precisa saber que ela existe — é o que a torna
            comprável — e clicar leva ao convite, nunca a um erro. */}
        <div className="mt-6 inline-flex rounded-full border border-white/10 bg-white/[0.04] p-1" data-testid="comunidade-salas">
          <button
            onClick={() => trocarSala("geral")}
            className={`pill rounded-full px-4 py-2 text-xs font-medium transition-colors ${
              sala === "geral" ? "bg-white/12 text-white" : "text-white/50 hover:text-white"
            }`}
            data-testid="comunidade-sala-geral"
          >
            Mural aberto
          </button>
          <button
            onClick={() => trocarSala("vip")}
            className={`pill inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-medium transition-colors ${
              sala === "vip"
                ? "bg-violet-500/25 text-violet-100"
                : "text-violet-300/70 hover:text-violet-200"
            }`}
            data-testid="comunidade-sala-vip"
          >
            {souVip === false && <Lock className="h-3 w-3" />} Sala VIP
          </button>
        </div>

        {sala === "vip" && souVip === false ? (
          <div
            className="mt-6 rounded-2xl border border-violet-400/30 bg-violet-500/10 p-6"
            data-testid="comunidade-vip-fechada"
          >
            <div className="flex items-center gap-2 font-display text-xl font-bold tracking-tight text-violet-100">
              <Lock className="h-5 w-5" /> Esta sala é fechada.
            </div>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-violet-100/70">
              A Comunidade VIP vem com o pacote de 4.000 Sparks (R$119,90) — o mesmo que deixa a
              Mentis ilimitada para sempre. É a sala com menos gente e resposta mais rápida, e a
              equipe lê todas as dúvidas que entram aqui.
            </p>
            <Link
              to="/sparks"
              className="pill btn-sapiens mt-5 inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-medium"
              data-testid="comunidade-vip-comprar"
            >
              Quero o acesso VIP
            </Link>
          </div>
        ) : (
          <div className="mt-8">
            <FormularioDeDuvida
              areas={dados.areas.length ? dados.areas : ["Matemática"]}
              aoPublicar={carregar}
              sala={sala}
            />
          </div>
        )}

        <div
          className={`mt-8 flex flex-wrap items-center gap-2 ${
            sala === "vip" && souVip === false ? "hidden" : ""
          }`}
        >
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

        <div className={`mt-4 space-y-3 ${sala === "vip" && souVip === false ? "hidden" : ""}`}>
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
