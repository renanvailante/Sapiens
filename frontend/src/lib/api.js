import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

// Attach bearer token if present (fallback for cross-domain cookie edge cases)
api.interceptors.request.use((config) => {
  const t = localStorage.getItem("sapiens_token");
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});
