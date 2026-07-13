import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import GenerateCertificate from "./pages/GenerateCertificate";
import GenerateId from "./pages/GenerateId";
import TemplateDesigner from "./pages/TemplateDesigner";

const App = () => (
  <AuthProvider>
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<ProtectedRoute adminOnly><Register /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/generate-certificate" element={<ProtectedRoute><GenerateCertificate /></ProtectedRoute>} />
        <Route path="/generate-id" element={<ProtectedRoute><GenerateId /></ProtectedRoute>} />
        <Route path="/designer" element={<ProtectedRoute><TemplateDesigner /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  </AuthProvider>
);

export default App;
