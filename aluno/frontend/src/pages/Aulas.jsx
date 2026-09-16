import { useNavigate } from "react-router-dom";
import Nav from "../components/Nav";
import AulasParticularesModal from "../components/AulasParticularesModal";

/**
 * `/aulas` — uma rota própria para o pedido de aula particular.
 *
 * Não existe formulário novo aqui: é o MESMO
 * `AulasParticularesModal`/`POST /aulas-particulares` que a barra e o Painel
 * já abriam. O que faltava era um endereço — sem rota, a Mentis não tinha
 * como levar o aluno até o pedido de aula, o lançador não tinha para onde
 * apontar, e ninguém conseguia mandar o link para um colega.
 */
export default function Aulas() {
  const nav = useNavigate();
  return (
    <div className="min-h-screen">
      <Nav />
      <AulasParticularesModal open onClose={() => nav("/dashboard")} />
    </div>
  );
}
