import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2, MessageCircleMore, Check } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../lib/auth";
import Logo from "../components/Logo";

/**
 * `/completar-cadastro` — a segunda metade do cadastro de quem entrou pelo
 * Google.
 *
 * **O buraco que ela fecha.** O botão "Continuar com Google" também cria conta
 * a partir da aba de LOGIN, onde não existe formulário nenhum: o Google
 * devolve nome e e-mail verificados, e mais nada. Essas contas nasciam sem
 * telefone e ficavam permanentemente fora do alcance da equipe — e desde
 * 2026-09-17, quando os cartões que pediam o número depois saíram das telas,
 * não havia mais nenhuma porta por onde ele entrasse.
 *
 * O e-mail já vem do Google, verificado. O que falta é o telefone, e é só isso
 * que esta tela pede — mais o responsável, quando o aluno se declara menor de
 * idade, pela mesma razão do cadastro por e-mail (LGPD art. 14).
 *
 * **Por que uma TELA e não um cartão dispensável.** Um cartão no Painel é
 * ignorável para sempre, e foi exatamente o que aconteceu com o anterior. Esta
 * tela é um portão: `ProtectedRoute` manda para cá todo mundo que não tem
 * telefone. Não tem "depois" — mas também não tem nada além de um campo, e o
 * texto diz por que ele é pedido em vez de mandar preencher.
 *
 * **Sair continua funcionando.** Um portão sem saída prende quem abriu a conta
 * por engano; o botão de sair fica aqui embaixo, visível.
 */
const CAMPO =
  "w-full rounded-xl border border-white/12 bg-white/[0.04] px-4 py-3 text-sm text-white " +
  "outline-none transition-colors placeholder:text-white/30 focus:border-[#4FD9FF]/55";

export default function CompletarCadastro() {
  const { user, refresh, logout } = useAuth();
  const nav = useNavigate();
  const [whatsapp, setWhatsapp] = useState("");
  const [menorDeIdade, setMenorDeIdade] = useState(false);
  const [responsavelNome, setResponsavelNome] = useState("");
  const [responsavelWhatsapp, setResponsavelWhatsapp] = useState("");
  const [salvando, setSalvando] = useState(false);

  const faltaResponsavel =
    menorDeIdade && !(responsavelNome.trim() && responsavelWhatsapp.trim());

  const salvar = async (e) => {
    e.preventDefault();
    if (!whatsapp.trim() || faltaResponsavel) return;
    setSalvando(true);
    try {
      await api.post("/auth/whatsapp", {
        whatsapp: whatsapp.trim(),
        menor_de_idade: menorDeIdade,
        responsavel_nome: responsavelNome.trim() || undefined,
        responsavel_whatsapp: responsavelWhatsapp.trim() || undefined,
      });
      // Relê a sessão: é o que abre o portão em `ProtectedRoute`. Sem isto o
      // `user` em memória continua sem telefone e a navegação volta para cá.
      await refresh();
      toast.success("Pronto. Bons estudos.");
      nav("/dashboard", { replace: true });
    } catch (err) {
      toast.error(errMsg(err, "Não consegui salvar seu WhatsApp."));
    } finally {
      setSalvando(false);
    }
  };

  const sair = async () => { await logout(); nav("/"); };

  return (
    <div className="exam-shell flex min-h-screen flex-col items-center justify-center p-5">
      <div className="card-sapiens w-full max-w-[26rem] rounded-[28px] p-6 sm:p-8">
        <Logo tamanho="m" testid="completar-brand" />

        <div className="mt-6 flex h-11 w-11 items-center justify-center rounded-2xl border border-[#4FD9FF]/30 bg-[#4FD9FF]/15 text-[#7FD8FF]">
          <MessageCircleMore className="h-5 w-5" strokeWidth={1.8} />
        </div>

        <h1 className="titulo-tela mt-4" data-testid="completar-title">
          Falta uma coisa só.
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-white/55">
          {user?.name ? `${user.name.split(" ")[0]}, o ` : "O "}seu e-mail já veio do Google
          {user?.email && <> (<strong className="text-white/75">{user.email}</strong>)</>}.
          Falta o WhatsApp — é por ele que a equipe fala com você: link de aula, aviso de
          turma e suporte.
        </p>

        <form onSubmit={salvar} className="mt-6 space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-white/55" htmlFor="completar-whatsapp">
              Seu WhatsApp
            </label>
            <input
              id="completar-whatsapp"
              required
              autoFocus
              type="tel"
              inputMode="tel"
              value={whatsapp}
              onChange={(e) => setWhatsapp(e.target.value)}
              placeholder="(11) 91234-5678"
              className={CAMPO}
              data-testid="completar-whatsapp"
            />
          </div>

          <label className="flex cursor-pointer items-center gap-2.5 text-sm text-white/65">
            <input
              type="checkbox"
              checked={menorDeIdade}
              onChange={(e) => setMenorDeIdade(e.target.checked)}
              className="h-5 w-5 shrink-0 rounded border-white/20 accent-[#4FD9FF]"
              data-testid="completar-menor"
            />
            Tenho menos de 18 anos
          </label>

          {menorDeIdade && (
            <div
              className="space-y-3 rounded-2xl border border-[#4FD9FF]/25 bg-[#4FD9FF]/[0.06] p-4"
              data-testid="completar-responsavel"
            >
              <p className="text-xs leading-relaxed text-white/55">
                Precisamos de um responsável por você. É com ele que falamos sobre cobrança
                e sobre os seus dados.
              </p>
              <input
                value={responsavelNome}
                onChange={(e) => setResponsavelNome(e.target.value)}
                placeholder="Nome do responsável"
                className={CAMPO}
                data-testid="completar-responsavel-nome"
              />
              <input
                type="tel"
                inputMode="tel"
                value={responsavelWhatsapp}
                onChange={(e) => setResponsavelWhatsapp(e.target.value)}
                placeholder="WhatsApp do responsável"
                className={CAMPO}
                data-testid="completar-responsavel-whatsapp"
              />
            </div>
          )}

          <button
            type="submit"
            disabled={salvando || !whatsapp.trim() || faltaResponsavel}
            className="pill btn-sapiens flex w-full items-center justify-center gap-2 rounded-full py-3.5 text-sm font-bold disabled:opacity-60"
            data-testid="completar-salvar"
          >
            {salvando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            {salvando ? "Salvando…" : "Entrar no Sapiens"}
          </button>
        </form>

        <button
          onClick={sair}
          className="mt-4 w-full py-2 text-center text-xs text-white/35 hover:text-white/70"
          data-testid="completar-sair"
        >
          Sair desta conta
        </button>
      </div>
    </div>
  );
}
