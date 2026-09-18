import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Trophy, Medal, ArrowRight } from "lucide-react";
import { api } from "../lib/api";
import Tela from "../components/Tela";
import AnelDeProgresso from "../components/AnelDeProgresso";
import { Bloco } from "../components/Esqueleto";
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
    <Tela
      olho={<><Trophy className="h-3 w-3" /> Conquistas</>}
      titulo="O que você já provou que sabe."
      subtitulo="Cada medalha abre com o seu progresso, a condição exata e o caminho até ela."
      voltar="/dashboard"
      testid="conquistas"
      acoes={
        // O anel no lugar do contador em pílula. O mesmo par de números —
        // feitas e total — mas agora o olho lê a PROPORÇÃO antes de ler o
        // número, que é a única coisa que interessa numa tela de coleção.
        <div className="flex items-center gap-3" data-testid="conquistas-contagem">
          <AnelDeProgresso
            valor={avaliadas.length ? (100 * feitas) / avaliadas.length : 0}
            tamanho={62}
            espessura={6}
          >
            <span className="medida-n text-lg">{feitas}</span>
          </AnelDeProgresso>
          <div>
            <div className="font-mono-alt text-sm font-bold text-white">de {avaliadas.length}</div>
            <div className="medida-rotulo">desbloqueadas</div>
          </div>
        </div>
      }
    >
      {/* A PONTE PARA A LIGA. As duas telas respondem a mesma pergunta — "o
          que o meu esforço rendeu" — e a partir de 2026-09-17 elas dividem uma
          linha só no menu, em vez de duas. Dividir a linha só é honesto se o
          caminho continuar existindo, e é este link que o garante: sem ele, a
          Liga ficaria alcançável apenas pelo azulejo do Painel. */}
      <Link
        to="/liga"
        className="lift mb-5 flex items-center gap-3.5 rounded-2xl border border-amber-300/25 bg-amber-400/[0.07] p-4 hover:border-amber-300/55"
        data-testid="conquistas-para-liga"
      >
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-amber-300/30 bg-amber-400/15 text-amber-200">
          <Medal className="h-5 w-5" strokeWidth={1.8} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="font-display text-base font-bold tracking-tight text-white">
            Liga da semana
          </div>
          <div className="text-xs text-white/45">
            Troféu é o que você já provou. A liga é onde você está agora, contra os outros
            alunos — e ela zera toda segunda.
          </div>
        </div>
        <ArrowRight className="h-4 w-4 shrink-0 text-white/30" />
      </Link>

      {ctx ? (
        <PainelDeConquistas contexto={ctx} agrupado testid="conquistas-grade" />
      ) : (
        <div className="grid grid-cols-4 gap-2.5 sm:grid-cols-6">
          {Array.from({ length: 12 }).map((_, i) => (
            <Bloco key={i} className="aspect-square rounded-[22px]" />
          ))}
        </div>
      )}
    </Tela>
  );
}
