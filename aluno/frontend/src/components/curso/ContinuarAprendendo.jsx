import { Link } from "react-router-dom";
import { ArrowRight, Sparkles, Target, Layers } from "lucide-react";
import AnelDeProgresso from "../AnelDeProgresso";
import { emAndamento, recomendar } from "../../lib/recomendacao";

/**
 * O TOPO DA HOME DE CURSOS: onde você parou, e qual é o próximo passo.
 *
 * Responde em três segundos as quatro perguntas de quem abre a aba:
 * *onde estou, o que estou estudando, quanto andei, o que faço agora.*
 * Um catálogo responde só a segunda.
 *
 * **Só aparece quando tem o que dizer.** Aluno sem curso no ar não vê um
 * painel vazio com 0% — vê o catálogo, que é o que interessa a ele. Um
 * cabeçalho de progresso para quem não tem progresso é ruído com aparência
 * de produto.
 *
 * Nada aqui é calculado na tela: o progresso e a próxima estação vêm de
 * `GET /cursos` (que os deriva do MESMO `mapa_de_estados` da tela do curso),
 * e a escolha do que sugerir mora em `lib/recomendacao.js`.
 */

function CardDeCurso({ curso }) {
  const p = curso.progresso || {};
  const proxima = p.proxima;
  return (
    <Link
      to={`/cursos/${curso.curso_id}`}
      className="superficie lift flex items-center gap-4 rounded-3xl p-4"
      data-testid={`continuar-${curso.curso_id}`}
    >
      <AnelDeProgresso valor={p.percentual || 0} tamanho={54} espessura={5}>
        <span className="font-mono-alt text-[11px] font-bold text-white/80 tabular-nums">
          {p.percentual || 0}%
        </span>
      </AnelDeProgresso>
      <div className="min-w-0 flex-1">
        <div className="secao-olho truncate">{curso.categoria || curso.area}</div>
        <div className="truncate font-display text-[15px] font-bold tracking-tight text-white">
          {curso.titulo}
        </div>
        <div className="mt-0.5 truncate text-[12px] text-white/45">
          {proxima ? (
            <>Próxima: {proxima.titulo}</>
          ) : (
            <>{p.concluidas} de {p.estacoes} estações</>
          )}
        </div>
      </div>
      <ArrowRight className="h-4 w-4 shrink-0 text-white/25" />
    </Link>
  );
}

export default function ContinuarAprendendo({ cursos = [] }) {
  const abertos = emAndamento(cursos);
  const sugestao = recomendar(cursos);
  if (!abertos.length && !sugestao) return null;

  const destaque = abertos[0] || null;
  const proxima = destaque?.progresso?.proxima;

  return (
    <section className="mb-10" data-testid="continuar-aprendendo">
      {destaque && (
        <Link
          to={proxima
            ? `/cursos/${destaque.curso_id}/estacao/${proxima.estacao_id}`
            : `/cursos/${destaque.curso_id}`}
          className="superficie superficie-viva lift block rounded-3xl p-5 md:p-7"
          data-testid="continuar-heroi"
        >
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div className="min-w-0 flex-1">
              <div className="secao-olho">Continue de onde parou</div>
              <h2 className="mt-2 font-display text-2xl font-extrabold tracking-tight text-white md:text-3xl">
                {proxima ? proxima.titulo : destaque.titulo}
              </h2>
              <p className="mt-1.5 text-sm text-white/50">
                {destaque.titulo}
                {proxima?.duracao_minutos ? ` · ${proxima.duracao_minutos} min` : ""}
              </p>
              {proxima?.objetivo && (
                <p className="mt-3 max-w-xl text-sm leading-relaxed text-white/60">
                  {proxima.objetivo}
                </p>
              )}
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <span className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold">
                  Continuar estudando <ArrowRight className="h-4 w-4" />
                </span>
                <span className="chip">
                  <Layers className="h-3 w-3" />
                  {destaque.progresso.concluidas}/{destaque.progresso.estacoes} estações
                </span>
                {destaque.progresso.puladas > 0 && (
                  <span className="chip border-violet-300/25 text-violet-200">
                    <Target className="h-3 w-3" /> {destaque.progresso.puladas} pulada
                    {destaque.progresso.puladas === 1 ? "" : "s"} por domínio
                  </span>
                )}
              </div>
            </div>
            <AnelDeProgresso valor={destaque.progresso.percentual} tamanho={96}>
              <span className="font-display text-xl font-extrabold tracking-tight text-white tabular-nums">
                {destaque.progresso.percentual}%
              </span>
              <span className="mt-0.5 font-mono-alt text-[9px] uppercase tracking-[0.2em] text-white/35">
                do curso
              </span>
            </AnelDeProgresso>
          </div>
        </Link>
      )}

      {abertos.length > 1 && (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {abertos.slice(1).map((c) => <CardDeCurso key={c.curso_id} curso={c} />)}
        </div>
      )}

      {/* A sugestão, com o MOTIVO junto. Uma recomendação sem motivo é um
          anúncio; com motivo, é uma leitura do que a pessoa fez. Some quando
          apontaria para o mesmo curso do herói — repetir a mesma coisa duas
          vezes na mesma dobra não recomenda nada. */}
      {sugestao && sugestao.curso.curso_id !== destaque?.curso_id && (
        <Link
          to={sugestao.destino}
          className="superficie lift mt-4 flex flex-col items-stretch gap-4 rounded-3xl p-5 sm:flex-row sm:items-center"
          data-testid="recomendacao"
        >
          <div className="flex min-w-0 flex-1 items-center gap-4">
            <Sparkles className="h-5 w-5 shrink-0 text-[#7FD8FF]" />
            <div className="min-w-0 flex-1">
              <div className="secao-olho">Sugestão para você</div>
              <div className="mt-1 font-display text-base font-bold tracking-tight text-white">
                {sugestao.curso.titulo}
              </div>
              <div className="text-[13px] text-white/50">{sugestao.motivo}</div>
            </div>
          </div>
          <span className="pill btn-vidro inline-flex w-full shrink-0 items-center justify-center gap-2 rounded-full px-4 py-2.5 text-xs font-semibold sm:w-auto">
            {sugestao.acao} <ArrowRight className="h-3.5 w-3.5" />
          </span>
        </Link>
      )}
    </section>
  );
}
