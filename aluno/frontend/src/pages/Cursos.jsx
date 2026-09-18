import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { toast } from "sonner";
import {
  Bell, BellRing, Lock, ArrowRight, PlayCircle, BookOpen,
  Infinity as Infinito, PackageCheck,
} from "lucide-react";
import { api, errMsg } from "../lib/api";
import { formatBRL } from "../lib/utils";
import { economiaDoPacote } from "../lib/venda";
import Nav, { avisarSparksMudou } from "../components/Nav";
import MentorUSP from "../components/MentorUSP";
import { MENTOR } from "../lib/mentor";
import ContagemEnem from "../components/ContagemEnem";
import ContinuarAprendendo from "../components/curso/ContinuarAprendendo";
import CapaDoCurso from "../components/curso/CapaDoCurso";
import { porArea } from "../lib/recomendacao";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { marcarAcessoDaLive } from "../lib/live";
import { quintasAteAProva } from "../lib/enem";

/**
 * `/cursos` — o CATÁLOGO de cursos gravados.
 *
 * Até 2026-09-16 esta página era duas: a aula ao vivo de quinta ocupava a
 * metade de cima e os cursos vinham depois dela. A aula saiu inteira para
 * `/aula-ao-vivo`, com endereço e entrada própria no lançador — ela acontece
 * toda semana, tem hora marcada e é a coisa mais concreta do produto, e
 * estava atrás de um nome que promete outra coisa. Aqui ficou só a ponte, no
 * topo: quem veio procurando a aula acha o caminho sem rolar a página.
 *
 * **O catálogo é uma VITRINE que cresce** (sete cursos em 2026-09-17, e a
 * conta sai do dado — nenhum número escrito nesta tela). Cada card tem capa,
 * título, chamada, status e uma ação só; a ementa fica atrás de um clique,
 * porque quarenta linhas de módulo entre o aluno e o botão é o que transforma
 * uma vitrine numa apostila. Um curso novo é um item em `backend/cursos.py`:
 * a interface não muda.
 *
 * Os cursos ainda sem estação publicada são vendidos assim mesmo, em pré-venda
 * declarada: cobra-se uma vez e o acesso é vitalício. Quem prefere esperar tem
 * o caminho de graça ao lado ("só me avise").
 *
 * **A prateleira de E-BOOKS** mora no fim, em seção própria e não misturada
 * aos cursos: baixar um PDF e percorrer estações são duas coisas diferentes,
 * e um card que parece o outro faz o aluno clicar errado.
 *
 * Tudo vem de `GET /cursos` numa chamada só — catálogo, o que este aluno já
 * comprou, o saldo dele e o bloco da live que a ponte usa.
 *
 * **O pacote de 4.000 Sparks inclui os cursos e os e-books** e chega como
 * `incluso_no_plano` em cada item — a tela nunca decide isso por
 * `package_id`. O catálogo da loja (`GET /sparks/packages`) vem junto só para
 * escrever QUAL pacote dá o quê e por quanto: preço em reais é decisão de
 * produto e mora no servidor, nunca aqui.
 */


