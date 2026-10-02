import { useEffect, useState } from "react";
import { MENTOR } from "../lib/mentor";
import { VOZ } from "../lib/historia";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { cadastroConcluido } from "../lib/rastreio";
import { api, errMsg, emailJaTemConta } from "../lib/api";
import { googleDisponivel, mensagemDeErroGoogle } from "../lib/firebase";
import { salvarAtribuicao, lerAtribuicao, modoInicialDoLogin } from "../lib/atribuicao";
import { navegadorEmbutido, esperaAteAvisarDoPopup } from "../lib/navegador";
import { origemParaEnvio } from "../lib/campanha";
import { toast } from "sonner";
import { Brain, Compass, Radio, Loader2, Gift } from "lucide-react";
import Logo from "../components/Logo";
import ContagemEnem from "../components/ContagemEnem";

/**
 * A porta de entrada — reescrita em 2026-09-16.
 *
 * O que ela era: duas colunas, a da esquerda com o manifesto sobre o ambiente
 * da marca e a da direita um formulário sobre `bg-white`. A metade branca era
 * a última superfície do produto que continuava sendo de outro sistema visual
 * — a camada de tradução de utilitários a escurecia, mas o que sobrava era um
 * retângulo neutro sem material nenhum, e era a PRIMEIRA coisa que um aluno
 * novo via do Sapiens.
 *
 * O que ela é agora: o mesmo ambiente dos dois lados, e o formulário dentro de
 * um painel de vidro — a mesma superfície do resto do produto. Quem entra já
 * está dentro do Sapiens antes de digitar a senha.
 *
 * Três mudanças de uso, e não de pintura:
 *
 * 1. **Entrar / Criar conta viraram um seletor no TOPO**, e não um link de
 *    texto no rodapé. Era a decisão mais importante da tela e ficava abaixo de
 *    tudo, em cinza, depois de um formulário que podia ser o errado.
 * 2. **A coluna da esquerda deixou de ser só manifesto.** Ela mostra o relógio
 *    do ENEM e as três coisas que o produto faz — quem chega aqui por um link
 *    de WhatsApp, sem ter passado pela landing, não tinha como saber o que
 *    está do outro lado do cadastro.
 * 3. **A ordem dos campos não mudou.** WhatsApp e cupom continuam ACIMA do
 *    botão do Google, pelo motivo documentado abaixo: eles valem para os dois
 *    caminhos de cadastro.
 */

const PROVAS = [
  // O plano, e não os recursos: a coluna da marca é a última coisa que a
  // pessoa lê antes de decidir dar o e-mail, e nesse segundo ela quer saber o
  // que VAI ACONTECER com ela, não o que a plataforma tem. Ver `lib/historia`.
  { icone: Brain, titulo: "1. Responda 10 questões", texto: "Dez minutos. É o que a Mentis precisa para ver como você pensa." },
  { icone: Compass, titulo: "2. Receba o seu plano", texto: "Com horário, prioridade e motivo. Você abre o app e já sabe o que fazer." },
  { icone: Radio, titulo: "3. Treine com quem passou", texto: `Aula ao vivo toda quinta com ${MENTOR.nome}, ${MENTOR.titulo}.` },
];

function Campo({ id, rotulo, dica, children }) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-semibold text-white/55" htmlFor={id}>
        {rotulo}
      </label>
      {children}
      {dica && <p className="mt-1.5 text-xs leading-relaxed text-white/40">{dica}</p>}
    </div>
  );
}

const CAMPO = "w-full rounded-xl border border-white/12 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none transition-colors placeholder:text-white/30 focus:border-[#4FD9FF]/55";

