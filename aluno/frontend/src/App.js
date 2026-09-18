import "./App.css";
import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
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
import BarraInferior from "./components/BarraInferior";
import BrandMark from "./components/BrandMark";
import { InstalacaoProvider } from "./components/InstalarApp";

// Entrada e prática vêm no bundle principal: são o caminho que todo aluno
// percorre, e adiar o carregamento delas trocaria peso por um flash de
// carregamento logo no primeiro clique.
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import ExamSelect from "./pages/ExamSelect";
import NaoEncontrada from "./pages/NaoEncontrada";

// O resto é carregado sob demanda. O bundle único de 413 kB gzip trazia
// `recharts`, `firebase`, `katex` e TODAS as telas de admin para um aluno que
// só queria responder questões no 4G. Cada `lazy` abaixo é uma tela que a
// maioria dos alunos nunca abre, ou abre depois de já estar usando o produto.
const AnswerInput = lazy(() => import("./pages/AnswerInput"));
const Diagnostic = lazy(() => import("./pages/Diagnostic"));
const StudyPlan = lazy(() => import("./pages/StudyPlan"));
const Revisoes = lazy(() => import("./pages/Revisoes"));
const Cronograma = lazy(() => import("./pages/Cronograma"));
const LearningMap = lazy(() => import("./pages/LearningMap"));
const History = lazy(() => import("./pages/History"));
const Trash = lazy(() => import("./pages/Trash"));
const PerfilCognitivo = lazy(() => import("./pages/PerfilCognitivo"));
const TreinoHabilidades = lazy(() => import("./pages/TreinoHabilidades"));
const MinhasQuestoes = lazy(() => import("./pages/MinhasQuestoes"));
const MentisChat = lazy(() => import("./pages/MentisChat"));
const BemVindo = lazy(() => import("./pages/BemVindo"));
const Conquistas = lazy(() => import("./pages/Conquistas"));
const CompletarCadastro = lazy(() => import("./pages/CompletarCadastro"));
const Mentoria = lazy(() => import("./pages/Mentoria"));
const Cursos = lazy(() => import("./pages/Cursos"));
const AulaAoVivo = lazy(() => import("./pages/AulaAoVivo"));
const CursoTrilha = lazy(() => import("./pages/CursoTrilha"));
const CursoEstacao = lazy(() => import("./pages/CursoEstacao"));
const EbookLeitor = lazy(() => import("./pages/EbookLeitor"));
const SparksStore = lazy(() => import("./pages/SparksStore"));
const Indicar = lazy(() => import("./pages/Indicar"));
const Feed = lazy(() => import("./pages/Feed"));
const Comunidade = lazy(() => import("./pages/Comunidade"));
const ComunidadeDuvida = lazy(() => import("./pages/ComunidadeDuvida"));
const Liga = lazy(() => import("./pages/Liga"));
const Questoes = lazy(() => import("./pages/Questoes"));
const Redacao = lazy(() => import("./pages/Redacao"));
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
 *  de cada página — 37 telas teriam de lembrar de pôr a classe, e as que
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

