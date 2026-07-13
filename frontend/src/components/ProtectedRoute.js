import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { isAuthed, role } = useAuth();
  if (!isAuthed) return <Navigate to="/login" replace />;
  if (adminOnly && role !== "admin") return <Navigate to="/dashboard" replace />;
  return children;
};

export default ProtectedRoute;
