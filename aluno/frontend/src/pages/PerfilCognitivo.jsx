import { useEffect, useState } from "react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { Brain, ThumbsUp, Target, Loader2 } from "lucide-react";

// Substitui Motor Cognitivo + Diagnóstico real + Mapa de Habilidades por uma
// única leitura, servida por `GET /perfil` (`perfil_pedagogico.py`). Essa
// rota é a única fronteira permitida: nunca devolve nome, ID ou percentual
// da ontologia interna (domínio/competência/processo/habilidade/tipo de
// erro/intervenção) — só rótulo pedagógico + explicação. Esta tela consome
// só esse formato; não busca nem deriva nada da ontologia por conta própria.

function Cartao({ item, tom }) {
  const cls = tom === "forte"
    ? "border-emerald-200 bg-emerald-50"
    : "border-amber-200 bg-amber-50";
  const tituloCls = tom === "forte" ? "text-emerald-900" : "text-amber-900";
  return (
    <div className={`rounded-2xl border p-5 ${cls}`} data-testid={`perfil-cartao-${tom}`}>
      <div className={`font-display font-bold ${tituloCls}`}>{item.rotulo}</div>
      <p className="mt-1.5 text-sm text-zinc-700 leading-relaxed">{item.explicacao}</p>
    </div>
  );
}

export default function PerfilCognitivo() {
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);

  const carregar = () => {
    setLoading(true);
    setErro(null);
    api
      .get("/perfil")
      .then(({ data }) => setDados(data))
      .catch((e) => setErro(errMsg(e, "Não foi possível carregar seu perfil agora.")))
      .finally(() => setLoading(false));
  };

  useEffect(carregar, []);

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-3 flex items-center gap-2">
          <Brain className="w-3.5 h-3.5" /> Seu perfil cognitivo
        </div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white" data-testid="perfil-title">
          O que você já manda bem — e no que focar.
        </h1>
        <p className="mt-3 text-white/60 max-w-xl">
          Um retrato direto, sem números nem categorias técnicas: só o que importa para você estudar melhor.
        </p>

        {loading ? (
          <div className="mt-10 flex items-center gap-2 text-sm text-white/60">
            <Loader2 className="w-4 h-4 animate-spin" /> Carregando seu perfil...
          </div>
        ) : erro ? (
          <div className="mt-6 card-sapiens rounded-2xl p-6 text-center">
            <div className="text-zinc-600">{erro}</div>
            <button onClick={carregar} className="pill mt-4 text-sm font-medium btn-sapiens px-4 py-2 rounded-full">
              Tentar de novo
            </button>
          </div>
        ) : dados?.amostra_insuficiente ? (
          <div className="mt-6 card-sapiens rounded-2xl p-6 text-center" data-testid="perfil-vazio">
            <div className="font-display font-bold text-lg text-zinc-950">Ainda não dá para traçar seu perfil.</div>
            <p className="mt-2 text-sm text-zinc-500 max-w-md mx-auto">
              Responda mais questões para o Sapiens conseguir apontar seus pontos fortes e o que vale mais a pena
              desenvolver.
            </p>
          </div>
        ) : (
          <div className="mt-8 grid md:grid-cols-2 gap-8">
            <div>
              <h2 className="flex items-center gap-2 font-display font-bold text-2xl text-white tracking-tight">
                <ThumbsUp className="w-5 h-5 text-emerald-400" /> Pontos fortes
              </h2>
              <div className="mt-4 space-y-3">
                {dados.pontos_fortes.map((item, i) => (
                  <Cartao key={i} item={item} tom="forte" />
                ))}
              </div>
            </div>
            <div>
              <h2 className="flex items-center gap-2 font-display font-bold text-2xl text-white tracking-tight">
                <Target className="w-5 h-5 text-amber-400" /> A desenvolver
              </h2>
              <div className="mt-4 space-y-3">
                {dados.pontos_a_desenvolver.map((item, i) => (
                  <Cartao key={i} item={item} tom="fraco" />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
