import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": process.env.REACT_APP_PIPELINE_API_KEY || "",
  },
});

export default api;
