import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { avisarSparksMudou } from "./Nav";
import AnelDeProgresso from "./AnelDeProgresso";
import ContagemEnem from "./ContagemEnem";
import {
  Flame, Snowflake, Trophy, Zap, ArrowRight, Check, Loader2,
} from "lucide-react";

/**
 * A TIRA DE PROGRESSO — ofensiva, nível, liga e o relógio do ENEM numa linha
 * só — e as missões do dia logo abaixo.
 *
 * O que ela era até 15/09: três painéis de vidro de 160px de altura com um
 * número gigante em cada um, mais uma faixa de contagem regressiva de altura
 * inteira acima deles. Quatro blocos grandes respondendo "como vai indo" numa
 * tela cuja primeira pergunta é "o que eu faço agora" — e todos eles em cima
 * do que o aluno podia fazer.
 *
 * O que ela é agora: quatro azulejos baixos, lado a lado, que o olho varre em
 * um movimento. A informação é a mesma; o espaço que ela ocupa caiu pela
 * metade, e a metade que sobrou foi para a ação.
 *
 * **O que esta tela se recusa a fazer** (a mesma linha ética de
 * `engajamento.py`, do lado de cá):
 *
 * * Nenhum contador regressivo além da virada do dia e da data do ENEM, que
 *   são os dois relógios reais que existem.
 * * Nenhum número inventado de "alunos estudando agora".
 * * O aviso de ofensiva em risco leva a ESTUDAR primeiro; o congelador é a
 *   segunda opção, e só aparece para quem tem sequência de verdade a perder.
 * * O preço de tudo aparece antes do clique.
 *
 * Os dados chegam por `dados` em vez de serem buscados aqui: o Painel já
 * carrega `/engajamento/me` para saber se a ofensiva está em risco (o
 * "próximo passo" usa esse sinal), e duas chamadas ao mesmo endereço na mesma
 * tela é o tipo de desperdício que a disciplina de leitura do produto existe
 * para impedir.
 */

/** Um azulejo da tira. Baixo, com o olho em cima e a medida embaixo — a
 *  mesma anatomia nos quatro, para o olho varrer em vez de ler. */
function Medida({ olho, cor, children, to, testid, tour }) {
  const conteudo = (
    <>
      <div className={`secao-olho flex items-center gap-1.5 ${cor || ""}`}>{olho}</div>
      {children}
    </>
  );
  const classe = "superficie flex flex-col justify-between p-4 min-h-[7rem]";
  if (to) {
    return (
      <Link to={to} className={`${classe} lift`} data-testid={testid} data-tour={tour}>
        {conteudo}
      </Link>
    );
  }
  return (
    <div className={classe} data-testid={testid} data-tour={tour}>
      {conteudo}
    </div>
  );
}

/** A sequência. O número é o que o aluno construiu; as sete bolinhas são a
 *  prova — cada uma só acende com resposta real por trás. */
function Ofensiva({ dados }) {
  const { dias, recorde, semana } = dados;
  return (
    <Medida
      olho={<><Flame className={`h-3 w-3 ${dias > 0 ? "text-amber-300" : ""}`} /> Ofensiva</>}
      cor={dias > 0 ? "text-amber-300/85" : ""}
      testid="progresso-ofensiva"
      tour="tour-ofensiva"
    >
      <div className="mt-2 flex items-baseline gap-1.5">
        <span className={`medida-n text-3xl ${dias > 0 ? "text-amber-100" : ""}`}>{dias}</span>
        <span className="text-sm text-white/45">{dias === 1 ? "dia" : "dias"}</span>
      </div>

      {/* Sete pontos, não sete círculos de 28px: a tira inteira tem 112px de
          altura e a semana é prova, não protagonista. O de HOJE tem anel. */}
      <div className="mt-2.5 flex items-center gap-[5px]">
        {semana.map((d) => (
          <span
            key={d.dia}
            className={[
              "h-2 w-2 rounded-full",
              d.ativo
                ? "bg-amber-400 shadow-[0_0_8px_-1px_rgba(251,191,36,0.9)]"
                : d.congelado
                ? "bg-sky-400/80"
                : "bg-white/15",
              d.hoje ? "ring-2 ring-[#4FD9FF]/70 ring-offset-1 ring-offset-[#070d18]" : "",
            ].join(" ")}
            title={d.congelado ? "Dia protegido por congelador" : d.dia}
          />
        ))}
      </div>
      {recorde > dias && <div className="medida-rotulo">recorde: {recorde} dias</div>}
    </Medida>
  );
}

