import { useCallback, useEffect, useRef, useState } from "react";
import Nav from "../components/Nav";
import { api, errMsg } from "../lib/api";
import { toast } from "sonner";
import { Zap, Check, Loader2, History, ShoppingBag, Network, RefreshCw, XCircle, AlertTriangle, Infinity as InfinityIcon, Copy, QrCode, ExternalLink } from "lucide-react";

const MP_SDK_URL = "https://sdk.mercadopago.com/js/v2";

// Carrega o SDK oficial do Mercado Pago uma única vez (mesmo padrão de outros
// scripts de terceiro carregados sob demanda) — o Brick de pagamento roda
// isolado (iframe do próprio MP): nenhum dado de cartão passa pelo nosso
// código ou pelo nosso backend em texto puro, só o token que o MP gera.
let _mpSdkPromise = null;
function loadMercadoPagoSdk() {
  if (window.MercadoPago) return Promise.resolve(window.MercadoPago);
  if (_mpSdkPromise) return _mpSdkPromise;
  _mpSdkPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = MP_SDK_URL;
    script.async = true;
    script.onload = () => resolve(window.MercadoPago);
    script.onerror = () => reject(new Error("Não foi possível carregar o Mercado Pago."));
    document.head.appendChild(script);
  });
  return _mpSdkPromise;
}

