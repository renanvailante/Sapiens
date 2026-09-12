import "./App.css";
import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./lib/auth";
import { MentisContextoProvider } from "./lib/mentisContexto";
import ErrorBoundary from "./components/ErrorBoundary";
import TituloDaPagina from "./components/TituloDaPagina";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import FirestoreStudentProvisioner from "./components/FirestoreStudentProvisioner";
import MentisWidget from "./components/MentisWidget";

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
const SparksStore = lazy(() => import("./pages/SparksStore"));
const Feed = lazy(() => import("./pages/Feed"));
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
const AdminAulasParticulares = lazy(() => import("./pages/AdminAulasParticulares"));
const AdminReportesQuestoes = lazy(() => import("./pages/AdminReportesQuestoes"));
const AdminSugestoes = lazy(() => import("./pages/AdminSugestoes"));
const AdminCuradoria = lazy(() => import("./pages/AdminCuradoria"));
const AdminPromoCodes = lazy(() => import("./pages/AdminPromoCodes"));
const StudentHistory = lazy(() => import("./pages/StudentHistory"));

function Carregando() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-2 border-white/15 border-t-sapiens-accent animate-spin" />
    </div>
  );
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
      <Route path="/" element={<Pagina titulo="Descubra por que você erra"><Landing /></Pagina>} />
      <Route path="/login" element={<Pagina titulo="Entrar"><Login /></Pagina>} />
      <Route path="/esqueci-senha" element={<Pagina titulo="Recuperar senha"><EsqueciSenha /></Pagina>} />
      <Route path="/redefinir-senha" element={<Pagina titulo="Nova senha"><RedefinirSenha /></Pagina>} />
      <Route path="/termos" element={<Pagina titulo="Termos de Uso"><Termos /></Pagina>} />
      <Route path="/privacidade" element={<Pagina titulo="Política de Privacidade"><Privacidade /></Pagina>} />

      <Route path="/questoes" element={<ProtectedRoute><Pagina titulo="Banco de questões"><Questoes /></Pagina></ProtectedRoute>} />
      <Route path="/dashboard" element={<ProtectedRoute><Pagina titulo="Painel"><Dashboard /></Pagina></ProtectedRoute>} />
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
      <Route path="/feed" element={<ProtectedRoute><Pagina titulo="Feed"><Feed /></Pagina></ProtectedRoute>} />
      <Route path="/redacao" element={<ProtectedRoute><Pagina titulo="Redação"><Redacao /></Pagina></ProtectedRoute>} />
      <Route path="/sugestoes" element={<ProtectedRoute><Pagina titulo="Reclamações e sugestões"><Sugestoes /></Pagina></ProtectedRoute>} />

      <Route path="/admin" element={<AdminRoute><Pagina titulo="Admin"><AdminDashboard /></Pagina></AdminRoute>} />
      <Route path="/admin/answer-keys" element={<AdminRoute><Pagina titulo="Admin · Gabaritos"><Admin /></Pagina></AdminRoute>} />
      <Route path="/admin/feed" element={<AdminRoute><Pagina titulo="Admin · Feed"><AdminFeed /></Pagina></AdminRoute>} />
      <Route path="/admin/annotations" element={<AdminRoute><Pagina titulo="Admin · Anotações"><AdminAnnotations /></Pagina></AdminRoute>} />
      <Route path="/admin/aulas-particulares" element={<AdminRoute><Pagina titulo="Admin · Aulas particulares"><AdminAulasParticulares /></Pagina></AdminRoute>} />
      <Route path="/admin/reportes-questoes" element={<AdminRoute><Pagina titulo="Admin · Sugestões de correção"><AdminReportesQuestoes /></Pagina></AdminRoute>} />
      <Route path="/admin/sugestoes" element={<AdminRoute><Pagina titulo="Admin · Reclamações e sugestões"><AdminSugestoes /></Pagina></AdminRoute>} />
      <Route path="/admin/curadoria" element={<AdminRoute><Pagina titulo="Admin · Curadoria"><AdminCuradoria /></Pagina></AdminRoute>} />
      <Route path="/admin/promo-codes" element={<AdminRoute><Pagina titulo="Admin · Códigos de promoção"><AdminPromoCodes /></Pagina></AdminRoute>} />
      <Route path="/admin/users" element={<AdminRoute><Pagina titulo="Admin · Usuários"><AdminUsers /></Pagina></AdminRoute>} />
      <Route path="/admin/history" element={<AdminRoute><Pagina titulo="Admin · Histórico"><StudentHistory /></Pagina></AdminRoute>} />

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
            <FirestoreStudentProvisioner />
            <ErrorBoundary>
              <Suspense fallback={<Carregando />}>
                <AppRouter />
              </Suspense>
            </ErrorBoundary>
            {/* Ícone sempre visível, em toda página logada — ver
                `MentisWidget.jsx` para por que ele se esconde em /mentis. */}
            <MentisWidget />
            {/* `theme="dark"`: o Sonner nasce claro e um toast branco era a única
                coisa do produto que continuava em tema claro sobre o ambiente novo. */}
            <Toaster position="top-center" richColors closeButton theme="dark" />
          </MentisContextoProvider>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}