function AppRouter() {
  return (
    <Routes>
      {/* O título da landing é o que o Google MOSTRA no resultado: o buscador
          renderiza o JavaScript, então este texto vence o `<title>` do
          index.html. Por isso ele carrega as palavras que o aluno digita
          ("plano de estudos", "ENEM", "vestibular") e não o slogan, que
          ninguém pesquisa — o slogan continua sendo o `h1` da tela. */}
      <Route path="/" element={<Pagina titulo="Plano de estudos personalizado para o ENEM e vestibular"><Landing /></Pagina>} />
      <Route path="/login" element={<Pagina titulo="Entrar"><Login /></Pagina>} />
      <Route path="/esqueci-senha" element={<Pagina titulo="Recuperar senha"><EsqueciSenha /></Pagina>} />
      <Route path="/redefinir-senha" element={<Pagina titulo="Nova senha"><RedefinirSenha /></Pagina>} />
      <Route path="/termos" element={<Pagina titulo="Termos de Uso"><Termos /></Pagina>} />
      <Route path="/privacidade" element={<Pagina titulo="Política de Privacidade"><Privacidade /></Pagina>} />

      <Route path="/questoes" element={<ProtectedRoute><Pagina titulo="Banco de questões"><Questoes /></Pagina></ProtectedRoute>} />
      <Route path="/dashboard" element={<ProtectedRoute><Pagina titulo="Painel"><Dashboard /></Pagina></ProtectedRoute>} />
      {/* Primeiro acesso: vídeo + as três perguntas da Mentis. O Painel manda
          para cá quem ainda tem `flags.onboarded === false`. */}
      <Route path="/bem-vindo" element={<ProtectedRoute><Pagina titulo="Bem-vindo ao Sapiens"><BemVindo /></Pagina></ProtectedRoute>} />
      <Route path="/conquistas" element={<ProtectedRoute><Pagina titulo="Conquistas"><Conquistas /></Pagina></ProtectedRoute>} />
      {/* A mentoria com o 1º colocado de Medicina da USP. Substituiu a "aula
          particular" em 2026-09-15: não é mais um pedido de aula avulsa, é a
          LISTA DE ESPERA de uma mentoria com uma pessoa só. `/aulas` continua
          existindo como redirect porque o endereço antigo circulou. */}
      {/* O portão de dados de contato. Protegida (precisa da sessão) e SEM
          `Pagina` com título de ferramenta: ela não é uma ferramenta, é a
          segunda metade de um cadastro. Ver `ProtectedRoute`. */}
      <Route path="/completar-cadastro" element={<ProtectedRoute><Pagina titulo="Completar cadastro"><CompletarCadastro /></Pagina></ProtectedRoute>} />
      <Route path="/mentoria" element={<ProtectedRoute><Pagina titulo="Mentoria com o 1º colocado de Medicina da USP"><Mentoria /></Pagina></ProtectedRoute>} />
      <Route path="/aulas" element={<Navigate to="/mentoria" replace />} />
      {/* A AULA AO VIVO DE QUINTA tem tela própria desde 2026-09-16. Ela
          morava no topo de `/cursos`, dividindo a página com um catálogo que
          ainda não existe — a coisa mais concreta do produto atrás do nome de
          outra. `/live` e `/cursos#live` continuam funcionando porque os dois
          endereços circularam no WhatsApp. */}
      <Route path="/aula-ao-vivo" element={<ProtectedRoute><Pagina titulo="Aula ao vivo de quinta"><AulaAoVivo /></Pagina></ProtectedRoute>} />
      <Route path="/live" element={<Navigate to="/aula-ao-vivo" replace />} />
      <Route path="/cursos" element={<ProtectedRoute><Pagina titulo="Cursos"><Cursos /></Pagina></ProtectedRoute>} />
      {/* O curso por dentro: o mapa das trilhas e a sala de aula de uma estação.
          Só chega aqui quem tem acesso — a porta é do servidor, não da rota. */}
      <Route path="/cursos/:cursoId" element={<ProtectedRoute><Pagina titulo="Curso"><CursoTrilha /></Pagina></ProtectedRoute>} />
      <Route path="/cursos/:cursoId/estacao/:estacaoId" element={<ProtectedRoute><Pagina titulo="Estação"><CursoEstacao /></Pagina></ProtectedRoute>} />
      {/* O e-book por dentro: lê-se aqui, página por página — nenhum aluno
          baixa nada do Sapiens. */}
      <Route path="/cursos/ebooks/:ebookId" element={<ProtectedRoute><Pagina titulo="E-book"><EbookLeitor /></Pagina></ProtectedRoute>} />
      <Route path="/exams" element={<ProtectedRoute><Pagina titulo="Praticar questões"><ExamSelect /></Pagina></ProtectedRoute>} />
      <Route path="/exam/:examId" element={<ProtectedRoute><Pagina titulo="Registrar respostas"><AnswerInput /></Pagina></ProtectedRoute>} />
      <Route path="/analysis/:analysisId" element={<ProtectedRoute><Pagina titulo="Diagnóstico"><Diagnostic /></Pagina></ProtectedRoute>} />
      <Route path="/plan/:analysisId" element={<ProtectedRoute><Pagina titulo="Plano de estudos"><StudyPlan /></Pagina></ProtectedRoute>} />
      {/* A fila viva. `/plan/:analysisId` continua sendo o snapshot de uma
          análise (histórico não pode quebrar); `/plan` sem id, que nunca
          existiu como tela, aponta para o que está valendo hoje. */}
      <Route path="/revisoes" element={<ProtectedRoute><Pagina titulo="Revisões"><Revisoes /></Pagina></ProtectedRoute>} />
      <Route path="/cronograma" element={<ProtectedRoute><Pagina titulo="Cronograma"><Cronograma /></Pagina></ProtectedRoute>} />
      {/* "agenda" é como metade dos alunos chama a tela; o redirect evita que
          o palpite caia na página de "não encontrada". */}
      <Route path="/agenda" element={<Navigate to="/cronograma" replace />} />
      <Route path="/plan" element={<Navigate to="/revisoes" replace />} />
      <Route path="/map/:analysisId" element={<ProtectedRoute><Pagina titulo="Mapa de aprendizagem"><LearningMap /></Pagina></ProtectedRoute>} />
      <Route path="/history" element={<ProtectedRoute><Pagina titulo="Histórico"><History /></Pagina></ProtectedRoute>} />
      <Route path="/trash" element={<ProtectedRoute><Pagina titulo="Lixeira"><Trash /></Pagina></ProtectedRoute>} />
      <Route path="/cognitive-profile" element={<ProtectedRoute><Pagina titulo="Seu perfil cognitivo"><PerfilCognitivo /></Pagina></ProtectedRoute>} />
      {/* Motor Cognitivo e Diagnóstico real viraram esta mesma aba — os
          redirects preservam links salvos/favoritos (inclusive os da
          própria Dashboard.jsx). */}
      <Route path="/diagnostico" element={<Navigate to="/cognitive-profile" replace />} />
      <Route path="/motor" element={<Navigate to="/cognitive-profile" replace />} />
      <Route path="/treino" element={<ProtectedRoute><Pagina titulo="Banco de treino"><TreinoHabilidades /></Pagina></ProtectedRoute>} />
      <Route path="/minhas-questoes" element={<ProtectedRoute><Pagina titulo="Minhas questões"><MinhasQuestoes /></Pagina></ProtectedRoute>} />
      <Route path="/mentis" element={<ProtectedRoute><Pagina titulo="Mentis"><MentisChat /></Pagina></ProtectedRoute>} />
      <Route path="/sparks" element={<ProtectedRoute><Pagina titulo="Sparks"><SparksStore /></Pagina></ProtectedRoute>} />
      <Route path="/indicar" element={<ProtectedRoute><Pagina titulo="Indique um amigo"><Indicar /></Pagina></ProtectedRoute>} />
      <Route path="/feed" element={<ProtectedRoute><Pagina titulo="Feed"><Feed /></Pagina></ProtectedRoute>} />
      <Route path="/comunidade" element={<ProtectedRoute><Pagina titulo="Comunidade"><Comunidade /></Pagina></ProtectedRoute>} />
      <Route path="/comunidade/:duvidaId" element={<ProtectedRoute><Pagina titulo="Dúvida da comunidade"><ComunidadeDuvida /></Pagina></ProtectedRoute>} />
      <Route path="/liga" element={<ProtectedRoute><Pagina titulo="Liga"><Liga /></Pagina></ProtectedRoute>} />
      {/* "mural" e "duvidas" são como o aluno chama a aba; o redirect evita
          que o palpite caia na página de "não encontrada". */}
      <Route path="/mural" element={<Navigate to="/comunidade" replace />} />
      <Route path="/duvidas" element={<Navigate to="/comunidade" replace />} />
      <Route path="/redacao" element={<ProtectedRoute><Pagina titulo="Redação"><Redacao /></Pagina></ProtectedRoute>} />
      <Route path="/sugestoes" element={<ProtectedRoute><Pagina titulo="Reclamações e sugestões"><Sugestoes /></Pagina></ProtectedRoute>} />

      <Route path="/admin" element={<AdminRoute><Pagina titulo="Admin"><AdminDashboard /></Pagina></AdminRoute>} />
      <Route path="/admin/answer-keys" element={<AdminRoute><Pagina titulo="Admin · Gabaritos"><Admin /></Pagina></AdminRoute>} />
      <Route path="/admin/feed" element={<AdminRoute><Pagina titulo="Admin · Feed"><AdminFeed /></Pagina></AdminRoute>} />
      <Route path="/admin/annotations" element={<AdminRoute><Pagina titulo="Admin · Anotações"><AdminAnnotations /></Pagina></AdminRoute>} />
      <Route path="/admin/mentoria" element={<AdminRoute><Pagina titulo="Admin · Lista de espera da mentoria"><AdminMentoria /></Pagina></AdminRoute>} />
      <Route path="/admin/aulas-particulares" element={<Navigate to="/admin/mentoria" replace />} />
      <Route path="/admin/cursos" element={<AdminRoute><Pagina titulo="Admin · Cursos e live"><AdminCursos /></Pagina></AdminRoute>} />
      <Route path="/admin/reportes-questoes" element={<AdminRoute><Pagina titulo="Admin · Sugestões de correção"><AdminReportesQuestoes /></Pagina></AdminRoute>} />
      <Route path="/admin/sugestoes" element={<AdminRoute><Pagina titulo="Admin · Reclamações e sugestões"><AdminSugestoes /></Pagina></AdminRoute>} />
      <Route path="/admin/curadoria" element={<AdminRoute><Pagina titulo="Admin · Curadoria"><AdminCuradoria /></Pagina></AdminRoute>} />
      <Route path="/admin/promo-codes" element={<AdminRoute><Pagina titulo="Admin · Códigos de promoção"><AdminPromoCodes /></Pagina></AdminRoute>} />
      <Route path="/admin/indicacoes" element={<AdminRoute><Pagina titulo="Admin · Indicações"><AdminIndicacoes /></Pagina></AdminRoute>} />
      <Route path="/admin/users" element={<AdminRoute><Pagina titulo="Admin · Usuários"><AdminUsers /></Pagina></AdminRoute>} />
      <Route path="/admin/transacoes" element={<AdminRoute><Pagina titulo="Admin · Transações"><AdminTransacoes /></Pagina></AdminRoute>} />
      <Route path="/admin/comunidade" element={<AdminRoute><Pagina titulo="Admin · Comunidade"><AdminComunidade /></Pagina></AdminRoute>} />
      <Route path="/admin/history" element={<AdminRoute><Pagina titulo="Admin · Histórico"><StudentHistory /></Pagina></AdminRoute>} />
      <Route path="/promoter" element={<PromoterRoute><Pagina titulo="Painel do promoter"><PromoterDashboard /></Pagina></PromoterRoute>} />

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
            <ErrorBoundary>
              <Suspense fallback={<Carregando />}>
                <Transicao>
                  <AppRouter />
                </Transicao>
              </Suspense>
            </ErrorBoundary>
            {/* Ícone sempre visível, em toda página logada — ver
                `MentisWidget.jsx` para por que ele se esconde em /mentis. */}
            <MentisWidget />
            {/* "Lembrar-me com a Mentis": o aluno seleciona qualquer trecho,
                em qualquer tela, e guarda aquilo na fila de Revisões. Mora
                aqui pelo mesmo motivo da barra de baixo — uma funcionalidade
                que vale para o produto inteiro, implementada tela a tela, é
                uma funcionalidade que a próxima tela nova não vai ter. */}
            <LembrarComAMentis />
            {/* A navegação do celular. Mora aqui, e não dentro de cada tela,
                porque as 37 páginas do produto montam a própria `<Nav />` e
                acrescentar uma linha em cada uma garantiria que a próxima
                tela nova nasceria sem barra. Ela mesma decide onde não
                aparecer (ver `BarraInferior.jsx`). */}
            <BarraInferior />
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
