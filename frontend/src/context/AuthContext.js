import { createContext, useContext, useState } from "react";

const AuthContext = createContext(null);

const readStore = () => ({
  token: localStorage.getItem("cg_token"),
  clientId: localStorage.getItem("cg_client"),
  role: localStorage.getItem("cg_role"),
});

export const AuthProvider = ({ children }) => {
  const [auth, setAuth] = useState(readStore());

  const login = (token, clientId, role) => {
    localStorage.setItem("cg_token", token);
    localStorage.setItem("cg_client", clientId);
    localStorage.setItem("cg_role", role || "client");
    setAuth(readStore());
  };

  const logout = () => {
    localStorage.removeItem("cg_token");
    localStorage.removeItem("cg_client");
    localStorage.removeItem("cg_role");
    setAuth(readStore());
  };

  return (
    <AuthContext.Provider value={{ ...auth, isAuthed: !!auth.token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
