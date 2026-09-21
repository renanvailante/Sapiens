import { Navigate, useLocation } from "react-router-dom";
import { destinoLegado } from "../lib/rotas";

/**
 * O redirecionamento de um endereço antigo — preservando query e hash.
 *
 * `<Navigate to="/estudar/provas" replace />` **come a query**. E a query é
 * onde mora a funcionalidade: o Painel, a fila de revisões e a Mentis abrem as
 * provas com `?area=Matemática` ou `?item_ids=...`, e o Treino com `?hab=`.
 * Um redirect que descarta isso não quebra nada visivelmente — ele abre a tela
 * certa, sem o filtro, e o aluno recebe um caderno genérico onde pediu a
 * questão que errou. Falha silenciosa, a pior classe deste repositório.
 *
 * Este componente resolve o destino com `destinoLegado`, que soma a query do
 * aluno à do próprio redirect e resolve o hash — ver `lib/rotas.js`.
 *
 * `replace` sempre: o endereço antigo não pode ficar no histórico, senão o
 * botão "voltar" do navegador cai nele e redireciona de novo, prendendo o
 * aluno num laço do qual só se sai fechando a aba.
 */
export default function Redireciona() {
  const location = useLocation();
  return <Navigate to={destinoLegado(location)} replace />;
}
