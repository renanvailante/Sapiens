import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ShieldOff } from "lucide-react";

export default function AdminRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-zinc-200 border-t-zinc-900 animate-spin" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  if (!user.is_admin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 px-6">
        <div className="max-w-sm text-center" data-testid="admin-forbidden">
          <div className="w-14 h-14 mx-auto rounded-full bg-rose-50 flex items-center justify-center">
            <ShieldOff className="w-6 h-6 text-rose-600" />
          </div>
          <div className="mt-6 font-display text-2xl font-bold tracking-tight text-zinc-950">Área restrita</div>
          <p className="mt-2 text-zinc-500 text-sm">Esta seção é acessível apenas por administradores. Peça a um admin para conceder acesso.</p>
        </div>
      </div>
    );
  }
  return children;
}
