import { useCallback, useEffect, useState } from "react";
import { errMsg } from "../lib/api";

/**
 * Carrega dados de uma rota com os TRÊS estados que uma tela precisa
 * distinguir: carregando, erro e pronto.
 *
 * Seis telas (`Diagnostic`, `StudyPlan`, `LearningMap`, `History`, `Trash`,
 * `AnswerInput`) chamavam a API sem nenhum `.catch`. Se a requisição falhasse
 * ou o id não existisse — link antigo, análise apagada, oscilação de rede — o
 * estado nunca saía de nulo e a tela ficava no texto de carregamento
 * indefinidamente, sem mensagem e sem saída.
 *
 * `recarregar` existe para o botão "tentar de novo" e para telas que precisam
 * refazer a busca depois de uma ação (renomear, restaurar, excluir).
 */
export function useCarregamento(buscar, deps = []) {
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);

  const executar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setDados(await buscar());
    } catch (e) {
      setErro(errMsg(e, "Não foi possível carregar esta página."));
    } finally {
      setCarregando(false);
    }
    // `buscar` é recriada a cada render nas telas que a definem inline; as
    // dependências reais são declaradas pelo chamador.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    let ativo = true;
    (async () => {
      if (ativo) await executar();
    })();
    return () => { ativo = false; };
  }, [executar]);

  return { dados, carregando, erro, recarregar: executar, setDados };
}
