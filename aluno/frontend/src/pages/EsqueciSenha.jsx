import { useState } from "react";
import { Link } from "react-router-dom";
import { MailCheck, ArrowLeft } from "lucide-react";
import { api, errMsg } from "../lib/api";
import BrandMark from "../components/BrandMark";

/**
 * Pedido de redefinição de senha.
 *
 * A tela mostra SEMPRE a mesma confirmação, exista ou não a conta — o backend
 * responde igual pelo mesmo motivo: dizer "e-mail não encontrado"
 * transformaria isto num verificador de quem estuda aqui, ou seja, numa lista
 * de menores de idade para quem quisesse coletá-la.
 */
export default function EsqueciSenha() {
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [busy, setBusy] = useState(false);
  const [erro, setErro] = useState(null);

  const enviar = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErro(null);
    try {
      await api.post("/auth/password/forgot", { email });
      setEnviado(true);
    } catch (err) {
      setErro(errMsg(err, "Não foi possível enviar agora. Tente de novo em alguns minutos."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <Link to="/" className="flex items-center justify-center gap-2 font-display text-2xl font-extrabold tracking-tighter text-white">
          <BrandMark className="w-6 h-6" />
          Sapiens
        </Link>

        <div className="card-sapiens rounded-2xl p-8 mt-10">
          {enviado ? (
            <div className="text-center" data-testid="esqueci-senha-enviado">
              <div className="w-12 h-12 mx-auto rounded-full bg-emerald-50 flex items-center justify-center">
                <MailCheck className="w-5 h-5 text-emerald-600" />
              </div>
              <div className="mt-5 font-display text-xl font-bold tracking-tight text-zinc-950">
                Confira seu e-mail
              </div>
              <p className="mt-2 text-sm text-zinc-500 leading-relaxed">
                Se houver uma conta com <strong className="text-zinc-700">{email}</strong>, enviamos
                um link para criar uma senha nova. Ele vale por 30 minutos.
              </p>
              <p className="mt-3 text-xs text-zinc-400">
                Não chegou? Confira a caixa de spam antes de pedir outro.
              </p>
            </div>
          ) : (
            <>
              <h1 className="font-display text-2xl font-bold tracking-tight text-zinc-950">
                Esqueceu a senha?
              </h1>
              <p className="mt-2 text-sm text-zinc-500">
                Informe o e-mail da sua conta e enviamos um link para criar uma nova.
              </p>

              <form onSubmit={enviar} className="mt-6 space-y-3">
                <input
                  required type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  placeholder="email@exemplo.com"
                  className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none"
                  data-testid="esqueci-senha-email"
                />
                {erro && <div className="text-sm text-rose-600">{erro}</div>}
                <button
                  type="submit" disabled={busy}
                  className="pill btn-sapiens w-full disabled:opacity-60 rounded-full py-3 font-medium"
                  data-testid="esqueci-senha-enviar"
                >
                  {busy ? "Enviando..." : "Enviar link"}
                </button>
              </form>
            </>
          )}

          <Link to="/login" className="mt-6 inline-flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-900">
            <ArrowLeft className="w-4 h-4" /> Voltar para o login
          </Link>
        </div>
      </div>
    </div>
  );
}
