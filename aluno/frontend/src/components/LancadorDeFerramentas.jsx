import { useNavigate, useLocation } from "react-router-dom";
import {
  Compass, Medal, Trophy, PlayCircle, PenLine, Brain, Zap, GraduationCap,
  CalendarDays, Sparkles, Users, CalendarClock, History, LayoutGrid, Trash2,
  MessageSquareWarning, ShieldCheck, LogOut, Download, MessageCircle, HelpCircle,
  Radio,
} from "lucide-react";
import { Sheet, SheetContent, SheetTitle, SheetDescription } from "./ui/sheet";
import BrandMark from "./BrandMark";
import BotaoInstalar from "./InstalarApp";

/**
 * Todas as ferramentas do Sapiens numa tela só, em grade visual.
 *
 * Substitui o menu "…" (dez itens de texto num dropdown) e a lista do menu
 * mobile. O problema que os dois tinham era o mesmo: uma ferramenta dentro de
 * uma lista de texto, atrás de um ícone de três pontos, **não existe** para
 * quem não sabe que ela existe — e metade do produto morava ali (mural,
 * liga, revisões, questões geradas, perfil cognitivo, histórico).
 *
 * Agora é uma grade com ícone, nome e uma linha de descrição, agrupada pelo
 * que o aluno quer fazer, e não pela ordem em que as telas foram construídas.
 * Nenhuma tela foi removida: só saíram de dentro de um menu e viraram
 * superfície.
 */

const GRUPOS = [
  {
    titulo: "Estudar",
    itens: [
      { rota: "/treino", icone: Compass, nome: "Mapa de Treino", nota: "Missões curtas num mapa que se revela", destaque: true },
      { rota: "/exams", icone: PlayCircle, nome: "Provas do ENEM", nota: "Todas as provas, questão por questão" },
      { rota: "/redacao", icone: PenLine, nome: "Redação", nota: "Nota nas cinco competências" },
      { rota: "/minhas-questoes", icone: Sparkles, nome: "Questões geradas", nota: "As que a Mentis criou para você" },
      { rota: "/revisoes", icone: CalendarClock, nome: "Revisões", nota: "O que voltou para ser cobrado hoje" },
      { rota: "/cronograma", icone: CalendarDays, nome: "Cronograma", nota: "Sua semana, montada nos seus horários" },
    ],
  },
  {
    titulo: "Acompanhar",
    itens: [
      { rota: "/dashboard", icone: LayoutGrid, nome: "Painel", nota: "Onde tudo começa" },
      { rota: "/conquistas", icone: Trophy, nome: "Conquistas", nota: "O que você já provou que sabe" },
      { rota: "/cognitive-profile", icone: Brain, nome: "Desempenho", nota: "Por que você erra, não quanto" },
      { rota: "/liga", icone: Medal, nome: "Liga da semana", nota: "Sua posição entre os alunos" },
      { rota: "/history", icone: History, nome: "Histórico", nota: "Tudo o que você já resolveu" },
      { rota: "/sparks", icone: Zap, nome: "Sparks", nota: "Saldo, preços e pacotes" },
    ],
  },
  {
    titulo: "Gente",
    itens: [
      { rota: "/mentis", icone: MessageCircle, nome: "Mentis", nota: "Ela leu o seu histórico inteiro" },
      { rota: "/cursos", icone: Radio, nome: "Aula ao vivo · quinta", nota: "Com o 1º colocado de Medicina da USP", destaque: true, aoVivo: true },
      { rota: "/cursos", icone: GraduationCap, nome: "Cursos", nota: "Matemática, redação, TRI e leitura", chave: "cursos-catalogo" },
      { rota: "/mentoria", icone: Medal, nome: "Mentoria", nota: "Lista de espera · com o 1º colocado de Medicina da USP", destaque: true },
      { rota: "/comunidade", icone: Users, nome: "Comunidade", nota: "Pergunte, responda, ganhe Sparks" },
      { rota: "/sugestoes", icone: MessageSquareWarning, nome: "Fale com a equipe", nota: "Achou um erro? Tem uma ideia?" },
    ],
  },
];

const EXTRAS = [
  { rota: "/feed", icone: Zap, nome: "Feed" },
  { rota: "/trash", icone: Trash2, nome: "Lixeira" },
];

