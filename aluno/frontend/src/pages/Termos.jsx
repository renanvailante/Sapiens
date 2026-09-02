import PaginaLegal from "../components/PaginaLegal";
import { OPERADOR } from "../lib/operador";

export default function Termos() {
  return (
    <PaginaLegal
      titulo="Termos de Uso"
      resumo="Estas são as regras de uso do Sapiens. Escrevemos em português direto porque quem usa o produto precisa entender o que aceitou."
    >
      <section>
        <h2>1. O que o Sapiens faz</h2>
        <p>
          O Sapiens é uma plataforma de estudo para vestibulares e ENEM. Você responde questões,
          registra o resultado de simulados e recebe análises sobre os seus padrões de erro.
        </p>
        <p className="mt-3">
          <strong>O que não somos:</strong> não somos curso preparatório, não garantimos aprovação e
          nossas análises não substituem professor, orientação pedagógica ou avaliação oficial. As
          notas e estimativas do produto são indicativas.
        </p>
      </section>

      <section>
        <h2>2. Quem pode usar</h2>
        <p>
          O serviço é destinado a estudantes de ensino médio e pré-vestibular, e é esperado que boa
          parte tenha menos de 18 anos. <strong>Se você tem menos de 18 anos, precisa da autorização
          do seu pai, mãe ou responsável</strong> para criar uma conta — e essa autorização é
          obrigatória para qualquer compra dentro do produto.
        </p>
        <p className="mt-3">
          Cada pessoa deve ter uma conta própria. Não compartilhe sua senha: as análises são
          construídas a partir das suas respostas, e respostas de outra pessoa distorcem o seu
          diagnóstico.
        </p>
      </section>

      <section>
        <h2>3. Sparks</h2>
        <p>
          Sparks são créditos usados dentro do Sapiens para acionar recursos que dependem de
          inteligência artificial. Você ganha Sparks praticando e pode comprá-los.
        </p>
        <ul className="mt-3">
          <li>Sparks <strong>não são moeda</strong>, não podem ser trocados por dinheiro, transferidos entre contas nem sacados.</li>
          <li>Sparks comprados não expiram enquanto sua conta estiver ativa.</li>
          <li>Se um recurso falhar por erro nosso depois de descontar Sparks, os créditos são devolvidos automaticamente.</li>
          <li>Os preços vigentes são sempre os exibidos na loja no momento da compra.</li>
        </ul>
      </section>

      <section>
        <h2>4. Compras, arrependimento e cancelamento</h2>
        <p>
          Os pagamentos são processados pelo <strong>Mercado Pago</strong>. Não recebemos nem
          armazenamos os dados do seu cartão — eles são digitados dentro do componente do próprio
          Mercado Pago.
        </p>
        <p className="mt-3">
          <strong>Direito de arrependimento (art. 49 do Código de Defesa do Consumidor):</strong> você
          pode desistir de qualquer compra em até <strong>7 dias corridos</strong> a partir do
          pagamento e receber o valor de volta, sem precisar justificar. Basta escrever para{" "}
          <a className="text-sapiens-accentDeep hover:underline" href={`mailto:${OPERADOR.emailContato}`}>{OPERADOR.emailContato}</a>.
          Se você já tiver usado parte dos Sparks comprados, devolvemos o valor proporcional ao que
          ainda não foi usado.
        </p>
        <p className="mt-3">
          <strong>Recarga automática:</strong> quando ativada, cobra o valor do pacote escolhido na
          frequência que você definiu, até que você cancele. O cancelamento é imediato e feito por
          você mesmo, na página de Sparks, sem precisar falar com ninguém. Cancelar interrompe as
          próximas cobranças; não desfaz cobranças já realizadas, que seguem a regra de
          arrependimento acima.
        </p>
      </section>

      <section>
        <h2>5. Conteúdo</h2>
        <p>
          As questões de provas oficiais (como o ENEM) são de domínio público e pertencem às
          instituições que as elaboraram. O que é nosso é a análise, a organização, os textos e a
          plataforma — e não pode ser copiado, revendido nem redistribuído.
        </p>
        <p className="mt-3">
          O que você escreve (redações, respostas) continua seu. Você nos autoriza a processá-lo
          para gerar as correções e análises que o produto oferece, e para nada além disso.
        </p>
      </section>

      <section>
        <h2>6. Uso adequado</h2>
        <p>Ao usar o Sapiens, você concorda em não:</p>
        <ul className="mt-3">
          <li>tentar burlar a contagem de Sparks ou obter créditos sem pagar por eles;</li>
          <li>extrair o acervo de questões de forma automatizada;</li>
          <li>acessar a conta de outra pessoa;</li>
          <li>enviar conteúdo ilegal, ofensivo ou que não seja seu.</li>
        </ul>
        <p className="mt-3">
          Podemos suspender contas que descumpram estas regras. Se isso acontecer com você por
          engano, escreva para o nosso contato — respondemos.
        </p>
      </section>

      <section>
        <h2>7. Disponibilidade</h2>
        <p>
          O Sapiens está em <strong>fase beta</strong>. Isso significa que funcionalidades podem
          mudar, ficar temporariamente indisponíveis ou apresentar falhas. Avisamos com antecedência
          antes de remover algo que você já usa, e Sparks comprados são preservados.
        </p>
      </section>

      <section>
        <h2>8. Encerrar sua conta</h2>
        <p>
          Você pode pedir a exclusão da sua conta a qualquer momento, escrevendo para o nosso
          contato. Excluímos seus dados conforme descrito na{" "}
          <a className="text-sapiens-accentDeep hover:underline" href="/privacidade">Política de Privacidade</a>.
        </p>
      </section>

      <section>
        <h2>9. Lei aplicável</h2>
        <p>
          Estes termos seguem a lei brasileira. Eventuais disputas são resolvidas no foro do
          domicílio do consumidor, como determina o Código de Defesa do Consumidor.
        </p>
      </section>
    </PaginaLegal>
  );
}
