/**
 * Relato de erros do frontend.
 *
 * Não havia nenhum: uma tela branca só chegava até a equipe se o aluno tivesse
 * disposição de avisar — e num beta a maioria desiste em silêncio.
 *
 * O destino é o próprio backend (`POST /api/client-errors`), não um serviço
 * externo: os dados já estão lá, é um endpoint pequeno, e não acrescenta
 * fornecedor nem contrato de privacidade novo a um produto que atende menores
 * de idade. Se um dia entrar Sentry, `reportarErro` é o único ponto a mudar.
 *
 * Nunca quebra a página: qualquer falha ao relatar é engolida de propósito —
 * um erro dentro do relator de erros não pode virar o erro visível.
 */
import { api } from "./api";

// Um erro em laço (render que falha, refaz e falha de novo) não pode virar
// centenas de requisições. Guarda a assinatura do que já foi relatado nesta
// sessão de página.
const jaRelatados = new Set();
const MAX_POR_SESSAO = 20;

function assinatura(mensagem, stack) {
  return `${mensagem}::${(stack || "").slice(0, 200)}`;
}

export function reportarErro(erro, contexto = {}) {
  try {
    const mensagem = erro?.message || String(erro || "erro desconhecido");
    const stack = erro?.stack || "";
    const chave = assinatura(mensagem, stack);
    if (jaRelatados.has(chave) || jaRelatados.size >= MAX_POR_SESSAO) return;
    jaRelatados.add(chave);

    api
      .post("/client-errors", {
        mensagem: mensagem.slice(0, 500),
        stack: stack.slice(0, 4000),
        rota: window.location.pathname,
        user_agent: navigator.userAgent?.slice(0, 300),
        contexto,
      })
      .catch(() => {});
  } catch {
    // Ver o comentário do topo: relator de erros não levanta erro.
  }
}

/**
 * Captura o que escapa de todo tratamento local: exceção solta e promise
 * rejeitada sem `.catch`. Chamado uma vez, em `index.js`.
 */
export function instalarCapturaGlobal() {
  window.addEventListener("error", (evento) => {
    reportarErro(evento.error || evento.message, { origem: "window.onerror" });
  });
  window.addEventListener("unhandledrejection", (evento) => {
    reportarErro(evento.reason, { origem: "unhandledrejection" });
  });
}
