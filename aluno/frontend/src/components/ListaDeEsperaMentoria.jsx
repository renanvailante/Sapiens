import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../lib/auth";
import { CheckCircle2, Loader2, Users } from "lucide-react";

export const MENTORIA_AREAS = [
  "Matemática",
  "Ciências da Natureza",
  "Linguagens",
  "Ciências Humanas",
  "Redação",
];

/**
 * O formulário da LISTA DE ESPERA da mentoria.
 *
 * Substituiu o modal de "aula particular" em 2026-09-15. A diferença não é de
 * rótulo — é de promessa, e a tela precisa fazer a promessa certa:
 *
 * * **não agenda nada.** Não existe horário para escolher, porque a mentoria
 *   é com UMA pessoa e a vaga abre quando abre;
 * * **devolve a POSIÇÃO na fila.** "Recebemos seu pedido" não diz nada; "você
 *   é o 14º" é uma informação verdadeira e é a única coisa que a pessoa
 *   realmente quer saber depois de enviar;
 * * **quem já está na fila não vê o formulário em branco.** Ele volta
 *   preenchido, e reenviar CORRIGE o pedido em vez de criar um segundo (ver
 *   `backend/mentoria_routes.py`).
 *
 * O WhatsApp da conta entra como valor inicial: o aluno já deu esse número no
 * cadastro e pedi-lo de novo é atrito puro.
 */
export default function ListaDeEsperaMentoria({ aoEntrar, testid = "mentoria-fila" }) {
  const { user } = useAuth();
  const [carregando, setCarregando] = useState(true);
  const [naFila, setNaFila] = useState(null);
  const [nomeCompleto, setNomeCompleto] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [areas, setAreas] = useState([]);
  const [descricao, setDescricao] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    let vivo = true;
    api
      .get("/mentoria/me")
      .then(({ data }) => {
        if (!vivo) return;
        if (data.na_fila) {
          setNaFila(data);
          setNomeCompleto(data.nome_completo || "");
          setWhatsapp(data.whatsapp || "");
          setAreas(data.areas || []);
          setDescricao(data.descricao || "");
        } else {
          setNomeCompleto(user?.name || "");
          setWhatsapp(user?.whatsapp || "");
        }
      })
      .catch(() => {})
      .finally(() => vivo && setCarregando(false));
    return () => { vivo = false; };
  }, [user]);

  const alternarArea = (area) =>
    setAreas((p) => (p.includes(area) ? p.filter((a) => a !== area) : [...p, area]));

  const enviar = async (e) => {
    e.preventDefault();
    if (!nomeCompleto.trim() || !whatsapp.trim() || areas.length === 0) {
      toast.error("Preencha nome, WhatsApp e ao menos uma área.");
      return;
    }
    setEnviando(true);
    try {
      const { data } = await api.post("/mentoria", {
        nome_completo: nomeCompleto.trim(),
        whatsapp: whatsapp.trim(),
        areas,
        descricao: descricao.trim(),
      });
      setNaFila(data);
      toast.success(
        data.ja_estava_na_fila ? "Pedido atualizado. Seu lugar na fila continua o mesmo."
                               : "Você está na lista.",
      );
      aoEntrar?.(data);
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível entrar na lista."));
    } finally {
      setEnviando(false);
    }
  };

  if (carregando) {
    return (
      <div className="flex items-center justify-center gap-2 py-10 text-sm text-white/45" data-testid={`${testid}-carregando`}>
        <Loader2 className="h-4 w-4 animate-spin" /> Consultando a fila…
      </div>
    );
  }

  return (
    <div data-testid={testid}>
      {naFila && (
        <div
          className="mb-5 flex flex-wrap items-center gap-4 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-5"
          data-testid={`${testid}-confirmado`}
        >
          <CheckCircle2 className="h-6 w-6 shrink-0 text-emerald-300" />
          <div className="min-w-0 flex-1">
            <div className="font-display text-lg font-bold tracking-tight text-emerald-200">
              Você está na lista de espera.
            </div>
            <div className="text-sm text-emerald-100/70">
              Falamos com você pelo WhatsApp assim que abrir vaga. Pode corrigir seus dados
              abaixo — seu lugar na fila não muda.
            </div>
          </div>
          {naFila.posicao != null && (
            <div className="shrink-0 text-center">
              <div className="font-display text-3xl font-extrabold leading-none tracking-tighter text-white">
                {naFila.posicao}º
              </div>
              <div className="font-mono-alt text-[9px] uppercase tracking-[0.2em] text-emerald-200/60">
                na fila
              </div>
            </div>
          )}
        </div>
      )}

      <form onSubmit={enviar} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-white/50" htmlFor={`${testid}-nome`}>
            Nome completo
          </label>
          <input
            id={`${testid}-nome`}
            required
            value={nomeCompleto}
            onChange={(e) => setNomeCompleto(e.target.value)}
            placeholder="Seu nome completo"
            className="w-full rounded-xl border border-white/12 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none placeholder:text-white/25 focus:border-[#4FD9FF]/60"
            data-testid={`${testid}-nome`}
          />
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-white/50" htmlFor={`${testid}-whatsapp`}>
            WhatsApp
          </label>
          <input
            id={`${testid}-whatsapp`}
            required
            type="tel"
            inputMode="tel"
            value={whatsapp}
            onChange={(e) => setWhatsapp(e.target.value)}
            placeholder="(11) 91234-5678"
            className="w-full rounded-xl border border-white/12 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none placeholder:text-white/25 focus:border-[#4FD9FF]/60"
            data-testid={`${testid}-whatsapp`}
          />
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-white/50">
            Onde você mais precisa de ajuda?
          </label>
          <div className="flex flex-wrap gap-2">
            {MENTORIA_AREAS.map((area) => {
              const ativa = areas.includes(area);
              return (
                <button
                  type="button"
                  key={area}
                  onClick={() => alternarArea(area)}
                  aria-pressed={ativa}
                  className={`pill rounded-full border px-3.5 py-2 text-xs font-medium transition-colors ${
                    ativa
                      ? "border-[#4FD9FF]/60 bg-[#4FD9FF]/15 text-[#BFE7FF]"
                      : "border-white/12 text-white/50 hover:border-white/30 hover:text-white"
                  }`}
                  data-testid={`${testid}-area-${area}`}
                >
                  {area}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-white/50" htmlFor={`${testid}-descricao`}>
            O que você quer destravar com a mentoria?
          </label>
          <textarea
            id={`${testid}-descricao`}
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            rows={4}
            placeholder="Ex.: estudo todo dia e a nota não sai do lugar. Quero saber o que estou fazendo errado na rotina."
            className="w-full resize-none rounded-xl border border-white/12 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none placeholder:text-white/25 focus:border-[#4FD9FF]/60"
            data-testid={`${testid}-descricao`}
          />
        </div>

        <button
          type="submit"
          disabled={enviando}
          className="pill btn-calor inline-flex w-full items-center justify-center gap-2 rounded-full px-6 py-4 text-sm disabled:opacity-50"
          data-testid={`${testid}-enviar`}
        >
          <Users className="h-4 w-4" />
          {enviando ? "Enviando…" : naFila ? "Atualizar meu pedido" : "Entrar na lista de espera"}
        </button>
        <p className="text-center text-[11px] leading-relaxed text-white/35">
          Entrar na lista é de graça e não compromete você a nada. Uma pessoa, poucas vagas —
          a ordem de chegada é a ordem da conversa.
        </p>
      </form>
    </div>
  );
}
