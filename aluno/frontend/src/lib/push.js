/**
 * NOTIFICAÇÃO NO CELULAR — o lado do navegador.
 *
 * O servidor guarda o aparelho e decide o que mandar (`push_service.py`); aqui
 * fica o que só o navegador sabe: se este aparelho consegue receber, se o
 * aluno já deu permissão, e a inscrição em si.
 *
 * Duas regras de quando PERGUNTAR, as duas do dono do produto:
 *
 *  · **nunca no primeiro acesso.** O pedido só aparece depois do primeiro
 *    fechamento de série — quando o aluno já viu o que o produto faz e a
 *    pergunta ("quer que eu te avise quando seus trechos voltarem?") fala de
 *    algo que ele acabou de usar. Um pedido de permissão na porta de entrada é
 *    recusado por reflexo, e a recusa no navegador é quase irreversível;
 *  · **e uma vez só.** Quem disse "agora não" não é perguntado de novo; o
 *    interruptor do Menu continua lá para quem mudar de ideia.
 *
 * iPhone: o Safari só entrega push para o app INSTALADO na tela de início
 * (iOS 16.4+). No navegador comum a API nem existe — então a situação é
 * "precisa instalar", e a tela explica isso com o passo a passo do
 * `InstalarApp`, em vez de mostrar um botão que não faz nada.
 */
import { api } from "./api";

export const CHAVE_PERGUNTADO = "sapiens_push_perguntado";

function lerPerguntado() {
  try {
    return localStorage.getItem(CHAVE_PERGUNTADO) === "1";
  } catch {
    return false;
  }
}

export function marcarPerguntado() {
  try {
    localStorage.setItem(CHAVE_PERGUNTADO, "1");
  } catch {
    /* modo privado: perguntar de novo amanhã é o pior que acontece */
  }
}

/** O que este aparelho consegue, hoje. Pura sobre o que o chamador mediu. */
export function situacaoDoPush({ suporte, plataforma, instalado, permissao }) {
  if (plataforma === "ios" && !instalado) return "precisa_instalar";
  if (!suporte) return "indisponivel";
  if (permissao === "denied") return "bloqueado";
  if (permissao === "granted") return "permitido";
  return "pode_pedir";
}

/** Se o pedido do fim da série deve aparecer. */
export function devePerguntar({ situacao, jaPerguntado, inscrito, respondeuNaSerie }) {
  if (!respondeuNaSerie || jaPerguntado || inscrito) return false;
  return situacao === "pode_pedir" || situacao === "precisa_instalar" || situacao === "permitido";
}

export function medirAparelho(plataforma, instalado) {
  const suporte =
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window;
  const permissao = suporte ? Notification.permission : "default";
  return { suporte, plataforma, instalado, permissao, situacao: situacaoDoPush({ suporte, plataforma, instalado, permissao }) };
}

export const jaPerguntado = lerPerguntado;

function base64UrlParaBytes(base64) {
  const preenchido = (base64 + "=".repeat((4 - (base64.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  const bruto = atob(preenchido);
  return Uint8Array.from(bruto, (c) => c.charCodeAt(0));
}

async function registro() {
  // O service worker só é registrado em produção (`src/index.js`); fora dela,
  // `ready` nunca resolve. O teto devolve o controle à tela.
  return Promise.race([
    navigator.serviceWorker.ready,
    new Promise((_, rejeitar) => setTimeout(() => rejeitar(new Error("sem service worker")), 6000)),
  ]);
}

export async function inscricaoAtual() {
  try {
    if (!("serviceWorker" in navigator)) return null;
    const reg = await registro();
    return (await reg.pushManager.getSubscription()) || null;
  } catch {
    return null;
  }
}

/** Pede a permissão (se ainda não houver), inscreve e entrega ao servidor.
 *  Devolve `"ativo"`, `"recusado"` ou lança com a mensagem para a tela. */
export async function ligarNotificacoes() {
  marcarPerguntado();
  const permissao = Notification.permission === "granted" ? "granted" : await Notification.requestPermission();
  if (permissao !== "granted") return "recusado";
  const { data } = await api.get("/push/chave");
  if (!data?.disponivel || !data?.chave_publica) throw new Error("As notificações não estão disponíveis agora.");
  const reg = await registro();
  let inscricao = await reg.pushManager.getSubscription();
  if (!inscricao) {
    inscricao = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: base64UrlParaBytes(data.chave_publica),
    });
  }
  const json = inscricao.toJSON();
  await api.post("/push/inscrever", { endpoint: json.endpoint, keys: json.keys });
  return "ativo";
}

export async function desligarNotificacoes() {
  const inscricao = await inscricaoAtual();
  if (!inscricao) return;
  // O servidor primeiro: se a rede cair no meio, o pior caso é o aparelho
  // continuar inscrito sem o servidor saber dele — ninguém recebe nada.
  await api.post("/push/desinscrever", { endpoint: inscricao.endpoint }).catch(() => {});
  await inscricao.unsubscribe().catch(() => {});
}
