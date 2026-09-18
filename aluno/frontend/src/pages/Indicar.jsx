import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import Tela from "../components/Tela";
import { Bloco } from "../components/Esqueleto";
import { api, errMsg } from "../lib/api";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { Gift, Copy, Check, Share2, Users, Zap, Hourglass } from "lucide-react";

/**
 * Indique um amigo — o código pessoal do aluno e o que ele já rendeu.
 *
 * A regra inteira cabe numa frase, e a tela é construída para dizer essa
 * frase antes de qualquer outra coisa: **na primeira compra do amigo, você
 * ganha metade dos Sparks que ele comprou.**
 *
 * Três decisões que a tela carrega:
 *
 * · **O código é a peça principal**, em corpo grande e monoespaçado, porque a
 *   ação real do aluno é COPIAR e mandar no WhatsApp. Tudo o mais é apoio.
 * · **A promessa nunca aparece sem a condição.** "Ganhe Sparks indicando"
 *   sozinho é propaganda: quem indica dez amigos que não compram ganha zero, e
 *   descobrir isso depois é pior do que não ter lido nada. Por isso "na
 *   primeira compra" está na mesma frase, sempre.
 * · **A lista mostra quem ainda não comprou**, e diz isso com todas as
 *   letras. É o que transforma "não ganhei nada" em "ainda não ganhei", que é
 *   a verdade.
 *
 * O código é criado pelo servidor na primeira vez que esta tela abre (ver
 * `indicacoes.garantir_codigo`) — nenhuma conta precisou ser migrada.
 */

/** O convite leva o código NO LINK (`/login?convite=XXXX`), e o campo do
 *  cadastro já abre preenchido com ele (ver `Login.jsx`). O código continua
 *  escrito por extenso na mensagem porque link se perde ao ser reencaminhado
 *  numa conversa, e aí o texto é o que sobra.
 *
 *  A origem vem de `window.location.origin`, nunca de um domínio escrito à
 *  mão: o aluno está DENTRO do app quando copia isto, então o endereço certo
 *  é, por construção, o que ele já está usando. */
const CONVITE = (codigo) => `${window.location.origin}/login?convite=${encodeURIComponent(codigo)}`;

const MENSAGEM = (codigo) =>
  `Tô usando o Sapiens para estudar para o ENEM — ele mostra POR QUE você erra, não só quanto.\n\n` +
  `Criei um convite para você: ${CONVITE(codigo)}\n\n` +
  `Se pedir código na hora de criar a conta, é este: ${codigo}`;

function formatarData(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
  } catch {
    return "";
  }
}

function CartaoDoCodigo({ codigo }) {
  const [copiado, setCopiado] = useState(false);

  const copiar = async () => {
    // Copia o LINK, não só o código: um link colado numa conversa é um clique
    // para o amigo, e o código sozinho é um formulário a preencher. O texto
    // do botão diz o que vai para a área de transferência.
    //
    // Mesmo cuidado de `SparksStore`: `writeText` REJEITA no navegador
    // embutido do WhatsApp e do Instagram, que é por onde boa parte dos
    // alunos abre o produto. Sem o `catch`, a tela diria "copiado" e a pessoa
    // colaria vazio na conversa do amigo.
    try {
      await navigator.clipboard.writeText(CONVITE(codigo));
      setCopiado(true);
      toast.success("Link do convite copiado. Manda para o seu amigo.");
      setTimeout(() => setCopiado(false), 2200);
    } catch {
      toast.error("Seu navegador não deixou copiar. Anote o código: " + codigo);
    }
  };

  const compartilhar = () => {
    const texto = MENSAGEM(codigo);
    // `navigator.share` é o caminho nativo no celular (abre o seletor do
    // sistema, com o WhatsApp em primeiro); no desktop ele não existe e o
    // link `wa.me` resolve. Não é um `if (mobile)`: é um `if` na capacidade.
    if (navigator.share) {
      navigator.share({ text: texto }).catch(() => {});
      return;
    }
    window.open(`https://wa.me/?text=${encodeURIComponent(texto)}`, "_blank", "noopener");
  };

  return (
    <div className="superficie superficie-viva p-6 text-center" data-testid="indicar-codigo">
      <div className="secao-olho justify-center flex items-center gap-1.5">
        <Gift className="h-3.5 w-3.5" /> Seu código
      </div>
      <div
        className="mt-3 font-mono-alt text-3xl font-extrabold tracking-[0.18em] text-white md:text-4xl"
        data-testid="indicar-codigo-valor"
      >
        {codigo}
      </div>
      <div className="mt-5 flex flex-wrap items-center justify-center gap-2.5">
        <button
          type="button"
          onClick={copiar}
          className="btn-vidro pill inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold"
          data-testid="indicar-copiar"
        >
          {copiado ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          {copiado ? "Copiado" : "Copiar convite"}
        </button>
        <button
          type="button"
          onClick={compartilhar}
          className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold"
          data-testid="indicar-compartilhar"
        >
          <Share2 className="h-4 w-4" /> Mandar no WhatsApp
        </button>
      </div>
    </div>
  );
}

function Numero({ icone: Icone, valor, rotulo, testid }) {
  return (
    <div className="superficie p-4" data-testid={testid}>
      <div className="flex items-center gap-2 text-white/45">
        <Icone className="h-3.5 w-3.5" />
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em]">{rotulo}</span>
      </div>
      <div className="medida-n mt-1.5 text-2xl">{valor}</div>
    </div>
  );
}