/** O nível. O anel é a peça: o número dentro dele deixa de ser um placar e
 *  vira o estado de uma coisa que está enchendo. */
function Nivel({ dados }) {
  return (
    <Medida olho={<><Zap className="h-3 w-3" /> Nível</>} testid="progresso-nivel">
      <div className="mt-1 flex items-center gap-3">
        <AnelDeProgresso valor={dados.percentual} tamanho={58} espessura={6}>
          <span className="medida-n text-xl">{dados.nivel}</span>
        </AnelDeProgresso>
        <div className="min-w-0">
          <div className="font-mono-alt text-sm tabular-nums text-white/80">
            {dados.xp_total.toLocaleString("pt-BR")} XP
          </div>
          <div className="medida-rotulo">
            faltam {dados.xp_para_o_proximo.toLocaleString("pt-BR")}
          </div>
        </div>
      </div>
    </Medida>
  );
}

function Liga({ dados }) {
  return (
    <Medida
      olho={<><Trophy className="h-3 w-3" /> Liga</>}
      to="/liga"
      testid="progresso-liga"
      tour="tour-liga"
    >
      <div className="mt-2 flex items-center gap-2">
        <Trophy className="h-5 w-5 shrink-0" style={{ color: dados.cor }} />
        <span className="truncate font-display text-lg font-extrabold tracking-tight text-white">
          {dados.nome}
        </span>
      </div>
      <div className="medida-rotulo">
        {dados.minha_posicao
          ? `${dados.minha_posicao}º de ${dados.total} · ${dados.meus_pontos} XP`
          : "estude para entrar"}
      </div>
    </Medida>
  );
}

