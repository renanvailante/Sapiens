import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";

/**
 * O portão de toda tela que exige sessão: **quem é você**.
 *
 * De 2026-09-17 a 2026-10-22 ele respondia uma segunda pergunta — "dá para
 * falar com você?" — e mandava todo aluno sem WhatsApp para
 * `/completar-cadastro` antes de qualquer tela. Com o número fora do cadastro
 * (ver o cabeçalho de `pages/Login.jsx`), esse portão seria o mesmo pedido de
 * antes, só que uma tela depois. O número agora é pedido onde o motivo está à
 * vista: no fim do plano (`/bem-vindo`) e na compra da aula ao vivo.
 * `/completar-cadastro` continua existindo como tela, sem ninguém empurrado
 * para ela.
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
  return children;
}
