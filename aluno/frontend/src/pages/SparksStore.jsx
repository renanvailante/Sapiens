import { useCallback, useEffect, useRef, useState } from "react";
import { MENTOR } from "../lib/mentor";
import { Link } from "react-router-dom";
import Tela from "../components/Tela";
import Indicacao from "../components/sparks/Indicacao";
import { useAncora } from "../components/SecaoDaAba";
import { ANCORAS } from "../lib/rotas";
import { Bloco } from "../components/Esqueleto";
import { api, errMsg } from "../lib/api";
import { formatBRL } from "../lib/utils";
import { economiaDoPacote } from "../lib/venda";
import { quintasAteAProva } from "../lib/enem";
import { toast } from "sonner";
import { Zap, Check, Loader2, History, RefreshCw, XCircle, AlertTriangle, Infinity as InfinityIcon, Copy, QrCode, ExternalLink, Gift, CreditCard, Star, Crown, ShieldCheck } from "lucide-react";

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

// A tela de pagamento PADRÃO da loja: Pix.
//
// Antes, clicar em "Comprar" abria o Payment Brick do Mercado Pago, que pede
// e-mail e CPF antes de mostrar qualquer coisa — um formulário inteiro entre
// a vontade de comprar e o código para pagar, com dados que nós já temos. O
// QR Code agora é gerado no próprio clique (`POST /sparks/purchases` com
// `payment_method_id: "pix"`), e o que aparece aqui é só o que serve para
// pagar: o código para escanear, o botão que abre o app do banco e o
// copia-e-cola.
function PainelPix({ pkg, estado, pix, erro, onFechar, onCartao, onTentarDeNovo }) {
  const campoPixRef = useRef(null);

  const copiar = async () => {
    // `writeText` devolve uma promessa e REJEITA onde a área de transferência
    // é bloqueada — navegador embutido do WhatsApp e do Instagram, que é por
    // onde boa parte dos alunos abre o link. Sem o `catch`, o toast dizia
    // "copiado" de qualquer jeito e a pessoa voltava para o banco com a área
    // de transferência vazia, sem entender por quê.
    try {
      await navigator.clipboard.writeText(pix.qr_code);
      toast.success("Código Pix copiado. Cole no app do seu banco.");
    } catch {
      campoPixRef.current?.select();
      toast.error("Seu navegador não deixou copiar. O código está selecionado acima — segure e escolha Copiar.");
    }
  };

  const validade = (() => {
    if (!pix?.expira_em) return null;
    const quando = new Date(pix.expira_em);
    if (Number.isNaN(quando.getTime())) return null;
    return quando.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  })();

  return (
    <div className="card-sapiens rounded-2xl p-6" data-testid="sparks-painel-pix">
      <div className="flex items-center justify-between gap-4 mb-4">
        <div>
          <div className="secao-olho">Pagamento por Pix · Mercado Pago</div>
          <div className="font-display font-bold text-lg text-zinc-950">{pkg.label} · {formatBRL(pkg.price_cents)}</div>
        </div>
        <button onClick={onFechar} className="text-xs text-zinc-400 hover:text-zinc-700">Fechar</button>
      </div>

      {estado === "gerando" && (
        <div className="flex items-center gap-2 text-sm text-zinc-500 py-10 justify-center" data-testid="sparks-pix-gerando">
          <Loader2 className="w-4 h-4 animate-spin" /> Gerando seu código Pix...
        </div>
      )}

      {estado === "erro" && (
        <div data-testid="sparks-pix-erro">
          <div className="text-sm text-rose-600">{erro}</div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={onTentarDeNovo}
              className="pill btn-sapiens px-4 py-2 rounded-full text-xs font-medium"
              data-testid="sparks-pix-tentar-de-novo"
            >
              Tentar de novo
            </button>
            {onCartao && (
              <button
                onClick={onCartao}
                className="pill px-4 py-2 rounded-full text-xs font-medium border border-zinc-200 text-zinc-600 hover:border-zinc-400"
                data-testid="sparks-pix-erro-cartao"
              >
                Pagar com cartão
              </button>
            )}
          </div>
        </div>
      )}

      {estado === "pronto" && pix && (
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 text-sm font-semibold text-zinc-800">
            <QrCode className="w-4 h-4" /> Escaneie o QR Code ou copie o código
          </div>
          {pix.qr_code_base64 && (
            <img
              src={`data:image/png;base64,${pix.qr_code_base64}`}
              alt="QR Code Pix"
              className="mx-auto mt-3 w-48 h-48 rounded-xl border border-zinc-200"
              data-testid="sparks-pix-qr-image"
            />
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
              <button
                onClick={copiar}
                className="pill btn-sapiens mt-2 inline-flex w-full items-center justify-center gap-2 px-5 py-3 rounded-full text-sm font-semibold sm:w-auto"
                data-testid="sparks-pix-copiar"
              >
                <Copy className="w-4 h-4" /> Copiar código Pix
              </button>
            </div>
          )}
          {/* No celular o QR Code não serve: ninguém escaneia a própria tela.
              O `ticket_url` é o que abre o pagamento no app do banco ou do
              MP, que é o caminho real de quem está no telefone. */}
          {pix.ticket_url && (
            <div>
              <a
                href={pix.ticket_url}
                target="_blank"
                rel="noopener noreferrer"
                className="pill mt-2 inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full text-xs font-medium border border-zinc-200 text-zinc-600 hover:border-zinc-400"
                data-testid="sparks-pix-abrir-app"
              >
                <ExternalLink className="w-3.5 h-3.5" /> Abrir no app do banco
              </a>
            </div>
          )}
          <p className="mt-4 text-xs text-zinc-500">
            Os Sparks entram automaticamente assim que o Mercado Pago confirmar o pagamento — pode fechar esta tela
            quando quiser, isso não cancela o Pix.
            {validade && ` Este código vale até ${validade}.`}
          </p>
        </div>
      )}

      {/* Fora do bloco do QR Code de propósito: quem já sabe que vai pagar no
          cartão não deve ter que esperar um código Pix terminar de nascer
          para poder dizer isso. */}
      {onCartao && estado !== "erro" && (
        <div className="mt-4">
          {/* Era um link cinza sublinhado de 12px. Quem chegou até aqui e
              PRECISA parcelar não ia encontrá-lo — e essa pessoa é a que tem
              mais dificuldade de pagar à vista, não menos. */}
          <button
            onClick={onCartao}
            className="botao-cartao"
            data-testid="sparks-pix-prefiro-cartao"
          >
            <CreditCard className="h-4 w-4 shrink-0" />
            <span className="min-w-0">
              Prefiro pagar com cartão
              <span className="botao-cartao-nota">dá para parcelar</span>
            </span>
          </button>
        </div>
      )}
    </div>
  );
}

