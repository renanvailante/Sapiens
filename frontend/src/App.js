import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";

import LoginPage from "@/pages/LoginPage";
import AppLayout from "@/layout/AppLayout";
import TurmaView from "@/pages/TurmaView";
import ProcessoView from "@/pages/ProcessoView";
import AlunoView from "@/pages/AlunoView";
import EvolucaoView from "@/pages/EvolucaoView";
import TaxonomiaView from "@/pages/TaxonomiaView";
import ImportView from "@/pages/ImportView";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading || user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm font-mono text-muted-foreground">
        Carregando…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/turma" replace />;
  return children;
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<PublicOnly><LoginPage /></PublicOnly>} />
            <Route
              element={
                <Protected>
                  <AppLayout />
                </Protected>
              }
            >
              <Route path="/" element={<Navigate to="/turma" replace />} />
              <Route path="/turma" element={<TurmaView />} />
              <Route path="/processo" element={<ProcessoView />} />
              <Route path="/aluno" element={<AlunoView />} />
              <Route path="/evolucao" element={<EvolucaoView />} />
              <Route path="/taxonomia" element={<TaxonomiaView />} />
              <Route path="/import" element={<ImportView />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" />
      </AuthProvider>
    </div>
  );
}

export default App;
