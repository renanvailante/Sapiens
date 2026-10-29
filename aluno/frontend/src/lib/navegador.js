/**
 * O NAVEGADOR EMBUTIDO DAS REDES SOCIAIS.
 *
 * Quem toca num anúncio do Instagram ou do Facebook **não** abre o Chrome ou
 * o Safari: abre um navegador embutido dentro do próprio aplicativo (o
 * "in-app browser", `WKWebView` no iOS, `WebView` no Android). Ele renderiza
 * quase tudo igual, e por isso passa despercebido — até bater numa das coisas
 * que ele faz diferente.
 *
 * ---------------------------------------------------------------------------
 * POR QUE O SAPIENS PRECISA SABER DISTO
 * ---------------------------------------------------------------------------
 *
 * O login com Google usa `signInWithPopup` (`lib/firebase.js`), e o handler do
 * Firebase mora em OUTRA origem (`sapiens-dataset.firebaseapp.com`, enquanto o
 * app é servido de `sapiens-aluno.pages.dev` — e `pages.dev` está na Public
 * Suffix List, então são sites distintos por definição). A janela precisa
 * devolver o resultado para a aba de origem passando por armazenamento de
 * terceiro, que é exatamente o que esses navegadores particionam.
 *
 * O desfecho medido e documentado em [[contas-e-acesso]]: no Android o
 * `window.open` falha rápido e o Firebase levanta um erro tratável; **no iOS
 * a janela abre, a pessoa escolhe a conta, e a tela fica branca** — sem erro,
 * sem exceção, sem nada para o `catch` pegar. O botão continua escrito
 * "Abrindo o Google…" com o anel girando, que lê como "está funcionando".
 *
 * Isso é caro em tráfego orgânico e é caríssimo em tráfego pago: é o caminho
 * de MENOR fricção do cadastro (nenhum campo para digitar) morrendo em
 * silêncio justamente para os 100% de visitantes que vieram de um anúncio.
 *
 * ---------------------------------------------------------------------------
 * O QUE ESTA DETECÇÃO PODE E NÃO PODE FAZER
 * ---------------------------------------------------------------------------
 *
 * Ela é por `userAgent`, e portanto é um palpite bem-informado, não um fato.
 * Por isso **nada aqui bloqueia caminho nenhum**: o botão do Google continua
 * lá e continua clicável. O que a detecção muda é só o que a pessoa SABE
 * antes de clicar, e em quanto tempo o aviso aparece se ela clicar mesmo
 * assim. Um falso positivo custa um aviso a mais; um falso negativo devolve
 * exatamente o comportamento de antes. Nenhum dos dois quebra o cadastro.
 *
 * A cura de verdade é servir o handler no próprio domínio (`public/_worker.js`
 * reencaminhando `/__/auth/*`). O worker já existe, mas o Google só aceita
 * esse handler depois que o URI dele for somado no OAuth Client — até lá o
 * `authDomain` é o do Firebase e vale tudo o que está acima ([[contas-e-acesso]]).
 * Enquanto ela não vem, isto evita que a pessoa fique olhando um anel girar.
 */

/** As marcas que os aplicativos deixam no `userAgent`. `FBAN`/`FBAV`/`FB_IAB`
 *  são do Facebook e do Messenger; `Instagram` é literal. As outras entram
 *  porque o produto circula por link de WhatsApp e o defeito é o mesmo. */
const MARCAS = ["FBAN", "FBAV", "FB_IAB", "Instagram", "Line/", "Twitter", "MicroMessenger"];

/**
 * A página está rodando dentro do navegador de um aplicativo?
 *
 * Lido na hora e não memorizado em constante de módulo: em teste o
 * `userAgent` é trocado entre casos, e um valor congelado na importação
 * tornaria o próprio módulo não testável.
 */
export function navegadorEmbutido(ua) {
  const agente = ua ?? (typeof navigator === "undefined" ? "" : navigator.userAgent || "");
  return MARCAS.some((marca) => agente.includes(marca));
}

/**
 * Quanto esperar antes de avisar que a janela do Google não respondeu.
 *
 * 25 segundos é o número calibrado para gente que simplesmente demora a
 * escolher a conta — cancelar antes disso seria cancelar pessoa lenta. Mas
 * num navegador embutido a espera não é lentidão, é o defeito conhecido
 * acontecendo, e 25 segundos olhando um anel girar é tempo suficiente para a
 * pessoa desistir e fechar a aba. Oito segundos é mais que o dobro do que
 * um login com Google que FUNCIONA costuma levar.
 */
export function esperaAteAvisarDoPopup(ua) {
  return navegadorEmbutido(ua) ? 8_000 : 25_000;
}
