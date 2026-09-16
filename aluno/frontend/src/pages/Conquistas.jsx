import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Trophy } from "lucide-react";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import PainelDeConquistas from "../components/PainelDeConquistas";
import { avaliarConquistas } from "../lib/conquistas";
import { computeStreak, computeWeek } from "../lib/atividade";
import { useDeclararContextoMentis } from "../lib/mentisContexto";

/**
 * A sala de troféus. O Painel mostra uma tira com as que estão mais perto de
 * sair; aqui estão todas, agrupadas, e cada uma abre com progresso, condição
 * e o caminho para conquistá-la.
 *
 * As seis chamadas abaixo são as MESMAS que o Painel já faz — nenhuma conta
 * nova, nenhum contador paralelo. Todas O(1): documento único do aluno ou
 * consulta indexada.
 */
export default function Conquistas() {
  const [ctx, setCtx] = useState(null);

  useEffect(() => {
    Promise.allSettled([
      api.get("/firestore/students/me/respondidas").then(({ data }) => (data.item_ids || []).length),
      api.get("/firestore/students/me/activity").then(({ data }) => data.dates || []),
      api.get("/skills-map").then(({ data }) => data.hubs || []),
      api.get("/analyses").then(({ data }) => data),
      api.get("/firestore/students/me/rounds").then(({ data }) => data.rounds || []),
      api.get("/redacao", { params: { limit: 20 } }).then(({ data }) => data.items || []),
    ]).then(([q, a, h, an, r, red]) => {
      const valor = (res, vazio) => (res.status === "fulfilled" ? res.value : vazio);
      const dates = valor(a, []);
      const redacoes = valor(red, []);
      setCtx({
        totalRespondidas: valor(q, 0),
        streak: computeStreak(dates),
        weekActiveDays: computeWeek(dates).filter((d) => d.active).length,
        hubs: valor(h, []),
        analyses: valor(an, []),
        rounds: valor(r, []),
        redacoesCorrigidas: redacoes.filter((x) => x.avaliacao).length,
        melhorRedacao: redacoes.reduce((m, x) => Math.max(m, x.avaliacao?.nota_total ?? 0), 0),
      });
    });
  }, []);

  const avaliadas = avaliarConquistas(ctx);
  const feitas = avaliadas.filter((c) => c.desbloqueada).length;

  useDeclararContextoMentis("Na tela de Conquistas.");

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-4xl px-6 py-10 md:px-10">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs text-white/45 hover:text-white"
          data-testid="conquistas-voltar"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Painel
        </Link>

        <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
          <h1
            className="font-display text-4xl font-extrabold tracking-tighter text-white md:text-5xl"
            data-testid="conquistas-title"
          >
            Conquistas
          </h1>
          <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2">
            <Trophy className="h-4 w-4 text-[#7FD8FF]" />
            <span className="font-mono-alt text-sm font-bold text-white" data-testid="conquistas-contagem">
              {feitas}
              <span className="text-white/40">/{avaliadas.length}</span>
            </span>
          </div>
        </div>

        <div className="mt-8">
          {ctx ? (
            <PainelDeConquistas contexto={ctx} agrupado testid="conquistas-grade" />
          ) : (
            <div className="text-sm text-white/45">Contando o que você já fez…</div>
          )}
        </div>
      </div>
    </div>
  );
}
