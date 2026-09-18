import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../lib/auth";
import { avisarSparksMudou } from "./Nav";
import { criarPortao } from "../lib/idempotencia";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";
import { CheckCircle2, Loader2, Users, AlertCircle, Zap, Clock } from "lucide-react";

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
 *
 * **ENTRAR CUSTA SPARKS desde 2026-09-17** (`mentoria_routes.ENTRADA_COST`).
 * Três consequências para esta tela, e as três são de honestidade:
 *
 * 1. **O preço aparece antes do clique**, no botão e na confirmação — nunca
 *    num toast depois do débito.
 * 2. **Os dados são conferidos ANTES de cobrar.** Nome, e-mail e WhatsApp são
 *    o que chega ao admin, e uma fila sem eles é uma linha que ninguém
 *    consegue atender. O que falta é pedido num aviso contextual dentro do
 *    próprio formulário — não num modal por cima dele: a pessoa já está
 *    olhando os campos, e empilhar uma janela sobre um formulário para pedir
 *    um campo do formulário é atrito por nada.
 * 3. **Corrigir o pedido continua de graça**, e a tela diz isso: quem já está
 *    na fila vê "Atualizar meu pedido", sem preço nenhum ao lado.
 */

// Espelha `mentoria_routes.ENTRADA_COST`. É só o valor exibido enquanto
// `GET /mentoria/me` não responde — quem cobra é o servidor.
const CUSTO_ENTRADA_PADRAO = 50;

