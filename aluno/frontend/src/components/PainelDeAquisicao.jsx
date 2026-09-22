import { useMemo } from "react";

/**
 * DE ONDE VIERAM OS ALUNOS — o leitor que faltava.
 *
 * O backend já carimba a origem de aquisição em cada conta nova:
 * `auth._registrar_origem` grava os sete campos de `models.PARAMS_DE_ORIGEM`
 * (`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`,
 * `campanha_id`, `fbclid`) no documento do usuário, nos DOIS caminhos de
 * cadastro — e-mail (`auth.py:339`) e Google (`auth.py:475`).
 *
 * Só que **não havia uma única tela lendo isso**. O dado era gravado desde
 * sempre e morria no banco: pagar mídia e depois não saber qual anúncio
 * trouxe qual aluno é o desfecho mais caro possível de uma campanha, porque
 * o dinheiro é gasto por inteiro e o aprendizado é zero.
 *
 * ---------------------------------------------------------------------------
 * POR QUE ISTO É FRONTEND PURO, E NÃO UM ENDPOINT NOVO
 * ---------------------------------------------------------------------------
 *
 * `GET /admin/users` já devolve o documento inteiro de cada aluno, menos
 * `_id` e `password_hash` (`admin_routes.py:76`). Os campos de origem já
 * chegam aqui. Um endpoint de relatório seria uma segunda fonte para a mesma
 * verdade, uma segunda coisa para manter em dia, e um deploy de backend — em
 * troca de uma agregação que cabe em trinta linhas sobre dados que a tela já
 * tem na mão.
 *
 * A base de alunos é da ordem de centenas: agregar em memória aqui é o mesmo
 * raciocínio que `promo_codes_routes.uso_por_codigo` já faz no servidor.
 *
 * ---------------------------------------------------------------------------
 * O QUE ESTE PAINEL NÃO FAZ
 * ---------------------------------------------------------------------------
 *
 * **Não mostra taxa de conversão.** Ele conhece o denominador errado: quem
 * chegou à landing e não se cadastrou nunca vira documento de usuário. Clique
 * e impressão moram no painel do Meta, e juntar os dois é trabalho humano.
 * Uma coluna "conversão" aqui seria um número inventado com cara de medida —
 * e o produto não faz isso nem com aluno nem com o dono.
 *
 * **Não mostra compra.** A primeira versão tinha uma coluna "Compraram" lendo
 * `total_gasto_cents`/`compras` — campos que NÃO EXISTEM neste payload
 * (`admin_routes.py:88-95` enriquece com `sparks_balance`,
 * `questoes_respondidas`, `dias_ativos` e `ultima_atividade`, e mais nada).
 * A coluna teria marcado zero para sempre, em toda linha, sem nenhum sinal de
 * que o campo não existia — uma medida falsa é pior que uma medida ausente,
 * porque a ausente você vai procurar. Compra mora em `/admin/transacoes`.
 *
 * **Não separa dois criativos do mesmo ângulo.** A chave é `utm_content`, e
 * duas peças com o mesmo `utm_content` colapsam numa linha. Para distinguir,
 * basta variar `utm_content` na URL do anúncio — o frontend preserva a query
 * inteira (`lib/campanha.js`) e o backend grava os sete campos.
 */

/** Um aluno é "pago" quando a conta carrega qualquer marca de campanha.
 *  `utm_source` é a mais confiável: é o único que toda URL de anúncio leva. */
function ehDeCampanha(u) {
  return Boolean(u.utm_source || u.utm_campaign || u.utm_content || u.campanha_id);
}

/** O rótulo da linha: o ângulo, quando existe; senão o que houver de mais
 *  específico. Nunca "desconhecido" para quem TEM origem — isso esconderia
 *  uma campanha mal etiquetada atrás de um balde genérico. */
function angulo(u) {
  return u.utm_content || u.utm_campaign || u.utm_source || "(sem etiqueta)";
}

