import { createContext, useContext, useEffect, useState } from "react";

/**
 * "O que está na tela agora" — uma frase curta que qualquer página pode
 * declarar para a Mentis saber, sem que o aluno precise repetir contexto que
 * o app já tem. Vive fora do chat de propósito: o widget flutuante e a
 * página /mentis leem o mesmo valor, e ele nunca entra no histórico
 * persistido da conversa (ver `mentis_routes._montar_prompt_chat` — é lido
 * uma vez por mensagem, nunca acumulado).
 */

const MentisContextoCtx = createContext({ contexto: "", setContexto: () => {} });

export function MentisContextoProvider({ children }) {
  const [contexto, setContexto] = useState("");
  return (
    <MentisContextoCtx.Provider value={{ contexto, setContexto }}>
      {children}
    </MentisContextoCtx.Provider>
  );
}

export const useMentisContextoStore = () => useContext(MentisContextoCtx);

/** Uma página chama isto com uma frase curta ("Praticando: Interpretação de
 *  gráficos", "Vendo a questão 3 da prova X") para que a Mentis a receba
 *  automaticamente na próxima mensagem. Limpa sozinho ao desmontar — a Mentis
 *  nunca acha que o aluno ainda está numa tela que ele já fechou. */
export function useDeclararContextoMentis(descricao) {
  const { setContexto } = useMentisContextoStore();
  useEffect(() => {
    if (!descricao) return undefined;
    setContexto(descricao);
    return () => setContexto((atual) => (atual === descricao ? "" : atual));
  }, [descricao, setContexto]);
}

/** Para quem só precisa LER o contexto atual (o widget/chat, na hora de
 *  montar o payload da mensagem) sem se inscrever para declarar nada. */
export function useContextoMentisAtual() {
  const { contexto } = useMentisContextoStore();
  return contexto;
}