function Missoes({ missoes, aoResgatar, resgatando, celebrando }) {
  return (
    <section className="mt-6" data-testid="progresso-missoes" data-tour="tour-missoes">
      <div className="secao-cabeca">
        <h3 className="secao-titulo">Missões de hoje</h3>
        <span className="text-xs text-white/40">Trocam à meia-noite</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {missoes.map((m) => {
          const pct = Math.max(0, Math.min(100, (m.progresso / m.alvo) * 100));
          const pronta = m.concluida && !m.resgatada;
          return (
            <div
              key={m.id}
              className={[
                "superficie relative flex flex-col p-4",
                // A missão PRONTA é a única acesa da grade. É o objeto que
                // pede ação, e a regra 1 do sistema diz que é dele o brilho.
                pronta ? "superficie-viva" : "",
                celebrando === m.id ? "recompensa" : "",
              ].join(" ")}
              data-testid={`missao-${m.id}`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold leading-snug text-white">{m.titulo}</p>
                <span className="chip shrink-0 border-amber-300/25 bg-amber-400/10 px-2 py-0.5 text-[11px] text-amber-200">
                  <Zap className="h-3 w-3" /> {m.sparks}
                </span>
              </div>

              <div className="mt-auto pt-3.5">
                <div className="barra" data-cheia={pct >= 100}>
                  <i style={{ width: `${pct}%` }} />
                </div>
                <div className="mt-2.5 flex items-center justify-between gap-2">
                  <span className="font-mono-alt text-xs tabular-nums text-white/45">
                    {m.progresso}/{m.alvo}
                  </span>
                  {m.resgatada ? (
                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-300">
                      <Check className="h-3.5 w-3.5" /> Resgatada
                    </span>
                  ) : m.concluida ? (
                    <button
                      onClick={() => aoResgatar(m.id)}
                      disabled={resgatando === m.id}
                      className="pill btn-sapiens inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-bold disabled:opacity-60"
                      data-testid={`missao-resgatar-${m.id}`}
                    >
                      {resgatando === m.id ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                      Resgatar
                    </button>
                  ) : (
                    <Link
                      to={m.rota}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-[#7FD8FF] hover:underline"
                    >
                      {m.cta} <ArrowRight className="h-3 w-3" />
                    </Link>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default function PainelDeProgresso({ dados, aoMudar }) {
  const [resgatando, setResgatando] = useState(null);
  const [comprando, setComprando] = useState(false);
  // Qual missão está comemorando. Meio segundo de pulso NO CARD que gerou o
  // ganho — o toast continua existindo, mas ele aparece num canto da tela que
  // o olho tem de ir procurar, e um ganho que o aluno não vê não motiva.
  const [celebrando, setCelebrando] = useState(null);

  const resgatar = async (missaoId) => {
    setResgatando(missaoId);
    try {
      const { data } = await api.post(`/engajamento/missoes/${missaoId}/resgatar`);
      setCelebrando(missaoId);
      setTimeout(() => setCelebrando(null), 700);
      toast.success(`+${data.sparks_ganhos} Sparks e +${data.xp_ganho} XP.`);
      avisarSparksMudou();
      aoMudar?.();
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível resgatar agora."));
    } finally {
      setResgatando(null);
    }
  };

  const comprarCongelador = async () => {
    setComprando(true);
    try {
      await api.post("/engajamento/congelador");
      toast.success("Congelador guardado. Ele entra sozinho no dia em que você não estudar.");
      avisarSparksMudou();
      aoMudar?.();
    } catch (err) {
      // 402 é saldo insuficiente — a mensagem do servidor já diz quantos
      // Sparks faltam, e a loja fica a um clique. Nada de empurrar a compra
      // para quem não pediu: só quem clicou no congelador chega aqui.
      toast.error(errMsg(err, "Não foi possível comprar agora."), {
        action: err?.response?.status === 402
          ? { label: "Ver Sparks", onClick: () => { window.location.href = "/sparks"; } }
          : undefined,
      });
    } finally {
      setComprando(false);
    }
  };

  // Falha de rede não pode deixar um buraco no Painel: a tela inteira funciona
  // sem este bloco, então ele simplesmente não aparece.
  if (!dados) return null;

  const { ofensiva } = dados;

  return (
    <section data-testid="painel-progresso">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Ofensiva dados={ofensiva} />
        <Nivel dados={dados.nivel} />
        <Liga dados={dados.liga} />
        {/* O relógio do ENEM como quarta medida. A faixa grande com o
            argumento de venda continua existindo — ela vive em /cursos,
            /mentoria e na landing, que é onde a compra acontece. */}
        <ContagemEnem variante="medida" testid="dash-contagem-enem" />
      </div>

      {/* O aviso só aparece quando há sequência DE VERDADE em risco, e o
          primeiro caminho é estudar — não comprar. Fora dos azulejos e em
          largura inteira: é a única coisa desta seção que pede ação. */}
      {ofensiva.em_risco && (
        <div
          className="superficie mt-3 flex flex-col items-stretch gap-3 border-amber-300/30 bg-amber-400/[0.07] p-4 sm:flex-row sm:items-center"
          data-testid="progresso-risco"
        >
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <Flame className="h-5 w-5 shrink-0 text-amber-300" />
            <p className="min-w-0 flex-1 text-sm text-amber-100">
              Você ainda não estudou hoje. Uma questão mantém seus {ofensiva.dias}{" "}
              {ofensiva.dias === 1 ? "dia" : "dias"}.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/exams"
              className="pill btn-sapiens inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-bold"
              data-testid="progresso-risco-praticar"
            >
              Praticar agora <ArrowRight className="h-3 w-3" />
            </Link>
            {ofensiva.congeladores === 0 && (
              <button
                onClick={comprarCongelador}
                disabled={comprando}
                className="pill btn-vidro inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs disabled:opacity-60"
                data-testid="progresso-comprar-congelador"
              >
                {comprando ? <Loader2 className="h-3 w-3 animate-spin" /> : <Snowflake className="h-3 w-3" />}
                Congelador · {ofensiva.custo_congelador} Sparks
              </button>
            )}
          </div>
        </div>
      )}

      {ofensiva.congeladores > 0 && (
        <p
          className="mt-2 inline-flex items-center gap-1.5 text-xs text-sky-300/80"
          data-testid="progresso-congeladores"
        >
          <Snowflake className="h-3.5 w-3.5" />
          {ofensiva.congeladores} {ofensiva.congeladores === 1 ? "congelador guardado" : "congeladores guardados"} —
          entram sozinhos num dia que você não estudar.
        </p>
      )}

      <Missoes
        missoes={dados.missoes}
        aoResgatar={resgatar}
        resgatando={resgatando}
        celebrando={celebrando}
      />
    </section>
  );
}
