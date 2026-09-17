import { useState } from "react";
import { Play, ExternalLink } from "lucide-react";
import { MENTOR, thumbDoVideo, embedDoVideo, linkDoVideo } from "../lib/mentor";

/**
 * O vídeo de apresentação do mentor — quem ele é, contado por ele.
 *
 * **Fachada, não iframe direto.** A tela mostra a thumbnail do YouTube com um
 * botão de play; o player só é montado no CLIQUE. Três razões, nesta ordem:
 *
 * 1. **Privacidade.** Um iframe do YouTube carregado junto com a página grava
 *    no navegador de quem nem assistiu. Esta é uma tela que fala com menor de
 *    idade, e o `youtube-nocookie.com` só entra depois de um gesto deliberado.
 * 2. **Peso.** O player do YouTube traz ~1 MB de JavaScript de terceiro. A
 *    landing é a tela que mais gente abre uma vez só, muitas vezes no 4G do
 *    celular, e ela não pode pagar isso para quem veio ler a proposta.
 * 3. **Layout.** A thumbnail tem proporção conhecida (16:9), então o espaço
 *    já nasce reservado e nada pula quando o vídeo entra.
 *
 * `maxresdefault` não existe para todo vídeo do YouTube — quando falta, o
 * serviço devolve uma imagem cinza de 120px em vez de um 404, e é por isso que
 * o fallback é por TAMANHO e não por erro de carregamento: `onError` nunca
 * dispararia. `hqdefault` existe sempre.
 */
export default function VideoDoMentor({ className = "", testid = "video-mentor" }) {
  const [tocando, setTocando] = useState(false);
  const [thumb, setThumb] = useState(() => thumbDoVideo("maxresdefault"));

  return (
    <div className={className} data-testid={testid}>
      <div className="relative aspect-video w-full overflow-hidden rounded-3xl border border-white/12 bg-black/40">
        {tocando ? (
          <iframe
            src={embedDoVideo()}
            title={MENTOR.video.titulo}
            className="absolute inset-0 h-full w-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            data-testid={`${testid}-player`}
          />
        ) : (
          <button
            type="button"
            onClick={() => setTocando(true)}
            className="group absolute inset-0 h-full w-full"
            aria-label={`Assistir: ${MENTOR.video.titulo}`}
            data-testid={`${testid}-play`}
          >
            <img
              src={thumb}
              alt=""
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
              loading="lazy"
              // `maxres` ausente volta como uma imagem cinza de 120px de
              // largura, não como erro. Medir é o único jeito de detectar.
              onLoad={(e) => {
                if (e.currentTarget.naturalWidth < 400) setThumb(thumbDoVideo("hqdefault"));
              }}
            />
            {/* Véu leve e uniforme, não um degradê pesado no pé: a thumbnail
                do YouTube já é uma peça gráfica com título próprio, e escurecer
                a base dela para escrever OUTRO título por cima empilha dois
                títulos que dizem a mesma coisa. O que fica por cima é só a
                etiqueta — o nome do vídeo vive no `aria-label` do botão, para
                quem navega por leitor de tela, e no link do YouTube abaixo. */}
            <span className="absolute inset-0 bg-black/20 transition-colors duration-300 group-hover:bg-black/10" />
            <span className="absolute left-1/2 top-1/2 flex h-16 w-16 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/30 bg-black/55 text-white backdrop-blur-sm transition-transform duration-300 group-hover:scale-110">
              <Play className="ml-0.5 h-6 w-6 fill-current" strokeWidth={0} />
            </span>
            <span className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-black/55 px-2.5 py-1 font-mono-alt text-[9px] font-bold uppercase tracking-[0.2em] text-[#7FD8FF] backdrop-blur-sm sm:left-4 sm:top-4">
              Conheça {MENTOR.nome}
            </span>
          </button>
        )}
      </div>

      {/* A saída para o YouTube fica FORA do quadro, e só depois dele: quem
          quiser ver na tela cheia, no app do YouTube ou depois, tem o caminho —
          sem que ele compita com o play. */}
      <a
        href={linkDoVideo()}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2 inline-flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70"
        data-testid={`${testid}-youtube`}
      >
        <ExternalLink className="h-3 w-3" /> Assistir no YouTube
      </a>
    </div>
  );
}
