import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./components/Home";
import Register from "./components/Register";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";
import GenerateID from "./components/GenerateID";
import GenerateCertificate from "./components/GenerateCertificate";

// Main app component
const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route exact path="/" element={<Home />} />
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/generate-id" element={<GenerateID />} />
        <Route path="/generate-certificate" element={<GenerateCertificate />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
