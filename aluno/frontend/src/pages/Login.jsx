import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";

export default function Login() {
  const { login, signup, startGoogle } = useAuth();
  const nav = useNavigate();
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await signup(name, email, password);
      toast.success("Bem-vindo ao Sapiens.");
      nav("/dashboard", { replace: true });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Não foi possível entrar.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-2">
      {/* Left brand panel */}
      <div className="hidden md:flex flex-col justify-between p-10 bg-zinc-950 text-white">
        <Link to="/" className="font-display text-2xl font-extrabold tracking-tighter" data-testid="login-brand">
          Sapiens<span className="text-emerald-400">.</span>
        </Link>
        <div>
          <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500">Manifesto</div>
          <p className="mt-4 font-display text-4xl leading-[1.05] tracking-tight">
            Descubra por que você erra.
          </p>
          <p className="mt-4 text-zinc-400 text-sm max-w-md leading-relaxed">
            Você não é uma nota. Você é um conjunto de padrões cognitivos que podemos revelar em minutos.
          </p>
        </div>
        <div className="text-xs text-zinc-500 font-mono-alt tracking-wider">© Sapiens Learning</div>
      </div>

      {/* Right form */}
      <div className="flex items-center justify-center p-6 md:p-10 bg-white">
        <div className="w-full max-w-sm">
          <h1 className="font-display text-3xl font-bold tracking-tight text-zinc-950" data-testid="login-title">
            {mode === "login" ? "Entrar" : "Criar conta"}
          </h1>
          <p className="mt-2 text-sm text-zinc-500">
            {mode === "login" ? "Bem-vindo de volta." : "Sua primeira análise é gratuita."}
          </p>

          <button
            onClick={startGoogle}
            className="pill mt-8 w-full border border-zinc-200 hover:bg-zinc-50 rounded-full px-4 py-3 flex items-center justify-center gap-3 font-medium text-zinc-900"
            data-testid="login-google"
          >
            <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#EA4335" d="M12 10.2v3.9h5.5c-.25 1.5-1.7 4.4-5.5 4.4-3.3 0-6-2.7-6-6.1s2.7-6.1 6-6.1c1.9 0 3.2.8 3.9 1.5l2.7-2.6C16.9 3.6 14.7 2.6 12 2.6 6.9 2.6 2.8 6.7 2.8 11.8S6.9 21 12 21c6.9 0 9.4-4.8 9.4-8.6 0-.6-.1-1-.2-1.5H12z"/></svg>
            Continuar com Google
          </button>

          <div className="my-6 flex items-center gap-3 text-xs text-zinc-400">
            <div className="flex-1 h-px bg-zinc-200" /> ou email <div className="flex-1 h-px bg-zinc-200" />
          </div>

          <form onSubmit={submit} className="space-y-3">
            {mode === "signup" && (
              <input
                required value={name} onChange={(e) => setName(e.target.value)}
                placeholder="Seu nome"
                className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-zinc-900 outline-none"
                data-testid="login-name"
              />
            )}
            <input
              required type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="email@exemplo.com"
              className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-zinc-900 outline-none"
              data-testid="login-email"
            />
            <input
              required type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="Senha (mín 6 caracteres)" minLength={6}
              className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-zinc-900 outline-none"
              data-testid="login-password"
            />
            <button
              type="submit" disabled={busy}
              className="pill w-full bg-zinc-950 hover:bg-zinc-800 disabled:opacity-60 text-white rounded-full py-3 font-medium"
              data-testid="login-submit"
            >
              {busy ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
            </button>
          </form>

          <div className="mt-6 text-sm text-zinc-500 text-center">
            {mode === "login" ? (
              <>Ainda não tem conta? <button className="text-zinc-900 font-medium hover:underline" onClick={() => setMode("signup")} data-testid="login-switch-signup">Criar conta</button></>
            ) : (
              <>Já tem conta? <button className="text-zinc-900 font-medium hover:underline" onClick={() => setMode("login")} data-testid="login-switch-login">Entrar</button></>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
