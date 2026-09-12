import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Download, Loader2, Trash2, AlertTriangle } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../lib/auth";

/**
 * Exercício dos direitos do titular (LGPD art. 18) dentro da própria Política
 * de Privacidade — que é onde o aluno lê que tem esses direitos.
 *
 * Antes daqui, o texto prometia cópia, exclusão e portabilidade em 15 dias e a
 * única forma de pedir era escrever um e-mail que alguém teria de atender à
 * mão, varrendo vinte coleções. O canal por e-mail continua valendo (é o
 * caminho do responsável, que não tem a conta do filho) — mas quem está
 * logado resolve aqui.
 *
 * A exclusão exige a palavra digitada, e a senha quando a conta tem senha.
 * Não é atrito decorativo: é uma ação sem volta, e um clique errado ou um
 * link malicioso não podem bastar.
 */
export default function MeusDadosLGPD() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [baixando, setBaixando] = useState(false);
  const [abrirExclusao, setAbrirExclusao] = useState(false);
  const [palavra, setPalavra] = useState("");
  const [senha, setSenha] = useState("");
  const [excluindo, setExcluindo] = useState(false);

  if (!user) {
    return (
      <div className="mt-4 rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-600">
        <Link to="/login" className="text-sapiens-accentDeep hover:underline">Entre na sua conta</Link>{" "}
        para baixar seus dados ou excluir sua conta aqui mesmo. Se você é responsável por um
        estudante menor de idade, use o e-mail acima — respondemos em até 15 dias.
      </div>
    );
  }

  const precisaSenha = user.provider === "email";

  async function baixar() {
    setBaixando(true);
    try {
      const { data } = await api.get("/me/dados");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sapiens-meus-dados-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Seus dados foram baixados.");
    } catch (e) {
      toast.error(errMsg(e, "Não consegui montar sua cópia agora. Tente de novo em alguns minutos."));
    } finally {
      setBaixando(false);
    }
  }

  async function excluir() {
    setExcluindo(true);
    try {
      await api.post("/me/conta/excluir", {
        confirmacao: palavra.trim(),
        senha: precisaSenha ? senha : null,
      });
      toast.success("Sua conta foi excluída.");
      await logout();
      navigate("/");
    } catch (e) {
      toast.error(errMsg(e, "Não consegui excluir a conta."));
      setExcluindo(false);
    }
  }

  const podeExcluir = palavra.trim() === "EXCLUIR" && (!precisaSenha || senha.length > 0);

  return (
    <div className="mt-4 space-y-3" data-testid="lgpd-meus-dados">
      <button
        type="button"
        onClick={baixar}
        disabled={baixando}
        data-testid="lgpd-baixar"
        className="inline-flex items-center gap-2 rounded-xl border border-zinc-300 px-4 py-2.5 text-sm font-medium text-zinc-800 transition hover:bg-zinc-50 disabled:opacity-60"
      >
        {baixando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
        Baixar uma cópia dos meus dados
      </button>

      {!abrirExclusao ? (
        <div>
          <button
            type="button"
            onClick={() => setAbrirExclusao(true)}
            data-testid="lgpd-abrir-exclusao"
            className="inline-flex items-center gap-2 rounded-xl border border-red-200 px-4 py-2.5 text-sm font-medium text-red-700 transition hover:bg-red-50"
          >
            <Trash2 className="w-4 h-4" /> Excluir minha conta
          </button>
        </div>
      ) : (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4" data-testid="lgpd-painel-exclusao">
          <div className="flex gap-2.5">
            <AlertTriangle className="w-5 h-5 shrink-0 text-red-600 mt-0.5" />
            <div className="text-sm text-red-900">
              <strong>Isto não tem volta.</strong> Apagamos seu cadastro, seu histórico de estudo,
              suas redações e o seu saldo de Sparks — inclusive Sparks comprados, que não são
              reembolsados. Seus registros de pagamento continuam guardados por obrigação legal,
              mas desligados do seu nome.
            </div>
          </div>

          <label className="mt-4 block text-sm">
            <span className="text-red-900">Digite <strong>EXCLUIR</strong> para confirmar</span>
            <input
              value={palavra}
              onChange={(e) => setPalavra(e.target.value)}
              data-testid="lgpd-palavra"
              className="mt-1.5 w-full rounded-lg border border-red-300 bg-white px-3 py-2 text-zinc-900 outline-none focus:border-red-500"
              placeholder="EXCLUIR"
              autoComplete="off"
            />
          </label>

          {precisaSenha && (
            <label className="mt-3 block text-sm">
              <span className="text-red-900">Sua senha</span>
              <input
                type="password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                data-testid="lgpd-senha"
                className="mt-1.5 w-full rounded-lg border border-red-300 bg-white px-3 py-2 text-zinc-900 outline-none focus:border-red-500"
                autoComplete="current-password"
              />
            </label>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={excluir}
              disabled={!podeExcluir || excluindo}
              data-testid="lgpd-confirmar"
              className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
            >
              {excluindo ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              Excluir definitivamente
            </button>
            <button
              type="button"
              onClick={() => { setAbrirExclusao(false); setPalavra(""); setSenha(""); }}
              className="rounded-xl border border-zinc-300 bg-white px-4 py-2.5 text-sm font-medium text-zinc-700 transition hover:bg-zinc-50"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
