import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Ditado por voz usando o reconhecimento do PRÓPRIO navegador (Web Speech API).
 *
 * Nenhum áudio sai do aparelho do aluno pelo Sapiens: o navegador transcreve e
 * o que o app recebe é texto. Isso resolve as duas coisas ao mesmo tempo —
 * não trafegamos gravação de voz de menor de idade para servidor nenhum, e
 * ditar não custa uma API de transcrição por minuto falado.
 *
 * O preço é que nem todo navegador tem: Safari no iOS e Chrome/Edge têm,
 * Firefox não. `disponivel` é falso nesse caso e a interface simplesmente não
 * oferece o microfone, em vez de mostrar um botão que não faz nada.
 */
export default function useDitado({ idioma = "pt-BR", aoTexto } = {}) {
  const [ouvindo, setOuvindo] = useState(false);
  const [parcial, setParcial] = useState("");
  const [erro, setErro] = useState(null);
  const reconhecimentoRef = useRef(null);
  const aoTextoRef = useRef(aoTexto);
  aoTextoRef.current = aoTexto;

  const Motor =
    typeof window !== "undefined" &&
    (window.SpeechRecognition || window.webkitSpeechRecognition);
  const disponivel = Boolean(Motor);

  const parar = useCallback(() => {
    try {
      reconhecimentoRef.current?.stop();
    } catch {
      /* já estava parado */
    }
    setOuvindo(false);
  }, []);

  const iniciar = useCallback(() => {
    if (!Motor || reconhecimentoRef.current) return;
    setErro(null);
    setParcial("");
    const r = new Motor();
    r.lang = idioma;
    // `continuous`: o aluno vai ditar a semana inteira numa tirada só ("aula
    // de segunda a sexta de manhã, inglês terça à noite..."). Sem isso o
    // reconhecimento corta na primeira pausa e ele perde metade da frase.
    r.continuous = true;
    r.interimResults = true;

    r.onresult = (evento) => {
      let finalizado = "";
      let emCurso = "";
      for (let i = evento.resultIndex; i < evento.results.length; i += 1) {
        const trecho = evento.results[i][0].transcript;
        if (evento.results[i].isFinal) finalizado += trecho;
        else emCurso += trecho;
      }
      setParcial(emCurso);
      if (finalizado.trim()) aoTextoRef.current?.(finalizado.trim());
    };
    r.onerror = (evento) => {
      const codigo = evento?.error;
      if (codigo === "not-allowed" || codigo === "service-not-allowed") {
        setErro("Seu navegador bloqueou o microfone. Libere o acesso e tente de novo.");
      } else if (codigo === "no-speech") {
        setErro("Não ouvi nada. Fale mais perto do microfone.");
      } else if (codigo !== "aborted") {
        setErro("O reconhecimento de voz falhou. Você pode digitar no campo abaixo.");
      }
      setOuvindo(false);
    };
    r.onend = () => {
      reconhecimentoRef.current = null;
      setOuvindo(false);
      setParcial("");
    };

    reconhecimentoRef.current = r;
    try {
      r.start();
      setOuvindo(true);
    } catch {
      reconhecimentoRef.current = null;
      setErro("Não consegui abrir o microfone agora.");
    }
  }, [Motor, idioma]);

  // Sair da tela com o microfone aberto deixaria o indicador de gravação do
  // navegador aceso numa página que nem existe mais.
  useEffect(() => () => {
    try {
      reconhecimentoRef.current?.abort();
    } catch {
      /* nada a fazer no desmonte */
    }
    reconhecimentoRef.current = null;
  }, []);

  return { disponivel, ouvindo, parcial, erro, iniciar, parar, alternar: () => (ouvindo ? parar() : iniciar()) };
}
