/**
 * O HANDLER DE AUTENTICAÇÃO DO FIREBASE, SERVIDO NO PRÓPRIO DOMÍNIO.
 *
 * ---------------------------------------------------------------------------
 * O DEFEITO QUE ISTO CONSERTA
 * ---------------------------------------------------------------------------
 *
 * `signInWithPopup` abre o handler do Firebase e espera que ele devolva o
 * resultado para a aba de origem. Com `authDomain` valendo
 * `sapiens-dataset.firebaseapp.com`, esse handler mora em OUTRO site, e a
 * devolução depende de armazenamento de terceiro — exatamente o que o Chrome
 * particiona e o que o WKWebView do Instagram bloqueia.
 *
 * Sintoma medido: a janela abre, a pessoa escolhe a conta, e a tela fica
 * branca. Sem erro, sem exceção, sem nada para o `catch` pegar. É o caminho
 * de MENOR fricção do cadastro morrendo em silêncio — e, em tráfego pago de
 * Instagram, é onde vai 100% dos cliques.
 *
 * Com este worker, `/__/auth/*` passa a ser servido por
 * `sapiens-aluno.pages.dev`. O handler vira mesma origem, a devolução deixa
 * de depender de terceiro, e a partição do navegador não tem o que bloquear.
 * `REACT_APP_FIREBASE_AUTH_DOMAIN` acompanha (ver `.env.example`).
 *
 * DORMENTE desde 2026-10-28: o `authDomain` voltou a ser o do Firebase porque
 * o Google recusa `https://sapiens-aluno.pages.dev/__/auth/handler` com
 * `redirect_uri_mismatch` — o URI nunca foi somado no OAuth Client. Ninguém
 * chama estes caminhos até o `.env` voltar para o domínio do app. O arquivo
 * fica para que essa volta seja só trocar a variável e publicar.
 *
 * ---------------------------------------------------------------------------
 * ESTE ARQUIVO PASSA A ATENDER **TODO** O TRÁFEGO DO SITE
 * ---------------------------------------------------------------------------
 *
 * Um `_worker.js` na raiz da saída de build coloca o Cloudflare Pages em modo
 * avançado: ele para de servir arquivo estático sozinho e passa tudo por
 * aqui. Ou seja, **um erro neste arquivo derruba o site inteiro**, não só o
 * login.
 *
 * Por isso a regra é uma só: qualquer caminho que não seja do Firebase, e
 * qualquer falha do proxy, terminam em `env.ASSETS.fetch(request)`. O caminho
 * de exceção serve o site; nunca o contrário.
 *
 * Ele mora em `public/` de propósito — o CRA copia tudo de lá para `build/`,
 * então sobrevive a todo rebuild sem ninguém precisar lembrar.
 */

const ORIGEM_FIREBASE = "https://sapiens-dataset.firebaseapp.com";
const PREFIXOS = ["/__/auth/", "/__/firebase/"];

export default {
  async fetch(request, env) {
    let url;
    try {
      url = new URL(request.url);
    } catch {
      return env.ASSETS.fetch(request);
    }

    const ehDoFirebase = PREFIXOS.some((p) => url.pathname.startsWith(p));
    if (!ehDoFirebase) return env.ASSETS.fetch(request);

    try {
      const alvo = new URL(url.pathname + url.search, ORIGEM_FIREBASE);

      /* `redirect: "manual"` é obrigatório, e não cautela.
       *
       * O handler responde 302 para `accounts.google.com` no meio do fluxo.
       * Com o padrão (`follow`), o worker seguiria esse salto NO SERVIDOR e
       * devolveria o HTML do Google servido a partir do nosso domínio — o
       * navegador veria a tela de login do Google numa origem que não é a do
       * Google, o que quebra o fluxo e o próprio Google recusa. Devolvendo o
       * 302 cru, quem navega é o navegador, que é quem deve navegar. */
      const resposta = await fetch(new Request(alvo, request), { redirect: "manual" });

      /* A resposta é reconstruída porque a original é imutável, e porque o
       * `Location` de um 302 precisa continuar exatamente como veio. */
      return new Response(resposta.body, {
        status: resposta.status,
        statusText: resposta.statusText,
        headers: resposta.headers,
      });
    } catch {
      /* O proxy falhou (Firebase fora do ar, DNS, timeout). Cair no asset
       * devolve 404 para um caminho que não é arquivo — feio, mas local. A
       * alternativa seria um 500 saindo do worker, que numa configuração de
       * modo avançado é indistinguível de "o site caiu". */
      return env.ASSETS.fetch(request);
    }
  },
};
