import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { useAuth } from "../lib/auth";
import BrandMark from "../components/BrandMark";

/**
 * 404 de verdade. A rota curinga renderizava a Landing: um link com erro de
 * digitação, uma rota antiga compartilhada por um aluno ou uma análise apagada
 * jogavam a pessoa na página de marketing sem dizer que a página não existe —
 * inclusive quando ela já estava logada.
 */
export default function NaoEncontrada() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="max-w-md text-center">
        <div className="flex items-center justify-center gap-2 font-display text-2xl font-extrabold tracking-tighter text-white">
          <BrandMark className="w-6 h-6" />
          Sapiens
        </div>
        <div className="mt-10 font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50">Erro 404</div>
        <h1 className="mt-4 font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white leading-tight">
          Esta página não existe.
        </h1>
        <p className="mt-4 text-white/60 leading-relaxed">
          O endereço pode ter mudado, ou o link que você abriu está incompleto. Seu progresso
          continua salvo — nada aqui tem a ver com as suas respostas.
        </p>
        <Link
          to={user ? "/dashboard" : "/"}
          className="pill btn-sapiens mt-8 inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-medium"
          data-testid="404-voltar"
        >
          <Compass className="w-4 h-4" /> {user ? "Ir para o painel" : "Voltar ao início"}
        </Link>
      </div>
    </div>
  );
}
