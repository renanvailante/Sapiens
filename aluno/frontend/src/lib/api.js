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

// Attach bearer token if present (fallback for cross-domain cookie edge cases)
api.interceptors.request.use((config) => {
  const t = localStorage.getItem("sapiens_token");
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});
