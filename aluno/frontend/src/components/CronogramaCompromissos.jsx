import { useState } from "react";
import { toast } from "sonner";
import {
  Mic, MicOff, Send, Loader2, Plus, CalendarPlus, Link2, Settings2, X,
} from "lucide-react";
import { api, errMsg } from "../lib/api";
import { lerEventosDaSemana } from "../lib/googleAgenda";
import { googleDisponivel } from "../lib/firebase";
import useDitado from "../hooks/useDitado";
import Mentis from "./Mentis";

/**
 * Onde o aluno conta ao Sapiens o que já ocupa o tempo dele.
 *
 * Quatro portas para a MESMA agenda, porque cada uma falha de um jeito e
 * nenhuma pode ser a única:
 *
 *  1. **Falar ou escrever** — a mais rápida ("aula de segunda a sexta das 7 ao
 *     meio-dia e inglês terça às 19h"). Custa Sparks: é a única que chama o
 *     modelo.
 *  2. **Google Agenda** — um clique, mas depende do popup do Google abrir e
 *     da API estar liberada no projeto.
 *  3. **Endereço iCal** — funciona sempre, inclusive com Outlook e iCloud, e
 *     é a saída quando a porta 2 recusa.
 *  4. **Formulário** — nunca falha, nunca cobra, e é o chão de onde as outras
 *     três partem.
 */

const TIPOS = [
  { id: "aula", rotulo: "Aula" },
  { id: "trabalho", rotulo: "Trabalho" },
  { id: "prova", rotulo: "Prova" },
  { id: "pessoal", rotulo: "Pessoal" },
];

const DIAS_CURTOS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

const EXEMPLO =
  "Ex.: tenho aula de segunda a sexta das 7h às 12h30, inglês terça e quinta às 19h, " +
  "trabalho sábado de manhã e prova de biologia dia 24.";

function Aba({ ativa, onClick, icone: Icone, children, testid }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testid}
      className={`pill inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-xs font-medium transition ${
        ativa
          ? "border-[#4FD9FF]/50 bg-[#4FD9FF]/12 text-white"
          : "border-white/12 bg-white/5 text-white/60 hover:text-white hover:border-white/25"
      }`}
    >
      <Icone className="h-3.5 w-3.5" /> {children}
    </button>
  );
}

