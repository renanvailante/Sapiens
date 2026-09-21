import "./App.css";
import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./lib/auth";
import { MentisContextoProvider } from "./lib/mentisContexto";
import ErrorBoundary from "./components/ErrorBoundary";
import TituloDaPagina from "./components/TituloDaPagina";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import PromoterRoute from "./components/PromoterRoute";
import FirestoreStudentProvisioner from "./components/FirestoreStudentProvisioner";
import MentisWidget from "./components/MentisWidget";
import LembrarComAMentis from "./components/LembrarComAMentis";
import Navegacao from "./components/Navegacao";
import Redireciona from "./components/Redireciona";
import ContinuidadeDaPagina from "./components/ContinuidadeDaPagina";
import BrandMark from "./components/BrandMark";
import { InstalacaoProvider } from "./components/InstalarApp";
import { ROTAS, LEGADO } from "./lib/rotas";

// Entrada e as duas áreas de maior tráfego vêm no bundle principal: são o
// caminho que todo aluno percorre, e adiar o carregamento delas trocaria peso
// por um flash de carregamento logo no primeiro clique.
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Hoje from "./pages/Hoje";
import Estudar from "./pages/Estudar";
import NaoEncontrada from "./pages/NaoEncontrada";

// O resto é carregado sob demanda. O bundle único de 413 kB gzip trazia
// `recharts`, `firebase`, `katex` e TODAS as telas de admin para um aluno que
// só queria responder questões no 4G. Cada `lazy` abaixo é uma tela que a
// maioria dos alunos nunca abre, ou abre depois de já estar usando o produto.
const Provas = lazy(() => import("./pages/Provas"));
const ResponderProva = lazy(() => import("./pages/ResponderProva"));
const Cursos = lazy(() => import("./pages/Cursos"));
const CursoTrilha = lazy(() => import("./pages/CursoTrilha"));
const CursoEstacao = lazy(() => import("./pages/CursoEstacao"));
const EbookLeitor = lazy(() => import("./pages/EbookLeitor"));
const Redacao = lazy(() => import("./pages/Redacao"));
const Treino = lazy(() => import("./pages/Treino"));
const Folhear = lazy(() => import("./pages/Folhear"));

const Agenda = lazy(() => import("./pages/Agenda"));
const Progresso = lazy(() => import("./pages/Progresso"));
const Comunidade = lazy(() => import("./pages/Comunidade"));
const ComunidadeDuvida = lazy(() => import("./pages/ComunidadeDuvida"));

// Os dois registros do passado do aluno: um diagnóstico de simulado e o plano
// que saiu dele. São snapshots, e continuam alcançáveis pelo Histórico dentro
// de Progresso — ver a nota em `Progresso.jsx`.
const Diagnostic = lazy(() => import("./pages/Diagnostic"));
const StudyPlan = lazy(() => import("./pages/StudyPlan"));

const MentisChat = lazy(() => import("./pages/MentisChat"));
const BemVindo = lazy(() => import("./pages/BemVindo"));
const CompletarCadastro = lazy(() => import("./pages/CompletarCadastro"));
const Mentoria = lazy(() => import("./pages/Mentoria"));
const AulaAoVivo = lazy(() => import("./pages/AulaAoVivo"));
const SparksStore = lazy(() => import("./pages/SparksStore"));
const Sugestoes = lazy(() => import("./pages/Sugestoes"));
const EsqueciSenha = lazy(() => import("./pages/EsqueciSenha"));
const RedefinirSenha = lazy(() => import("./pages/RedefinirSenha"));
const Termos = lazy(() => import("./pages/Termos"));
const Privacidade = lazy(() => import("./pages/Privacidade"));

const Admin = lazy(() => import("./pages/Admin"));
const AdminDashboard = lazy(() => import("./pages/AdminDashboard"));
const AdminUsers = lazy(() => import("./pages/AdminUsers"));
const AdminFeed = lazy(() => import("./pages/AdminFeed"));
const AdminAnnotations = lazy(() => import("./pages/AdminAnnotations"));
const AdminMentoria = lazy(() => import("./pages/AdminMentoria"));
const AdminCursos = lazy(() => import("./pages/AdminCursos"));
const AdminReportesQuestoes = lazy(() => import("./pages/AdminReportesQuestoes"));
const AdminSugestoes = lazy(() => import("./pages/AdminSugestoes"));
const AdminCuradoria = lazy(() => import("./pages/AdminCuradoria"));
const AdminPromoCodes = lazy(() => import("./pages/AdminPromoCodes"));
const AdminIndicacoes = lazy(() => import("./pages/AdminIndicacoes"));
const AdminInfluencers = lazy(() => import("./pages/AdminInfluencers"));
const StudentHistory = lazy(() => import("./pages/StudentHistory"));
const AdminTransacoes = lazy(() => import("./pages/AdminTransacoes"));
const AdminComunidade = lazy(() => import("./pages/AdminComunidade"));
const PromoterDashboard = lazy(() => import("./pages/PromoterDashboard"));