function formatBRL(cents) {
  return (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// Painel de pagamento — monta o Payment Brick do Mercado Pago dentro de
// `containerId`. O aluno digita os dados do cartão DENTRO do widget oficial
// do MP (não num campo nosso); `onSubmit` só recebe de volta um token opaco.
function PaymentBrick({ publicKey, pkg, onSuccess, onCancel }) {
  const containerId = useRef(`mp-brick-${pkg.package_id}`).current;
  const brickRef = useRef(null);
  const [status, setStatus] = useState("loading"); // 'loading' | 'ready' | 'submitting' | 'error' | 'pix'
  const [error, setError] = useState(null);
  const [pix, setPix] = useState(null); // { qr_code, qr_code_base64, ticket_url } quando o método é Pix
  const campoPixRef = useRef(null);

  useEffect(() => {
    let cancelado = false;
    setStatus("loading");
    setError(null);

    // O Brick do Mercado Pago às vezes falha por dentro (chave pública
    // inválida, bloqueador de anúncios, instabilidade da rede) sem NUNCA
    // chamar `onReady` nem `onError` — sem este teto, a tela ficava presa em
    // "Carregando pagamento..." para sempre, sem nenhum jeito de tentar de
    // novo. 12s é folga de sobra: o Brick normalmente fica pronto em <2s.
    const tempoLimite = setTimeout(() => {
      if (cancelado) return;
      setStatus("error");
      setError("O formulário de pagamento demorou demais para carregar. Verifique sua conexão (ou um bloqueador de anúncios) e tente de novo.");
    }, 12000);

    loadMercadoPagoSdk()
      .then((MercadoPago) => {
        if (cancelado) return;
        const mp = new MercadoPago(publicKey, { locale: "pt-BR" });
        return mp.bricks().create("payment", containerId, {
          initialization: { amount: pkg.price_cents / 100 },
          customization: {
            // Pix entra na categoria "bankTransfer" na taxonomia do Brick —
            // não existe uma chave dedicada "pix". Cartão continua
            // exatamente como estava, só acrescentei a categoria nova.
            paymentMethods: { creditCard: "all", debitCard: "all", bankTransfer: "all" },
          },
          callbacks: {
            onReady: () => { if (!cancelado) { clearTimeout(tempoLimite); setStatus("ready"); } },
            onError: (err) => {
              if (cancelado) return;
              clearTimeout(tempoLimite);
              console.error("Mercado Pago Brick onError:", err);
              setStatus("error");
              setError(err?.message || "O Mercado Pago não conseguiu carregar o pagamento.");
            },
            onSubmit: ({ formData }) => {
              setStatus("submitting");
              return api
                .post("/sparks/purchases", {
                  package_id: pkg.package_id,
                  token: formData.token,
                  payment_method_id: formData.payment_method_id,
                  installments: formData.installments,
                  issuer_id: formData.issuer_id,
                  payer: formData.payer,
                })
                .then(({ data }) => {
                  // Pix não aprova na hora: fica "pending" até o aluno pagar.
                  // O QR Code/copia-e-cola vêm nesta MESMA resposta — nada de
                  // segunda chamada — e ficam na tela enquanto o pagamento é
                  // aguardado em segundo plano (`acompanharPagamento`, no
                  // componente pai, credita os Sparks quando o webhook confirmar).
                  if (data.pix?.qr_code) {
                    setPix(data.pix);
                    setStatus("pix");
                  }
                  onSuccess(data);
                })
                .catch((e) => {
                  setStatus("ready");
                  setError(errMsg(e, "O Mercado Pago recusou o pagamento."));
                });
            },
          },
        });
      })
      .then((brick) => { if (!cancelado) brickRef.current = brick; })
      .catch((e) => {
        if (cancelado) return;
        clearTimeout(tempoLimite);
        console.error("Mercado Pago Brick falhou ao inicializar:", e);
        setStatus("error");
        setError(e.message || "Não foi possível carregar o Mercado Pago.");
      });
    return () => {
      cancelado = true;
      clearTimeout(tempoLimite);
      brickRef.current?.unmount?.();
    };
  }, [publicKey, pkg, containerId, onSuccess]);


  return (
    <div className="card-sapiens rounded-2xl p-6" data-testid="sparks-payment-brick">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">Pagamento seguro · Mercado Pago</div>
          <div className="font-display font-bold text-lg text-zinc-950">{pkg.label} · {formatBRL(pkg.price_cents)}</div>
        </div>
        <button onClick={onCancel} className="text-xs text-zinc-400 hover:text-zinc-700">Cancelar</button>
      </div>
      {status === "loading" && (
        <div className="flex items-center gap-2 text-sm text-zinc-500 py-8 justify-center">
          <Loader2 className="w-4 h-4 animate-spin" /> Carregando pagamento...
        </div>
      )}
      {error && (
        <div className="mb-3" data-testid="sparks-payment-error">
          <div className="text-sm text-rose-600">{error}</div>
          {status === "error" && (
            <button
              onClick={onCancel}
              className="pill mt-2 px-4 py-2 rounded-full text-xs font-medium border border-zinc-200 text-zinc-600 hover:border-zinc-400"
              data-testid="sparks-payment-tentar-de-novo"
            >
              Fechar e tentar de novo
            </button>
          )}
        </div>
      )}
      <div id={containerId} className={status === "pix" ? "hidden" : ""} />
      {status === "submitting" && (
        <div className="flex items-center gap-2 text-sm text-zinc-500 mt-3 justify-center">
          <Loader2 className="w-4 h-4 animate-spin" /> Confirmando com o Mercado Pago...
        </div>
      )}
      {status === "pix" && pix && (
        <div className="text-center" data-testid="sparks-pix-panel">
          <div className="flex items-center justify-center gap-2 text-sm font-semibold text-zinc-800 mb-3">
            <QrCode className="w-4 h-4" /> Escaneie o QR Code ou copie o código Pix
          </div>
          {pix.qr_code_base64 && (
            <img
              src={`data:image/png;base64,${pix.qr_code_base64}`}
              alt="QR Code Pix"
              className="mx-auto w-48 h-48 rounded-xl border border-zinc-200"
              data-testid="sparks-pix-qr-image"
            />
          )}
          {/* No celular o QR Code não serve: ninguém escaneia a própria tela.
              O `ticket_url` já vinha na resposta do Mercado Pago e não era
              usado por tela nenhuma — é ele que abre o pagamento no app do
              banco ou do MP, que é o caminho real de quem está no telefone. */}
          {pix.ticket_url && (
            <a
              href={pix.ticket_url}
              target="_blank"
              rel="noopener noreferrer"
              className="pill btn-sapiens mt-4 inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full text-xs font-medium"
              data-testid="sparks-pix-abrir-app"
            >
              <ExternalLink className="w-3.5 h-3.5" /> Pagar no app do banco
            </a>
          )}
          {pix.qr_code && (
            <div className="mt-4">
              <textarea
                ref={campoPixRef}
                readOnly
                value={pix.qr_code}
                rows={3}
                onClick={(e) => e.target.select()}
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-xs text-zinc-600 font-mono-alt resize-none"
                data-testid="sparks-pix-copia-cola"
              />
              {/* `writeText` devolve uma promessa e REJEITA onde a área de
                  transferência é bloqueada — navegador embutido do WhatsApp e
                  do Instagram, que é por onde boa parte dos alunos abre o
                  link. Sem o `catch`, o toast dizia "copiado" de qualquer
                  jeito e a pessoa voltava para o banco com a área de
                  transferência vazia, sem entender por quê. */}
              <button
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(pix.qr_code);
                    toast.success("Código Pix copiado.");
                  } catch {
                    campoPixRef.current?.select();
                    toast.error("Seu navegador não deixou copiar. O código está selecionado acima — segure e escolha Copiar.");
                  }
                }}
                className="pill btn-sapiens mt-2 inline-flex items-center justify-center gap-2 px-4 py-2 rounded-full text-xs font-medium"
                data-testid="sparks-pix-copiar"
              >
                <Copy className="w-3.5 h-3.5" /> Copiar código
              </button>
            </div>
          )}
          <p className="mt-4 text-xs text-zinc-500">
            Os Sparks entram automaticamente assim que o Mercado Pago confirmar o pagamento — pode fechar esta tela
            quando quiser, isso não cancela o Pix.
          </p>
        </div>
      )}
    </div>
  );
}