export default function CronogramaCompromissos({
  semana, compromissos, preferencias, custoTexto, onSemana, onSaldo,
}) {
  const [aba, setAba] = useState("falar");
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [importando, setImportando] = useState(null);
  const [urlIcs, setUrlIcs] = useState("");
  const [form, setForm] = useState({
    titulo: "", dia: 0, inicio: "08:00", fim: "09:00", tipo: "aula", data: "",
  });
  const [prefs, setPrefs] = useState(preferencias);
  const [ditadoPorVoz, setDitadoPorVoz] = useState(false);

  const ditado = useDitado({
    aoTexto: (trecho) => {
      setDitadoPorVoz(true);
      setTexto((atual) => (atual ? `${atual} ${trecho}` : trecho));
    },
  });

  const aplicar = (dados) => {
    if (dados?.semana) onSemana(dados.semana);
    if (typeof dados?.sparks_balance === "number") onSaldo(dados.sparks_balance);
  };

  const enviarTexto = async () => {
    const frase = `${texto} ${ditado.parcial}`.trim();
    if (!frase || enviando) return;
    setEnviando(true);
    try {
      ditado.parar();
      const { data } = await api.post("/cronograma/compromissos/texto", {
        texto: frase,
        origem: ditadoPorVoz ? "voz" : "chat",
        semana,
      });
      aplicar(data);
      setTexto("");
      setDitadoPorVoz(false);
      toast[data.criados ? "success" : "info"](data.resposta);
    } catch (e) {
      toast.error(errMsg(e, "Não consegui ler seus compromissos agora."));
    } finally {
      setEnviando(false);
    }
  };

  const importarGoogle = async () => {
    setImportando("google");
    try {
      const de = new Date(`${semana}T00:00:00`);
      const ate = new Date(de);
      ate.setDate(ate.getDate() + 7);
      const eventos = await lerEventosDaSemana(de, ate);
      const { data } = await api.post("/cronograma/importar/google", { eventos, semana });
      aplicar(data);
      toast.success(
        data.criados || data.atualizados
          ? `${data.criados} novo(s) e ${data.atualizados} atualizado(s) da sua agenda.`
          : data.aviso || "Nada novo nesta semana."
      );
    } catch (e) {
      // Fechar o popup é uma decisão, não um erro: avisar disso seria ruído.
      const codigo = e?.code || "";
      if (codigo === "auth/popup-closed-by-user" || codigo === "auth/cancelled-popup-request") return;
      toast.error(e?.message || errMsg(e, "Não consegui importar sua agenda do Google."));
    } finally {
      setImportando(null);
    }
  };

  const importarIcs = async () => {
    if (!urlIcs.trim()) return;
    setImportando("ics");
    try {
      const { data } = await api.post("/cronograma/importar/ics", { url: urlIcs.trim(), semana });
      aplicar(data);
      setUrlIcs("");
      toast.success(
        data.criados || data.atualizados
          ? `${data.criados} novo(s) e ${data.atualizados} atualizado(s) do seu calendário.`
          : data.aviso || "Nada novo nesta semana."
      );
    } catch (e) {
      toast.error(errMsg(e, "Não consegui abrir esse calendário."));
    } finally {
      setImportando(null);
    }
  };

  const criarManual = async () => {
    if (!form.titulo.trim()) return;
    setEnviando(true);
    try {
      await api.post("/cronograma/compromisso", {
        titulo: form.titulo.trim(),
        tipo: form.tipo,
        inicio: form.inicio,
        fim: form.fim,
        ...(form.data ? { data: form.data } : { dia: Number(form.dia) }),
      });
      const { data } = await api.get("/cronograma", { params: { semana } });
      onSemana(data);
      setForm((f) => ({ ...f, titulo: "" }));
      toast.success("Compromisso anotado.");
    } catch (e) {
      toast.error(errMsg(e, "Não consegui salvar esse compromisso."));
    } finally {
      setEnviando(false);
    }
  };

  const apagar = async (id) => {
    try {
      await api.delete(`/cronograma/compromisso/${id}`);
      const { data } = await api.get("/cronograma", { params: { semana } });
      onSemana(data);
    } catch (e) {
      toast.error(errMsg(e, "Não consegui apagar."));
    }
  };

  const salvarPrefs = async () => {
    try {
      const { data } = await api.put("/cronograma/preferencias", prefs);
      setPrefs(data.preferencias);
      const atual = await api.get("/cronograma", { params: { semana } });
      onSemana(atual.data);
      toast.success("Janela de estudo atualizada. Monte a semana de novo para valer.");
    } catch (e) {
      toast.error(errMsg(e, "Não consegui salvar suas preferências."));
    }
  };

  const alternarFolga = (dia) => {
    const atuais = new Set(prefs.dias_de_folga || []);
    if (atuais.has(dia)) atuais.delete(dia);
    else atuais.add(dia);
    setPrefs({ ...prefs, dias_de_folga: [...atuais].sort() });
  };

  return (
    <section className="card-sapiens rounded-3xl p-6 md:p-7" data-testid="cronograma-compromissos">
      <h2 className="font-display text-xl font-bold tracking-tight text-zinc-950">
        O que já ocupa a sua semana
      </h2>
      <p className="mt-1 text-sm text-zinc-500">
        O Sapiens monta o estudo no que sobra. Quanto mais certo estiver isto aqui, menos o
        cronograma vai marcar aula em cima de aula.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <Aba ativa={aba === "falar"} onClick={() => setAba("falar")} icone={Mic} testid="cronograma-aba-falar">
          Falar ou escrever
        </Aba>
        <Aba ativa={aba === "importar"} onClick={() => setAba("importar")} icone={CalendarPlus} testid="cronograma-aba-importar">
          Importar agenda
        </Aba>
        <Aba ativa={aba === "manual"} onClick={() => setAba("manual")} icone={Plus} testid="cronograma-aba-manual">
          Adicionar à mão
        </Aba>
        <Aba ativa={aba === "janela"} onClick={() => setAba("janela")} icone={Settings2} testid="cronograma-aba-janela">
          Janela de estudo
        </Aba>
      </div>

      {aba === "falar" && (
        <div className="mt-5">
          <div className="flex items-start gap-2.5">
            <Mentis className="mt-1 h-6 w-6 shrink-0" variante="icone" estado={enviando ? "analise" : "neutra"} />
            <div className="bolha-mentis rounded-2xl px-4 py-3 text-[13px] leading-relaxed">
              Me conte a sua rotina do jeito que você falaria para um amigo. Eu transformo em agenda.
              <span className="mt-1 block text-white/45">{EXEMPLO}</span>
            </div>
          </div>

          <div className="mt-3 rounded-2xl border border-white/12 bg-white/5 p-3">
            <textarea
              value={`${texto}${ditado.parcial ? ` ${ditado.parcial}` : ""}`}
              onChange={(e) => setTexto(e.target.value.slice(0, 800))}
              rows={3}
              placeholder="Escreva aqui, ou toque no microfone e fale."
              className="w-full resize-none bg-transparent text-sm outline-none"
              data-testid="cronograma-texto"
            />
            <div className="mt-2 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                {ditado.disponivel ? (
                  <button
                    type="button"
                    onClick={ditado.alternar}
                    className={`pill inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition ${
                      ditado.ouvindo
                        ? "border-rose-400/50 bg-rose-500/15 text-rose-200"
                        : "border-white/15 bg-white/5 text-white/70 hover:text-white"
                    }`}
                    data-testid="cronograma-microfone"
                  >
                    {ditado.ouvindo ? <MicOff className="h-3.5 w-3.5" /> : <Mic className="h-3.5 w-3.5" />}
                    {ditado.ouvindo ? "Parar de ouvir" : "Falar"}
                  </button>
                ) : (
                  <span className="text-[11px] text-white/35">
                    Seu navegador não tem reconhecimento de voz — escreva no campo acima.
                  </span>
                )}
                {ditado.ouvindo && (
                  <span className="inline-flex items-center gap-1.5 text-[11px] text-rose-200">
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-rose-400" /> ouvindo…
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={enviarTexto}
                disabled={enviando || !`${texto}${ditado.parcial}`.trim()}
                className="pill btn-sapiens inline-flex shrink-0 items-center gap-1.5 rounded-full px-4 py-2 text-xs disabled:opacity-40"
                data-testid="cronograma-enviar-texto"
              >
                {enviando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                Anotar · {custoTexto} Sparks
              </button>
            </div>
          </div>
          {ditado.erro && <p className="mt-2 text-[11px] text-rose-300">{ditado.erro}</p>}
        </div>
      )}

      {aba === "importar" && (
        <div className="mt-5 space-y-4">
          {googleDisponivel && (
            <div className="rounded-2xl border border-white/12 bg-white/5 p-4">
              <p className="text-sm font-medium text-zinc-950">Google Agenda</p>
              <p className="mt-1 text-xs text-zinc-500">
                O Google pede a sua autorização e os eventos da semana são lidos aqui no seu
                navegador. O Sapiens guarda os compromissos, nunca o acesso à sua agenda — e a
                permissão pedida é só de leitura.
              </p>
              <button
                type="button"
                onClick={importarGoogle}
                disabled={importando === "google"}
                className="pill btn-sapiens mt-3 inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs disabled:opacity-50"
                data-testid="cronograma-importar-google"
              >
                {importando === "google" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CalendarPlus className="h-3.5 w-3.5" />}
                Importar do Google · grátis
              </button>
            </div>
          )}

          <div className="rounded-2xl border border-white/12 bg-white/5 p-4">
            <p className="text-sm font-medium text-zinc-950">Endereço do calendário (iCal)</p>
            <p className="mt-1 text-xs text-zinc-500">
              Funciona com Google, Outlook e iCloud, e não depende de popup nenhum. No Google
              Agenda: Configurações → seu calendário → “Endereço secreto em formato iCal”.
            </p>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <input
                value={urlIcs}
                onChange={(e) => setUrlIcs(e.target.value)}
                placeholder="https://calendar.google.com/calendar/ical/.../basic.ics"
                className="flex-1 rounded-xl border border-zinc-200 px-3 py-2 text-xs outline-none"
                data-testid="cronograma-ics-url"
              />
              <button
                type="button"
                onClick={importarIcs}
                disabled={importando === "ics" || !urlIcs.trim()}
                className="pill btn-vidro inline-flex shrink-0 items-center justify-center gap-2 rounded-full px-4 py-2 text-xs disabled:opacity-40"
                data-testid="cronograma-importar-ics"
              >
                {importando === "ics" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Link2 className="h-3.5 w-3.5" />}
                Importar
              </button>
            </div>
          </div>
        </div>
      )}

      {aba === "manual" && (
        <div className="mt-5 rounded-2xl border border-white/12 bg-white/5 p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="sm:col-span-2 text-xs text-zinc-500">
              O que é
              <input
                value={form.titulo}
                onChange={(e) => setForm({ ...form, titulo: e.target.value })}
                placeholder="Aula de matemática"
                className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none"
                data-testid="cronograma-manual-titulo"
              />
            </label>
            <label className="text-xs text-zinc-500">
              Tipo
              <select
                value={form.tipo}
                onChange={(e) => setForm({ ...form, tipo: e.target.value })}
                className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none"
              >
                {TIPOS.map((t) => <option key={t.id} value={t.id}>{t.rotulo}</option>)}
              </select>
            </label>
            <label className="text-xs text-zinc-500">
              Dia da semana (toda semana)
              <select
                value={form.dia}
                onChange={(e) => setForm({ ...form, dia: e.target.value, data: "" })}
                className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none"
              >
                {DIAS_CURTOS.map((d, i) => <option key={d} value={i}>{d}</option>)}
              </select>
            </label>
            <label className="text-xs text-zinc-500">
              Começa
              <input
                type="time"
                value={form.inicio}
                onChange={(e) => setForm({ ...form, inicio: e.target.value })}
                className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none"
              />
            </label>
            <label className="text-xs text-zinc-500">
              Termina
              <input
                type="time"
                value={form.fim}
                onChange={(e) => setForm({ ...form, fim: e.target.value })}
                className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none"
              />
            </label>
            <label className="sm:col-span-2 text-xs text-zinc-500">
              Ou uma data específica (para prova e evento de um dia só)
              <input
                type="date"
                value={form.data}
                onChange={(e) => setForm({ ...form, data: e.target.value })}
                className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none"
                data-testid="cronograma-manual-data"
              />
            </label>
          </div>
          <button
            type="button"
            onClick={criarManual}
            disabled={enviando || !form.titulo.trim()}
            className="pill btn-sapiens mt-3 inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs disabled:opacity-40"
            data-testid="cronograma-manual-salvar"
          >
            <Plus className="h-3.5 w-3.5" /> Adicionar · grátis
          </button>
        </div>
      )}

      {aba === "janela" && (
        <div className="mt-5 rounded-2xl border border-white/12 bg-white/5 p-4">
          <p className="text-xs text-zinc-500">
            A janela em que o Sapiens pode marcar estudo. Nada é marcado fora dela, nem nos dias
            que você deixar de folga.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-4">
            <label className="text-xs text-zinc-500">
              Começo do dia
              <input type="time" value={prefs.inicio_dia}
                onChange={(e) => setPrefs({ ...prefs, inicio_dia: e.target.value })}
                className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none" />
            </label>
            <label className="text-xs text-zinc-500">
              Fim do dia
              <input type="time" value={prefs.fim_dia}
                onChange={(e) => setPrefs({ ...prefs, fim_dia: e.target.value })}
                className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none" />
            </label>
            <label className="text-xs text-zinc-500">
              Minutos por bloco
              <input type="number" min={20} max={180} value={prefs.bloco_minutos}
                onChange={(e) => setPrefs({ ...prefs, bloco_minutos: Number(e.target.value) })}
                className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none" />
            </label>
            <label className="text-xs text-zinc-500">
              Blocos por dia
              <input type="number" min={1} max={8} value={prefs.blocos_por_dia}
                onChange={(e) => setPrefs({ ...prefs, blocos_por_dia: Number(e.target.value) })}
                className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none" />
            </label>
          </div>
          <p className="mt-4 text-xs text-zinc-500">Dias de folga</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {DIAS_CURTOS.map((d, i) => (
              <button
                key={d}
                type="button"
                onClick={() => alternarFolga(i)}
                className={`pill rounded-full border px-3 py-1.5 text-xs transition ${
                  (prefs.dias_de_folga || []).includes(i)
                    ? "border-amber-400/40 bg-amber-400/15 text-amber-200"
                    : "border-white/12 bg-white/5 text-white/60"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={salvarPrefs}
            className="pill btn-sapiens mt-4 inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs"
            data-testid="cronograma-salvar-janela"
          >
            Salvar janela
          </button>
        </div>
      )}

      {compromissos.length > 0 && (
        <div className="mt-6 border-t border-white/10 pt-4">
          <p className="text-xs uppercase tracking-[0.28em] text-zinc-400">
            Compromissos desta semana · {compromissos.length}
          </p>
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {compromissos.map((c) => (
              <span
                key={c.id}
                className="group inline-flex items-center gap-1.5 rounded-full border border-white/12 bg-white/5 px-3 py-1.5 text-[11px] text-white/70"
              >
                <span className="font-medium text-white/85">{DIAS_CURTOS[c.dia]}</span>
                {c.dia_inteiro ? "dia todo" : `${c.inicio}–${c.fim}`}
                <span className="text-white/50">·</span> {c.titulo}
                <button
                  type="button"
                  onClick={() => apagar(c.id)}
                  // 12px para apagar um compromisso era alvo de mira, não de
                  // dedo — e apagar não tem desfazer. `-m-2.5 p-2.5` leva a
                  // área para ~32px sem mover o X um pixel.
                  className="-m-2.5 p-2.5 opacity-40 transition hover:opacity-100"
                  aria-label={`Apagar ${c.titulo}`}
                  data-testid={`cronograma-apagar-${c.id}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
