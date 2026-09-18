import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";

/**
 * O portão de toda tela que exige sessão. Ele responde a duas perguntas, nesta
 * ordem: **quem é você** e **dá para falar com você**.
 *
 * A segunda entrou em 2026-09-17. O botão "Continuar com Google" cria conta a
 * partir da aba de LOGIN, onde não existe formulário — o Google devolve nome e
 * e-mail e mais nada, e essas contas nasciam sem telefone. Enquanto havia um
 * cartão no Painel pedindo o número, dava para ignorá-lo para sempre; quando
 * esse cartão saiu, o telefone simplesmente deixou de ser coletado nesse
 * caminho. Agora quem não tem telefone passa por `/completar-cadastro` antes
 * de qualquer outra tela.
 *
 * Vale também para as contas anteriores a 2026-09-15, quando o campo não
 * existia — são justamente os alunos mais antigos, e os que a equipe mais
 * precisa conseguir alcançar.
 */
export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-white/15 border-t-sapiens-accent animate-spin" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  // A própria tela de completar é `ProtectedRoute` (ela precisa da sessão),
  // então sem esta guarda o redirecionamento cairia em laço sobre si mesmo.
  if (!user.whatsapp && location.pathname !== "/completar-cadastro") {
    return <Navigate to="/completar-cadastro" replace />;
  }
  return children;
}
