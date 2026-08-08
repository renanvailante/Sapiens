import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const done = useRef(false);

  useEffect(() => {
    if (done.current) return;
    done.current = true;
    (async () => {
      const hash = window.location.hash || "";
      const match = hash.match(/session_id=([^&]+)/);
      const sid = match ? decodeURIComponent(match[1]) : null;
      if (!sid) return navigate("/login", { replace: true });
      try {
        const { data } = await api.post("/auth/emergent/session", null, {
          headers: { "X-Session-ID": sid },
        });
        localStorage.setItem("sapiens_token", data.token);
        setUser(data.user);
        window.history.replaceState(null, "", "/dashboard");
        navigate("/dashboard", { replace: true, state: { user: data.user } });
      } catch (e) {
        navigate("/login", { replace: true });
      }
    })();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center" data-testid="auth-callback">
      <p className="text-zinc-500 font-medium">Entrando...</p>
    </div>
  );
}
