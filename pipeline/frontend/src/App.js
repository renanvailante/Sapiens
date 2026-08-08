import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Ontology from "@/pages/Ontology";
import PipelineGenerator from "@/pages/PipelineGenerator";
import ProcessedQuestions from "@/pages/ProcessedQuestions";
import PipelineDetail from "@/pages/PipelineDetail";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/ontologia" element={<Ontology />} />
            <Route path="/gerador" element={<PipelineGenerator />} />
            <Route path="/questoes" element={<ProcessedQuestions />} />
            <Route path="/questoes/:id" element={<PipelineDetail />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </div>
  );
}

export default App;