/** A espera entre uma rota preguiçosa e a tela dela.
 *
 *  Era um anel girando de 32px, sem nada em volta — indistinguível da espera
 *  de qualquer site, e a única tela do produto em que a marca não aparecia. A
 *  marca com o halo aceso, pulsando devagar, diz duas coisas que o anel não
 *  dizia: que é o Sapiens que está carregando, e que há algo acontecendo. */
function Carregando() {
  return (
    <div className="flex min-h-screen items-center justify-center" data-testid="app-carregando">
      <div className="mentis-halo">
        <BrandMark className="h-14 w-14" halo />
      </div>
    </div>
  );
}

/** Uma rota nova não deve aparecer estalada no lugar.
 *
 *  A `key` é o caminho: trocar de rota remonta o envelope, e remontar
 *  reinicia a animação de entrada (uma animação CSS só dispara ao montar).
 *  É por isso que isto é um envelope com chave e não uma classe no `<main>`
 *  de cada página — 52 telas teriam de lembrar de pôr a classe, e as que
 *  esquecessem entrariam sem ritmo no meio das que não esquecem.
 *
 *  Por que CSS e não `framer-motion` (que já está no pacote): a saída animada
 *  exige manter a tela ANTIGA montada enquanto a nova entra, e as telas do
 *  Sapiens buscam dados na montagem. Duas montadas ao mesmo tempo é o dobro
 *  das chamadas em cada navegação — e a disciplina de leitura do Firestore do
 *  produto não paga esse preço por uma transição. */
function Transicao({ children }) {
  const { pathname } = useLocation();
  return <div key={pathname} className="pagina-entra">{children}</div>;
}

/** Uma rota = um título de aba. Antes toda página se chamava "Sapiens", o que
 *  torna várias abas abertas indistinguíveis e o histórico do navegador inútil. */
function Pagina({ titulo, children }) {
  return (
    <>
      <TituloDaPagina titulo={titulo} />
      {children}
    </>
  );
}

/** Uma rota de aluno: título + portão de sessão, numa linha só. As 30 rotas
 *  protegidas repetiam `<ProtectedRoute><Pagina …>` inteiro, e uma rota nova
 *  que esquecesse o `ProtectedRoute` ficaria aberta sem ninguém notar até
 *  alguém abrir a URL deslogado. */
function Aluno({ titulo, children }) {
  return (
    <ProtectedRoute>
      <Pagina titulo={titulo}>{children}</Pagina>
    </ProtectedRoute>
  );
}

function Equipe({ titulo, children }) {
  return (
    <AdminRoute>
      <Pagina titulo={titulo}>{children}</Pagina>
    </AdminRoute>
  );
}

/**
 * OS REDIRECTS DE ENDEREÇO ANTIGO.
 *
 * Um `<Route>` por linha de `LEGADO`, desenhado a partir da tabela em vez de
 * escrito à mão: a lista de redirects e a lista de traduções eram a mesma
 * informação em dois lugares, e foi assim que `/cognitive-profile` continuou
 * vivo no backend meses depois de a tela mudar de nome.
 *
 * `Redireciona` preserva query e hash — ver o arquivo, a razão é cara.
 */
function RotasLegadas() {
  return Object.keys(LEGADO).map((antiga) => (
    <Route key={antiga} path={antiga} element={<Redireciona />} />
  ));
}

