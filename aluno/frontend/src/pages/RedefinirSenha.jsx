import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { KeyRound } from "lucide-react";
import { api, errMsg } from "../lib/api";
import BrandMark from "../components/BrandMark";

const MIN_SENHA = 8;

/** Consome o token do e-mail e define a senha nova. O token é de uso único e
 *  trocar a senha derruba todas as sessões abertas — se a conta estava tomada,
 *  é aqui que o acesso do invasor termina. */
export default function RedefinirSenha() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const nav = useNavigate();
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [busy, setBusy] = useState(false);
  const [erro, setErro] = useState(null);

  const submeter = async (e) => {
    e.preventDefault();
    if (senha !== confirmacao) {
      setErro("As duas senhas não são iguais.");
      return;
    }
    setBusy(true);
    setErro(null);
    try {
      await api.post("/auth/password/reset", { token, nova_senha: senha });
      toast.success("Senha redefinida. Faça login com a nova senha.");
      nav("/login", { replace: true });
    } catch (err) {
      setErro(errMsg(err, "Não foi possível redefinir a senha."));
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="card-sapiens rounded-2xl p-8 max-w-sm text-center">
          <div className="font-display text-xl font-bold tracking-tight text-zinc-950">Link incompleto</div>
          <p className="mt-2 text-sm text-zinc-500">
            Este endereço não traz o código de redefinição. Abra o link direto do e-mail que você recebeu.
          </p>
          <Link to="/esqueci-senha" className="pill btn-sapiens mt-6 inline-flex px-5 py-2.5 rounded-full text-sm font-medium">
            Pedir um link novo
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <Link to="/" className="flex items-center justify-center gap-2 font-display text-2xl font-extrabold tracking-tighter text-white">
          <BrandMark className="w-6 h-6" />
          Sapiens
        </Link>

        <div className="card-sapiens rounded-2xl p-8 mt-10">
          <div className="w-11 h-11 rounded-xl bg-sapiens-accentSoft text-sapiens-accentDeep flex items-center justify-center">
            <KeyRound className="w-5 h-5" />
          </div>
          <h1 className="mt-4 font-display text-2xl font-bold tracking-tight text-zinc-950">Criar senha nova</h1>
          <p className="mt-2 text-sm text-zinc-500">
            Mínimo de {MIN_SENHA} caracteres. Ao salvar, você sai de todos os dispositivos conectados.
          </p>

          <form onSubmit={submeter} className="mt-6 space-y-3">
            <input
              required type="password" minLength={MIN_SENHA} value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder={`Nova senha (mín ${MIN_SENHA} caracteres)`}
              className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none"
              data-testid="redefinir-senha"
            />
            <input
              required type="password" minLength={MIN_SENHA} value={confirmacao}
              onChange={(e) => setConfirmacao(e.target.value)}
              placeholder="Repita a nova senha"
              className="w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-sapiens-accent outline-none"
              data-testid="redefinir-senha-confirmacao"
            />
            {erro && <div className="text-sm text-rose-600" data-testid="redefinir-senha-erro">{erro}</div>}
            <button
              type="submit" disabled={busy}
              className="pill btn-sapiens w-full disabled:opacity-60 rounded-full py-3 font-medium"
              data-testid="redefinir-senha-salvar"
            >
              {busy ? "Salvando..." : "Salvar e entrar"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
