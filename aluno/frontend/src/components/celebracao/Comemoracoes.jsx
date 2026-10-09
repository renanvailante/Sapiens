import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useAuth } from "../../lib/auth";
import {
  deveComemorarOfensiva, deveComemorarPlus, lerComemoracoes,
  marcarOfensivaComemorada, marcarPlusComemorado,
} from "../../lib/celebracao";
import TelaDaOfensiva from "./TelaDaOfensiva";

/**
 * Decide se a tela da ofensiva abre — e abre uma vez só.
 *
 * Montado por quem JÁ tem `/engajamento/me` na mão (o Hoje e o fim da série):
 * nenhuma requisição nova só para comemorar. A marca de "comemorado" é
 * gravada no instante em que a tela abre, não quando fecha — duas telas
 * montando ao mesmo tempo (o Hoje carregando por trás do fim da série) não
 * podem abrir duas comemorações em cima uma da outra.
 *
 * `atraso` existe para o fim da série: o Duolingo mostra primeiro o placar da
 * lição e só depois a chama. Abrir as duas juntas apagaria o placar.
 */
export default function Comemoracoes({ engajamento, atraso = 0 }) {
  const { user } = useAuth() || {};
  const uid = user?.user_id;
  const [aberta, setAberta] = useState(null);

  useEffect(() => {
    if (!engajamento || aberta) return undefined;
    const ja = lerComemoracoes(uid);
    const ofensiva = deveComemorarOfensiva(engajamento, ja.ofensiva);
    const presente = deveComemorarPlus(engajamento.plus, ja.plus);
    if (!ofensiva && !presente) return undefined;
    const t = setTimeout(() => {
      // Relida na hora: outra montagem pode ter aberto no intervalo.
      const agora = lerComemoracoes(uid);
      const of = deveComemorarOfensiva(engajamento, agora.ofensiva);
      const pr = deveComemorarPlus(engajamento.plus, agora.plus);
      if (!of && !pr) return;
      if (of) marcarOfensivaComemorada(uid, engajamento.hoje);
      if (pr) marcarPlusComemorado(uid, engajamento.plus.concedido_em);
      setAberta({ ofensiva: of, presente: pr });
    }, atraso);
    return () => clearTimeout(t);
  }, [engajamento, uid, atraso, aberta]);

  if (!aberta || typeof document === "undefined") return null;
  return createPortal(
    <TelaDaOfensiva
      engajamento={engajamento}
      ofensiva={aberta.ofensiva}
      presente={aberta.presente}
      aoFechar={() => setAberta(false)}
    />,
    document.body,
  );
}
