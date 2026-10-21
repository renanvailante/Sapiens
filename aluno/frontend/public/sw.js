/* Service worker do Sapiens — deliberadamente MÍNIMO.
 *
 * Ele existe por DUAS razões:
 *
 *  1. Navegadores Chromium só oferecem a instalação do app (o evento
 *     `beforeinstallprompt`) para páginas que tenham um service worker com
 *     handler de `fetch`. Sem este arquivo, o botão "Instalar o Sapiens" não
 *     teria como existir no Android, no Windows nem no macOS.
 *  2. A notificação no celular (Web Push): o aviso chega com o app FECHADO, e
 *     quem o recebe e desenha é este arquivo — `push` mostra, e
 *     `notificationclick` abre a tela de que a notificação fala.
 *
 * O que ele NÃO faz, de propósito: **não guarda nada em cache.** Um cache de
 * app shell aqui significaria alunos presos numa versão antiga do bundle
 * depois de cada deploy, e o produto já teve incidente de deploy silenciosamente
 * anulado — um service worker com cache transformaria esse tipo de falha em
 * algo que nem um recarregar forçado resolve. O handler de `fetch` é um
 * repasse para a rede, e só.
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

/* ---------------------------------------------------------------- push --
 * O servidor (`push_service.py`) manda JSON cifrado: { titulo, corpo, rota,
 * tag, tipo }. Todo texto vem de lá, montado com números do próprio aluno;
 * aqui só se desenha. A `tag` é uma só por dia: um aviso novo substitui o
 * anterior na bandeja em vez de empilhar.
 */
self.addEventListener("push", (evento) => {
  let dados = {};
  try {
    dados = evento.data ? evento.data.json() : {};
  } catch (e) {
    dados = { corpo: evento.data ? evento.data.text() : "" };
  }
  const titulo = dados.titulo || "Sapiens";
  evento.waitUntil(
    self.registration.showNotification(titulo, {
      body: dados.corpo || "",
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      tag: dados.tag || "sapiens",
      lang: "pt-BR",
      data: { rota: dados.rota || "/hoje" },
    }),
  );
});

/** Só caminho DESTE site. Uma rota que chegasse como `//outro.site` ou
 *  `https://…` abriria outra origem a partir de um toque na notificação. */
function rotaSegura(rota) {
  return typeof rota === "string" && rota.startsWith("/") && !rota.startsWith("//") ? rota : "/hoje";
}

self.addEventListener("notificationclick", (evento) => {
  evento.notification.close();
  const destino = new URL(rotaSegura(evento.notification.data && evento.notification.data.rota), self.location.origin).href;
  evento.waitUntil(
    (async () => {
      // Uma aba do Sapiens já aberta é reaproveitada: abrir uma segunda janela
      // a cada toque deixaria o aluno com três cópias do app no celular.
      const janelas = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      for (const janela of janelas) {
        if (new URL(janela.url).origin === self.location.origin && "focus" in janela) {
          await janela.focus();
          if ("navigate" in janela) return janela.navigate(destino);
          return undefined;
        }
      }
      return self.clients.openWindow(destino);
    })(),
  );
});
