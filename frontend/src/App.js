import "./App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./lib/auth";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import ExamSelect from "./pages/ExamSelect";
import AnswerInput from "./pages/AnswerInput";
import Diagnostic from "./pages/Diagnostic";
import StudyPlan from "./pages/StudyPlan";
import LearningMap from "./pages/LearningMap";
import History from "./pages/History";
import Trash from "./pages/Trash";
import Admin from "./pages/Admin";
import AdminFeed from "./pages/AdminFeed";
import AdminAnnotations from "./pages/AdminAnnotations";
import CognitiveProfile from "./pages/CognitiveProfile";
import Feed from "./pages/Feed";
import AuthCallback from "./components/AuthCallback";
import ProtectedRoute from "./components/ProtectedRoute";

function AppRouter() {
  const location = useLocation();
  // CRITICAL: handle Emergent OAuth session_id BEFORE routing
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/exams" element={<ProtectedRoute><ExamSelect /></ProtectedRoute>} />
      <Route path="/exam/:examId" element={<ProtectedRoute><AnswerInput /></ProtectedRoute>} />
      <Route path="/analysis/:analysisId" element={<ProtectedRoute><Diagnostic /></ProtectedRoute>} />
      <Route path="/plan/:analysisId" element={<ProtectedRoute><StudyPlan /></ProtectedRoute>} />
      <Route path="/map/:analysisId" element={<ProtectedRoute><LearningMap /></ProtectedRoute>} />
      <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
      <Route path="/trash" element={<ProtectedRoute><Trash /></ProtectedRoute>} />
      <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
      <Route path="/admin/feed" element={<ProtectedRoute><AdminFeed /></ProtectedRoute>} />
      <Route path="/admin/annotations" element={<ProtectedRoute><AdminAnnotations /></ProtectedRoute>} />
      <Route path="/cognitive-profile" element={<ProtectedRoute><CognitiveProfile /></ProtectedRoute>} />
      <Route path="/feed" element={<ProtectedRoute><Feed /></ProtectedRoute>} />
      <Route path="*" element={<Landing />} />
    </Routes>
  );
}

export default function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster position="top-center" richColors closeButton />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}