export default function Cursos() {
  const { hash } = useLocation();
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);
  const [marcando, setMarcando] = useState(null);
  const [comprandoCurso, setComprandoCurso] = useState(null);
  const [comprandoEbook, setComprandoEbook] = useState(null);
  const [pacotes, setPacotes] = useState([]);
  const [precos, setPrecos] = useState(null);

  // O catálogo da loja, só para a frase "isto já vem no pacote X, por Y".
  // Não depende do Firestore e não muda durante a sessão: uma vez, e se
  // falhar a página inteira continua de pé sem a oferta.
  useEffect(() => {
    api.get("/sparks/packages")
      .then(({ data }) => {
        setPacotes(data.packages || []);
        setPrecos(data.precos_avulsos || null);
      })
      .catch(() => setPacotes([]));
  }, []);

  const carregar = useCallback(() => {
    api
      .get("/cursos")
      .then(({ data }) => {
        setDados(data);
        setErro(null);
        // O Painel anuncia a live sem chamar a API (ver `lib/live.js`); esta
        // marca é o que impede o anúncio de oferecer "garanta sua vaga" a
        // quem acabou de pagar.
        if (data.live?.tenho_acesso) marcarAcessoDaLive(data.live.edicao);
      })
      .catch((e) => setErro(errMsg(e, "Não foi possível carregar os cursos agora.")));
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  // `/cursos#ebooks` é o endereço que o menu usa para a prateleira de
  // e-books. O React Router empurra a URL sem rolar a página (é navegação de
  // aplicação, não do documento), então a rolagem é feita aqui — e OUVE o
  // hash, porque quem já está em `/cursos` e clica em "E-books" no menu só
  // muda a âncora: não há remontagem, e um efeito de montagem não veria esse
  // clique nunca. Depois de `dados` porque antes disso a seção não existe no
  // DOM para ser rolada até.
  useEffect(() => {
    if (!dados || !hash) return;
    const alvo = document.getElementById(hash.slice(1));
    if (alvo) alvo.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [dados, hash]);

  const live = dados?.live;

  // Quem vende cada direito sai do CATÁLOGO, nunca de um `package_id` escrito
  // aqui: se o produto mudar o pacote que inclui as lives, esta tela
  // acompanha sozinha.
  const pacoteDe = (direito) =>
    pacotes.find((p) => !p.oculto && (p.direitos || []).includes(direito));
  const pacoteDosCursos = pacoteDe("cursos_inclusos");
  const cursosInclusos = Boolean(dados?.cursos?.[0]?.incluso_no_plano);

  useDeclararContextoMentis(
    "Na aba Cursos, olhando o catálogo de cursos gravados.",
  );

  /** Pré-venda: cobra uma vez, o acesso é vitalício, e o aluno confirma
   *  sabendo que as aulas ainda não existem. */
  const comprarCurso = async (curso) => {
    setComprandoCurso(curso.curso_id);
    try {
      const { data } = await api.post(`/cursos/${curso.curso_id}/acesso`);
      avisarSparksMudou();
      toast.success(
        data.cobrado
          ? `"${curso.titulo}" é seu para sempre. Avisamos assim que abrir.`
          : data.incluso_no_plano
            ? `"${curso.titulo}" já vem no seu pacote. Avisamos assim que abrir.`
            : "Você já tem acesso vitalício a este curso.",
      );
      carregar();
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível concluir a compra."));
    } finally {
      setComprandoCurso(null);
    }
  };

  /** E-book: mesma pré-venda dos cursos — uma cobrança, acesso vitalício. */
  const comprarEbook = async (ebook) => {
    setComprandoEbook(ebook.ebook_id);
    try {
      const { data } = await api.post(`/cursos/ebooks/${ebook.ebook_id}/acesso`);
      avisarSparksMudou();
      toast.success(
        data.cobrado
          ? `"${ebook.titulo}" é seu para sempre.`
          : data.incluso_no_plano
            ? `"${ebook.titulo}" já vem no seu pacote.`
            : "Você já tem acesso a este e-book.",
      );
      carregar();
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível concluir a compra."));
    } finally {
      setComprandoEbook(null);
    }
  };

  const alternarInteresse = async (curso) => {
    setMarcando(curso.curso_id);
    try {
      if (curso.tenho_interesse) {
        await api.delete(`/cursos/${curso.curso_id}/interesse`);
      } else {
        await api.post(`/cursos/${curso.curso_id}/interesse`);
        toast.success(`Beleza! Você é avisado assim que "${curso.titulo}" abrir.`);
      }
      carregar();
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível registrar seu interesse."));
    } finally {
      setMarcando(null);
    }
  };

  // Aritmética, não retórica: cada quinta até a prova é uma aula que existe
  // ou não existe. Ver `lib/enem.js`.
  const quintasRestantes = quintasAteAProva();

  // A conta do pacote de cima: o que sairia comprando avulso o que ele já
  // inclui. Só aparece para quem ainda não tem os direitos.
  const conta = useMemo(
    () =>
      economiaDoPacote({
        pacote: pacoteDosCursos,
        quintasRestantes,
        precos,
        direitos: dados?.direitos || {},
      }),
    [pacoteDosCursos, quintasRestantes, precos, dados],
  );

  // Os cursos agrupados por área, na ordem que o servidor manda.
  const grupos = useMemo(
    () => porArea(dados?.areas || [], dados?.cursos || []),
    [dados],
  );

  /** O card de um curso. Função e não componente de módulo porque ele depende
   *  de quatro estados desta tela (comprando, marcando, a conta do pacote) —
   *  passar os quatro por props seria mudar a assinatura toda vez que a
   *  vitrine ganha um estado. */
  const cartaoDoCurso = (c) => (
    <article
      key={c.curso_id}
      className="macio lift flex flex-col overflow-hidden border border-white/25 bg-white/[0.07]"
      data-testid={`curso-${c.curso_id}`}
    >
      {/* A CAPA. É ela que torna o catálogo navegável de relance: sem imagem,
          sete cards são sete retângulos de texto e o olho não separa um do
          outro. As cores vêm do servidor (ver `components/curso/CapaDoCurso`
          e `backend/cursos.Capa`). */}
      <div className="relative">
        <CapaDoCurso capa={c.capa} testid={`curso-${c.curso_id}-capa`} />
        {/* O selo segue o CONTEÚDO, não uma data no calendário: um
            curso é "em breve" enquanto não tem estação publicada, e
            vira "no ar" no instante em que a primeira entra. Quem
            responde isso é o servidor (`tem_conteudo`). */}
        <span
          className={[
            "absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 font-mono-alt text-[11px] font-bold uppercase tracking-[0.18em] backdrop-blur-sm",
            c.tem_conteudo
              ? "border-emerald-300/40 bg-emerald-500/25 text-emerald-100"
              : "border-white/25 bg-black/35 text-white/85",
          ].join(" ")}
          data-testid={`curso-${c.curso_id}-selo`}
        >
          {c.tem_conteudo
            ? <><PlayCircle className="h-3 w-3" /> No ar</>
            : <><Lock className="h-3 w-3" /> Em breve</>}
        </span>
        {c.tenho_acesso && (
          <span
            className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-black/35 px-3 py-1.5 font-mono-alt text-[11px] font-bold uppercase tracking-[0.18em] text-white backdrop-blur-sm"
            data-testid={`curso-${c.curso_id}-selo-meu`}
          >
            <Infinito className="h-3 w-3" /> Meu
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col p-5">
      <h3 className="font-display text-xl font-bold leading-snug tracking-tight text-white">
        {c.titulo}
      </h3>

      <div className="mt-1.5 text-[15px] font-semibold text-[#7FD8FF]">{c.chamada}</div>
      <p className="mt-2.5 text-sm leading-relaxed text-white/75">{c.descricao}</p>

      {/* Os módulos ficam atrás de um clique: sete cards com seis linhas de
          módulo cada são quarenta e duas linhas de texto entre o aluno e o
          botão. Quem quer a ementa abre; quem quer o curso não paga por ela. */}
      <details className="mt-3">
        <summary className="cursor-pointer py-1 text-sm font-semibold text-[#7FD8FF] hover:underline">
          Ver os {c.modulos.length} módulos
        </summary>
        <ul className="mt-2 space-y-1">
          {c.modulos.map((m) => (
            <li key={m} className="flex items-start gap-2 text-sm text-white/75">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-[#4FD9FF]/60" />
              {m}
            </li>
          ))}
        </ul>
      </details>

      <div className="mt-auto border-t border-white/8 pt-3.5">
        <div className="font-mono-alt text-[11px] uppercase tracking-[0.15em] text-white/60">
          {c.carga} · {c.nivel}
        </div>

        {c.tenho_acesso && c.tem_conteudo ? (
          // Comprou E existe aula: o card diz "entra" e diz quanto ele já
          // andou — é o que o separa de um card de vitrine. Qualquer texto
          // a mais fica entre o aluno e a aula pela qual ele já pagou.
          <>
            {c.progresso?.comecou && (
              <div className="mt-3" data-testid={`curso-${c.curso_id}-progresso`}>
                <div className="flex items-center justify-between gap-2 text-[11px] text-white/45">
                  <span className="truncate">
                    {c.progresso.proxima
                      ? `Próxima: ${c.progresso.proxima.titulo}`
                      : `${c.progresso.concluidas}/${c.progresso.estacoes} estações`}
                  </span>
                  <span className="shrink-0 font-mono-alt tabular-nums">
                    {c.progresso.percentual}%
                  </span>
                </div>
                <div
                  className="barra mt-1.5"
                  data-cheia={c.progresso.percentual >= 100}
                  aria-hidden="true"
                >
                  <i style={{ width: `${c.progresso.percentual}%` }} />
                </div>
              </div>
            )}
            <Link
              to={`/cursos/${c.curso_id}`}
              className="pill btn-sapiens mt-3 inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-3.5 text-sm font-bold"
              data-testid={`curso-${c.curso_id}-estudar`}
            >
              <PlayCircle className="h-3.5 w-3.5" />
              {c.progresso?.comecou ? "Continuar" : "Começar agora"}
            </Link>
          </>
        ) : c.tenho_acesso ? (
          <div
            className="mt-3 flex items-center gap-2 rounded-xl border border-emerald-400/30 bg-emerald-500/10 px-3.5 py-3"
            data-testid={`curso-${c.curso_id}-meu`}
          >
            {c.incluso_no_plano ? (
              <PackageCheck className="h-4 w-4 shrink-0 text-emerald-300" />
            ) : (
              <Infinito className="h-4 w-4 shrink-0 text-emerald-300" />
            )}
            <span className="text-xs text-emerald-100/80">
              <strong className="font-semibold text-emerald-200">
                {c.incluso_no_plano ? "Incluso no seu pacote." : "Seu para sempre."}
              </strong>{" "}
              Avisamos no WhatsApp assim que as aulas entrarem no ar — sem pagar de novo.
            </span>
          </div>
        ) : (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              onClick={() => comprarCurso(c)}
              disabled={comprandoCurso === c.curso_id}
              className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-5 py-3 text-xs font-medium disabled:opacity-50"
              data-testid={`curso-${c.curso_id}-comprar`}
            >
              <Infinito className="h-3.5 w-3.5" />
              {comprandoCurso === c.curso_id
                ? "Garantindo…"
                : `Acesso vitalício · ${c.custo_sparks} Sparks`}
            </button>
            <button
              onClick={() => alternarInteresse(c)}
              disabled={marcando === c.curso_id}
              className={[
                "pill inline-flex items-center gap-1.5 rounded-full px-4 py-2.5 text-xs font-medium disabled:opacity-50",
                c.tenho_interesse
                  ? "border border-emerald-400/30 bg-emerald-500/15 text-emerald-200"
                  : "btn-vidro",
              ].join(" ")}
              data-testid={`curso-${c.curso_id}-avisar`}
            >
              {c.tenho_interesse ? (
                <><BellRing className="h-3.5 w-3.5" /> Na lista</>
              ) : (
                <><Bell className="h-3.5 w-3.5" /> Só me avise</>
              )}
            </button>
          </div>
        )}
      </div>
      </div>
    </article>
  );

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-5xl px-6 py-8 md:px-10 md:py-10">
        {erro && (
          <div className="mb-6 rounded-2xl border border-amber-300/30 bg-amber-500/10 px-5 py-4 text-sm text-amber-100">
            {erro}
          </div>
        )}

        {/* O relógio primeiro: é ele que explica por que esta página importa
            hoje e não mês que vem. */}
        <div className="mb-6">
          <ContagemEnem comCta={false} testid="cursos-contagem-enem" />
        </div>

        {/* ONDE VOCÊ PAROU — antes do catálogo, e antes da ponte da live.
            Quem já está estudando abre esta aba para voltar ao estudo, não
            para ver a vitrine de novo. O componente some sozinho para quem
            ainda não tem curso no ar, e aí a página começa pela ponte da
            aula ao vivo, como antes. */}
        <ContinuarAprendendo cursos={dados?.cursos || []} />

        {/* ---------------------------------------------------------------
            A AULA AO VIVO — que desde 2026-09-16 tem tela própria.
            ---------------------------------------------------------------
            Ela era a metade de cima desta página. Saiu inteira para
            `/aula-ao-vivo`: a compra, o link do Meet e a contagem regressiva
            moram num lugar só, e esta página voltou a ser o que o nome dela
            promete. O que fica aqui é a ponte — a aula é semanal e cara de
            perder, e quem abre "Cursos" procurando por ela precisa encontrar
            o caminho na primeira dobra. */}
        <Link
          to="/aula-ao-vivo"
          className="lift flex flex-wrap items-center gap-4 rounded-3xl border border-rose-400/25 bg-gradient-to-r from-rose-500/[0.12] via-amber-400/[0.07] to-transparent p-5 hover:border-rose-400/50"
          data-testid="cursos-ponte-live"
        >
          <span className="relative shrink-0">
            <MentorUSP tamanho="p" comSelo={false} testid="cursos-ponte-live-mentor" />
            <span className="absolute -right-1 -top-1 flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-500 opacity-80" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-rose-500" />
            </span>
          </span>
          <div className="min-w-0 flex-1">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-rose-200/90">
              {live?.ao_vivo_agora ? "Acontecendo agora" : "Ao vivo · toda quinta"}
            </div>
            <div className="mt-0.5 font-display text-lg font-bold tracking-tight text-white">
              A aula ao vivo com o {MENTOR.nome}, {MENTOR.titulo}.
            </div>
            <div className="text-xs text-white/50">
              {live?.tenho_acesso
                ? live.incluso_no_plano
                  ? "Inclusa no seu pacote — esta quinta e as próximas. Toque para entrar na sala."
                  : "Sua vaga desta quinta está garantida. Toque para pegar o link da sala."
                : `${live?.duracao_minutos ?? 60} minutos, uma vez por semana · ${live?.custo_sparks ?? 200} Sparks por edição`}
            </div>
          </div>
          <ArrowRight className="h-4 w-4 shrink-0 text-white/30" />
        </Link>

        {/* ---------------------------------------------------------------
            OS CURSOS — todos em breve, nenhum cobra nada
            --------------------------------------------------------------- */}
        <section id="cursos" className="mt-12 scroll-mt-24" data-testid="cursos-catalogo">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="font-display text-2xl font-extrabold tracking-tighter text-white md:text-3xl">
              O caminho inteiro, do zero à prova
            </h2>
            <span className="secao-olho">
              Em produção · entre na lista
            </span>
          </div>
          <p className="mt-2 max-w-2xl text-sm text-white/55">
            {/* O número de cursos sai do DADO e não do texto: até 2026-09-17
                esta frase dizia "quatro trilhas", e o catálogo passou a ter
                sete no dia em que três entraram. Um número escrito à mão numa
                vitrine é um número que mente na próxima entrada. */}
            {dados?.cursos?.length || ""} trilhas do zero ao ENEM, gravadas{" "}
            <strong className="font-semibold text-white/85">pelo {MENTOR.nome}</strong>, o
            mesmo {MENTOR.titulo} que dá a aula ao vivo de quinta — na ordem em que o
            conteúdo cobra, e não na ordem em que o livro apresenta.{" "}
            <strong className="font-semibold text-white/80">A maioria ainda não abriu</strong>:
            quem garante agora paga uma vez e fica com o curso para sempre, sem pagar de
            novo quando ele entrar no ar.
          </p>
          {/* O pacote que leva os quatro de uma vez. Só para quem ainda não
              tem: repetir a oferta a quem já comprou é o jeito mais rápido de
              fazer a pessoa duvidar do que comprou (mesma regra da loja). */}
          {pacoteDosCursos && !cursosInclusos && (
            <Link
              to="/sparks"
              className="lift mt-4 flex flex-wrap items-center gap-3 rounded-2xl border border-violet-400/30 bg-violet-500/[0.10] p-4 hover:border-violet-400/60"
              data-testid="cursos-oferta-pacote"
            >
              <PackageCheck className="h-6 w-6 shrink-0 text-violet-300" />
              <div className="min-w-0 flex-1">
                <div className="font-display text-sm font-bold tracking-tight text-violet-100">
                  Todos saem juntos no pacote de {pacoteDosCursos.sparks_amount} Sparks.
                </div>
                <div className="text-xs text-violet-200/70">
                  {conta ? (
                    <>
                      Avulso isto seria{" "}
                      <strong className="font-semibold text-violet-100">
                        {conta.partes.join(" + ")} = {conta.total} Sparks
                      </strong>
                      . O pacote de {formatBRL(pacoteDosCursos.price_cents)} inclui os dois — e
                      ainda credita {conta.sparksDoPacote} Sparks no seu saldo.
                    </>
                  ) : (
                    <>
                      {formatBRL(pacoteDosCursos.price_cents)} uma vez: os{" "}
                      {dados?.cursos?.length || 7} cursos e os e-books inclusos, para sempre — em vez de{" "}
                      {dados?.cursos?.[0]?.custo_sparks || 200} Sparks por curso. Os{" "}
                      {pacoteDosCursos.sparks_amount} Sparks entram no seu saldo do mesmo jeito.
                    </>
                  )}
                </div>
              </div>
              <ArrowRight className="h-4 w-4 shrink-0 text-violet-300/60" />
            </Link>
          )}
          {cursosInclusos && (
            <div
              className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-4"
              data-testid="cursos-todos-inclusos"
            >
              <PackageCheck className="h-6 w-6 shrink-0 text-emerald-300" />
              <div className="min-w-0 flex-1 text-sm text-emerald-100/85">
                <strong className="font-semibold text-emerald-200">Todos já são seus.</strong>{" "}
                Cursos e e-books vieram no seu pacote de Sparks — inclusive os que ainda
                entrarem no catálogo.
                Avisamos no WhatsApp assim que cada um abrir.
              </div>
            </div>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-2.5 rounded-2xl border border-white/10 bg-white/[0.035] p-4">
            <MentorUSP tamanho="p" comSelo={false} testid="cursos-catalogo-mentor" />
            <div className="min-w-0 flex-1 text-sm text-white/60">
              <strong className="font-semibold text-white">Quem grava é o {MENTOR.nome}.</strong>{" "}
              Os cursos são feitos pela mesma pessoa que passou em 1º lugar em Medicina na
              USP — não é conteúdo de banco de apostila com nome de professor na capa.
            </div>
          </div>

          {/* O catálogo por ÁREA, e não uma grade plana.

              Com sete cursos a diferença já aparece; com dezoito, uma lista
              plana deixa de ser navegável. A hierarquia (Área → Categoria →
              Curso) vem pronta do servidor em `areas` — a tela não deduz a
              área pelo título, e área sem curso não aparece. */}
          {grupos.map((area) => (
            <div key={area.area_id} id={`area-${area.area_id}`} className="mt-8 scroll-mt-24">
              <div className="secao-cabeca">
                <div className="min-w-0">
                  <h3 className="secao-titulo">{area.titulo}</h3>
                  <p className="mt-0.5 text-sm text-white/70">{area.chamada}</p>
                </div>
                <span className="shrink-0 font-mono-alt text-xs text-white/60">
                  {area.itens.length} curso{area.itens.length === 1 ? "" : "s"}
                </span>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                {area.itens.map((c) => cartaoDoCurso(c))}
              </div>
            </div>
          ))}
        </section>

        {/* ---------------------------------------------------------------
            E-BOOKS — prateleira própria, e não um curso com outro nome.
            ---------------------------------------------------------------
            O que se faz com um e-book é BAIXAR e ler (no ônibus, impresso,
            sem internet); o que se faz com um curso é percorrer estações
            dentro do app. Misturar os dois na mesma grade faz o aluno clicar
            num esperando o outro.

            A prateleira vem do servidor (`cursos.EBOOKS`) e cresce lá: um
            e-book novo é um item numa tupla, e esta seção não muda. */}
        {(dados?.ebooks?.length || 0) > 0 && (
          <section id="ebooks" className="mt-12 scroll-mt-24" data-testid="cursos-ebooks">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h2 className="font-display text-2xl font-extrabold tracking-tighter text-white md:text-3xl">
                E-books
              </h2>
              <span className="secao-olho">Para ler no celular ou imprimir</span>
            </div>
            <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-white/75">
              Material curto e direto, feito para sair do app: formulário, repertório e plano de
              estudo. Quem tem o pacote de Sparks já tem a prateleira inteira.
            </p>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              {dados.ebooks.map((e) => (
                <article
                  key={e.ebook_id}
                  className="macio lift flex flex-col overflow-hidden border border-white/25 bg-white/[0.07]"
                  data-testid={`ebook-${e.ebook_id}`}
                >
                  <div className="relative">
                    <CapaDoCurso capa={e.capa} altura="h-36" testid={`ebook-${e.ebook_id}-capa`} />
                    <span className="absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-black/35 px-2.5 py-1 font-mono-alt text-[11px] font-bold uppercase tracking-[0.18em] text-white backdrop-blur-sm">
                      <BookOpen className="h-3 w-3" /> {e.paginas} páginas
                    </span>
                  </div>

                  <div className="flex flex-1 flex-col p-5">
                    <h3 className="font-display text-lg font-bold leading-snug tracking-tight text-white">
                      {e.titulo}
                    </h3>
                    <div className="mt-1 text-sm font-semibold text-[#7FD8FF]">{e.chamada}</div>
                    <p className="mt-2 text-sm leading-relaxed text-white/75">{e.descricao}</p>

                    <div className="mt-auto pt-4">
                      {e.tenho_acesso && e.tem_conteudo ? (
                        // Lê-se DENTRO do app, página por página — nenhum
                        // aluno baixa nada do Sapiens. Ver `EbookLeitor`.
                        <Link
                          to={`/cursos/ebooks/${e.ebook_id}`}
                          className="pill btn-sapiens inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-3.5 text-sm font-bold"
                          data-testid={`ebook-${e.ebook_id}-ler`}
                        >
                          <BookOpen className="h-3.5 w-3.5" /> Ler agora
                        </Link>
                      ) : e.tenho_acesso ? (
                        // Comprou, mas as páginas ainda não existem. A mesma
                        // distinção do curso comprado sem estação no ar: nunca
                        // oferecemos um link que não abre.
                        <div
                          className="flex items-center gap-2 rounded-xl border border-emerald-400/30 bg-emerald-500/10 px-3.5 py-3 text-xs text-emerald-100/85"
                          data-testid={`ebook-${e.ebook_id}-meu`}
                        >
                          {e.incluso_no_plano
                            ? <PackageCheck className="h-4 w-4 shrink-0 text-emerald-300" />
                            : <Infinito className="h-4 w-4 shrink-0 text-emerald-300" />}
                          <span>
                            <strong className="font-semibold text-emerald-200">
                              {e.incluso_no_plano ? "Incluso no seu pacote." : "Seu para sempre."}
                            </strong>{" "}
                            Avisamos quando ele entrar no ar.
                          </span>
                        </div>
                      ) : (
                        <button
                          onClick={() => comprarEbook(e)}
                          disabled={comprandoEbook === e.ebook_id}
                          className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-5 py-3 text-xs font-medium disabled:opacity-50"
                          data-testid={`ebook-${e.ebook_id}-comprar`}
                        >
                          <Infinito className="h-3.5 w-3.5" />
                          {comprandoEbook === e.ebook_id
                            ? "Garantindo…"
                            : `Acesso vitalício · ${e.custo_sparks} Sparks`}
                        </button>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        {/* ---- A mentoria: a mesma pessoa, um a um, com fila ---- */}
        <Link
          to="/mentoria"
          className="lift mt-10 flex items-center gap-4 rounded-2xl border border-[#4FD9FF]/20 bg-[#4FD9FF]/[0.06] p-5 hover:border-[#4FD9FF]/45"
          data-testid="cursos-mentoria"
        >
          <MentorUSP tamanho="p" comSelo={false} testid="cursos-mentoria-foto" />
          <div className="min-w-0 flex-1">
            <div className="font-display text-base font-bold tracking-tight text-white">
              Quer ele só para você?
            </div>
            <div className="text-xs text-white/45">
              A mentoria é um a um, com o próprio {MENTOR.nome}. Uma pessoa, poucas
              vagas — entre na lista de espera.
            </div>
          </div>
          <ArrowRight className="h-4 w-4 shrink-0 text-white/30" />
        </Link>
      </div>
    </div>
  );
}
