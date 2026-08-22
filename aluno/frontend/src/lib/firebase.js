// Firebase Authentication — apenas login com Google.
//
// A configuração abaixo vem de variáveis REACT_APP_*, que o Create React App
// substitui no bundle em tempo de build. Isso é correto aqui e NÃO é vazamento
// de segredo: a `apiKey` do Firebase Web é um identificador público de projeto,
// não uma credencial. Quem protege o projeto são os **domínios autorizados**
// (configurados no Identity Platform) e as regras de segurança — não o sigilo
// dessa chave, que o Google publica no próprio snippet de instalação.
//
// O que nunca entra aqui: a service account (fica só no backend, e é ela que
// verifica o ID token em /auth/google).
import { initializeApp } from "firebase/app";
import {
  GoogleAuthProvider,
  browserPopupRedirectResolver,
  getAuth,
  signInWithPopup,
} from "firebase/auth";

const config = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
  appId: process.env.REACT_APP_FIREBASE_APP_ID,
};

/** Se a build não recebeu a config, o botão some em vez de falhar no clique. */
export const googleDisponivel = Boolean(config.apiKey && config.authDomain && config.projectId);

let _auth = null;
function auth() {
  if (!_auth) {
    _auth = getAuth(initializeApp(config));
    // Mensagens de erro do Firebase no idioma do navegador.
    _auth.useDeviceLanguage();
  }
  return _auth;
}

/**
 * Abre o popup do Google e devolve o ID token para o backend trocar por sessão.
 *
 * Popup e não redirect: o redirect obriga a página a recarregar e voltar com
 * estado na URL, e em navegadores que bloqueiam cookies de terceiros o retorno
 * do redirect é justamente onde o fluxo costuma quebrar. O popup mantém a SPA
 * viva e o erro, quando ocorre, é local e legível.
 */
export async function entrarComGoogle() {
  const provider = new GoogleAuthProvider();
  // Força a escolha de conta: sem isto, o Google reusa a sessão ativa em
  // silêncio e quem tem duas contas nunca consegue trocar.
  provider.setCustomParameters({ prompt: "select_account" });

  const cred = await signInWithPopup(auth(), provider, browserPopupRedirectResolver);
  return cred.user.getIdToken();
}

/** Traduz os códigos do Firebase para algo que o aluno entenda. */
export function mensagemDeErroGoogle(e) {
  const code = e?.code || "";
  if (code === "auth/popup-closed-by-user" || code === "auth/cancelled-popup-request") return null;
  if (code === "auth/popup-blocked")
    return "Seu navegador bloqueou a janela do Google. Libere os pop-ups para este site e tente de novo.";
  if (code === "auth/unauthorized-domain")
    return "Este domínio não está autorizado no Firebase. Avise o suporte.";
  if (code === "auth/network-request-failed")
    return "Falha de rede ao falar com o Google. Verifique sua conexão.";
  return "Não foi possível entrar com o Google. Tente novamente ou use e-mail e senha.";
}
