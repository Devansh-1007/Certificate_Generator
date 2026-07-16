import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import GenerateCertificate from "./pages/GenerateCertificate";
import BulkGenerate from "./pages/BulkGenerate";
import BatchJobs from "./pages/BatchJobs";
import GenerateId from "./pages/GenerateId";
import IdCards from "./pages/IdCards";
import Certificates from "./pages/Certificates";
import Templates from "./pages/Templates";
import TemplateDesigner from "./pages/TemplateDesigner";
import Verify from "./pages/Verify";

const App = () => (
  <AuthProvider>
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/verify/:id" element={<Verify />} />
        <Route path="/register" element={<ProtectedRoute adminOnly><Register /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/generate-certificate" element={<ProtectedRoute><GenerateCertificate /></ProtectedRoute>} />
        <Route path="/certificates" element={<ProtectedRoute><Certificates /></ProtectedRoute>} />
        <Route path="/bulk" element={<ProtectedRoute><BulkGenerate /></ProtectedRoute>} />
        <Route path="/batch-jobs" element={<ProtectedRoute><BatchJobs /></ProtectedRoute>} />
        <Route path="/generate-id" element={<ProtectedRoute><GenerateId /></ProtectedRoute>} />
        <Route path="/id-cards" element={<ProtectedRoute><IdCards /></ProtectedRoute>} />
        <Route path="/templates" element={<ProtectedRoute><Templates /></ProtectedRoute>} />
        <Route path="/designer" element={<ProtectedRoute><TemplateDesigner /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  </AuthProvider>
);

export default App;
