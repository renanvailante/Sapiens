/**
 * A detecção do navegador embutido decide o que a tela de cadastro diz a
 * 100% do tráfego pago antes de a pessoa tocar no botão do Google. É pura,
 * e por isso é travada aqui — no navegador não dá para emular o `userAgent`
 * do Instagram de fora da página.
 */
import { navegadorEmbutido, esperaAteAvisarDoPopup } from "./navegador";

const IOS_INSTAGRAM =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/22F76 Instagram 336.0.0.25.90";
const ANDROID_FACEBOOK =
  "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/462.0.0.33.83;]";
const SAFARI_IOS =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1";
const CHROME_ANDROID =
  "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36";

test("reconhece o navegador do Instagram — de onde vem o tráfego pago", () => {
  expect(navegadorEmbutido(IOS_INSTAGRAM)).toBe(true);
});

test("reconhece o navegador do Facebook no Android", () => {
  expect(navegadorEmbutido(ANDROID_FACEBOOK)).toBe(true);
});

test("não confunde Safari nem Chrome de verdade com navegador embutido", () => {
  // Falso positivo aqui custaria um aviso desnecessário para quem abriu no
  // navegador normal, onde o login com Google funciona.
  expect(navegadorEmbutido(SAFARI_IOS)).toBe(false);
  expect(navegadorEmbutido(CHROME_ANDROID)).toBe(false);
});

test("sem userAgent nenhum, não acusa nada", () => {
  expect(navegadorEmbutido("")).toBe(false);
});

test("a espera até o aviso encurta só dentro do aplicativo", () => {
  // 25s é calibrado para gente que demora a escolher a conta; dentro do
  // aplicativo a espera não é lentidão, é o defeito acontecendo em silêncio.
  expect(esperaAteAvisarDoPopup(SAFARI_IOS)).toBe(25_000);
  expect(esperaAteAvisarDoPopup(IOS_INSTAGRAM)).toBe(8_000);
  expect(esperaAteAvisarDoPopup(IOS_INSTAGRAM)).toBeLessThan(esperaAteAvisarDoPopup(CHROME_ANDROID));
});
