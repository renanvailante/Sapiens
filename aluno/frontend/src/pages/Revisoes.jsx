import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import EstadoDeErro from "../components/EstadoDeErro";
import FilaDeRevisao from "../components/FilaDeRevisao";
import Trajetoria from "../components/Trajetoria";
import ListaDeLembretes from "../components/ListaDeLembretes";
import { useCarregamento } from "../hooks/useCarregamento";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { BookmarkPlus, CalendarClock, Loader2, LineChart } from "lucide-react";

/**
 * Revisões — a tela onde o ciclo aparece inteiro.
 *
 * Em cima, o que fazer HOJE (Fase 1): a fila diária, fechada e curta, montada
 * do estado que cada resposta atualiza. Embaixo, o que MUDOU (Fase 4): a linha
 * do tempo por habilidade, que é a única evidência de que o produto funcionou.
 *
 * As duas custam uma leitura do Firestore cada, independentemente de quantas
 * questões o aluno já respondeu. Isso não é detalhe de implementação: é a
 * razão de a tela existir desta forma e não como uma varredura do histórico.
 *
 * Medida pedagógica é de graça. O que custa Spark no Sapiens é geração de
 * conteúdo (Mentis), nunca medir o que o próprio aluno produziu respondendo.
 */

function Secao({ icone: Icone, titulo, descricao, children, testid }) {
  return (
    <section className="mt-10 first:mt-0" data-testid={testid}>
      <div className="flex items-center gap-2">
        <Icone className="h-4 w-4 text-white/50" />
        <h2 className="font-display text-2xl font-bold tracking-tight text-white">{titulo}</h2>
      </div>
      {descricao && <p className="mt-1.5 max-w-xl text-sm text-white/60">{descricao}</p>}
      <div className="mt-5">{children}</div>
    </section>
  );
}

/** A instrumentação do §12, mostrada ao aluno como o que ela é: uma medida. */
function ComoVaoAsRevisoes({ dados }) {
  const r = dados?.retestes;
  const t = dados?.transferencia;
  if (!r?.total) return null;
  return (
    <div className="card-sapiens mt-4 rounded-2xl p-5" data-testid="revisoes-instrumentacao">
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-400">
        Como vão as suas revisões
      </div>
      <div className="mt-3 flex flex-wrap gap-6">
        <div>
          <div className="font-display text-2xl font-extrabold tracking-tight text-zinc-950">{r.taxa}%</div>
          <div className="text-[11px] text-zinc-500">
            de acerto nas revisões ({r.acertos} de {r.total})
          </div>
        </div>
        {t?.total > 0 && (
          <div>
            <div className="font-display text-2xl font-extrabold tracking-tight text-zinc-950">{t.taxa}%</div>
            <div className="text-[11px] text-zinc-500">
              quando a mesma habilidade aparece em outro contexto ({t.acertos} de {t.total})
            </div>
          </div>
        )}
      </div>
      {t?.total > 0 && (
        <p className="mt-3 text-xs leading-relaxed text-zinc-500">
          O segundo número é o que importa: acertar a revisão pode ser memória da questão. Acertar em
          outro contexto é a habilidade.
        </p>
      )}
    </div>
  );
}

export default function Revisoes() {
  const [trajetoria, setTrajetoria] = useState(null);
  const [carregandoTrajetoria, setCarregandoTrajetoria] = useState(true);

  useDeclararContextoMentis("Na tela de revisões, vendo o que precisa retomar hoje.");

  const { dados: fila, carregando, erro, recarregar } = useCarregamento(
    async () => (await api.get("/revisao/fila")).data,
    [],
  );

  useEffect(() => {
    let ativo = true;
    api
      .get("/revisao/trajetoria")
      .then(({ data }) => { if (ativo) setTrajetoria(data); })
      .catch(() => { if (ativo) setTrajetoria({ indisponivel: true, habilidades: [] }); })
      .finally(() => { if (ativo) setCarregandoTrajetoria(false); });
    return () => { ativo = false; };
  }, []);

  if (carregando) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="flex items-center gap-2 p-10 text-white/60">
          <Loader2 className="h-4 w-4 animate-spin" /> Carregando suas revisões...
        </div>
      </div>
    );
  }

  if (erro) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="mx-auto max-w-3xl px-5 py-7 md:px-10 md:py-10">
          <EstadoDeErro mensagem={erro} aoTentarNovamente={recarregar} voltarPara="/dashboard" voltarLabel="Ir para o Painel" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-3xl px-5 py-7 md:px-10 md:py-10">
        <div className="mb-3 flex items-center gap-2 font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50">
          <CalendarClock className="h-3.5 w-3.5" /> Revisões
        </div>
        <h1
          className="titulo-tela"
          data-testid="revisoes-title"
        >
          O que voltar a estudar hoje.
        </h1>
        <p className="mt-3 max-w-xl text-white/60">
          Esta fila não é uma lista de matérias. Cada linha veio de um erro seu que o Sapiens
          conseguiu explicar — e a data de voltar a cobrar cada uma sai daí. Mais abaixo ficam os
          pontos que <strong className="font-semibold text-white/80">você</strong> marcou pelo app.
        </p>

        <div className="mt-8">
          <FilaDeRevisao fila={fila} />
        </div>

        <Secao
          icone={BookmarkPlus}
          titulo="O que você marcou"
          descricao={
            "Os pontos que você mesmo separou pelo app com \"Lembrar-me com a Mentis\" — " +
            "o que a fila de cima não tem como adivinhar."
          }
          testid="revisoes-lembretes"
        >
          <ListaDeLembretes />
        </Secao>

        <Secao
          icone={LineChart}
          titulo="Sua trajetória"
          descricao="O que aconteceu com cada habilidade ao longo do tempo — não o seu estado de hoje."
          testid="revisoes-trajetoria"
        >
          {carregandoTrajetoria ? (
            <div className="flex items-center gap-2 text-sm text-white/60">
              <Loader2 className="h-4 w-4 animate-spin" /> Carregando...
            </div>
          ) : (
            <>
              <Trajetoria dados={trajetoria} />
              <ComoVaoAsRevisoes dados={trajetoria?.instrumentacao || fila?.instrumentacao} />
            </>
          )}
        </Secao>
      </div>
    </div>
  );
}
