import PaginaLegal from "../components/PaginaLegal";
import MeusDadosLGPD from "../components/MeusDadosLGPD";
import { OPERADOR, PRIVACIDADE_ATUALIZADA_EM, identificacaoDoOperador } from "../lib/operador";

export default function Privacidade() {
  return (
    <PaginaLegal
      titulo="Política de Privacidade"
      atualizadoEm={PRIVACIDADE_ATUALIZADA_EM}
      resumo="Quais dados coletamos, por que, com quem compartilhamos e como você controla tudo isso. Escrito conforme a LGPD (Lei 13.709/2018)."
    >
      <section>
        <h2>1. Quem trata seus dados</h2>
        <p>
          {/* `identificacaoDoOperador()` e não `razaoSocial || nomeFantasia`:
              o fallback antigo dizia "o controlador é Sapiens", que é uma
              MARCA, não alguém a quem o titular possa se dirigir. A LGPD
              (art. 9º) dá ao titular o direito de saber quem trata os dados
              dele; uma marca não responde a isso. */}
          O controlador dos dados é {identificacaoDoOperador()}. Para qualquer
          assunto de privacidade — inclusive os pedidos descritos na seção 6 — escreva para{" "}
          <a className="text-sapiens-accentDeep hover:underline" href={`mailto:${OPERADOR.emailPrivacidade || OPERADOR.emailContato}`}>
            {OPERADOR.emailPrivacidade || OPERADOR.emailContato}
          </a>.
        </p>
      </section>

      <section>
        <h2>2. O que coletamos</h2>
        <ul>
          <li><strong>Cadastro:</strong> nome, e-mail e, se você entrar com Google, sua foto de perfil.</li>
          <li><strong>Estudo:</strong> as questões que você respondeu, a alternativa escolhida, se acertou, quanto tempo levou e se mudou de resposta.</li>
          <li><strong>Conteúdo enviado:</strong> redações que você submete e fotos de cartão-resposta.</li>
          <li><strong>Contato:</strong> nome e WhatsApp, informados no cadastro e quando você entra na lista de espera da mentoria.</li>
          <li><strong>Técnico:</strong> endereço IP e navegador, registrados junto a erros da aplicação por até 30 dias.</li>
          <li><strong>Navegação nas páginas abertas:</strong> a visita à página inicial, à tela de entrada e às páginas de campanha, e o momento em que uma conta é criada, medidos pelo Meta Pixel — ver a seção 9.</li>
        </ul>
        <p className="mt-3">
          <strong>Não coletamos</strong> dados do seu cartão de crédito: eles são digitados dentro
          do componente do Mercado Pago e nunca passam pelos nossos servidores.
        </p>
      </section>

      <section>
        <h2>3. Por que coletamos (bases legais)</h2>
        <ul>
          <li><strong>Execução do contrato</strong> (art. 7º, V): cadastro, respostas e conteúdo enviado — sem eles o produto não funciona.</li>
          <li><strong>Cumprimento de obrigação legal</strong> (art. 7º, II): registros de pagamento, guardados pelo prazo que a legislação fiscal exige.</li>
          <li><strong>Legítimo interesse</strong> (art. 7º, IX): registros técnicos de erro, usados só para consertar o que quebrou e mantidos por 30 dias.</li>
          <li><strong>Consentimento</strong> (art. 7º, I): entrada na lista de espera da mentoria, que só acontece quando você preenche o formulário.</li>
          <li><strong>Legítimo interesse</strong> (art. 7º, IX): a medição de audiência das páginas abertas pelo Meta Pixel, usada para saber quais anúncios trazem gente que realmente se cadastra. Você pode se opor a esse tratamento (art. 18, § 2º) escrevendo para o nosso contato de privacidade, e bloqueadores de rastreamento do navegador também impedem essa medição sem prejudicar o uso do produto.</li>
        </ul>
      </section>

      <section>
        <h2>4. Adolescentes e crianças</h2>
        <p>
          Sabemos que grande parte de quem usa o Sapiens tem menos de 18 anos. Tratamos esses dados
          <strong> no melhor interesse do titular</strong>, como manda o art. 14 da LGPD:
        </p>
        <ul className="mt-3">
          <li>coletamos o mínimo necessário para o produto funcionar;</li>
          <li>nunca vendemos, alugamos nem cedemos dados a terceiros;</li>
          <li><strong>nada do que você faz estudando vira anúncio.</strong> A medição do Meta Pixel (seção 9) acontece apenas nas páginas abertas — a inicial, a de entrada e as de campanha — e <strong>nunca</strong> nas telas de estudo, que ficam atrás do seu login. Nenhuma resposta sua, nenhuma redação, nenhum resultado e nenhum dado de contato é enviado a plataforma de anúncio nenhuma;</li>
          <li>não exigimos dado nenhum além do necessário como condição para estudar.</li>
        </ul>
        <p className="mt-3">
          Se você tem menos de 18 anos, precisa da autorização do seu responsável para criar conta e
          para qualquer compra. Um responsável pode, a qualquer momento, pedir acesso ou exclusão dos
          dados escrevendo para o nosso contato.
        </p>
      </section>

      <section>
        <h2>5. Com quem compartilhamos</h2>
        <p>Só com os prestadores necessários para o serviço existir:</p>
        <ul className="mt-3">
          <li><strong>Google (Firebase/Firestore)</strong> — login e armazenamento das suas respostas.</li>
          <li><strong>Google (Gemini)</strong> — geração das análises e leitura do cartão-resposta. O conteúdo enviado não é usado para treinar modelos.</li>
          <li><strong>Mercado Pago</strong> — processamento dos pagamentos.</li>
          <li><strong>Fly.io e Cloudflare</strong> — hospedagem da aplicação.</li>
          <li><strong>Meta (Facebook/Instagram)</strong> — medição dos anúncios nas páginas abertas, descrita na seção 9. Recebe que uma página foi vista e que um cadastro foi concluído, junto do endereço IP e do identificador de navegador que qualquer site visitado recebe. <strong>Não recebe seu nome, e-mail, WhatsApp, respostas, redações nem resultados.</strong></li>
        </ul>
        <p className="mt-3">
          Alguns desses serviços processam dados fora do Brasil, o que a LGPD permite (art. 33) desde
          que o nível de proteção seja adequado — condição que consta dos contratos desses
          fornecedores. <strong>Nunca vendemos seus dados.</strong>
        </p>
      </section>

      <section>
        <h2>6. Seus direitos</h2>
        <p>A LGPD (art. 18) garante a você o direito de:</p>
        <ul className="mt-3">
          <li>saber se tratamos seus dados e acessar uma cópia deles;</li>
          <li>corrigir dados incompletos ou desatualizados;</li>
          <li>pedir a exclusão dos dados tratados com base em consentimento;</li>
          <li>pedir a portabilidade para outro serviço;</li>
          <li>revogar um consentimento dado antes;</li>
          <li>saber com quem compartilhamos seus dados.</li>
        </ul>
        <p className="mt-3">
          Escreva para o nosso contato de privacidade. Respondemos em até <strong>15 dias</strong>.
        </p>
        <p className="mt-3">
          Dois desses direitos você exerce agora, sem esperar resposta:
        </p>
        <MeusDadosLGPD />
      </section>

      <section>
        <h2>7. Por quanto tempo guardamos</h2>
        <ul>
          <li><strong>Conta e histórico de estudo:</strong> enquanto a conta existir.</li>
          <li><strong>Após pedido de exclusão:</strong> apagados em até 30 dias.</li>
          <li><strong>Registros de pagamento:</strong> 5 anos, por exigência fiscal.</li>
          <li><strong>Registros técnicos de erro:</strong> 30 dias.</li>
          <li><strong>Sessões de login:</strong> 7 dias, e são apagadas sozinhas depois disso.</li>
        </ul>
      </section>

      <section>
        <h2>8. Segurança</h2>
        <p>
          Todo o tráfego é criptografado (HTTPS). Senhas são guardadas com bcrypt, um algoritmo que
          não permite recuperar a senha original. O acesso administrativo é restrito a uma lista
          nominal de pessoas. Se um incidente de segurança afetar seus dados, avisaremos você e a
          ANPD, como manda o art. 48 da LGPD.
        </p>
      </section>

      <section>
        <h2>9. Cookies e medição de anúncios</h2>
        <p>
          Nosso próprio cookie é <strong>um</strong> só, chamado <code>session_token</code>, que
          mantém você logado. Ele é estritamente necessário para o serviço funcionar e por isso não
          depende de consentimento.
        </p>
        <p className="mt-3">
          Desde <strong>22 de setembro de 2026</strong> usamos também o <strong>Meta Pixel</strong>,
          da Meta (Facebook/Instagram), para medir os anúncios que trazem gente até aqui. Ele grava
          cookie próprio e é, sim, um rastreador de terceiro — dizemos isso com todas as letras
          porque até esta data esta política afirmava que não existia nenhum.
        </p>
        <p className="mt-3">
          O que ele faz, exatamente: registra que a <strong>página inicial</strong>, a{" "}
          <strong>tela de entrada</strong> ou uma <strong>página de campanha</strong> foi aberta, e
          que um <strong>cadastro foi concluído</strong> (sem dizer de quem). Só isso.
        </p>
        <p className="mt-3">
          O que ele <strong>não</strong> faz: não carrega em nenhuma tela de dentro do produto.
          Depois que você entra na sua conta, não há pixel nenhum acompanhando você estudando — e
          nenhum dado de estudo, de contato ou de pagamento é enviado à Meta em momento algum.
        </p>
        <p className="mt-3">
          Para bloqueá-lo, basta uma extensão de bloqueio de rastreadores ou a proteção que o seu
          navegador já traz; o Sapiens continua funcionando igual. Você também pode se opor ao
          tratamento escrevendo para o nosso contato de privacidade.
        </p>
      </section>

      <section>
        <h2>10. Mudanças</h2>
        <p>
          Se mudarmos algo relevante desta política, avisaremos por e-mail e dentro do produto antes
          de a mudança valer.
        </p>
      </section>
    </PaginaLegal>
  );
}
