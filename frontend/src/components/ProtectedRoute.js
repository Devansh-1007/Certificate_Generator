import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/**
 * `adminOnly` guards organisation administration (settings, team, console).
 * Everything else is open to any signed-in member — the product is the point.
 */
const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { isAuthed, canAdminister } = useAuth();
  if (!isAuthed) return <Navigate to="/login" replace />;
  if (adminOnly && !canAdminister) return <Navigate to="/dashboard" replace />;
  return children;
};

export default ProtectedRoute;