export default function Login() {
  const { login, signup, loginGoogle } = useAuth();
  const nav = useNavigate();
  // `/login?convite=RENAN4K7Q` — o link que um aluno manda para um amigo (ver
  // `pages/Indicar.jsx`). Ele decide DUAS coisas de uma vez: o campo de código
  // já nasce preenchido e a tela abre em "Criar conta", não em "Entrar". Quem
  // clica num convite não está voltando; está chegando, e abrir no formulário
  // de login é pedir uma senha que essa pessoa ainda não tem.
  const [params] = useSearchParams();
  const conviteDaUrl = (params.get("convite") || "").trim().toUpperCase();
  // Sem `?convite=` na URL, ainda pode existir um clique de até 30 dias atrás
  // guardado pelo navegador (ver `lib/atribuicao.js`) — a janela de
  // atribuição do programa de afiliados/campanhas. Sem isso, quem clica no
  // link, fecha a aba e volta depois pra se cadastrar perderia a atribuição.
  const atribuicaoSalva = !conviteDaUrl ? lerAtribuicao() : null;
  const convite = conviteDaUrl || atribuicaoSalva?.codigo || "";
  // A origem (UTM/campanha) que a landing colou na URL ao levar ao cadastro
  // (ver `AdsLandingLayout`), com a janela de 30 dias guardada como reforço
  // para quem chega sem parâmetro — mesma regra de precedência do convite
  // acima. `{}` para quem chega direto, sem passar por anúncio nenhum.
  const origem = origemParaEnvio(params);
  // `?novo=1` é a porta do "Começar agora" da landing. Mesma razão do
  // convite: quem clicou em começar não está voltando, está chegando, e abrir
  // no formulário de login é pedir uma senha que essa pessoa ainda não tem.
  //
  // A atribuição GUARDADA preenche o cupom, mas não decide o modo — ver
  // `modoInicialDoLogin`: ela fazia o "Entrar" abrir em "Criar conta".
  const [mode, setMode] = useState(() =>
    modoInicialDoLogin({ novo: params.get("novo") === "1", conviteDaUrl }),
  );
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  // Menor de idade e o responsável. Autodeclarado, e revelado só quando a
  // caixa é marcada: um adolescente vê dois campos a mais, e um adulto não vê
  // nenhum. Ver `backend/models.User` para por que o dado é guardado.
  const [menorDeIdade, setMenorDeIdade] = useState(false);
  const [responsavelNome, setResponsavelNome] = useState("");
  const [responsavelWhatsapp, setResponsavelWhatsapp] = useState("");
  const [promoCode, setPromoCode] = useState(convite);

  // Guarda o convite da URL para sobreviver 30 dias (e conta o clique, uma
  // vez, sem bloquear nada se a rota pública falhar). Só o CÓDIGO viaja: o
  // link já carregou um `&bonus=N` que a tela exibia, e que qualquer pessoa
  // editava na barra de endereço para a página prometer o número que ela
  // quisesse. Quem decide o valor é sempre `/auth/signup` lendo o catálogo.
  useEffect(() => {
    if (!conviteDaUrl) return;
    salvarAtribuicao(conviteDaUrl);
    api.post("/track/click", { codigo: conviteDaUrl }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conviteDaUrl]);
  const [busy, setBusy] = useState(false);
  const [busyGoogle, setBusyGoogle] = useState(false);
  const [aceitouTermos, setAceitouTermos] = useState(false);
  // A janela do Google está demorando demais ou voltou sem resultado.
  const [dicaPopup, setDicaPopup] = useState(false);

  const criando = mode === "signup";
  // Calculado uma vez por montagem: o `userAgent` não muda com a pessoa na
  // página, e reavaliar a cada render não acrescentaria nada.
  const [embutido] = useState(() => navegadorEmbutido());

  const comGoogle = async () => {
    setBusyGoogle(true);
    setDicaPopup(false);
    // A janela do Google demora o que a pessoa demorar para escolher a conta —
    // não dá para cancelar por tempo sem cancelar gente lenta. O que dá é
    // AVISAR: passados 25 segundos a dica aparece embaixo do botão, e o fluxo
    // continua esperando normalmente. É a diferença entre "travou e eu não sei
    // o que fazer" e "travou, e o app me disse a saída".
    // 8s dentro do navegador de um aplicativo, 25s fora dele. Ver
    // `lib/navegador.js`: ali a espera não é lentidão da pessoa, é o defeito
    // conhecido do popup cross-origin acontecendo em silêncio.
    const avisar = setTimeout(() => setDicaPopup(true), esperaAteAvisarDoPopup());
    const abertoEm = Date.now();
    try {
      if (criando && menorDeIdade && !(responsavelNome.trim() && responsavelWhatsapp.trim())) {
        toast.error("Informe o nome e o WhatsApp do seu responsável.");
        setBusyGoogle(false);
        return;
      }
      const { contaCriada } = await loginGoogle(
        criando ? promoCode : undefined,
        criando ? whatsapp : undefined,
        criando ? { menorDeIdade, responsavelNome, responsavelWhatsapp, origem } : undefined,
      );
      // `contaCriada` vem do BACKEND, e não do modo em que o formulário
      // estava: este botão cria conta também a partir da tela de "Entrar", e
      // um aluno antigo que volte por aqui não é cadastro nenhum. Ver
      // `lib/rastreio.cadastroConcluido` — nada que identifique a pessoa sai
      // junto. Antes do `nav`, porque navegar desmonta esta tela.
      if (contaCriada) cadastroConcluido("google");
      nav("/hoje");
    } catch (e) {
      // Fechar o popup NÃO é erro quando foi rápido: é cancelamento
      // deliberado, e um toast ali seria ruído sobre uma decisão da pessoa.
      //
      // Mas fechar depois de MUITO tempo é outra coisa: é a janela que travou
      // (o handler do Firebase mora em outro domínio e, com o armazenamento de
      // terceiros particionado, ele às vezes fica numa tela branca sem nunca
      // devolver o resultado). Nesse caso o silêncio é o pior desfecho — o
      // aluno fecha a janela branca e o app não diz nada, como se nada tivesse
      // acontecido. O tempo decorrido separa os dois casos.
      const cancelouRapido =
        mensagemDeErroGoogle(e) === null && Date.now() - abertoEm < 25_000;
      if (cancelouRapido) {
        // nada: a pessoa desistiu, e ela sabe disso.
      } else if (mensagemDeErroGoogle(e) === null) {
        setDicaPopup(true);
        toast.error("A janela do Google não terminou de responder. Tente de novo ou entre com e-mail e senha.");
      } else {
        const doFirebase = mensagemDeErroGoogle(e);
        if (doFirebase !== null) toast.error(doFirebase || errMsg(e));
        else if (e?.response) toast.error(errMsg(e));
      }
    } finally {
      clearTimeout(avisar);
      setBusyGoogle(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (criando && !whatsapp.trim()) {
      toast.error("Informe seu WhatsApp — é por ele que a gente fala com você.");
      return;
    }
    if (criando && menorDeIdade && !(responsavelNome.trim() && responsavelWhatsapp.trim())) {
      toast.error("Informe o nome e o WhatsApp do seu responsável.");
      return;
    }
    setBusy(true);
    try {
      if (!criando) await login(email, password);
      else {
        await signup(name, email, password, whatsapp, promoCode, {
          menorDeIdade, responsavelNome, responsavelWhatsapp, origem,
        });
      }
      if (criando) cadastroConcluido("email");
      toast.success("Bem-vindo ao Sapiens.");
      nav("/hoje", { replace: true });
    } catch (err) {
      // A tela se corrige sozinha em vez de acusar a pessoa: vira "Entrar",
      // guarda o e-mail que ela já digitou e diz o que fez. Um clique, e não
      // um formulário inteiro de novo.
      //
      // A senha é LIMPA, e isso é deliberado. A que ela acabou de inventar
      // para o cadastro quase nunca é a senha da conta que já existe;
      // mantê-la no campo convida a clicar em "Entrar" e colher um
      // "credenciais inválidas" logo depois do aviso — dois erros no lugar de
      // um, e o segundo parecendo culpa dela.
      if (criando && emailJaTemConta(err)) {
        setMode("login");
        setPassword("");
        toast.info("Esse e-mail já tem conta no Sapiens. Trouxemos você para a tela de entrar — digite sua senha.");
        return;
      }
      toast.error(errMsg(err, "Não foi possível entrar."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="exam-shell grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      {/* ---------------- A COLUNA DA MARCA ---------------- */}
      <div className="relative hidden flex-col justify-between p-12 lg:flex">
        <Logo to="/" tamanho="m" testid="login-brand" />

        <div className="max-w-md">
          <div className="secao-olho">Manifesto</div>
          <p className="titulo-heroi mt-4">Transforme seus erros em conhecimento.</p>
          <p className="mt-4 text-sm leading-relaxed text-white/60">
            Você não erra por falta de estudo. Erra por um padrão que ninguém
            nunca te mostrou — e é esse padrão que a Mentis encontra.
          </p>

          <div className="mt-9 space-y-4">
            {PROVAS.map((p) => (
              <div key={p.titulo} className="flex items-start gap-3.5">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-[#7FD8FF]">
                  <p.icone className="h-5 w-5" strokeWidth={1.8} />
                </span>
                <div className="min-w-0">
                  <div className="text-sm font-bold text-white">{p.titulo}</div>
                  <div className="text-xs leading-relaxed text-white/50">{p.texto}</div>
                </div>
              </div>
            ))}
          </div>

          {/* O relógio do ENEM, na variante de linha: quem ainda não entrou
              corre contra a mesma data de quem já está dentro. Some sozinho
              quando as duas provas passam. */}
          <div className="mt-9 border-t border-white/10 pt-5">
            <ContagemEnem variante="linha" testid="login-contagem-enem" />
          </div>
        </div>

        <div className="font-mono-alt text-xs tracking-wider text-white/40">© Sapiens Learning</div>
      </div>

      {/* ---------------- O FORMULÁRIO ---------------- */}
      <div className="flex items-center justify-center p-5 sm:p-8">
        <div className="card-sapiens w-full max-w-[26rem] rounded-[28px] p-6 sm:p-8">
          {/* A marca aparece aqui só no celular, onde a coluna da esquerda não
              existe: sem ela, a tela de entrada não dizia de que produto é. */}
          <div className="mb-6 lg:hidden">
            <Logo to="/" tamanho="m" testid="login-brand-mobile" />
          </div>

          {/* O SELETOR. Era um link de texto em cinza no rodapé da página, e
              a pessoa só descobria que estava no formulário errado depois de
              preencher o formulário errado. */}
          <div
            className="mb-6 grid grid-cols-2 gap-1 rounded-full border border-white/10 bg-white/[0.04] p-1"
            role="tablist"
          >
            <button
              type="button"
              role="tab"
              aria-selected={!criando}
              onClick={() => setMode("login")}
              className={`rounded-full py-2.5 text-sm font-bold transition-colors ${
                !criando ? "btn-sapiens" : "text-white/55 hover:text-white"
              }`}
              data-testid="login-switch-login"
            >
              Entrar
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={criando}
              onClick={() => setMode("signup")}
              className={`rounded-full py-2.5 text-sm font-bold transition-colors ${
                criando ? "btn-sapiens" : "text-white/55 hover:text-white"
              }`}
              data-testid="login-switch-signup"
            >
              Criar conta
            </button>
          </div>

          <h1 className="titulo-tela" data-testid="login-title">
            {criando ? "Criar conta" : "Entrar"}
          </h1>
          <p className="mt-1.5 text-sm text-white/50">
            {criando ? VOZ.promessa : "Bem-vindo de volta."}
          </p>

          {/* Só aparece com um convite reconhecido (URL ou janela de 30 dias
              guardada no navegador — ver `lib/atribuicao.js`). SEM número: o
              valor do bônus mora no catálogo do backend, e o único jeito de a
              tela exibi-lo aqui seria confiar na URL (que a pessoa edita) ou
              cravá-lo no JS (que a primeira afiliada com valor diferente
              tornaria mentira). Quem decide é sempre `/auth/signup`. */}
          {criando && convite && (
            <div
              className="mt-4 flex items-center gap-2.5 rounded-xl border border-emerald-400/25 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200"
              data-testid="login-banner-convite"
            >
              <Gift className="h-4 w-4 shrink-0" />
              Você foi convidado! Sua conta nova já começa com Sparks de bônus.
            </div>
          )}

          {/* O cupom e o WhatsApp ficam ACIMA do botão do Google, e não no meio
              do formulário de e-mail: eles valem para os DOIS caminhos de
              cadastro (o backend aceita `promo_code` e `whatsapp` no signup por
              e-mail e no primeiro login pelo Google), mas embaixo do botão
              ninguém que entra pelo Google chegava a vê-los — e o código
              trocaria o bônus padrão de 100 Sparks pelo valor programado.
              O WhatsApp é o único canal em que a equipe alcança o aluno de
              verdade, e é por ele que o link da aula ao vivo de quinta chega a
              quem pagou. A obrigatoriedade é checada à mão em `submit` (o campo
              mora fora do `<form>`, então o `required` do HTML não o alcança) e
              o backend recusa o cadastro por e-mail sem número de qualquer
              forma. Pelo Google ele é opcional: o botão também cria conta a
              partir da aba de LOGIN, onde não há formulário nenhum. */}
          {criando && (
            <div className="mt-6 space-y-4">
              <Campo
                id="login-whatsapp"
                rotulo="Seu WhatsApp"
                dica="É o canal por onde a equipe fala com você: link de aula, aviso de turma e suporte."
              >
                <input
                  id="login-whatsapp"
                  type="tel"
                  inputMode="tel"
                  value={whatsapp}
                  onChange={(e) => setWhatsapp(e.target.value)}
                  placeholder="(11) 91234-5678"
                  className={CAMPO}
                  data-testid="login-whatsapp"
                />
              </Campo>

              {/* MENOR DE IDADE. A caixa é uma linha; os dois campos só
                  existem para quem a marca. A LGPD (art. 14) trata dado de
                  adolescente à parte e pede um responsável identificável —
                  até aqui o produto resolvia isso com uma frase dentro do
                  aceite dos termos, que não deixa registro de ninguém. */}
              <label
                className="flex cursor-pointer items-center gap-2.5 text-sm text-white/65"
                data-testid="login-menor-label"
              >
                <input
                  type="checkbox"
                  checked={menorDeIdade}
                  onChange={(e) => setMenorDeIdade(e.target.checked)}
                  className="h-5 w-5 shrink-0 rounded border-white/20 accent-[#4FD9FF]"
                  data-testid="login-menor"
                />
                Tenho menos de 18 anos
              </label>

              {menorDeIdade && (
                <div className="space-y-4 rounded-2xl border border-[#4FD9FF]/25 bg-[#4FD9FF]/[0.06] p-4" data-testid="login-responsavel">
                  <p className="text-xs leading-relaxed text-white/55">
                    Precisamos de um responsável por você. É com ele que falamos sobre
                    cobrança e sobre os seus dados.
                  </p>
                  <Campo id="login-responsavel-nome" rotulo="Nome do responsável">
                    <input
                      id="login-responsavel-nome"
                      value={responsavelNome}
                      onChange={(e) => setResponsavelNome(e.target.value)}
                      placeholder="Nome completo"
                      className={CAMPO}
                      data-testid="login-responsavel-nome"
                    />
                  </Campo>
                  <Campo id="login-responsavel-whatsapp" rotulo="WhatsApp do responsável">
                    <input
                      id="login-responsavel-whatsapp"
                      type="tel"
                      inputMode="tel"
                      value={responsavelWhatsapp}
                      onChange={(e) => setResponsavelWhatsapp(e.target.value)}
                      placeholder="(11) 91234-5678"
                      className={CAMPO}
                      data-testid="login-responsavel-whatsapp"
                    />
                  </Campo>
                </div>
              )}

              {/* UM campo para os dois tipos de código, de propósito: cupom
                  de promoção (catálogo do admin) e código de indicação de um
                  amigo têm o mesmo formato, e quem recebeu um código pelo
                  WhatsApp não tem como saber de qual se trata. O servidor
                  resolve na ordem — cupom primeiro, indicação depois (ver
                  `auth._bonus_de_cadastro`). Pedir essa distinção aqui só
                  transformaria o erro de classificação da pessoa em "não
                  funcionou". */}
              <Campo
                id="login-promo-code"
                rotulo="Tem um código?"
                dica={
                  convite ? (
                    <>
                      Você chegou por um convite — o código do seu amigo já está preenchido.
                      Na sua primeira compra, ele ganha metade dos Sparks.
                    </>
                  ) : (
                    "Cupom de promoção ou o código de indicação de um amigo."
                  )
                }
              >
                <input
                  id="login-promo-code"
                  value={promoCode}
                  onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                  placeholder="Opcional — vale para os dois jeitos de entrar"
                  className={CAMPO}
                  data-testid="login-promo-code"
                />
              </Campo>
            </div>
          )}

          {googleDisponivel && (
            <>
              <button
                type="button"
                onClick={comGoogle}
                disabled={busyGoogle || busy}
                className="btn-vidro pill mt-6 flex w-full items-center justify-center gap-3 rounded-full px-4 py-3 text-sm font-semibold disabled:opacity-50"
                data-testid="login-google"
              >
                {busyGoogle ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="#EA4335" d="M12 10.2v3.9h5.5c-.25 1.5-1.7 4.4-5.5 4.4-3.3 0-6-2.7-6-6.1s2.7-6.1 6-6.1c1.9 0 3.2.8 3.9 1.5l2.7-2.6C16.9 3.6 14.7 2.6 12 2.6 6.9 2.6 2.8 6.7 2.8 11.8S6.9 21 12 21c6.9 0 9.4-4.8 9.4-8.6 0-.6-.1-1-.2-1.5H12z"/></svg>
                )}
                {busyGoogle ? "Abrindo o Google…" : "Continuar com Google"}
              </button>

              {/* O aviso que chega ANTES do prejuízo.
                  Num navegador embutido de rede social o login com Google
                  costuma abrir e branquear sem erro nenhum — e 100% do
                  tráfego pago chega por aí. Dizer isso depois de 8 segundos
                  de anel girando é melhor que depois de 25, mas dizer ANTES
                  do clique é melhor que as duas. O botão continua lá e
                  continua clicável: a detecção é por `userAgent` e portanto
                  é palpite, então ela informa em vez de bloquear. */}
              {embutido && !dicaPopup && (
                <p
                  className="mt-2.5 rounded-xl border border-white/12 bg-white/[0.04] px-3.5 py-2.5 text-xs leading-relaxed text-white/55"
                  data-testid="login-aviso-embutido"
                >
                  Você abriu este link dentro de um aplicativo. O login com Google
                  costuma falhar aqui —{" "}
                  <strong className="font-semibold text-white/80">criar conta com e-mail</strong>{" "}
                  logo abaixo é o caminho mais garantido.
                </p>
              )}

              {dicaPopup && (
                <p
                  className="mt-2.5 rounded-xl border border-amber-400/30 bg-amber-400/[0.08] px-3.5 py-2.5 text-xs leading-relaxed text-amber-100"
                  data-testid="login-dica-popup"
                >
                  A janela do Google não respondeu. Feche-a e tente de novo — ou{" "}
                  <strong className="font-semibold">crie sua conta com e-mail e senha</strong>{" "}
                  aqui embaixo, que funciona igual. Se você abriu este link dentro do
                  WhatsApp ou do Instagram, abra no navegador do celular.
                </p>
              )}

              <div className="my-5 flex items-center gap-3 text-[11px] uppercase tracking-[0.2em] text-white/30">
                <div className="h-px flex-1 bg-white/10" /> ou e-mail <div className="h-px flex-1 bg-white/10" />
              </div>
            </>
          )}
          {!googleDisponivel && <div className="mt-6" />}

          <form onSubmit={submit} className="space-y-3">
            {criando && (
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Seu nome"
                className={CAMPO}
                data-testid="login-name"
              />
            )}
            <input
              required
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="email@exemplo.com"
              className={CAMPO}
              data-testid="login-email"
            />
            <input
              required
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={criando ? "Senha (mín 8 caracteres)" : "Sua senha"}
              minLength={criando ? 8 : undefined}
              className={CAMPO}
              data-testid="login-password"
            />
            {criando && (
              <label className="flex cursor-pointer items-start gap-2.5 pt-1 text-xs leading-relaxed text-white/50">
                <input
                  type="checkbox"
                  required
                  checked={aceitouTermos}
                  onChange={(e) => setAceitouTermos(e.target.checked)}
                  className="mt-0.5 h-5 w-5 shrink-0 rounded border-white/20 accent-[#4FD9FF]"
                  data-testid="login-aceite-termos"
                />
                <span>
                  Li e aceito os <Link to="/termos" target="_blank" className="text-white underline">Termos de Uso</Link>{" "}
                  e a <Link to="/privacidade" target="_blank" className="text-white underline">Política de Privacidade</Link>.
                  {menorDeIdade && " Confirmo ter a autorização do responsável que informei acima."}
                </span>
              </label>
            )}
            <button
              type="submit"
              disabled={busy || (criando && !aceitouTermos)}
              className="pill btn-sapiens flex w-full items-center justify-center gap-2 rounded-full py-3.5 text-sm font-bold disabled:opacity-60"
              data-testid="login-submit"
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              {busy ? "Aguarde..." : criando ? "Criar conta" : "Entrar"}
            </button>
          </form>

          {!criando && (
            <div className="mt-3 text-center">
              <Link
                to="/esqueci-senha"
                className="inline-block py-2.5 text-sm text-white/50 hover:text-white hover:underline"
                data-testid="login-esqueci-senha"
              >
                Esqueci minha senha
              </Link>
            </div>
          )}

          <div className="mt-6 border-t border-white/8 pt-5 text-center text-xs text-white/35">
            <Link to="/termos" className="inline-block py-2 hover:text-white/70 hover:underline">Termos de Uso</Link>
            <span className="mx-2">·</span>
            <Link to="/privacidade" className="inline-block py-2 hover:text-white/70 hover:underline">Privacidade</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