function AppRouter() {
  return (
    <Routes>
      {/* O título da landing é o que o Google MOSTRA no resultado: o buscador
          renderiza o JavaScript, então este texto vence o `<title>` do
          index.html. Por isso ele carrega as palavras que o aluno digita
          ("plano de estudos", "ENEM", "vestibular") e não o slogan, que
          ninguém pesquisa — o slogan continua sendo o `h1` da tela. */}
      <Route path={ROTAS.LANDING} element={<Pagina titulo="Plano de estudos personalizado para o ENEM e vestibular"><Landing /></Pagina>} />
      <Route path={ROTAS.LOGIN} element={<Pagina titulo="Entrar"><Login /></Pagina>} />
      <Route path={ROTAS.ESQUECI_SENHA} element={<Pagina titulo="Recuperar senha"><EsqueciSenha /></Pagina>} />
      <Route path={ROTAS.REDEFINIR_SENHA} element={<Pagina titulo="Nova senha"><RedefinirSenha /></Pagina>} />
      <Route path={ROTAS.TERMOS} element={<Pagina titulo="Termos de Uso"><Termos /></Pagina>} />
      <Route path={ROTAS.PRIVACIDADE} element={<Pagina titulo="Política de Privacidade"><Privacidade /></Pagina>} />

      {/* Os dois portões de conta. `/completar-cadastro` é ela mesma protegida
          (precisa da sessão) — ver a guarda contra laço em `ProtectedRoute`. */}
      <Route path={ROTAS.BEM_VINDO} element={<Aluno titulo="Bem-vindo ao Sapiens"><BemVindo /></Aluno>} />
      <Route path={ROTAS.COMPLETAR_CADASTRO} element={<Aluno titulo="Completar cadastro"><CompletarCadastro /></Aluno>} />

      {/* ─── 1. HOJE ─────────────────────────────────────── "e agora?" ─── */}
      <Route path={ROTAS.HOJE} element={<Aluno titulo="Hoje"><Hoje /></Aluno>} />

      {/* ─── 2. ESTUDAR ──────────────────────── "o que eu vou fazer?" ─── */}
      <Route path={ROTAS.ESTUDAR} element={<Aluno titulo="Estudar"><Estudar /></Aluno>} />
      {/* A lista de cadernos continua sendo tela própria, e não só a coluna
          embutida em `/estudar`: é ela que o Hoje, a Agenda e a Mentis abrem
          COM filtro na URL (`?area=`, `?item_ids=`), e é onde o motor de prova
          roda em tela cheia. */}
      <Route path={ROTAS.PROVAS} element={<Aluno titulo="Provas do ENEM"><Provas /></Aluno>} />
      <Route path={ROTAS.PROVA} element={<Aluno titulo="Registrar respostas"><ResponderProva /></Aluno>} />
      <Route path={ROTAS.CURSOS} element={<Aluno titulo="Cursos e e-books"><Cursos /></Aluno>} />
      {/* O curso por dentro. Só chega aqui quem tem acesso — a porta é do
          servidor, não da rota. */}
      <Route path={ROTAS.CURSO} element={<Aluno titulo="Curso"><CursoTrilha /></Aluno>} />
      <Route path={ROTAS.ESTACAO} element={<Aluno titulo="Estação"><CursoEstacao /></Aluno>} />
      {/* O e-book se lê aqui, página por página — nenhum aluno baixa nada. */}
      <Route path={ROTAS.EBOOK} element={<Aluno titulo="E-book"><EbookLeitor /></Aluno>} />
      <Route path={ROTAS.REDACAO} element={<Aluno titulo="Redação"><Redacao /></Aluno>} />
      <Route path={ROTAS.TREINO} element={<Aluno titulo="Mapa de Treino"><Treino /></Aluno>} />
      <Route path={ROTAS.FOLHEAR} element={<Aluno titulo="Folhear"><Folhear /></Aluno>} />

      {/* ─── 3. AGENDA ───────────────────────────────────── "quando?" ─── */}
      <Route path={ROTAS.AGENDA} element={<Aluno titulo="Agenda"><Agenda /></Aluno>} />

      {/* ─── 4. PROGRESSO ─────────────────────── "estou evoluindo?" ─── */}
      <Route path={ROTAS.PROGRESSO} element={<Aluno titulo="Progresso"><Progresso /></Aluno>} />
      <Route path={ROTAS.ANALISE} element={<Aluno titulo="Diagnóstico do simulado"><Diagnostic /></Aluno>} />
      <Route path={ROTAS.PLANO} element={<Aluno titulo="Plano de estudos"><StudyPlan /></Aluno>} />

      {/* ─── 5. COMUNIDADE ────────────────────── "quem me responde?" ─── */}
      <Route path={ROTAS.COMUNIDADE} element={<Aluno titulo="Comunidade"><Comunidade /></Aluno>} />
      <Route path={ROTAS.DUVIDA} element={<Aluno titulo="Dúvida da comunidade"><ComunidadeDuvida /></Aluno>} />

      {/* ─── Camada e fluxos (fora da navegação principal) ───────────── */}
      {/* A Mentis flutua em toda tela; esta rota é a MESMA sessão em tela
          cheia, e por isso o widget se esconde aqui. Não é aba. */}
      <Route path={ROTAS.MENTIS} element={<Aluno titulo="Mentis"><MentisChat /></Aluno>} />
      <Route path={ROTAS.SPARKS} element={<Aluno titulo="Meus Sparks"><SparksStore /></Aluno>} />
      <Route path={ROTAS.SUGESTOES} element={<Aluno titulo="Fale com a equipe"><Sugestoes /></Aluno>} />
      <Route path={ROTAS.AULA_AO_VIVO} element={<Aluno titulo="Aula ao vivo de quinta"><AulaAoVivo /></Aluno>} />
      <Route path={ROTAS.MENTORIA} element={<Aluno titulo="Mentoria com Vitor Lara"><Mentoria /></Aluno>} />

      {/* ─── Endereços antigos ───────────────────────────────────────── */}
      {RotasLegadas()}

      {/* ─── Equipe ──────────────────────────────────────────────────── */}
      <Route path={ROTAS.ADMIN} element={<Equipe titulo="Admin"><AdminDashboard /></Equipe>} />
      <Route path="/admin/answer-keys" element={<Equipe titulo="Admin · Gabaritos"><Admin /></Equipe>} />
      <Route path="/admin/feed" element={<Equipe titulo="Admin · Folhear"><AdminFeed /></Equipe>} />
      <Route path="/admin/annotations" element={<Equipe titulo="Admin · Anotações"><AdminAnnotations /></Equipe>} />
      <Route path="/admin/mentoria" element={<Equipe titulo="Admin · Lista de espera da mentoria"><AdminMentoria /></Equipe>} />
      <Route path="/admin/aulas-particulares" element={<Redireciona />} />
      <Route path="/admin/cursos" element={<Equipe titulo="Admin · Cursos e live"><AdminCursos /></Equipe>} />
      <Route path="/admin/reportes-questoes" element={<Equipe titulo="Admin · Sugestões de correção"><AdminReportesQuestoes /></Equipe>} />
      <Route path="/admin/sugestoes" element={<Equipe titulo="Admin · Reclamações e sugestões"><AdminSugestoes /></Equipe>} />
      <Route path="/admin/curadoria" element={<Equipe titulo="Admin · Curadoria"><AdminCuradoria /></Equipe>} />
      <Route path="/admin/promo-codes" element={<Equipe titulo="Admin · Códigos de promoção"><AdminPromoCodes /></Equipe>} />
      <Route path="/admin/indicacoes" element={<Equipe titulo="Admin · Indicações"><AdminIndicacoes /></Equipe>} />
      <Route path="/admin/influencers" element={<Equipe titulo="Admin · Influencers"><AdminInfluencers /></Equipe>} />
      <Route path="/admin/users" element={<Equipe titulo="Admin · Usuários"><AdminUsers /></Equipe>} />
      <Route path="/admin/transacoes" element={<Equipe titulo="Admin · Transações"><AdminTransacoes /></Equipe>} />
      <Route path="/admin/comunidade" element={<Equipe titulo="Admin · Comunidade"><AdminComunidade /></Equipe>} />
      <Route path="/admin/history" element={<Equipe titulo="Admin · Histórico"><StudentHistory /></Equipe>} />
      <Route path={ROTAS.PROMOTER} element={<PromoterRoute><Pagina titulo="Painel do promoter"><PromoterDashboard /></Pagina></PromoterRoute>} />

      {/* Antes caía na landing: uma URL errada levava a pessoa para a página de
          marketing sem dizer que a página não existe, inclusive já logada. */}
      <Route path="*" element={<Pagina titulo="Página não encontrada"><NaoEncontrada /></Pagina>} />
    </Routes>
  );
}