// Painel de ativação da recarga automática — mesmo Brick oficial do MP, mas
// o "cardPayment" (só cartão, sem Pix/boleto): a assinatura do Mercado Pago
// só aceita cartão. `onSubmit` gera um token e ativa a assinatura — nenhum
// pagamento é criado aqui na hora, quem cobra depois é o próprio Mercado
// Pago, no calendário escolhido.
function AutoRechargeBrick({ publicKey, pkg, frequencyDays, baseline, onSuccess, onCancel }) {
  const containerId = useRef(`mp-recharge-brick-${pkg.package_id}`).current;
  const brickRef = useRef(null);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelado = false;
    setStatus("loading");
    setError(null);

    // Mesmo teto de `PaymentBrick`: o Brick às vezes nunca chama `onReady`
    // nem `onError` (chave inválida, bloqueador de anúncios, rede) e a tela
    // ficava presa em "Carregando..." para sempre.
    const tempoLimite = setTimeout(() => {
      if (cancelado) return;
      setStatus("error");
      setError("O formulário demorou demais para carregar. Verifique sua conexão (ou um bloqueador de anúncios) e tente de novo.");
    }, 12000);

    loadMercadoPagoSdk()
      .then((MercadoPago) => {
        if (cancelado) return;
        const mp = new MercadoPago(publicKey, { locale: "pt-BR" });
        return mp.bricks().create("cardPayment", containerId, {
          initialization: { amount: pkg.price_cents / 100 },
          callbacks: {
            onReady: () => { if (!cancelado) { clearTimeout(tempoLimite); setStatus("ready"); } },
            onError: (err) => {
              if (cancelado) return;
              clearTimeout(tempoLimite);
              console.error("Mercado Pago Brick (recarga) onError:", err);
              setStatus("error");
              setError(err?.message || "O Mercado Pago não conseguiu carregar o formulário.");
            },
            onSubmit: (formData) => {
              setStatus("submitting");
              return api
                .post("/sparks/auto-recharge", {
                  package_id: pkg.package_id,
                  frequency_days: frequencyDays,
                  baseline,
                  card_token_id: formData.token,
                })
                .then(({ data }) => onSuccess(data))
                .catch((e) => {
                  setStatus("ready");
                  setError(errMsg(e, "O Mercado Pago recusou o cartão."));
                });
            },
          },
        });
      })
      .then((brick) => { if (!cancelado) brickRef.current = brick; })
      .catch((e) => {
        if (cancelado) return;
        clearTimeout(tempoLimite);
        console.error("Mercado Pago Brick (recarga) falhou ao inicializar:", e);
        setStatus("error");
        setError(e.message || "Não foi possível carregar o Mercado Pago.");
      });
    return () => {
      cancelado = true;
      clearTimeout(tempoLimite);
      brickRef.current?.unmount?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [publicKey, pkg, frequencyDays, baseline, containerId, onSuccess]);

  return (
    <div className="card-sapiens rounded-2xl p-6" data-testid="sparks-auto-recharge-brick">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">Cartão para a recarga automática</div>
          <div className="font-display font-bold text-lg text-zinc-950">
            {pkg.label} · a cada {frequencyDays} dias
          </div>
        </div>
        <button onClick={onCancel} className="text-xs text-zinc-400 hover:text-zinc-700">Cancelar</button>
      </div>
      {status === "loading" && (
        <div className="flex items-center gap-2 text-sm text-zinc-500 py-8 justify-center">
          <Loader2 className="w-4 h-4 animate-spin" /> Carregando formulário...
        </div>
      )}
      {error && (
        <div className="mb-3" data-testid="sparks-auto-recharge-error">
          <div className="text-sm text-rose-600">{error}</div>
          {status === "error" && (
            <button
              onClick={onCancel}
              className="pill mt-2 px-4 py-2 rounded-full text-xs font-medium border border-zinc-200 text-zinc-600 hover:border-zinc-400"
              data-testid="sparks-auto-recharge-tentar-de-novo"
            >
              Fechar e tentar de novo
            </button>
          )}
        </div>
      )}
      <div id={containerId} />
      {status === "submitting" && (
        <div className="flex items-center gap-2 text-sm text-zinc-500 mt-3 justify-center">
          <Loader2 className="w-4 h-4 animate-spin" /> Ativando recarga automática...
        </div>
      )}
    </div>
  );
}

