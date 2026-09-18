import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import Mentis from "../components/Mentis";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { MessageSquareWarning, Lightbulb, Bug, Heart, Send, Loader2, CheckCircle2 } from "lucide-react";

/**
 * Reclamações e sugestões — o canal do aluno com quem faz o Sapiens.
 *
 * Não é a bandeira de questão (`ReportarQuestao`), que fala de UMA questão e
 * paga Sparks quando aprovada. Aqui o assunto é o produto, e não custa nem
 * rende Spark nenhum: cobrar para reclamar calaria justamente quem tem menos
 * saldo, e pagar por reclamação encheria a fila de ruído.
 *
 * A tela mostra o que o aluno já mandou junto com o estado de cada mensagem —
 * é o que diferencia um canal de uma caixa de correio sem carteiro.
 */

const TIPOS = [
  { id: "reclamacao", rotulo: "Reclamação", icone: MessageSquareWarning,
    convite: "O que aconteceu? Conte com detalhe — onde foi, o que você esperava e o que veio no lugar." },
  { id: "sugestao", rotulo: "Sugestão", icone: Lightbulb,
    convite: "O que faria o Sapiens ficar melhor para você?" },
  { id: "problema", rotulo: "Algo quebrado", icone: Bug,
    convite: "Descreva o que travou, em que tela, e o que você estava fazendo na hora." },
  { id: "elogio", rotulo: "Elogio", icone: Heart,
    convite: "O que funcionou bem? Isso ajuda a saber o que não mexer." },
];

const STATUS_LABEL = { nova: "Recebida", lida: "Lida pela equipe", respondida: "Respondida" };
const STATUS_CLS = {
  nova: "border-zinc-200 bg-zinc-50 text-zinc-500",
  lida: "border-sky-100 bg-sky-50 text-sky-700",
  respondida: "border-emerald-100 bg-emerald-50 text-emerald-700",
};

const MAX_CHARS = 2000;
const MIN_CHARS = 5;

