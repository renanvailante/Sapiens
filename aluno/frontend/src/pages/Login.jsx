import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { errMsg } from "../lib/api";
import { googleDisponivel, mensagemDeErroGoogle } from "../lib/firebase";
import { toast } from "sonner";
import BrandMark from "../components/BrandMark";

export default function Login() {
  const { login, signup, loginGoogle } = useAuth();
  const nav = useNavigate();
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [promoCode, setPromoCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyGoogle, setBusyGoogle] = useState(false);
  const [aceitouTermos, setAceitouTermos] = useState(false);

  const comGoogle = async () => {
    setBusyGoogle(true);
    try {
      await loginGoogle(
        mode === "signup" ? promoCode : undefined,
        mode === "signup" ? whatsapp : undefined,
      );
      nav("/dashboard");
    } catch (e) {
      // Fechar o popup não é erro: `mensagemDeErroGoogle` devolve null nesse
      // caso, e um toast ali seria ruído sobre uma ação deliberada.
      const doFirebase = mensagemDeErroGoogle(e);
      if (doFirebase !== null) toast.error(doFirebase || errMsg(e));
      else if (e?.response) toast.error(errMsg(e));
    } finally {
      setBusyGoogle(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (mode === "signup" && !whatsapp.trim()) {
      toast.error("Informe seu WhatsApp — é por ele que a gente te avisa da aula ao vivo.");
      return;
    }
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await signup(name, email, password, whatsapp, promoCode);
      toast.success("Bem-vindo ao Sapiens.");
      nav("/dashboard", { replace: true });
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível entrar."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-2">
      {/* Left brand panel */}
      <div className="hidden md:flex flex-col justify-between p-10 exam-shell text-white">
        <Link to="/" className="flex items-center gap-2 font-display text-2xl font-extrabold tracking-tighter" data-testid="login-brand">
          <BrandMark className="w-6 h-6" />
          Sapiens
        </Link>
        <div>
          <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50">Manifesto</div>
          <p className="mt-4 font-display text-4xl leading-[1.05] tracking-tight">
            Descubra por que você erra.
          </p>
          <p className="mt-4 text-white/60 text-sm max-w-md leading-relaxed">
            Você não é uma nota. Você é um conjunto de padrões cognitivos que podemos revelar em minutos.
          </p>
        </div>
        <div className="text-xs text-white/50 font-mono-alt tracking-wider">© Sapiens Learning</div>
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

          {/* O cupom fica ACIMA do botão do Google, e não no meio do formulário
              de e-mail: ele vale para os DOIS caminhos de cadastro (o backend
              aceita `promo_code` no signup por e-mail e no primeiro login pelo
              Google), mas embaixo do botão ninguém que entra pelo Google
              chegava a vê-lo — e o código trocaria o bônus padrão de 100
              Sparks pelo valor programado. */}
          {/* WhatsApp: pedido ANTES do botão do Google, pelo mesmo motivo do
              cupom — ele vale para os DOIS caminhos de cadastro, e embaixo do
              formulário de e-mail quem entra pelo Google nunca chegaria a
              vê-lo. É o único canal em que a equipe alcança o aluno de
              verdade, e é por ele que o link da aula ao vivo de quinta chega
              a quem pagou.

              A obrigatoriedade é checada à mão em `submit` (o campo mora fora
              do `<form>`, então o `required` do HTML não o alcançaria) e o
              backend recusa o cadastro por e-mail sem número, de qualquer
              forma. Pelo Google ele é opcional: o botão também cria conta a
              partir da tela de LOGIN, onde não há formulário nenhum. */}
          {mode === "signup" && (
            <div className="mt-8">
              <label className="text-xs font-medium text-zinc-500 mb-1.5 block" htmlFor="login-whatsapp">
                Seu WhatsApp
              </label>
              <input
                id="login-whatsapp"
                type="tel" inputMode="tel"
                value={whatsapp} onChange={(e) => setWhatsapp(e.target.value)}
                placeholder="(11) 91234-5678"
                className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none"
                data-testid="login-whatsapp"
              />
              <p className="mt-1.5 text-xs text-zinc-400 leading-relaxed">
                É por aqui que enviamos o link da{" "}
                <strong className="font-medium text-zinc-500">
                  aula ao vivo de quinta-feira com o 1º colocado de Medicina da USP
                </strong>{" "}
                e os avisos de turma.
              </p>
            </div>
          )}

          {mode === "signup" && (
            <div className="mt-5">
              <label className="text-xs font-medium text-zinc-500 mb-1.5 block" htmlFor="login-promo-code">
                Tem um código de promoção?
              </label>
              <input
                id="login-promo-code"
                value={promoCode} onChange={(e) => setPromoCode(e.target.value)}
                placeholder="Opcional — vale para os dois jeitos de entrar"
                className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none"
                data-testid="login-promo-code"
              />
            </div>
          )}

          {googleDisponivel && (
            <>
              <button
                type="button"
                onClick={comGoogle}
                disabled={busyGoogle || busy}
                className={`pill w-full border border-zinc-200 hover:bg-zinc-50 disabled:opacity-50 rounded-full px-4 py-3 flex items-center justify-center gap-3 font-medium text-zinc-900 ${mode === "signup" ? "mt-4" : "mt-8"}`}
                data-testid="login-google"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="#EA4335" d="M12 10.2v3.9h5.5c-.25 1.5-1.7 4.4-5.5 4.4-3.3 0-6-2.7-6-6.1s2.7-6.1 6-6.1c1.9 0 3.2.8 3.9 1.5l2.7-2.6C16.9 3.6 14.7 2.6 12 2.6 6.9 2.6 2.8 6.7 2.8 11.8S6.9 21 12 21c6.9 0 9.4-4.8 9.4-8.6 0-.6-.1-1-.2-1.5H12z"/></svg>
                {busyGoogle ? "Abrindo o Google…" : "Continuar com Google"}
              </button>

              <div className="my-6 flex items-center gap-3 text-xs text-zinc-400">
                <div className="flex-1 h-px bg-zinc-200" /> ou email <div className="flex-1 h-px bg-zinc-200" />
              </div>
            </>
          )}
          {!googleDisponivel && <div className="mt-8" />}

          <form onSubmit={submit} className="space-y-3">
            {mode === "signup" && (
              <input
                required value={name} onChange={(e) => setName(e.target.value)}
                placeholder="Seu nome"
                className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none"
                data-testid="login-name"
              />
            )}
            <input
              required type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="email@exemplo.com"
              className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none"
              data-testid="login-email"
            />
            <input
              required type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === "signup" ? "Senha (mín 8 caracteres)" : "Sua senha"}
              minLength={mode === "signup" ? 8 : undefined}
              className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none"
              data-testid="login-password"
            />
            {mode === "signup" && (
              <label className="flex items-start gap-2.5 pt-1 text-xs text-zinc-500 leading-relaxed cursor-pointer">
                <input
                  type="checkbox"
                  required
                  checked={aceitouTermos}
                  onChange={(e) => setAceitouTermos(e.target.checked)}
                  className="mt-0.5 w-5 h-5 rounded border-zinc-300 accent-sapiens-accent shrink-0"
                  data-testid="login-aceite-termos"
                />
                <span>
                  Li e aceito os <Link to="/termos" target="_blank" className="text-zinc-900 underline">Termos de Uso</Link>{" "}
                  e a <Link to="/privacidade" target="_blank" className="text-zinc-900 underline">Política de Privacidade</Link>.
                  Se eu tiver menos de 18 anos, confirmo ter autorização do meu responsável.
                </span>
              </label>
            )}
            <button
              type="submit" disabled={busy || (mode === "signup" && !aceitouTermos)}
              className="pill btn-sapiens w-full disabled:opacity-60 rounded-full py-3 font-medium"
              data-testid="login-submit"
            >
              {busy ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
            </button>
          </form>

          {mode === "login" && (
            <div className="mt-3 text-center">
              <Link to="/esqueci-senha" className="inline-block py-2.5 text-sm text-zinc-500 hover:text-zinc-900 hover:underline" data-testid="login-esqueci-senha">
                Esqueci minha senha
              </Link>
            </div>
          )}

          <div className="mt-6 text-sm text-zinc-500 text-center">
            {mode === "login" ? (
              <>Ainda não tem conta? <button className="inline-block px-2 py-2.5 text-zinc-900 font-medium hover:underline" onClick={() => setMode("signup")} data-testid="login-switch-signup">Criar conta</button></>
            ) : (
              <>Já tem conta? <button className="inline-block px-2 py-2.5 text-zinc-900 font-medium hover:underline" onClick={() => setMode("login")} data-testid="login-switch-login">Entrar</button></>
            )}
          </div>

          <div className="mt-8 pt-6 border-t border-zinc-100 text-center text-xs text-zinc-400">
            <Link to="/termos" className="inline-block py-2.5 hover:text-zinc-600 hover:underline">Termos de Uso</Link>
            <span className="mx-2">·</span>
            <Link to="/privacidade" className="inline-block py-2.5 hover:text-zinc-600 hover:underline">Privacidade</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
