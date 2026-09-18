import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, BookOpen } from "lucide-react";
import { api, errMsg } from "../lib/api";
import Tela from "../components/Tela";
import EstadoDeErro from "../components/EstadoDeErro";
import { Bloco as Esqueleto, Linha } from "../components/Esqueleto";
import Bloco from "../components/curso/Blocos";
import { useDeclararContextoMentis } from "../lib/mentisContexto";

/**
 * `/cursos/ebooks/:ebookId` — O LEITOR DE E-BOOK, dentro do app.
 *
 * Nenhum aluno baixa nada do Sapiens: um e-book se lê aqui, página por
 * página, do mesmo jeito que um curso se estuda em `CursoEstacao`. Os blocos
 * são os MESMOS três tipos de leitura de um curso (texto, tabela, exemplo) —
 * por isso este leitor reaproveita `components/curso/Blocos` sem reescrever
 * nada: o que muda é que aqui não há exercício, não há progresso para
 * gravar e não há "estação seguinte" — só a página seguinte.
 *
 * **"Explicar melhor" é o mesmo botão do curso**, por
 * `mentis_routes.EXPLICACAO_CONTEUDO_COST` Sparks: o componente de bloco só
 * chama `aoExplicar`, e quem sabe que isto é um e-book (e não uma estação de
 * curso) é esta tela, que aponta para a rota certa.
 *
 * **Sair a qualquer momento** volta para a prateleira (`/cursos#ebooks`) — um
 * e-book não tem "mapa" próprio como um curso; a prateleira É o mapa dele.
 */

function EsqueletoDoLeitor() {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Carregando o e-book">
      <Linha w="min(70%, 22rem)" h={26} />
      <Esqueleto className="rounded-3xl" altura={260} />
    </div>
  );
}

export default function EbookLeitor() {
  const { ebookId } = useParams();

  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [pagina, setPagina] = useState(0);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const { data } = await api.get(`/cursos/ebooks/${ebookId}/conteudo`);
      setDados(data);
      setPagina(0);
    } catch (e) {
      setErro(errMsg(e, "Não conseguimos abrir este e-book."));
    } finally {
      setCarregando(false);
    }
  }, [ebookId]);

  useEffect(() => { carregar(); }, [carregar]);

  useEffect(() => { window.scrollTo({ top: 0, behavior: "smooth" }); }, [pagina, ebookId]);

  const paginas = dados?.paginas || [];
  const atual = paginas[pagina] || null;
  const ultima = pagina >= paginas.length - 1;

  useDeclararContextoMentis(
    useMemo(
      () => (dados && atual
        ? `Lendo o e-book "${dados.titulo}", página "${atual.titulo}" (${pagina + 1} de ${paginas.length}).`
        : ""),
      [dados, atual, pagina, paginas.length],
    ),
  );

  // "Explicar melhor" — 10 Sparks, cobrados no servidor. Quem sabe que isto é
  // um E-BOOK (e não um curso) é esta tela; o componente do bloco só chama.
  const aoExplicar = useCallback(async (blocoId) => {
    const { data } = await api.post(
      `/cursos/ebooks/${ebookId}/paginas/${atual.pagina_id}/blocos/${blocoId}/explicar`,
    );
    return data;
  }, [ebookId, atual]);

  return (
    <Tela
      olho="E-book"
      titulo={dados?.titulo || "E-book"}
      subtitulo={atual?.titulo}
      voltar="/cursos#ebooks"
      voltarLabel="Meus e-books"
      largura="md"
      testid="ebook-leitor"
    >
      {carregando && <EsqueletoDoLeitor />}

      {!carregando && erro && (
        <EstadoDeErro
          mensagem={erro}
          aoTentarNovamente={carregar}
          voltarPara="/cursos#ebooks"
          voltarLabel="Voltar aos e-books"
        />
      )}

      {!carregando && !erro && atual && (
        <div className="space-y-5">
          {/* A régua de páginas — o que substitui o trilho de um curso.
              Simples de propósito: um e-book não tem estado para desenhar,
              só posição. */}
          <div className="flex items-center gap-2 font-mono-alt text-[11px] uppercase tracking-[0.15em] text-white/45">
            <BookOpen className="h-3.5 w-3.5" />
            Página {pagina + 1} de {paginas.length}
          </div>
          <div className="barra" aria-hidden="true">
            <i style={{ width: `${((pagina + 1) / paginas.length) * 100}%` }} />
          </div>

          <div key={atual.pagina_id} className="space-y-5 reveal">
            {atual.blocos.map((bloco) => (
              <Bloco key={bloco.bloco_id} bloco={bloco} aoExplicar={aoExplicar} />
            ))}
          </div>

          <nav className="flex items-center justify-between gap-3 pt-2">
            {pagina > 0 ? (
              <button
                type="button"
                onClick={() => setPagina((i) => Math.max(0, i - 1))}
                className="chip inline-flex items-center gap-1.5"
                data-testid="pagina-anterior"
              >
                <ArrowLeft className="h-3 w-3" /> Página anterior
              </button>
            ) : <span />}
            {!ultima && (
              <button
                type="button"
                onClick={() => setPagina((i) => Math.min(paginas.length - 1, i + 1))}
                className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold"
                data-testid="pagina-seguinte"
              >
                Próxima página <ArrowRight className="h-4 w-4" />
              </button>
            )}
          </nav>
        </div>
      )}
    </Tela>
  );
}