export default function ListaDeEsperaMentoria({ aoEntrar, testid = "mentoria-fila" }) {
  const { user } = useAuth();
  const [carregando, setCarregando] = useState(true);
  const [naFila, setNaFila] = useState(null);
  const [nomeCompleto, setNomeCompleto] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [areas, setAreas] = useState([]);
  const [descricao, setDescricao] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [custo, setCusto] = useState(CUSTO_ENTRADA_PADRAO);
  const [conta, setConta] = useState(null);
  const [confirmando, setConfirmando] = useState(false);
  const enviandoRef = useRef(criarPortao("fila"));

  useEffect(() => {
    let vivo = true;
    api
      .get("/mentoria/me")
      .then(({ data }) => {
        if (!vivo) return;
        if (typeof data.custo_entrada === "number") setCusto(data.custo_entrada);
        setConta(data.conta || null);
        if (data.na_fila) {
          setNaFila(data);
          setNomeCompleto(data.nome_completo || "");
          setWhatsapp(data.whatsapp || "");
          setAreas(data.areas || []);
          setDescricao(data.descricao || "");
        } else {
          setNomeCompleto(data.conta?.nome || user?.name || "");
          setWhatsapp(data.conta?.whatsapp || user?.whatsapp || "");
        }
      })
      .catch(() => {})
      .finally(() => vivo && setCarregando(false));
    return () => { vivo = false; };
  }, [user]);

  const alternarArea = (area) =>
    setAreas((p) => (p.includes(area) ? p.filter((a) => a !== area) : [...p, area]));

  // O que ainda falta para o pedido chegar ao admin em condições de ser
  // atendido. É calculado a cada render e usado em dois lugares: o aviso
  // contextual e o portão que impede a cobrança.
  const email = conta?.email || user?.email || "";
  const faltando = [
    !nomeCompleto.trim() && "seu nome completo",
    !email && "o e-mail da sua conta",
    !whatsapp.trim() && "seu WhatsApp",
  ].filter(Boolean);
  const semArea = areas.length === 0;

  const pedirEntrada = (e) => {
    e.preventDefault();
    if (faltando.length || semArea) {
      // Nada de toast: o aviso já está impresso ACIMA do botão, no mesmo
      // formulário. Um toast que some em três segundos para pedir um campo
      // que está na tela é a pior forma possível de dizer isto.
      return;
    }
    // Quem já está na fila está CORRIGINDO, e corrigir é de graça: não há o
    // que confirmar.
    if (naFila) { enviar(); return; }
    setConfirmando(true);
  };

  const enviar = async () => {
    // A trava do toque duplo. Aqui ela não protege o dinheiro — o servidor já
    // garante "um aluno, um lugar" pelo `user_id`, com índice único — mas
    // protege a TELA: sem ela, dois toques disparam duas requisições, a
    // segunda esbarra no registro que a primeira acabou de criar e o aluno vê
    // uma mensagem de erro logo depois de ter entrado na fila com sucesso.
    if (!enviandoRef.current.entrar()) return;
    setConfirmando(false);
    setEnviando(true);
    try {
      const { data } = await api.post("/mentoria", {
        nome_completo: nomeCompleto.trim(),
        whatsapp: whatsapp.trim(),
        areas,
        descricao: descricao.trim(),
      });
      setNaFila(data);
      if (data.cobrado) avisarSparksMudou();
      toast.success(
        data.ja_estava_na_fila
          ? "Pedido atualizado. Seu lugar na fila continua o mesmo."
          : `Você está na lista · ${data.cobrado} Sparks`,
      );
      aoEntrar?.(data);
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível entrar na lista."));
    } finally {
      enviandoRef.current.sair();
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

      <form onSubmit={pedirEntrada} className="space-y-4">
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

        {/* O AVISO CONTEXTUAL. Fica colado no botão, dentro do formulário e
            acima dele: quem lê descobre o que falta sem sair de onde já está
            olhando, e o pedido não chega ao admin sem contato. Some sozinho
            quando os campos são preenchidos. */}
        {(faltando.length > 0 || semArea) && (
          <div
            className="flex items-start gap-2.5 rounded-2xl border border-amber-400/30 bg-amber-400/[0.08] p-3.5 text-xs leading-relaxed text-amber-100"
            data-testid={`${testid}-faltando`}
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
            <span>
              {faltando.length > 0 && (
                <>
                  Antes de continuar, precisamos de <strong>{faltando.join(", ")}</strong> — é
                  por aí que a equipe fala com você.{" "}
                </>
              )}
              {semArea && <>Escolha ao menos uma área acima.</>}
              {!email && (
                <>
                  {" "}O e-mail vem da sua conta; se ele não aparece, fale com a equipe em
                  Reclamações e sugestões.
                </>
              )}
            </span>
          </div>
        )}

        <button
          type="submit"
          disabled={enviando || faltando.length > 0 || semArea}
          className="pill btn-calor inline-flex w-full items-center justify-center gap-2 rounded-full px-6 py-4 text-sm disabled:opacity-50"
          data-testid={`${testid}-enviar`}
        >
          {enviando ? (
            <><Loader2 className="h-4 w-4 animate-spin" /> Enviando…</>
          ) : naFila ? (
            <><Users className="h-4 w-4" /> Atualizar meu pedido</>
          ) : (
            <><Zap className="h-4 w-4" /> Entrar na lista · {custo} Sparks</>
          )}
        </button>
        <p className="flex flex-wrap items-center justify-center gap-x-1.5 gap-y-1 text-center text-[11px] leading-relaxed text-white/35">
          <Clock className="h-3 w-3" />
          <strong className="font-semibold text-white/60">
            Geralmente respondemos em até 2 dias úteis.
          </strong>
          {naFila
            ? "Corrigir seus dados é de graça e não muda o seu lugar na fila."
            : "Uma pessoa, poucas vagas — a ordem de chegada é a ordem da conversa."}
        </p>
      </form>

      {/* A cobrança, dita antes de acontecer — mesma regra da redação e do
          cronograma. Só aparece na ENTRADA: corrigir não custa nada. */}
      <Dialog open={confirmando} onOpenChange={(v) => !v && setConfirmando(false)}>
        <DialogContent className="rounded-2xl" data-testid={`${testid}-confirmar`}>
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight">
              Entrar na lista de espera?
            </DialogTitle>
          </DialogHeader>
          <p className="text-sm leading-relaxed text-zinc-600">
            Isto custa <strong>{custo} Sparks</strong>, uma única vez. Depois disso você fica na
            fila e pode corrigir seus dados quantas vezes quiser, de graça.
          </p>
          <div className="rounded-xl border border-zinc-200 p-3 text-sm text-zinc-700">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
              O que a equipe recebe
            </div>
            <div className="mt-1.5 space-y-0.5">
              <div>{nomeCompleto.trim()}</div>
              <div className="text-zinc-500">{email}</div>
              <div className="text-zinc-500">{whatsapp.trim()}</div>
            </div>
          </div>
          <p className="text-xs text-zinc-500">Geralmente respondemos em até 2 dias úteis.</p>
          <DialogFooter>
            <button
              onClick={() => setConfirmando(false)}
              className="pill inline-flex items-center justify-center rounded-full border border-zinc-200 px-5 py-2.5 text-sm font-medium text-zinc-700 hover:border-zinc-300"
              data-testid={`${testid}-cancelar`}
            >
              Cancelar
            </button>
            <button
              onClick={enviar}
              className="pill btn-sapiens inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium"
              data-testid={`${testid}-confirmar-btn`}
            >
              <Zap className="h-4 w-4" /> Entrar por {custo} Sparks
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