function Tile({ item, aoIr }) {
  return (
    <button
      type="button"
      onClick={() => aoIr(item.rota)}
      className={[
        "macio flex items-start gap-3 border p-3.5 text-left",
        item.destaque
          ? "border-[#4FD9FF]/30 bg-[#4FD9FF]/[0.07] hover:border-[#4FD9FF]/55 hover:bg-[#4FD9FF]/[0.12]"
          : "border-white/10 bg-white/[0.035] hover:border-white/25 hover:bg-white/[0.07]",
      ].join(" ")}
      data-testid={`lancador-${(item.chave || item.rota).replace(/\//g, "-")}`}
    >
      <span
        className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border ${
          item.destaque
            ? "border-[#4FD9FF]/35 bg-[#4FD9FF]/15 text-[#7FD8FF]"
            : "border-white/10 bg-white/5 text-white/60"
        }`}
      >
        <item.icone className="h-4 w-4" strokeWidth={1.8} />
        {/* Mesma marca que a barra usa: o ponto vermelho é o sinal de "isto
            acontece ao vivo", e ele precisa ser o mesmo nos dois lugares. */}
        {item.aoVivo && (
          <span className="absolute -right-0.5 -top-0.5 flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-500 opacity-80" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-rose-500" />
          </span>
        )}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium text-white">{item.nome}</span>
        <span className="mt-0.5 block text-[11px] leading-snug text-white/40">{item.nota}</span>
      </span>
    </button>
  );
}

export default function LancadorDeFerramentas({ aberto, aoFechar, user, aoSair }) {
  const nav = useNavigate();
  const { pathname } = useLocation();

  // `de` é a tela de onde a pessoa saiu — hoje só a página de reclamações e
  // sugestões usa, para a queixa chegar à equipe já dizendo de onde veio.
  const ir = (rota) => {
    aoFechar();
    nav(rota, { state: { de: pathname } });
  };

  return (
    <Sheet open={aberto} onOpenChange={(v) => { if (!v) aoFechar(); }}>
      <SheetContent
        side="left"
        className="flex w-[92vw] max-w-md flex-col border-r border-white/10 p-0"
        style={{ background: "rgba(9,17,31,0.97)", backdropFilter: "blur(16px)" }}
        data-testid="lancador"
      >
        <SheetTitle className="sr-only">Ferramentas do Sapiens</SheetTitle>
        <SheetDescription className="sr-only">
          Todas as telas do Sapiens, agrupadas pelo que você quer fazer.
        </SheetDescription>

        <div className="flex items-center gap-2 px-5 pb-3 pt-6 font-display text-2xl font-extrabold tracking-tighter text-white">
          <BrandMark className="h-6 w-6" /> Sapiens
        </div>

        <div className="flex-1 overflow-y-auto px-4 pb-4">
          {GRUPOS.map((g) => (
            <section key={g.titulo} className="mb-5">
              <div className="mb-2 px-1 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-white/30">
                {g.titulo}
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {g.itens.map((i) => (
                  <Tile key={i.chave || i.rota} item={i} aoIr={ir} />
                ))}
              </div>
            </section>
          ))}

          <div className="flex flex-wrap items-center gap-2 border-t border-white/8 pt-4">
            {EXTRAS.map((e) => (
              <button
                key={e.rota}
                type="button"
                onClick={() => ir(e.rota)}
                className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] text-white/50 hover:text-white"
                data-testid={`lancador-${e.rota.replace(/\//g, "-")}`}
              >
                <e.icone className="h-3 w-3" /> {e.nome}
              </button>
            ))}
            {/* O guia da Mentis abre sozinho a cada entrada, mas ele vive no
                Painel (é lá que estão os alvos que ele aponta). Daqui a porta
                é o endereço: `?guia=1` é a mesma porta que `/bem-vindo` usa. */}
            <button
              type="button"
              onClick={() => ir("/dashboard?guia=1")}
              className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] text-white/50 hover:text-white"
              data-testid="lancador-guia"
            >
              <HelpCircle className="h-3 w-3" /> Rever o guia
            </button>
            {/* Instalar some sozinho quando o app já está instalado. */}
            <BotaoInstalar
              className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] text-white/50 hover:text-white"
              testid="lancador-instalar"
            >
              <Download className="h-3 w-3" /> Instalar o app
            </BotaoInstalar>
            {user?.is_admin && (
              <button
                type="button"
                onClick={() => ir("/admin")}
                className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/25 bg-emerald-500/10 px-3 py-1.5 text-[11px] text-emerald-300"
                data-testid="lancador-admin"
              >
                <ShieldCheck className="h-3 w-3" /> Admin
              </button>
            )}
          </div>
        </div>

        <div className="border-t border-white/10 px-5 pb-6 pt-3">
          <button
            type="button"
            onClick={async () => { aoFechar(); await aoSair(); }}
            className="pill inline-flex w-full items-center justify-center gap-2 rounded-full border border-white/12 bg-white/5 px-4 py-3 text-sm font-medium text-white/70 hover:text-white"
            data-testid="lancador-sair"
          >
            <LogOut className="h-4 w-4" /> Sair
          </button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
