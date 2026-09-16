/* Service worker do Sapiens — deliberadamente MÍNIMO.
 *
 * Ele existe por UMA razão: navegadores Chromium só oferecem a instalação do
 * app (o evento `beforeinstallprompt`) para páginas que tenham um service
 * worker com handler de `fetch`. Sem este arquivo, o botão "Instalar o
 * Sapiens" não teria como existir no Android, no Windows nem no macOS.
 *
 * O que ele NÃO faz, de propósito: **não guarda nada em cache.** Um cache de
 * app shell aqui significaria alunos presos numa versão antiga do bundle
 * depois de cada deploy, e o produto já teve incidente de deploy silenciosamente
 * anulado — um service worker com cache transformaria esse tipo de falha em
 * algo que nem um recarregar forçado resolve. O handler abaixo é um repasse
 * para a rede, e só.
 *
 * `skipWaiting` + `clients.claim`: uma versão nova deste arquivo substitui a
 * anterior imediatamente, sem esperar todas as abas fecharem.
 */
self.addEventListener("install", (evento) => {
  evento.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", () => {
  // Sem `respondWith`: o navegador segue com a requisição normal. O handler
  // precisa EXISTIR para o app ser instalável; ele não precisa interferir.
});
