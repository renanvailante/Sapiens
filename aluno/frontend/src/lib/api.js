import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

/** FastAPI returns `detail` as a string for HTTPException but as an array of
 *  objects for 422 validation errors — rendering that array directly crashes React. */
export function errMsg(e, fallback = "Algo deu errado.") {
  const detail = e?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail[0]?.msg || fallback;
  return fallback;
}

/**
 * A recusa de cadastro que quase nunca é erro de quem digitou.
 *
 * `/auth/signup` responde 400 com `"Email already registered"` (ver
 * `backend/auth.py`) — em inglês, que era o que o aluno via na cara. E quem
 * bate nisso raramente é alguém se confundindo: é um aluno ANTIGO que voltou
 * pela landing e clicou em "Começar agora", porque é o botão grande e roxo.
 * O caminho de volta existe (o seletor no topo da tela de login), mas exige
 * perceber que a tela inteira é a errada — depois de já ter preenchido nome,
 * WhatsApp e senha. `Login.jsx` usa isto para trocar de tela sozinho.
 *
 * Comparado por trecho e em minúsculas de propósito: o status 400 sozinho não
 * serve (é o genérico de várias recusas do cadastro), e casar a frase inteira
 * quebraria no dia em que alguém acrescentasse um detalhe à mensagem.
 */
export function emailJaTemConta(e) {
  if (e?.response?.status !== 400) return false;
  const detail = e?.response?.data?.detail;
  return typeof detail === "string" && detail.toLowerCase().includes("already registered");
}

// Attach bearer token if present (fallback for cross-domain cookie edge cases)
api.interceptors.request.use((config) => {
  const t = localStorage.getItem("sapiens_token");
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});
