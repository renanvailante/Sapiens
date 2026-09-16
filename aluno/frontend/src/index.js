import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@/index.css";
import "katex/dist/katex.min.css";
import App from "@/App";
import { instalarCapturaGlobal } from "@/lib/monitoring";

// Captura o que escapa de todo tratamento local. Sem isto, uma tela branca
// só chegava à equipe se o aluno avisasse.
instalarCapturaGlobal();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

// Service worker: registrado SÓ para tornar o app instalável (Android,
// Windows, macOS — ver `public/sw.js` e `components/InstalarApp.jsx`). Ele não
// guarda nada em cache de propósito, então não há risco de aluno preso numa
// versão antiga do bundle depois de um deploy.
//
// Fora de produção não registra: em `npm start` o service worker interceptaria
// o servidor de desenvolvimento sem ganho nenhum.
if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Falhar aqui só significa que o botão de instalar nativo não aparece;
      // o passo a passo manual continua valendo. Nada do produto depende disto.
    });
  });
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