function formatarData(iso) {
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function Sugestoes() {
  const location = useLocation();
  const [tipo, setTipo] = useState("reclamacao");
  const [mensagem, setMensagem] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [minhas, setMinhas] = useState([]);
  const [carregando, setCarregando] = useState(true);

  useDeclararContextoMentis("Na tela de reclamações e sugestões.");

  const carregar = () => {
    setCarregando(true);
    api
      .get("/sugestoes/me")
      .then(({ data }) => setMinhas(data.items || []))
      .catch(() => setMinhas([]))
      .finally(() => setCarregando(false));
  };

  useEffect(carregar, []);

  const tipoAtual = TIPOS.find((t) => t.id === tipo) || TIPOS[0];
  const curta = mensagem.trim().length < MIN_CHARS;

  const enviar = async (e) => {
    e.preventDefault();
    if (curta || enviando) return;
    setEnviando(true);
    try {
      await api.post("/sugestoes", {
        tipo,
        mensagem: mensagem.trim(),
        // A rota de onde o aluno veio, quando quem trouxe ele até aqui
        // informou (o menu e o link do Painel informam). Quem lê a
        // reclamação sabe de que tela ela saiu sem ter que perguntar de
        // volta. Nunca `document.referrer`: numa SPA ele aponta para o site
        // que trouxe a pessoa ao Sapiens, não para a tela anterior.
        contexto: location.state?.de || undefined,
      });
      setMensagem("");
      toast.success("Recebemos sua mensagem. Obrigado — a equipe lê todas.");
      carregar();
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível enviar agora."));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-3xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="secao-olho flex items-center gap-1.5">
          <MessageSquareWarning className="w-3.5 h-3.5" /> Reclamações e sugestões
        </div>
        <h1 className="titulo-tela" data-testid="sugestoes-title">
          Fale direto com quem faz o Sapiens.
        </h1>
        <p className="mt-3 text-white/60 max-w-xl">
          Uma pessoa lê cada mensagem daqui. Não custa Sparks, não é robô, e você acompanha
          nesta mesma tela quando a equipe responder.
        </p>

        <form onSubmit={enviar} className="mt-8 card-sapiens rounded-2xl p-6 md:p-7" data-testid="sugestoes-form">
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-3">
            Do que se trata
          </div>
          <div className="flex flex-wrap gap-2">
            {TIPOS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTipo(t.id)}
                className={`pill inline-flex items-center gap-1.5 rounded-full border px-4 py-2 text-xs font-medium transition ${
                  tipo === t.id
                    ? "border-sapiens-accent bg-sapiens-accentSoft text-sapiens-navy"
                    : "border-zinc-200 text-zinc-500 hover:border-zinc-300"
                }`}
                data-testid={`sugestoes-tipo-${t.id}`}
              >
                <t.icone className="w-3.5 h-3.5" /> {t.rotulo}
              </button>
            ))}
          </div>

          <label className="mt-5 block">
            <div className="text-sm text-zinc-600 mb-2">{tipoAtual.convite}</div>
            <textarea
              value={mensagem}
              onChange={(e) => setMensagem(e.target.value.slice(0, MAX_CHARS))}
              rows={6}
              placeholder="Escreva aqui..."
              className="w-full resize-none rounded-xl px-4 py-3 text-sm leading-relaxed outline-none"
              data-testid="sugestoes-texto"
            />
          </label>

          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <span className="font-mono-alt text-[10px] text-zinc-400">{mensagem.length}/{MAX_CHARS}</span>
            <button
              type="submit"
              disabled={curta || enviando}
              className="pill btn-sapiens inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-medium disabled:opacity-40"
              data-testid="sugestoes-enviar"
            >
              {enviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Enviar para a equipe
            </button>
          </div>
        </form>

        <div className="mt-10">
          <h2 className="font-display text-2xl font-bold tracking-tight text-white">O que você já mandou</h2>
          {carregando ? (
            <div className="mt-4 flex items-center gap-2 text-sm text-white/60">
              <Loader2 className="w-4 h-4 animate-spin" /> Carregando...
            </div>
          ) : minhas.length === 0 ? (
            <p className="mt-3 text-sm text-white/50" data-testid="sugestoes-vazio">
              Nada ainda. Quando você mandar algo, ele aparece aqui com o estado de cada mensagem.
            </p>
          ) : (
            <div className="mt-4 space-y-3">
              {minhas.map((s) => {
                const t = TIPOS.find((x) => x.id === s.tipo);
                return (
                  <div key={s.sugestao_id} className="card-sapiens rounded-2xl p-5" data-testid={`sugestoes-item-${s.sugestao_id}`}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2 text-xs text-zinc-500">
                        {t && <t.icone className="w-3.5 h-3.5" />}
                        <span className="font-medium text-zinc-700">{t?.rotulo || s.tipo}</span>
                        <span className="text-zinc-400">· {formatarData(s.created_at)}</span>
                      </div>
                      <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${STATUS_CLS[s.status] || STATUS_CLS.nova}`}>
                        {s.status === "respondida" && <CheckCircle2 className="w-3 h-3" />}
                        {STATUS_LABEL[s.status] || s.status}
                      </span>
                    </div>
                    <p className="mt-2.5 whitespace-pre-line text-sm leading-relaxed text-zinc-700">{s.mensagem}</p>
                    {s.resposta && (
                      <div className="mt-4 flex gap-3 rounded-xl border border-zinc-200 bg-white/70 p-4">
                        <Mentis className="w-6 h-6 shrink-0" variante="icone" animada={false} />
                        <div className="min-w-0">
                          <div className="text-[11px] font-bold uppercase tracking-wide text-sapiens-accentDeep">
                            Resposta da equipe
                          </div>
                          <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-zinc-700">{s.resposta}</p>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