export default function SparksStore() {
  const [sparks, setSparks] = useState(null);
  const [packages, setPackages] = useState([]);
  const [publicKey, setPublicKey] = useState(null);
  const [mpDisponivel, setMpDisponivel] = useState(true);
  const [purchases, setPurchases] = useState([]);
  const [rounds, setRounds] = useState([]);
  const [mapCost, setMapCost] = useState(null);
  const [selectedPkg, setSelectedPkg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [aguardandoPagamento, setAguardandoPagamento] = useState(false);

  const [frequencies, setFrequencies] = useState([]);
  const [defaultBaseline, setDefaultBaseline] = useState(50);
  const [autoRecharge, setAutoRecharge] = useState(null);
  const [showActivate, setShowActivate] = useState(false);
  const [activatePkg, setActivatePkg] = useState(null);
  const [activateFreq, setActivateFreq] = useState(null);
  const [activateBaseline, setActivateBaseline] = useState(50);

  const carregar = () => {
    Promise.all([
      api.get("/firestore/students/me/sparks").then(({ data }) => data.sparks_balance).catch(() => null),
      api.get("/sparks/packages").then(({ data }) => data).catch(() => ({ packages: [], auto_recharge_frequencies_days: [], default_baseline: 50 })),
      api.get("/sparks/config").then(({ data }) => data.public_key).catch(() => { setMpDisponivel(false); return null; }),
      api.get("/sparks/purchases/me").then(({ data }) => data.items || []).catch(() => []),
      api.get("/firestore/students/me/rounds").then(({ data }) => data.rounds || []).catch(() => []),
      api.get("/skills-map").then(({ data }) => data.cost).catch(() => null),
      api.get("/sparks/auto-recharge/me").then(({ data }) => (data?.active ? data : null)).catch(() => null),
    ]).then(([s, catalogo, pk, purch, rds, cost, recarga]) => {
      setSparks(s);
      setPackages(catalogo.packages || []);
      setFrequencies(catalogo.auto_recharge_frequencies_days || []);
      setDefaultBaseline(catalogo.default_baseline ?? 50);
      setActivateBaseline(catalogo.default_baseline ?? 50);
      setPublicKey(pk);
      setPurchases(purch);
      setRounds(rds);
      setMapCost(cost);
      setAutoRecharge(recarga);
      setLoading(false);
    });
  };
  useEffect(carregar, []);

  const baseline = autoRecharge?.baseline ?? defaultBaseline;
  // `Number(x) || padrao` devolvia o padrão quando o aluno digitava 0, porque
  // 0 é falso em JavaScript — o campo parecia não funcionar. Zero é um valor
  // legítimo aqui (quer dizer "não me avise").
  const baselineEscolhida = Number.isFinite(Number(activateBaseline))
    ? Number(activateBaseline)
    : defaultBaseline;
  const saldoBaixo = sparks !== null && sparks < baseline;

  const onAutoRechargeAtivada = () => {
    setShowActivate(false);
    setActivatePkg(null);
    setActivateFreq(null);
    toast.success("Recarga automática ativada.");
    carregar();
  };

  const desativarRecarga = () => {
    api
      .delete("/sparks/auto-recharge")
      .then(() => { toast.success("Recarga automática desativada."); carregar(); })
      .catch((e) => toast.error(errMsg(e, "Falha ao desativar.")));
  };

  // Os Sparks só entram quando o webhook do Mercado Pago confirma o pagamento
  // no servidor — mesmo com `status: "approved"` aqui, o saldo ainda não subiu
  // no instante desta resposta.
  //
  // Antes havia um único `setTimeout(carregar, 2000)`: o webhook costuma
  // demorar mais que dois segundos, então o aluno via o saldo antigo e nada
  // mais acontecia na tela. Quem acabou de passar o cartão e não vê o produto
  // chegar abre chamado ou contesta a compra.
  //
  // Cada volta deste laço é também o que dispara a reconsulta ao Mercado Pago
  // no servidor: `GET /sparks/purchases/{id}` repergunta o status enquanto o
  // pagamento estiver em aberto. Por isso o Pix precisa de uma janela longa —
  // não é "esperar o webhook", é a própria tela confirmando o pagamento.
  const acompanharPagamento = useCallback(async (purchaseId, ehPix = false) => {
    setAguardandoPagamento(true);
    // Cartão responde em segundos. Pix leva o tempo de o aluno sair para o app
    // do banco, pagar e voltar — um minuto não cobre isso, e desistir cedo era
    // deixar quem já tinha pago olhando uma tela parada.
    const ATE = ehPix ? 15 * 60_000 : 60_000;
    const INTERVALO = ehPix ? 5_000 : 3_000;
    const inicio = Date.now();

    while (Date.now() - inicio < ATE) {
      await new Promise((r) => setTimeout(r, INTERVALO));
      try {
        const { data } = await api.get(`/sparks/purchases/${purchaseId}`);
        if (data.credited) {
          setAguardandoPagamento(false);
          // Pix fica com o QR Code aberto até confirmar — fecha só agora,
          // que o pagamento realmente foi creditado. Cartão já tinha fechado
          // na hora (`onPurchaseSuccess`), então isto é um no-op pra ele.
          setSelectedPkg(null);
          toast.success(`+${data.sparks_amount} Sparks creditados!`);
          carregar();
          return;
        }
        // `cancelled` é como o Mercado Pago encerra um Pix que expirou sem
        // pagamento — continuar perguntando por 15 minutos depois disso é só
        // deixar o aluno olhando um QR Code que não vale mais nada.
        if (data.status === "rejected" || data.status === "cancelled") {
          setAguardandoPagamento(false);
          setSelectedPkg(null);
          toast.error(
            ehPix
              ? "O prazo deste Pix expirou. Gere um novo para pagar."
              : "Pagamento recusado — tente outro cartão.",
          );
          carregar();
          return;
        }
      } catch {
        // Oscilação de rede não interrompe o acompanhamento: a próxima volta
        // do laço tenta de novo.
      }
    }

    // Esgotou a janela sem resposta definitiva: pode ser análise manual do
    // Mercado Pago, o que é normal e não significa erro. A promessa abaixo não
    // depende mais de o webhook chegar — o servidor varre os pagamentos em
    // aberto sozinho (`_sparks_reconciliacao_loop`) e credita quando aprovar.
    setAguardandoPagamento(false);
    toast.message(
      "O Mercado Pago ainda está confirmando. Os Sparks entram sozinhos assim que ele responder.",
    );
    carregar();
  }, []);

  const onPurchaseSuccess = (data) => {
    if (data?.status === "rejected") {
      setSelectedPkg(null);
      toast.error("Pagamento recusado — tente outro cartão.");
      return;
    }
    // Pix mostra QR Code + copia-e-cola dentro do próprio `PaymentBrick` — a
    // tela só fecha quando `acompanharPagamento` detectar o crédito (acima).
    // Cartão continua fechando na hora, como sempre fez.
    if (!data?.pix) {
      setSelectedPkg(null);
    }
    if (data?.purchase_id) {
      acompanharPagamento(data.purchase_id, !!data?.pix);
    } else if (!data?.pix) {
      setTimeout(carregar, 3000);
    }
  };

  // Histórico unificado: compras (Mercado Pago) e rodadas (Sparks ganhos
  // praticando), cada evento com seu próprio sinal — nunca inventa um saldo
  // "de consumo" que este backend ainda não rastreia à parte.
  const historico = [
    ...purchases.map((p) => ({
      key: `p-${p.purchase_id || p.mp_payment_id}`,
      quando: p.created_at,
      texto: `${p.source === "auto_recharge" ? "Recarga automática" : "Compra"} · ${p.package_id}`,
      valor: p.credited ? `+${p.sparks_amount}` : p.status,
      positivo: !!p.credited,
      pendente: !p.credited && p.status && p.status !== "rejected",
    })),
    ...rounds.map((r) => ({
      key: `r-${r.round_key}`,
      quando: r.created_at,
      texto: `Rodada ${r.rodada} · ${r.acertos}/${r.total} acertos`,
      valor: `+${r.sparks_ganhos}`,
      positivo: true,
    })),
  ].sort((a, b) => (b.quando || "").localeCompare(a.quando || "")).slice(0, 30);

  if (loading) {
    return <div><Nav /><div className="max-w-4xl mx-auto px-6 md:px-10 py-12 text-white/60">Carregando loja de Sparks...</div></div>;
  }

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-3">Sparks</div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white" data-testid="sparks-title">
          Quanto custa usar a inteligência do Sapiens.
        </h1>
        <p className="mt-3 text-white/60 max-w-lg">Sparks alimentam os recursos que usam IA. Ganhe praticando, ou compre quando precisar de mais.</p>

        <div className="mt-8 card-sapiens rounded-2xl p-6 flex items-center justify-between gap-4">
          <div>
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">Seu saldo</div>
            <div className="mt-2 font-display text-3xl font-bold tracking-tight flex items-center gap-2 text-zinc-950" data-testid="sparks-store-balance">
              <Zap className="w-6 h-6 text-amber-500" fill="currentColor" /> {sparks ?? "—"}
            </div>
            {aguardandoPagamento && (
              <div className="mt-2 inline-flex items-center gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-3 py-1.5" data-testid="sparks-aguardando">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Confirmando seu pagamento — os Sparks entram em instantes.
              </div>
            )}
          </div>
          {mapCost != null && (
            <div className="text-right text-xs text-zinc-500" data-testid="sparks-cost-example">
              <div className="flex items-center gap-1.5 justify-end"><Network className="w-3.5 h-3.5" /> Gerar/atualizar mapa cognitivo</div>
              <div className="font-mono-alt font-bold text-zinc-800">{mapCost} Sparks</div>
            </div>
          )}
        </div>

        {saldoBaixo && (
          <div className="mt-3 flex items-center gap-2 text-sm text-amber-400" data-testid="sparks-low-balance-warning">
            <AlertTriangle className="w-4 h-4" /> Seu saldo está abaixo do aviso configurado ({baseline} Sparks).
          </div>
        )}

        <div className="mt-10 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-white/80 font-display font-bold text-lg">
            <ShoppingBag className="w-4 h-4" /> Pacotes de Sparks
          </div>
          <span
            className="inline-flex items-center gap-1.5 rounded-full bg-sapiens-accentSoft text-sapiens-navy text-xs font-bold px-3 py-1.5"
            data-testid="sparks-nao-expiram"
          >
            <InfinityIcon className="w-3.5 h-3.5" /> Sparks não expiram
          </span>
        </div>

        {!mpDisponivel && (
          <div className="mt-3 text-sm text-white/50" data-testid="sparks-mp-unavailable">
            A compra de Sparks está temporariamente indisponível. Continue ganhando Sparks praticando questões.
          </div>
        )}

        <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 lg:items-end">
          {packages.filter((p) => !p.oculto).map((p) => {
            // Ordem crescente de destaque visual (200 < 600 < 4000), com UMA
            // exceção pedida: o pacote de R$54,90 (1.500 Sparks) é o maior de
            // todos, maior até que o de 4.000 — por isso o nível dele (3) não
            // segue a ordem natural dos outros três (0, 1, 2).
            const nivel = p.destaque_tamanho || 0;
            const NIVEL = {
              0: { pad: "p-5", amount: "text-xl", price: "text-base", btn: "py-2 text-xs", scale: "" },
              1: { pad: "p-6", amount: "text-2xl", price: "text-lg", btn: "py-2.5 text-sm", scale: "" },
              2: { pad: "p-7", amount: "text-3xl", price: "text-xl", btn: "py-2.5 text-sm", scale: "lg:scale-105" },
              3: { pad: "p-8 lg:p-9", amount: "text-4xl md:text-5xl", price: "text-2xl md:text-3xl", btn: "py-3.5 text-base", scale: "lg:scale-110 lg:z-10" },
            }[nivel];
            const anel = nivel >= 2 ? `ring-4 ring-sapiens-accent shadow-2xl shadow-sapiens-accent/30 ${NIVEL.scale}` : nivel === 1 ? "ring-2 ring-sapiens-accent/60" : "";
            return (
              // `.card-sapiens` tem `overflow:hidden` (recorta o brilho de borda
              // no canto arredondado) — um selo posicionado a -top-3 DENTRO dela
              // era cortado ao meio. O selo agora vive num wrapper por fora, que
              // não recorta nada, com o card em si por dentro.
              <div key={p.package_id} className={`relative pt-4 ${nivel >= 2 ? "lg:pt-5" : ""}`}>
                {p.highlight && (
                  <span
                    className={`absolute top-0 left-1/2 -translate-x-1/2 z-20 rounded-full bg-sapiens-navyDeep text-sapiens-accent border border-sapiens-accent/50 font-bold uppercase tracking-wide whitespace-nowrap shadow-md ${
                      nivel >= 2 ? "text-xs px-4 py-1.5" : "text-[10px] px-3 py-1"
                    }`}
                    data-testid={`sparks-package-highlight-${p.package_id}`}
                  >
                    {p.highlight}
                  </span>
                )}
                <div
                  className={`lift card-sapiens rounded-2xl flex flex-col ${NIVEL.pad} ${anel}`}
                  data-testid={`sparks-package-${p.package_id}`}
                >
                  <div className={`flex items-center gap-2 font-display font-extrabold text-zinc-950 ${NIVEL.amount}`}>
                    <Zap className={nivel >= 2 ? "w-7 h-7 text-amber-500" : "w-5 h-5 text-amber-500"} fill="currentColor" /> {p.sparks_amount}
                  </div>
                  <div className="mt-1 text-sm text-zinc-500">{p.label}</div>
                  <div className={`mt-4 font-mono-alt font-bold text-sapiens-navy ${NIVEL.price}`}>{formatBRL(p.price_cents)}</div>
                  <button
                    onClick={() => setSelectedPkg(p)}
                    disabled={!mpDisponivel || !publicKey}
                    className={`pill btn-sapiens mt-5 inline-flex items-center justify-center gap-2 px-4 rounded-full font-medium disabled:opacity-40 disabled:cursor-not-allowed ${NIVEL.btn}`}
                    data-testid={`sparks-buy-${p.package_id}`}
                  >
                    Comprar
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {selectedPkg && publicKey && (
          <div className="mt-6">
            <PaymentBrick
              publicKey={publicKey}
              pkg={selectedPkg}
              onSuccess={onPurchaseSuccess}
              onCancel={() => setSelectedPkg(null)}
            />
          </div>
        )}

        <div className="mt-10 flex items-center gap-2 text-white/80 font-display font-bold text-lg">
          <RefreshCw className="w-4 h-4" /> Recarga automática
        </div>
        <div className="mt-4 card-sapiens rounded-2xl p-6" data-testid="sparks-auto-recharge-panel">
          {autoRecharge ? (
            <div className="space-y-2">
              <p className="text-zinc-700 text-sm">
                Ativa: <strong>{packages.find((p) => p.package_id === autoRecharge.package_id)?.label || autoRecharge.package_id}</strong>,
                a cada {autoRecharge.frequency_days} dias.
              </p>
              {autoRecharge.next_payment_date && (
                <p className="text-zinc-500 text-xs">
                  Próxima cobrança: {new Date(autoRecharge.next_payment_date).toLocaleDateString("pt-BR")}
                  {autoRecharge.transaction_amount != null && ` · ${formatBRL(Math.round(autoRecharge.transaction_amount * 100))}`}
                </p>
              )}
              <p className="text-zinc-500 text-xs">Aviso de saldo baixo em {autoRecharge.baseline} Sparks.</p>
              <button
                onClick={desativarRecarga}
                className="pill mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium border border-rose-200 text-rose-600 hover:bg-rose-50"
                data-testid="sparks-deactivate-auto-recharge"
              >
                <XCircle className="w-3.5 h-3.5" /> Desativar recarga automática
              </button>
            </div>
          ) : showActivate ? (
            <div className="space-y-4">
              <p className="text-xs text-zinc-500">
                A recarga cobra sozinha, sem pedir o cartão de novo, mas só no calendário escolhido abaixo — o Mercado
                Pago exige um agendamento fixo para cobrar sem intervenção manual a cada vez; não é acionada no instante
                exato em que o saldo cai.
              </p>
              <div className="flex flex-wrap gap-2">
                {packages.filter((p) => !p.oculto).map((p) => (
                  <button
                    key={p.package_id}
                    onClick={() => setActivatePkg(p.package_id)}
                    className={`pill px-4 py-2 rounded-full text-xs font-medium ${activatePkg === p.package_id ? "btn-sapiens" : "border border-zinc-200 text-zinc-600"}`}
                    data-testid={`sparks-recharge-pkg-${p.package_id}`}
                  >
                    {p.label} · {formatBRL(p.price_cents)}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                {frequencies.map((dias) => (
                  <button
                    key={dias}
                    onClick={() => setActivateFreq(dias)}
                    className={`pill px-4 py-2 rounded-full text-xs font-medium ${activateFreq === dias ? "btn-sapiens" : "border border-zinc-200 text-zinc-600"}`}
                    data-testid={`sparks-recharge-freq-${dias}`}
                  >
                    A cada {dias} dias
                  </button>
                ))}
              </div>
              <label className="block text-xs text-zinc-500">
                Avisar quando o saldo cair abaixo de
                <input
                  type="number"
                  min={0}
                  value={activateBaseline}
                  onChange={(e) => setActivateBaseline(e.target.value)}
                  className="ml-2 w-20 rounded border border-zinc-200 px-2 py-1 text-zinc-800"
                  data-testid="sparks-recharge-baseline"
                />
                Sparks
              </label>

              {activatePkg && activateFreq && publicKey && (
                <AutoRechargeBrick
                  publicKey={publicKey}
                  pkg={packages.find((p) => p.package_id === activatePkg)}
                  frequencyDays={activateFreq}
                  baseline={baselineEscolhida}
                  onSuccess={onAutoRechargeAtivada}
                  onCancel={() => setShowActivate(false)}
                />
              )}
              <button className="text-xs text-zinc-400 hover:text-zinc-700" onClick={() => setShowActivate(false)}>
                Cancelar
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowActivate(true)}
              disabled={!mpDisponivel || !publicKey}
              className="pill btn-sapiens inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
              data-testid="sparks-activate-auto-recharge"
            >
              <RefreshCw className="w-4 h-4" /> Ativar recarga automática
            </button>
          )}
        </div>

        <div className="mt-10 flex items-center gap-2 text-white/80 font-display font-bold text-lg">
          <History className="w-4 h-4" /> Histórico
        </div>
        <div className="mt-4 card-sapiens rounded-2xl p-5 md:p-6" data-testid="sparks-history">
          {historico.length === 0 ? (
            <p className="text-sm text-zinc-500">Sem eventos de Sparks ainda.</p>
          ) : (
            <div className="divide-y divide-zinc-100">
              {historico.map((h) => (
                <div key={h.key} className="flex items-center justify-between py-2.5 text-sm" data-testid={`sparks-history-${h.key}`}>
                  <div className="flex items-center gap-2 text-zinc-700">
                    {h.positivo && <Check className="w-3.5 h-3.5 text-emerald-500" />}
                    {h.texto}
                    {h.quando && <span className="text-zinc-400 text-xs">· {new Date(h.quando).toLocaleDateString("pt-BR")}</span>}
                  </div>
                  <span className={`font-mono-alt font-bold ${h.positivo ? "text-emerald-600" : h.pendente ? "text-amber-600" : "text-zinc-400"}`}>
                    {h.valor}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* TEMPORÁRIO — só para validar um pagamento real (não-TEST) de ponta
            a ponta em produção. Remover este bloco e o pacote "spark_test_15"
            em sparks_store.py depois do teste. De propósito isolado, longe da
            grade principal, sem estilo de destaque. */}
        {mpDisponivel && publicKey && (() => {
          const pacoteTeste = packages.find((p) => p.package_id === "spark_test_15");
          return pacoteTeste ? (
            <div className="mt-16 pt-6 border-t border-white/10 text-center">
              <button
                onClick={() => setSelectedPkg(pacoteTeste)}
                className="text-[11px] text-white/30 hover:text-white/60 underline"
                data-testid="sparks-buy-spark_test_15"
              >
                [teste interno] R$ 1,00 → 15 Sparks
              </button>
            </div>
          ) : null;
        })()}
      </div>
    </div>
  );
}