export default function PainelDeAquisicao({ users = [] }) {
  const linhas = useMemo(() => {
    const porAngulo = new Map();

    for (const u of users) {
      if (!ehDeCampanha(u)) continue;
      const chave = angulo(u);
      const linha = porAngulo.get(chave) || {
        chave,
        origem: u.utm_source || "—",
        campanha: u.utm_campaign || "—",
        cadastros: 0,
        responderam: 0,
        questoes: 0,
        diasAtivos: 0,
      };
      linha.cadastros += 1;
      // "Respondeu" é derivado, não um evento à parte: `questoes_respondidas`
      // já vem no payload e é a única definição de ativação que não duplica
      // telemetria que já existe (mesma disciplina de `growth_events`).
      if ((u.questoes_respondidas || 0) > 0) linha.responderam += 1;
      linha.questoes += u.questoes_respondidas || 0;
      linha.diasAtivos += u.dias_ativos || 0;
      porAngulo.set(chave, linha);
    }

    return [...porAngulo.values()].sort((a, b) => b.cadastros - a.cadastros);
  }, [users]);

  const totalPago = linhas.reduce((s, l) => s + l.cadastros, 0);
  const organicos = users.length - totalPago;

  if (linhas.length === 0) {
    return (
      <section className="superficie mt-6 rounded-2xl p-5" data-testid="painel-aquisicao-vazio">
        <div className="secao-olho">De onde vieram</div>
        <p className="mt-2 text-sm text-white/55">
          Nenhuma conta com marca de campanha ainda. Assim que alguém se cadastrar
          vindo de uma URL com <code className="text-white/75">utm_source</code>, o
          ângulo aparece aqui — a origem é gravada no cadastro, não depende de cupom
          nem de pixel.
        </p>
      </section>
    );
  }

  return (
    <section className="superficie mt-6 rounded-2xl p-5" data-testid="painel-aquisicao">
      <div className="secao-cabeca">
        <div>
          <div className="secao-olho">De onde vieram</div>
          <h2 className="secao-titulo mt-1">Cadastros por ângulo de campanha</h2>
        </div>
        <span className="chip">
          {totalPago} de campanha · {organicos} orgânico{organicos === 1 ? "" : "s"}
        </span>
      </div>

      {/* `corta-rolagem` em vez de `tira-rolavel`: tabela não sobrevive a
          `display:flex` — ver `ux/padroes-de-tela.md`. */}
      <div className="corta-rolagem -mx-1 overflow-x-auto px-1">
        <table className="w-full min-w-[520px] border-collapse text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-[0.14em] text-white/35">
              <th className="pb-2 pr-3 font-semibold">Ângulo</th>
              <th className="pb-2 pr-3 font-semibold">Origem</th>
              <th className="pb-2 pr-3 text-right font-semibold">Cadastros</th>
              <th className="pb-2 pr-3 text-right font-semibold">Responderam</th>
              <th className="pb-2 pr-3 text-right font-semibold">Questões</th>
              <th className="pb-2 text-right font-semibold">Dias ativos</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.chave} className="border-t border-white/8" data-testid={`aquisicao-${l.chave}`}>
                <td className="py-2.5 pr-3 font-bold text-white">{l.chave}</td>
                <td className="py-2.5 pr-3 text-white/45">
                  {l.origem}
                  {l.campanha !== "—" && <span className="text-white/25"> · {l.campanha}</span>}
                </td>
                <td className="py-2.5 pr-3 text-right font-mono-alt font-bold text-white/85">{l.cadastros}</td>
                <td className="py-2.5 pr-3 text-right font-mono-alt text-white/70">{l.responderam}</td>
                <td className="py-2.5 pr-3 text-right font-mono-alt text-white/45">{l.questoes}</td>
                <td className="py-2.5 text-right font-mono-alt text-white/45">{l.diasAtivos}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-[11px] leading-relaxed text-white/30">
        Cadastros, não cliques: quem viu a landing e não criou conta não aparece aqui —
        esse número mora no painel do Meta. “Responderam” é quem já tem pelo menos uma
        questão registrada. Compra não aparece neste payload; veja
        <span className="text-white/45"> /admin/transacoes</span>.
      </p>
    </section>
  );
}