// Pagamento com cartão — só para quem escolhe explicitamente, pelo link no
// painel do Pix. Monta o Payment Brick do Mercado Pago dentro de
// `containerId`: o aluno digita os dados do cartão DENTRO do widget oficial
// do MP (não num campo nosso); `onSubmit` só recebe de volta um token opaco.
function PaymentBrick({ publicKey, pkg, onSuccess, onCancel }) {
  const containerId = useRef(`mp-brick-${pkg.package_id}`).current;
  const brickRef = useRef(null);
  const [status, setStatus] = useState("loading"); // 'loading' | 'ready' | 'submitting' | 'error'
  const [error, setError] = useState(null);

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
            // Só cartão: o Pix tem caminho próprio (`PainelPix`), gerado no
            // clique e sem formulário. Deixar `bankTransfer` aqui devolveria
            // o aluno ao pedido de e-mail e CPF que esta mudança tirou do
            // caminho — dois jeitos de pagar por Pix, um deles pior.
            paymentMethods: { creditCard: "all", debitCard: "all" },
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
                .then(({ data }) => onSuccess(data))
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
          <div className="secao-olho">Cartão · Mercado Pago</div>
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
      <div id={containerId} />
      {status === "submitting" && (
        <div className="flex items-center gap-2 text-sm text-zinc-500 mt-3 justify-center">
          <Loader2 className="w-4 h-4 animate-spin" /> Confirmando com o Mercado Pago...
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
          <div className="secao-olho">Cartão para a recarga automática</div>
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

// A "pilha" de moedas do card: cresce com a QUANTIDADE do pacote (1 a 4
// moedas, pela posição dele no catálogo ordenado por Sparks), para o olho
// comparar tamanhos antes de ler número. É desenho, não promessa — nenhum
// valor sai daqui.
const MOEDAS = {
  1: [[38, 26, 17]],
  2: [[48, 22, 14], [30, 30, 14]],
  3: [[38, 16, 13], [24, 32, 13], [52, 32, 13]],
  4: [[38, 13, 12], [24, 26, 12], [52, 26, 12], [38, 37, 12]],
};

function raio(cx, cy, r) {
  const k = r / 13;
  const p = (x, y) => `${(cx + x * k).toFixed(2)} ${(cy + y * k).toFixed(2)}`;
  return `M ${p(1.5, -8)} L ${p(-5, 1.2)} L ${p(-0.6, 1.2)} L ${p(-1.8, 8)} L ${p(5, -1.2)} L ${p(0.6, -1.2)} Z`;
}

function faisca(x, y, t) {
  return `M ${x} ${y - t} Q ${x} ${y} ${x + t} ${y} Q ${x} ${y} ${x} ${y + t} Q ${x} ${y} ${x - t} ${y} Q ${x} ${y} ${x} ${y - t} Z`;
}

function PilhaDeSparks({ n }) {
  const moedas = MOEDAS[Math.min(Math.max(n, 1), 4)];
  return (
    <svg className="loja-pilha" viewBox="0 0 76 54" aria-hidden="true">
      {n >= 3 && (
        <>
          <path className="loja-faisca" d={faisca(9, 12, 5)} fill="#FFE2B0" />
          <path className="loja-faisca" d={faisca(68, 9, 4)} fill="#FFE2B0" />
        </>
      )}
      {moedas.map(([cx, cy, r]) => (
        <g key={`${cx}-${cy}`}>
          <circle cx={cx} cy={cy + 3} r={r} fill="#C27B12" />
          <circle cx={cx} cy={cy} r={r} fill="#FFB547" />
          <circle cx={cx} cy={cy} r={r * 0.74} fill="none" stroke="#FFD691" strokeWidth="1.5" />
          <path d={raio(cx, cy, r)} fill="#8A4A00" />
        </g>
      ))}
    </svg>
  );
}

/**
 * UM PACOTE DA GRADE. Tudo o que ele escreve vem do catálogo do servidor
 * (`GET /sparks/packages`): quantidade, preço, selo e benefícios. O que a
 * tela acrescenta é só ARITMÉTICA sobre esses números — o preço de 100
 * Sparks e quanto mais barato sai cada Spark em relação ao pacote de pior
 * preço por Spark —, e ela é conferível por quem olhar dois cards lado a lado.
 */
function CartaoDoPacote({ p, moedas, destaque, economia, rende = [], escolhido, desabilitado, onPix, onCartao }) {
  const plus = (p.beneficios || []).length > 0;
  const classe = [
    "loja-pacote",
    destaque && "loja-pacote--destaque",
    plus && !destaque && "loja-pacote--plus",
  ].filter(Boolean).join(" ");
  const porCem = formatBRL(Math.round((p.price_cents * 100) / p.sparks_amount));

  return (
    <article
      className={classe}
      data-escolhido={escolhido ? "true" : undefined}
      data-testid={`sparks-package-${p.package_id}`}
    >
      {p.highlight ? (
        <div className="loja-selo" data-testid={`sparks-package-highlight-${p.package_id}`}>
          {destaque ? (
            <Star className="h-3.5 w-3.5 shrink-0" fill="currentColor" />
          ) : plus ? (
            <Crown className="h-3.5 w-3.5 shrink-0" />
          ) : null}
          {p.highlight}
        </div>
      ) : (
        <div className="loja-selo loja-selo--vazio" aria-hidden="true">·</div>
      )}

      <div className="loja-corpo">
        <PilhaDeSparks n={moedas} />
        <div className="loja-qtd-bloco">
          <span className="loja-qtd">{p.sparks_amount.toLocaleString("pt-BR")}</span>
          <span className="loja-unid">Sparks</span>
        </div>
        <div className="loja-preco-bloco">
          <span className="loja-preco" data-testid={`sparks-preco-${p.package_id}`}>{formatBRL(p.price_cents)}</span>
          <span className="loja-unitario">{porCem} / 100 Sparks</span>
          {economia > 0 && (
            <span className="loja-economia" data-testid={`sparks-economia-${p.package_id}`}>
              Economize {economia}%
            </span>
          )}
        </div>

        {/* O direito que a compra concede. Vem do catálogo do servidor
            (`sparks_store.beneficios`), a mesma fonte que o webhook usa para
            conceder — anunciar aqui o que o servidor não entrega seria o pior
            defeito possível numa tela de pagamento. */}
        {plus && (
          <ul className="loja-beneficios" data-testid={`sparks-beneficios-${p.package_id}`}>
            {p.beneficios.map((b) => (
              <li key={b}>
                <Check className="h-3.5 w-3.5" strokeWidth={3} />
                {b}
              </li>
            ))}
          </ul>
        )}

        {/* Quanto o pacote RENDE, em coisas que o aluno reconhece. "ou", e não
            "e": é o mesmo saldo gasto de um jeito OU de outro. O pacote que
            vende direitos não tem esta lista — ele já mostra os benefícios. */}
        {!plus && rende.length > 0 && (
          <div className="loja-rende" data-testid={`sparks-rende-${p.package_id}`}>
            <span className="loja-rende-olho">Dá para</span>
            {rende.map((r, i) => (
              <span key={r.chave} className="loja-rende-item">
                {i > 0 && <span className="loja-rende-ou">ou </span>}
                <strong>{r.n.toLocaleString("pt-BR")}</strong> {r.n === 1 ? r.um : r.varios}
              </span>
            ))}
          </div>
        )}

        <div className="loja-acoes">
          <button
            type="button"
            onClick={onPix}
            disabled={desabilitado}
            className={`loja-pix ${destaque ? "btn-sapiens" : "btn-contorno"}`}
            data-testid={`sparks-buy-${p.package_id}`}
          >
            <QrCode className="h-4 w-4 shrink-0" /> Pagar com Pix
          </button>
          {/* O cartão no próprio card, e não escondido atrás do Pix (até
              2026-09-18 só se chegava a ele depois de gerar um QR Code). É o
              terceiro degrau visual, mas legível e com a única coisa que
              decide a compra de quem não tem o valor inteiro hoje. */}
          <button
            type="button"
            onClick={onCartao}
            disabled={desabilitado}
            className="loja-cartao"
            data-testid={`sparks-buy-cartao-${p.package_id}`}
          >
            <span className="loja-cartao-rotulo">
              <CreditCard className="h-4 w-4 shrink-0" /> Pagar no cartão
            </span>
            <span className="loja-cartao-nota">dá para parcelar</span>
          </button>
        </div>
      </div>
    </article>
  );
}

export default function SparksStore() {
  // `/indicar` redireciona para `/sparks#indicar`. Sem isto, o link antigo
  // abre a loja no topo e o aluno precisa procurar a seção que ele pediu.
  useAncora();

  const [sparks, setSparks] = useState(null);
  // O direito permanente do pacote de R$119,90. Vem do MESMO GET do saldo —
  // as duas informações aparecem juntas na tela e buscá-las em duas chamadas
  // faria a loja piscar entre "compre" e "você já tem".
  const [mentisIlimitada, setMentisIlimitada] = useState(false);
  // O preço AVULSO do que os direitos incluem, vindo do catálogo do servidor
  // (`sparks_store` + `cursos`). É com ele que a loja escreve o que o pacote
  // substitui — 200 e 500 nunca são escritos aqui.
  const [precosAvulsos, setPrecosAvulsos] = useState(null);
  // O que um Spark compra, para o card dizer quanto o pacote RENDE. Os dois
  // preços vêm das rotas que leem as mesmas constantes que cobram
  // (`/redacao/precos`, `/mentis/precos`) — nenhum número escrito aqui.
  const [custos, setCustos] = useState({ correcao: null, explicacao: null });
  const [direitos, setDireitos] = useState({});
  const [packages, setPackages] = useState([]);
  const [publicKey, setPublicKey] = useState(null);
  const [mpDisponivel, setMpDisponivel] = useState(true);
  const [purchases, setPurchases] = useState([]);
  const [rounds, setRounds] = useState([]);
  // Cartão: só para quem escolhe de propósito, pelo link dentro do painel do Pix.
  const [selectedPkg, setSelectedPkg] = useState(null);
  // Pix é o caminho padrão da loja — o clique em "Comprar" já gera o código,
  // sem pedir e-mail nem CPF antes (o e-mail o servidor tira da conta).
  const [pixPkg, setPixPkg] = useState(null);
  const [pixEstado, setPixEstado] = useState("gerando"); // 'gerando' | 'pronto' | 'erro'
  const [pixDados, setPixDados] = useState(null);
  const [pixErro, setPixErro] = useState(null);
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
      api.get("/firestore/students/me/sparks").then(({ data }) => data).catch(() => null),
      api.get("/sparks/packages").then(({ data }) => data).catch(() => ({ packages: [], auto_recharge_frequencies_days: [], default_baseline: 50 })),
      api.get("/sparks/config").then(({ data }) => data.public_key).catch(() => { setMpDisponivel(false); return null; }),
      api.get("/sparks/purchases/me").then(({ data }) => data.items || []).catch(() => []),
      api.get("/firestore/students/me/rounds").then(({ data }) => data.rounds || []).catch(() => []),
      api.get("/sparks/auto-recharge/me").then(({ data }) => (data?.active ? data : null)).catch(() => null),
      api.get("/redacao/precos").then(({ data }) => data?.custo_correcao ?? null).catch(() => null),
      api.get("/mentis/precos").then(({ data }) => data?.explicacao ?? null).catch(() => null),
    ]).then(([saldo, catalogo, pk, purch, rds, recarga, correcao, explicacao]) => {
      setSparks(saldo?.sparks_balance ?? null);
      setMentisIlimitada(Boolean(saldo?.mentis_ilimitada));
      setPackages(catalogo.packages || []);
      setPrecosAvulsos(catalogo.precos_avulsos || null);
      setDireitos(saldo?.direitos || {});
      setFrequencies(catalogo.auto_recharge_frequencies_days || []);
      setDefaultBaseline(catalogo.default_baseline ?? 50);
      setActivateBaseline(catalogo.default_baseline ?? 50);
      setPublicKey(pk);
      setPurchases(purch);
      setRounds(rds);
      setAutoRecharge(recarga);
      setCustos({ correcao, explicacao });
      setLoading(false);
    });
  };
  useEffect(carregar, []);

  // O pacote que concede o direito, escolhido pelo CATÁLOGO e não por um
  // `package_id` escrito na tela: o dia em que o produto mudar o pacote que
  // dá Mentis ilimitada, esta tela acompanha sozinha.
  //
  // Procura pelo DIREITO e não por "tem benefício": o catálogo já teve dois
  // cards com benefício (o de 1.500 incluiu as aulas ao vivo até 2026-09-16)
  // e vai ter de novo — "o primeiro que tiver benefício" acertaria hoje por
  // acidente e erraria na próxima mudança de catálogo.
  const pacoteIlimitado = packages.find(
    (p) => !p.oculto && (p.direitos || []).includes("mentis_ilimitada"),
  );

  // O que o aluno gastaria comprando avulso o que este pacote já inclui. É
  // multiplicação conferível (ver `lib/venda.js`), não "economize até X": as
  // quintas que ainda cabem antes da prova vezes o preço da edição, mais os
  // cursos vezes o preço do curso. Some sozinha para quem já tem os direitos.
  const contaDoPacote = economiaDoPacote({
    pacote: pacoteIlimitado,
    quintasRestantes: quintasAteAProva(),
    precos: precosAvulsos,
    direitos,
  });

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
  const fecharPagamento = useCallback(() => {
    setSelectedPkg(null);
    setPixPkg(null);
    setPixDados(null);
    setPixErro(null);
  }, []);

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
          // O Pix fica com o QR Code aberto até confirmar — fecha só agora,
          // que o pagamento realmente foi creditado. Cartão já tinha fechado
          // na hora (`onPurchaseSuccess`), então isto é um no-op pra ele.
          fecharPagamento();
          toast.success(`+${data.sparks_amount} Sparks creditados!`);
          carregar();
          return;
        }
        // `cancelled` é como o Mercado Pago encerra um Pix que expirou sem
        // pagamento — continuar perguntando por 15 minutos depois disso é só
        // deixar o aluno olhando um QR Code que não vale mais nada.
        if (data.status === "rejected" || data.status === "cancelled") {
          setAguardandoPagamento(false);
          fecharPagamento();
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fecharPagamento]);

  // O caminho normal da loja: um clique, e o código para pagar aparece.
  // Nenhum formulário no meio — o servidor já sabe quem é o aluno e usa o
  // e-mail da conta, que é o único campo que o Mercado Pago exige no Pix.
  //
  // Clicar de novo no mesmo pacote NÃO gera um segundo código: o servidor
  // devolve o Pix que ainda está em aberto (`_pix_em_aberto`), justamente
  // para ninguém pagar dois QR Codes do mesmo produto.
  /**
   * CARTÃO, direto do card do pacote.
   *
   * Até 2026-09-18 o cartão existia, mas só se alcançava por um link cinza
   * sublinhado DENTRO do painel do Pix — ou seja: para pagar no cartão, o
   * aluno tinha de primeiro pedir um Pix, esperar o QR Code nascer e então
   * descobrir, em letra miúda, que havia outro caminho. Quem não quer Pix
   * (ou quem precisa PARCELAR, que é a maioria dos pacotes maiores) abandonava
   * antes disso.
   *
   * O Pix continua sendo o primeiro botão: ele é um clique, cai na hora e não
   * tem taxa de parcelamento para o aluno. O cartão é o segundo — mas segundo
   * VISÍVEL, com o nome escrito e dizendo que dá para parcelar, que é a
   * informação que decide a compra de quem tem R$ 119,90 para gastar e não
   * tem R$ 119,90 hoje.
   */
  const comprarComCartao = (p) => {
    setPixPkg(null);
    setPixDados(null);
    setPixErro(null);
    setSelectedPkg(p);
  };

  const comprarComPix = (p) => {
    setSelectedPkg(null);
    setPixPkg(p);
    setPixEstado("gerando");
    setPixDados(null);
    setPixErro(null);
    api
      .post("/sparks/purchases", { package_id: p.package_id, payment_method_id: "pix" })
      .then(({ data }) => {
        if (!data?.pix?.qr_code) {
          setPixEstado("erro");
          setPixErro("O Mercado Pago não devolveu o código Pix desta vez.");
          return;
        }
        setPixDados(data.pix);
        setPixEstado("pronto");
        if (data.purchase_id) acompanharPagamento(data.purchase_id, true);
      })
      .catch((e) => {
        setPixEstado("erro");
        setPixErro(errMsg(e, "Não foi possível gerar o código Pix."));
      });
  };

  // Cartão — só para quem pede. O Brick do Mercado Pago (e o formulário que
  // vem com ele) deixou de ser o primeiro passo de toda compra.
  const onPurchaseSuccess = (data) => {
    setSelectedPkg(null);
    if (data?.status === "rejected") {
      toast.error("Pagamento recusado — tente outro cartão.");
      return;
    }
    if (data?.purchase_id) {
      acompanharPagamento(data.purchase_id, false);
    } else {
      setTimeout(carregar, 3000);
    }
  };

  // O painel de pagamento nasce abaixo da grade de pacotes: sem isto, em
  // tela pequena o aluno clica em "Comprar" e parece que nada aconteceu.
  useEffect(() => {
    if (!pixPkg && !selectedPkg) return undefined;
    const t = setTimeout(() => {
      document
        .getElementById("painel-pagamento")
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 80);
    return () => clearTimeout(t);
  }, [pixPkg, selectedPkg]);

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

  // A grade: só os pacotes visíveis, na ordem do catálogo (crescente por
  // preço, da esquerda para a direita — ver `sparks_store.PACKAGES`).
  const visiveis = packages.filter((p) => !p.oculto);
  // O destaque é o de MAIOR `destaque_tamanho` (decisão de produto que mora no
  // catálogo, hoje o de 1.500). Sem nenhum nível acima de zero, ninguém sobe.
  const nivelMaximo = Math.max(0, ...visiveis.map((p) => p.destaque_tamanho || 0));
  const idDoDestaque = nivelMaximo > 0
    ? visiveis.find((p) => (p.destaque_tamanho || 0) === nivelMaximo)?.package_id
    : null;
  // Quantas moedas cada card desenha: a posição dele por QUANTIDADE.
  const porQuantidade = [...visiveis].sort((a, b) => a.sparks_amount - b.sparks_amount);
  const moedasDe = (p) => Math.min(porQuantidade.indexOf(p) + 1, 4);
  // "Economize X%": quanto mais barato sai cada Spark em relação ao pacote de
  // PIOR preço por Spark. Arredonda para baixo — nunca anuncia um ponto a mais
  // do que a conta dá — e só aparece a partir de 5%.
  const piorPorSpark = Math.max(0, ...visiveis.map((p) => p.price_cents / p.sparks_amount));
  const economiaDe = (p) => {
    if (!piorPorSpark) return 0;
    const e = Math.floor((1 - p.price_cents / p.sparks_amount / piorPorSpark) * 100);
    return e >= 5 ? e : 0;
  };
  // O que o saldo do pacote compra, pela divisão inteira — "12 correções"
  // quando dá 12,5. A explicação some para quem tem a Mentis ilimitada,
  // porque para ele ela já não custa Spark.
  const rendeDe = (p) => [
    custos.correcao > 0 && {
      chave: "correcao", n: Math.floor(p.sparks_amount / custos.correcao),
      um: "correção de redação", varios: "correções de redação",
    },
    custos.explicacao > 0 && !mentisIlimitada && {
      chave: "explicacao", n: Math.floor(p.sparks_amount / custos.explicacao),
      um: "explicação de questão", varios: "explicações de questão",
    },
  ].filter((r) => r && r.n >= 1);
  const pagamentoAberto = pixPkg?.package_id || selectedPkg?.package_id || null;
  const semPagamento = !mpDisponivel || !publicKey;

  const cabeca = {
    olho: "Loja de Sparks",
    titulo: "Escolha seu pacote",
    subtitulo: "Cada Spark vira uma resposta da Mentis, uma correção de redação ou uma semana montada para você.",
  };

  if (loading) {
    return (
      <Tela {...cabeca} largura="xl" voltar="/hoje" testid="sparks">
        <div className="loja-casca">
          <div className="loja-grade">
            {[0, 1, 2, 3].map((i) => (
              <Bloco key={i} className="rounded-3xl" altura={300} />
            ))}
          </div>
        </div>
      </Tela>
    );
  }

  return (
    <Tela
      /* A loja abre nos PACOTES (pedido do dono, 2026-10-19: "é aí que o
          pessoal vai comprar, e eu quero que fique no topo da página"). O
          título diz o que fazer aqui; o saldo é um chip no canto, não um
          cartão de primeira dobra. */
      {...cabeca}
      largura="xl"
      voltar="/hoje"
      testid="sparks"
      acoes={
        <div className="loja-saldo" title="Seu saldo de Sparks">
          <Zap className="h-5 w-5 text-amber-400" fill="currentColor" />
          <span className="loja-saldo-n" data-testid="sparks-store-balance">{sparks ?? "—"}</span>
          <span className="loja-saldo-rotulo">no saldo</span>
        </div>
      }
    >
      <>
        {aguardandoPagamento && (
          <div
            className="mb-4 flex items-center gap-2 rounded-2xl border-2 border-amber-400/40 bg-amber-400/10 px-4 py-3 text-sm font-bold text-amber-200"
            data-testid="sparks-aguardando"
          >
            <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
            Confirmando seu pagamento — os Sparks entram em instantes.
          </div>
        )}

        {saldoBaixo && !aguardandoPagamento && (
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-amber-300" data-testid="sparks-low-balance-warning">
            <AlertTriangle className="h-4 w-4 shrink-0" /> Seu saldo está abaixo do aviso configurado ({baseline} Sparks).
          </div>
        )}

        {!mpDisponivel && (
          <div className="mb-4 text-sm text-white/60" data-testid="sparks-mp-unavailable">
            A compra de Sparks está temporariamente indisponível. Continue ganhando Sparks praticando questões.
          </div>
        )}

        {/* OS PACOTES — a primeira coisa da loja. */}
        <section className="loja-casca" aria-label="Pacotes de Sparks">
          <div className="loja-grade">
            {visiveis.map((p) => (
              <CartaoDoPacote
                key={p.package_id}
                p={p}
                moedas={moedasDe(p)}
                destaque={p.package_id === idDoDestaque}
                economia={economiaDe(p)}
                rende={rendeDe(p)}
                escolhido={pagamentoAberto === p.package_id}
                desabilitado={semPagamento}
                onPix={() => comprarComPix(p)}
                onCartao={() => comprarComCartao(p)}
              />
            ))}
          </div>
        </section>

        {/* O pagamento abre logo abaixo da grade, no lugar onde o olho já está. */}
        {(pixPkg || selectedPkg) && (
          <div className="mt-6 scroll-mt-24" id="painel-pagamento">
            {selectedPkg && publicKey ? (
              <PaymentBrick
                publicKey={publicKey}
                pkg={selectedPkg}
                onSuccess={onPurchaseSuccess}
                onCancel={() => setSelectedPkg(null)}
              />
            ) : pixPkg ? (
              <PainelPix
                pkg={pixPkg}
                estado={pixEstado}
                pix={pixDados}
                erro={pixErro}
                onFechar={fecharPagamento}
                onTentarDeNovo={() => comprarComPix(pixPkg)}
                // Sem chave pública não há Brick para abrir — melhor não
                // oferecer um caminho que não existe.
                onCartao={publicKey ? () => { setPixPkg(null); setSelectedPkg(pixPkg); } : null}
              />
            ) : null}
          </div>
        )}

        {/* As garantias, coladas na grade: o que tira a dúvida de quem está
            com o dedo no botão. Cada linha é verdade do caminho de pagamento —
            o Pix sai num clique sem formulário (`comprarComPix`), o
            parcelamento é decisão do Mercado Pago, e Spark não tem validade. */}
        <div className="loja-garantias">
          <div className="loja-garantia">
            <QrCode className="h-[18px] w-[18px]" /> Pix em um clique, sem formulário
          </div>
          <div className="loja-garantia">
            <CreditCard className="h-[18px] w-[18px]" /> No cartão, dá para parcelar
          </div>
          <div className="loja-garantia" data-testid="sparks-nao-expiram">
            <InfinityIcon className="h-[18px] w-[18px]" /> Sparks não expiram
          </div>
          <div className="loja-garantia">
            <ShieldCheck className="h-[18px] w-[18px]" /> Pagamento seguro pelo Mercado Pago
          </div>
        </div>

        {/* O ARGUMENTO DO PACOTE DE CIMA, logo depois da grade: o de R$119,90
            não é "mais Sparks", é a Mentis parar de cobrar por 30 dias
            (decisão do dono, 2026-09-21 — reverte a promessa anterior de
            "para sempre", ver `Cerebro/regras/inviolaveis.md`). Cursos, lives
            e Comunidade VIP continuam permanentes, só a Mentis tem prazo.
            Quem já comprou vê a confirmação no lugar do anúncio — vender de
            novo o que a pessoa já tem é o jeito mais rápido de fazer ela
            duvidar do que comprou. */}
        {mentisIlimitada ? (
          <div
            className="mt-8 flex flex-wrap items-center gap-4 rounded-2xl border-2 border-violet-400/35 bg-violet-500/10 p-5"
            data-testid="sparks-mentis-ilimitada-ativa"
          >
            <InfinityIcon className="h-7 w-7 shrink-0 text-violet-300" />
            <div className="min-w-0 flex-1">
              <div className="font-display text-lg font-bold tracking-tight text-violet-100">
                Mentis ilimitada por 30 dias, cursos, lives e Comunidade VIP: são seus.
              </div>
              <div className="text-sm text-violet-200/70">
                Chat, explicação de questão e intervenção da causa raiz não gastam Spark
                por 30 dias a partir da compra. Os quatro cursos e as aulas ao vivo de
                quinta são permanentes e já estão inclusos. Seu saldo serve para o resto
                do produto.{" "}
                <Link to="/estudar/cursos" className="font-semibold text-violet-100 underline">
                  Ver os cursos
                </Link>{" "}
                ·{" "}
                <Link to="/comunidade?sala=vip" className="font-semibold text-violet-100 underline">
                  Abrir a sala VIP
                </Link>
              </div>
            </div>
          </div>
        ) : pacoteIlimitado ? (
          <button
            type="button"
            onClick={() => comprarComPix(pacoteIlimitado)}
            disabled={semPagamento}
            className="mt-8 flex w-full flex-col items-stretch gap-4 rounded-2xl border-2 border-violet-400/40 bg-violet-500/10 p-5 text-left transition-colors hover:border-violet-400/70 disabled:cursor-not-allowed sm:flex-row sm:items-center"
            data-testid="sparks-mentis-ilimitada-oferta"
          >
            <div className="flex min-w-0 flex-1 items-start gap-4 sm:items-center">
              <InfinityIcon className="h-8 w-8 shrink-0 text-violet-300" />
              <div className="min-w-0 flex-1">
                <div className="secao-olho text-violet-300">
                  {formatBRL(pacoteIlimitado.price_cents)} · {pacoteIlimitado.sparks_amount.toLocaleString("pt-BR")} Sparks
                </div>
                <div className="mt-0.5 font-display text-xl font-extrabold tracking-tight text-white md:text-2xl">
                  A Mentis para de cobrar por 30 dias. E os cursos já vêm inclusos.
                </div>
                <div className="mt-1 text-sm leading-relaxed text-white/60">
                  Uma compra e, por 30 dias, o chat, as explicações de questão e as intervenções
                  da causa raiz deixam de gastar Spark, sem limite de mensagens. Junto vêm{" "}
                  <strong className="font-semibold text-white/85">todos os cursos</strong> e{" "}
                  <strong className="font-semibold text-white/85">todas as aulas ao vivo de
                  quinta</strong> com o {MENTOR.nome}, a{" "}
                  <strong className="font-semibold text-white/85">Comunidade VIP</strong> (a sala
                  fechada do mural) e os {pacoteIlimitado.sparks_amount.toLocaleString("pt-BR")} Sparks, que não expiram.
                </div>
              </div>
            </div>
            <span className="btn-sapiens loja-btn-plus inline-flex w-full shrink-0 items-center justify-center gap-2 px-6 py-3.5 text-sm sm:w-auto">
              <Crown className="h-4 w-4" /> Quero a Mentis ilimitada
            </span>
          </button>
        ) : null}

        {/* A CONTA, separada do argumento: é a única frase da loja que pede
            para ser conferida, e ela não depende de adjetivo nenhum para
            funcionar. Só aparece para quem ainda não tem os direitos. */}
        {contaDoPacote && !mentisIlimitada ? (
          <div
            className="mt-3 rounded-2xl border-2 border-white/10 p-4 text-sm text-white/60"
            data-testid="sparks-conta-do-pacote"
          >
            <span className="secao-olho">A conta</span>
            <div className="mt-1.5 leading-relaxed">
              Comprando avulso: {contaDoPacote.partes.join(" + ")} ={" "}
              <strong className="font-semibold text-white/90">{contaDoPacote.total} Sparks</strong>.
              O pacote de {pacoteIlimitado ? formatBRL(pacoteIlimitado.price_cents) : "cima"} inclui
              tudo isso <em className="not-italic text-white/80">e</em> credita{" "}
              {contaDoPacote.sparksDoPacote} Sparks no seu saldo.
            </div>
          </div>
        ) : null}

        {/* O jeito de conseguir Sparks sem pagar. Ficava ANTES da grade; desde
            2026-10-19 a loja abre nos pacotes (pedido do dono), e indicar vem
            logo depois da compra. `/indicar` continua caindo aqui pela âncora.
            A condição ("na primeira compra dele") vem na mesma frase da
            promessa: sem ela, a linha vira propaganda. */}
        <section id={ANCORAS.SPARKS_INDICAR} className="mt-12 scroll-mt-24" data-testid="sparks-indicar">
          <div className="flex items-center gap-2">
            <Gift className="h-[18px] w-[18px] shrink-0 text-sapiens-accent" />
            <h2 className="font-display text-xl font-bold tracking-tight text-white">
              Indique um amigo e ganhe Sparks
            </h2>
          </div>
          <p className="mt-1.5 max-w-2xl text-sm text-white/55">
            Ele cria a conta com o seu código; na primeira compra dele, metade dos Sparks
            daquele pacote cai no seu saldo.
          </p>
          <div className="mt-5">
            <Indicacao />
          </div>
        </section>

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
                onClick={() => comprarComPix(pacoteTeste)}
                className="text-[11px] text-white/30 hover:text-white/60 underline"
                data-testid="sparks-buy-spark_test_15"
              >
                [teste interno] R$ 1,00 → 15 Sparks
              </button>
            </div>
          ) : null;
        })()}
      </>
    </Tela>
  );
}
