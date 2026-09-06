import { Component } from "react";
import { AlertTriangle, RotateCw, LayoutGrid } from "lucide-react";
import { reportarErro } from "../lib/monitoring";

/**
 * Rede de segurança de render. Sem isto, qualquer exceção durante o render
 * derrubava a árvore inteira do React e o aluno ficava com a página EM BRANCO
 * — sem mensagem, sem botão de voltar, sem nenhum sinal chegando até nós.
 *
 * Não substitui tratamento de erro local (uma chamada de API que falha deve
 * mostrar seu próprio estado de erro, ver `useCarregamento`); cobre o que
 * escapou de todo o resto.
 */
// Toda tela lazy-carregada (ver `App.js`) busca seu chunk pelo hash do build
// atual. Um aluno com a aba aberta DE ANTES de um deploy carrega o `main.js`
// velho; ao navegar para uma tela que ainda não tinha aberto, o navegador
// pede o chunk pelo hash velho — que o deploy novo já substituiu — e o
// `import()` dinâmico rejeita. Isso não é um bug de produto, é inerente a
// build com hash de conteúdo; a correção padrão é recarregar a página UMA
// vez (busca o `main.js` novo, com os hashes certos). A guarda em
// `sessionStorage` existe só para nunca virar um loop se o recarregamento
// não resolver por algum outro motivo.
const CHUNK_RELOAD_KEY = "sapiens_chunk_reload_tentado";

function _eErroDeChunk(erro) {
  const msg = String(erro?.message || erro || "");
  return (
    erro?.name === "ChunkLoadError" ||
    /loading chunk [\w.-]+ failed/i.test(msg) ||
    /failed to fetch dynamically imported module/i.test(msg) ||
    /error loading dynamically imported module/i.test(msg)
  );
}

export default class ErrorBoundary extends Component {
  state = { erro: null };

  static getDerivedStateFromError(erro) {
    return { erro };
  }

  componentDidCatch(erro, info) {
    if (_eErroDeChunk(erro)) {
      try {
        if (!sessionStorage.getItem(CHUNK_RELOAD_KEY)) {
          sessionStorage.setItem(CHUNK_RELOAD_KEY, "1");
          window.location.reload();
          return;
        }
      } catch {
        // sessionStorage indisponível (modo privado etc.) — cai no relato normal abaixo.
      }
    }
    reportarErro(erro, { origem: "ErrorBoundary", componente: info?.componentStack });
  }

  render() {
    if (!this.state.erro) return this.props.children;

    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="card-sapiens rounded-2xl p-8 md:p-10 max-w-md text-center" data-testid="error-boundary">
          <div className="w-14 h-14 mx-auto rounded-full bg-amber-50 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6 text-amber-600" />
          </div>
          <div className="mt-6 font-display text-2xl font-bold tracking-tight text-zinc-950">
            Algo quebrou nesta tela
          </div>
          <p className="mt-2 text-sm text-zinc-500 leading-relaxed">
            O erro foi registrado e vamos investigar. Seu progresso está salvo — nada do que você
            respondeu se perdeu.
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <button
              onClick={() => window.location.reload()}
              className="pill btn-sapiens inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium"
              data-testid="error-boundary-reload"
            >
              <RotateCw className="w-4 h-4" /> Tentar de novo
            </button>
            <a
              href="/dashboard"
              className="pill inline-flex items-center gap-2 border border-zinc-200 text-sapiens-navy hover:border-sapiens-accent px-5 py-2.5 rounded-full text-sm font-medium"
              data-testid="error-boundary-home"
            >
              <LayoutGrid className="w-4 h-4" /> Ir para o painel
            </a>
          </div>
        </div>
      </div>
    );
  }
}