export default function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <MentisContextoProvider>
            {/* Guarda o evento de instalação do navegador, que é disparado uma
                única vez e cedo — ver `components/InstalarApp.jsx`. */}
            <InstalacaoProvider>
            <FirestoreStudentProvisioner />

            {/* A NAVEGAÇÃO, montada uma vez. Ela decide sozinha onde não
                aparecer (ver `lib/navegacao.temNavegacao`) e desenha a barra de
                cima ou a de baixo conforme a largura.

                Mora aqui, e não dentro de cada tela, porque 39 arquivos
                montavam a própria `<Nav/>` à mão: era garantido que a próxima
                tela nova nasceria sem barra — foi exatamente o que aconteceu
                com a navegação do celular, que passou meses sem existir abaixo
                de 1024px. É a mesma razão das três camadas abaixo. */}
            <Navegacao />

            <ErrorBoundary>
              <Suspense fallback={<Carregando />}>
                <Transicao>
                  <AppRouter />
                </Transicao>
              </Suspense>
            </ErrorBoundary>

            {/* Ícone sempre visível, em toda página logada — ver
                `MentisWidget.jsx` para por que ele se esconde em `/mentis`. */}
            <MentisWidget />
            {/* "Lembrar-me com a Mentis": o aluno seleciona qualquer trecho,
                em qualquer tela, e guarda aquilo na Agenda. */}
            <LembrarComAMentis />
            {/* A pista de que a página CONTINUA. */}
            <ContinuidadeDaPagina />
            {/* `theme="dark"`: o Sonner nasce claro e um toast branco era a única
                coisa do produto que continuava em tema claro sobre o ambiente novo. */}
            <Toaster position="top-center" richColors closeButton theme="dark" />
            </InstalacaoProvider>
          </MentisContextoProvider>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}
