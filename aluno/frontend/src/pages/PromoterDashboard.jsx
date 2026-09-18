import { useEffect, useState } from "react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { Megaphone, Zap, Users, Ticket } from "lucide-react";

function reais(centavos) {
  if (centavos == null) return "—";
  return (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function dataLegivel(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("pt-BR");
  } catch {
    return iso;
  }
}

// Painel do promoter — a MESMA paleta e os mesmos componentes (`card-sapiens`,
// `secao-olho`) do Admin, mas uma tela à parte: `/promoter/dashboard` só
// devolve os alunos que usaram O CUPOM deste promoter e o quanto CADA UM
// gastou comprando Sparks. Não há como este painel mostrar outro cupom ou
// outro promoter — o isolamento é feito no backend, pelo próprio e-mail de
// quem está logado (ver `promoter_routes.py`).
export default function PromoterDashboard() {
  const [dados, setDados] = useState(null);
  const [carregado, setCarregado] = useState(false);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    api
      .get("/promoter/dashboard")
      .then(({ data }) => setDados(data))
      .catch((e) => setErro(errMsg(e, "Falha ao carregar o painel do promoter.")))
      .finally(() => setCarregado(true));
  }, []);

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="flex items-center gap-3 mb-3">
          <Megaphone className="w-4 h-4 text-emerald-400" />
          <div className="secao-olho">Painel do promoter</div>
        </div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-white" data-testid="promoter-title">
          Seus cupons
        </h1>
        <p className="mt-3 text-white/60 max-w-lg">
          Quantos alunos usaram cada cupom seu, o saldo de Sparks de cada um e quanto cada um gastou
          comprando Sparks — é a partir desse valor que sua parte é calculada.
        </p>

        {erro && <div className="mt-8 card-sapiens rounded-2xl p-6 text-sm text-rose-500">{erro}</div>}

        {dados && (
          <>
            <div className="mt-8 grid grid-cols-2 gap-3">
              <div className="card-sapiens rounded-2xl p-4">
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Alunos</div>
                <div className="mt-1 font-display text-2xl font-extrabold tracking-tighter text-zinc-950">
                  {dados.total_alunos}
                </div>
              </div>
              <div className="card-sapiens rounded-2xl p-4">
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Gasto total</div>
                <div className="mt-1 font-display text-2xl font-extrabold tracking-tighter text-zinc-950">
                  {reais(dados.total_gasto_centavos)}
                </div>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              {dados.cupons.length === 0 && (
                <div className="card-sapiens rounded-2xl p-8 text-center text-zinc-500 text-sm">
                  Nenhum cupom vinculado à sua conta ainda.
                </div>
              )}
              {dados.cupons.map((c) => (
                <div key={c.code} className="card-sapiens rounded-2xl p-5" data-testid={`promoter-cupom-${c.code}`}>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Ticket className="w-3.5 h-3.5 text-sapiens-accent" />
                    <span className="font-mono-alt font-bold text-zinc-950 tracking-wide">{c.code}</span>
                    <span className={`inline-flex items-center text-[11px] font-medium border px-2 py-0.5 rounded-full ${c.active ? "bg-emerald-50 text-emerald-700 border-emerald-100" : "bg-zinc-100 text-zinc-500 border-zinc-200"}`}>
                      {c.active ? "Ativo" : "Desativado"}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-1.5 text-sm text-zinc-500">
                    <Users className="w-3.5 h-3.5" /> {c.alunos_count} aluno(s) · gasto total {reais(c.gasto_total_centavos)}
                  </div>

                  <div className="mt-3 space-y-1.5">
                    {c.alunos.length === 0 && (
                      <div className="text-xs text-zinc-400">Ninguém usou este cupom ainda.</div>
                    )}
                    {c.alunos.map((a, i) => (
                      <div key={i} className="flex items-center gap-3 border border-zinc-100 rounded-xl px-3 py-2">
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-zinc-900 truncate">{a.name}</div>
                          <div className="text-xs text-zinc-400">desde {dataLegivel(a.desde)}</div>
                        </div>
                        <div className="flex items-center gap-1 text-xs font-mono-alt text-amber-600 shrink-0">
                          <Zap className="w-3 h-3" /> {a.sparks_balance ?? "—"}
                        </div>
                        <div className="text-sm font-semibold text-zinc-900 shrink-0 w-24 text-right">
                          {reais(a.gasto_centavos)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {!dados && carregado && !erro && (
          <div className="mt-8 card-sapiens rounded-2xl p-8 text-center text-zinc-500 text-sm">
            Não foi possível carregar seu painel.
          </div>
        )}
      </div>
    </div>
  );
}
