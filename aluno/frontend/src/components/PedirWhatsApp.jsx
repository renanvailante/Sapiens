import { useState } from "react";
import { toast } from "sonner";
import { MessageCircleMore, Check } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../lib/auth";

/**
 * Pede o WhatsApp de quem ainda não tem um na conta — e some sozinho quando
 * tem.
 *
 * O campo passou a ser obrigatório no cadastro por e-mail em 2026-09-15, mas
 * dois grupos entram sem ele: quem criou a conta ANTES dessa data (ou seja, os
 * alunos mais antigos, que são os mais engajados) e quem entra pelo botão do
 * Google a partir da tela de login, onde não existe formulário nenhum.
 *
 * Sem este pedido, esses dois grupos ficariam permanentemente fora do alcance
 * da equipe — justamente as pessoas para quem o link da aula ao vivo de quinta
 * precisa chegar.
 *
 * O componente não tem estado próprio de "já pedi": a fonte da verdade é
 * `user.whatsapp`. Guardar um "dispensado" no localStorage esconderia o pedido
 * de quem trocou de aparelho e continuaria mostrando para quem já respondeu.
 */
export default function PedirWhatsApp({
  titulo = "Qual é o seu WhatsApp?",
  motivo = "É por ele que a gente manda o link da aula ao vivo de quinta e os avisos de turma.",
  compacto = false,
  testid = "pedir-whatsapp",
}) {
  const { user, refresh } = useAuth();
  const [valor, setValor] = useState("");
  const [salvando, setSalvando] = useState(false);

  if (!user || user.whatsapp) return null;

  const salvar = async (e) => {
    e.preventDefault();
    if (!valor.trim()) return;
    setSalvando(true);
    try {
      await api.post("/auth/whatsapp", { whatsapp: valor.trim() });
      toast.success("WhatsApp salvo. Agora a gente consegue te avisar.");
      // Relê a sessão: é o que faz este cartão desaparecer da tela inteira,
      // em todos os lugares onde ele aparece, sem recarregar a página.
      await refresh();
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível salvar seu WhatsApp."));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <form
      onSubmit={salvar}
      className={`macio border border-[#4FD9FF]/25 bg-[#4FD9FF]/[0.06] ${compacto ? "p-4" : "p-5"}`}
      data-testid={testid}
    >
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-[#4FD9FF]/30 bg-[#4FD9FF]/15 text-[#7FD8FF]">
          <MessageCircleMore className="h-4 w-4" strokeWidth={1.8} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="font-display text-base font-bold tracking-tight text-white">{titulo}</div>
          <div className="mt-0.5 text-xs leading-snug text-white/50">{motivo}</div>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <input
              type="tel"
              inputMode="tel"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
              placeholder="(11) 91234-5678"
              className="min-w-0 flex-1 rounded-xl border border-white/12 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none placeholder:text-white/30 focus:border-[#4FD9FF]/60"
              data-testid={`${testid}-campo`}
            />
            <button
              type="submit"
              disabled={salvando || !valor.trim()}
              className="pill btn-sapiens inline-flex shrink-0 items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-medium disabled:opacity-50"
              data-testid={`${testid}-salvar`}
            >
              <Check className="h-4 w-4" /> {salvando ? "Salvando…" : "Salvar"}
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}
