/**
 * Uma chave por TENTATIVA de uma ação paga.
 *
 * Enquanto ela não muda, o servidor trata qualquer reenvio como retry da mesma
 * ação e não cobra de novo — é o que protege o aluno do duplo clique, do retry
 * do axios e do F5 no meio. O gesto que isto cobre não é raro: no celular, o
 * toque duplo num botão que demora a responder é o comportamento normal.
 *
 * Mora em `lib/` e não dentro de uma tela porque três compras já precisavam
 * dela (correção de redação, digitalização da foto e montagem do cronograma) e
 * a terceira cópia seria a primeira a divergir.
 *
 * Quem consome do outro lado: `redacao_routes._reivindicar` e
 * `cronograma_routes._reivindicar_montagem`.
 */
export function novaChave(prefixo = "sap") {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `${prefixo}-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

/**
 * O par da chave: a trava de "uma ação por vez", do lado do navegador.
 *
 * A chave sozinha NÃO resolve o duplo clique — ela só resolve se as duas
 * chamadas mandarem a MESMA chave. Um `novaChave()` gerado dentro do
 * manipulador de clique gera duas chaves diferentes em dois cliques, e o
 * servidor, corretamente, trata as duas como duas ações e cobra duas vezes.
 *
 * `desabilitado`/`setEstado` não bastam: `setState` do React não é síncrono, e
 * dois cliques em 50ms acontecem os dois antes da re-renderização que
 * desabilita o botão. Uma `ref` muda no mesmo instante em que é escrita, que é
 * o que um portão de concorrência precisa ser.
 *
 * Uso:
 *
 *     const portao = useRef(criarPortao());
 *     ...
 *     if (!portao.current.entrar()) return;      // já tem uma em voo
 *     try { await api.post(url, { idempotency_key: portao.current.chave }); portao.current.concluir(); }
 *     finally { portao.current.sair(); }
 *
 * `concluir()` é o que troca a chave: enquanto a ação não terminar bem, uma
 * nova tentativa reusa a mesma — é o mesmo pedido, e o servidor tem de
 * reconhecê-lo como tal.
 */
export function criarPortao(prefixo = "sap") {
  return {
    chave: novaChave(prefixo),
    emVoo: false,
    entrar() {
      if (this.emVoo) return false;
      this.emVoo = true;
      return true;
    },
    sair() {
      this.emVoo = false;
    },
    concluir() {
      this.chave = novaChave(prefixo);
    },
  };
}
