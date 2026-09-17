/**
 * Quem é o mentor do Sapiens — um lugar só.
 *
 * Ele aparece em seis telas (landing, login, mentoria, cursos, aula ao vivo e
 * painel) e o nome dele passou a ser dito em 2026-09-17: até então o produto
 * inteiro se referia a "o 1º colocado de Medicina da USP", sem nome. Uma
 * pessoa anônima com uma credencial enorme é menos confiável, não mais — quem
 * chega pela primeira vez não tem como checar nada, e um nome é a primeira
 * coisa que se pode checar.
 *
 * Constante de módulo e não chamada de API porque isto é COPY: aparece na
 * landing, onde não há sessão, e mudar uma vez por ano não justifica uma
 * requisição por abertura de tela. O mesmo critério de `lib/enem.js`.
 *
 * O backend tem a sua própria cópia em `cursos.LIVE_APRESENTADOR`, e as duas
 * precisam mudar juntas — é o mesmo acordo já documentado para as datas do
 * ENEM. O que o servidor manda é o que a tela da aula ao vivo mostra; esta
 * constante serve às telas que não chamam aquela rota.
 */
export const MENTOR = {
  nome: "Vitor Lara",
  // NÃO existe `primeiroNome`, e a ausência é a regra: ele é sempre "Vitor
  // Lara", nunca "o Vitor". Existia um `primeiroNome` aqui e seis telas o
  // usavam — "o Vitor dá aula ao vivo", "a mentoria com o Vitor". Tratar por
  // primeiro nome é o registro que se usa para um conhecido, e ele desfaz
  // exatamente o que o nome completo foi posto para construir: a credencial
  // pertence a uma pessoa pública, verificável, e o nome inteiro é o que se
  // pode checar. Quem precisar do nome no texto usa `MENTOR.nome`.
  titulo: "1º colocado de Medicina da USP",
  // A foto mora em `public/mentor-usp.jpg`. Ver `components/MentorUSP.jsx`:
  // quando o arquivo falta, o componente cai na medalha em vez de mostrar o
  // ícone de imagem quebrada do navegador.
  foto: "/mentor-usp.jpg",
  // O vídeo de apresentação. `inicio` é o segundo em que ele começa a
  // interessar — veio no próprio link que o usuário mandou (`&t=791s`), e
  // respeitá-lo é a diferença entre abrir no ponto certo e abrir em treze
  // minutos de contexto que o aluno não pediu.
  video: {
    id: "WH2R_VlZgto",
    inicio: 791,
    titulo: "Como Vitor Lara passou em 1º lugar em Medicina na USP",
  },
};

/** A thumbnail oficial do YouTube. `maxres` existe para este vídeo (conferido);
 *  `hq` é o fallback universal, porque `maxres` não é gerada para todo vídeo e
 *  quando falta o YouTube devolve uma imagem cinza de 120px. */
export const thumbDoVideo = (qualidade = "maxresdefault") =>
  `https://img.youtube.com/vi/${MENTOR.video.id}/${qualidade}.jpg`;

/** O endereço para ASSISTIR fora do app (nova aba), já no ponto certo. */
export const linkDoVideo = () =>
  `https://www.youtube.com/watch?v=${MENTOR.video.id}&t=${MENTOR.video.inicio}s`;

/** O `src` do player embutido. `youtube-nocookie.com` e não `youtube.com`: o
 *  domínio sem cookies não grava nada no navegador do aluno enquanto ele não
 *  dá play, o que importa numa página que fala com menor de idade. */
export const embedDoVideo = () =>
  `https://www.youtube-nocookie.com/embed/${MENTOR.video.id}` +
  `?start=${MENTOR.video.inicio}&autoplay=1&rel=0&modestbranding=1`;