export default function Indicar() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);

  useDeclararContextoMentis("Na tela de indicar um amigo.");

  useEffect(() => {
    api
      .get("/indicacoes/me")
      .then(({ data }) => setDados(data))
      .catch((e) => setErro(errMsg(e, "Não foi possível abrir seu código agora.")));
  }, []);

  if (erro) {
    return (
      <Tela olho="Indique um amigo" titulo="Quem estuda junto, passa junto." testid="indicar">
        <div className="superficie p-6 text-sm text-white/60">{erro}</div>
      </Tela>
    );
  }

  if (!dados) {
    return (
      <Tela olho="Indique um amigo" titulo="Quem estuda junto, passa junto." testid="indicar">
        <div className="space-y-3">
          <Bloco altura={160} />
          <div className="grid gap-3 sm:grid-cols-3">
            <Bloco altura={84} />
            <Bloco altura={84} />
            <Bloco altura={84} />
          </div>
        </div>
      </Tela>
    );
  }

  const { codigo, amigos, total_amigos: totalAmigos, total_sparks: totalSparks } = dados;
  const esperando = dados.aguardando_primeira_compra;

  return (
    <Tela
      olho="Indique um amigo"
      titulo="Quem estuda junto, passa junto."
      subtitulo="Quando um amigo criar a conta com o seu código e fizer a primeira compra, você ganha metade dos Sparks que ele comprou."
      voltar="/sparks"
      voltarLabel="Sparks"
      testid="indicar"
    >
      <div className="space-y-4">
        <CartaoDoCodigo codigo={codigo} />

        {/* A CONTA, com um número concreto. "Metade" é abstrato até virar
            "ele compra 1.500, você recebe 750" — e é esse par que a pessoa
            repete para o amigo. */}
        <div className="superficie p-5 text-sm leading-relaxed text-white/60">
          <span className="font-semibold text-white/85">Como funciona.</span> O link do convite já
          abre o cadastro com o seu código preenchido — e quem preferir digitar usa{" "}
          <span className="font-mono-alt font-bold text-white/85">{codigo}</span> no campo de código
          ao criar a conta. Na <strong className="font-semibold text-white/85">primeira compra</strong>{" "}
          dele, metade dos Sparks daquele pacote cai no seu saldo — se ele comprar 1.500, você recebe
          750. Vale uma vez por amigo, e não há limite de amigos.
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <Numero icone={Users} valor={totalAmigos} rotulo="Amigos" testid="indicar-total-amigos" />
          <Numero icone={Zap} valor={totalSparks} rotulo="Sparks ganhos" testid="indicar-total-sparks" />
          <Numero icone={Hourglass} valor={esperando} rotulo="Sem comprar ainda" testid="indicar-esperando" />
        </div>

        <div className="superficie p-5" data-testid="indicar-lista">
          <div className="secao-olho">Quem entrou pelo seu código</div>
          {amigos.length === 0 ? (
            <p className="mt-2.5 text-sm leading-relaxed text-white/50">
              Ninguém ainda. Mande seu código para alguém da sua turma — quem estuda junto
              costuma render mais que quem estuda sozinho, e aqui isso também vale em Sparks.
            </p>
          ) : (
            <div className="mt-3 divide-y divide-white/[0.07]">
              {amigos.map((a, i) => (
                <div key={i} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-white/85">{a.nome}</div>
                    <div className="text-xs text-white/40">entrou em {formatarData(a.entrou_em)}</div>
                  </div>
                  {a.ja_comprou ? (
                    <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1.5 text-xs font-bold text-emerald-300">
                      <Zap className="h-3.5 w-3.5" /> +{a.premio_sparks}
                    </span>
                  ) : (
                    <span className="shrink-0 text-xs text-white/35">ainda não comprou</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="text-center text-xs text-white/35">
          Os Sparks ganhos aqui entram no mesmo saldo de sempre —{" "}
          <Link to="/sparks" className="underline hover:text-white/60">
            ver seu saldo
          </Link>
          .
        </div>
      </div>
    </Tela>
  );
}
