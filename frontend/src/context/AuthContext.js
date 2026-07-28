import { createContext, useContext, useState } from "react";

/**
 * Session state for the multi-tenant app.
 *
 * Every signed-in user belongs to exactly one organisation and can use the
 * product; `role` (owner / admin / member) only gates organisation
 * administration, so the UI hides settings rather than showing actions that
 * would be rejected.
 */
const AuthContext = createContext(null);

const KEYS = ["cg_token", "cg_user", "cg_org"];

const read = () => {
  try {
    return {
      token: localStorage.getItem("cg_token"),
      user: JSON.parse(localStorage.getItem("cg_user") || "null"),
      org: JSON.parse(localStorage.getItem("cg_org") || "null"),
    };
  } catch {
    return { token: null, user: null, org: null };
  }
};

export const AuthProvider = ({ children }) => {
  const [state, setState] = useState(read);

  const login = ({ access_token, USER, ORGANISATION }) => {
    localStorage.setItem("cg_token", access_token);
    localStorage.setItem("cg_user", JSON.stringify(USER || null));
    localStorage.setItem("cg_org", JSON.stringify(ORGANISATION || null));
    setState(read());
  };

  const logout = () => {
    KEYS.forEach((k) => localStorage.removeItem(k));
    setState(read());
  };

  const setOrg = (org) => {
    localStorage.setItem("cg_org", JSON.stringify(org));
    setState(read());
  };

  // Sessions created before the multi-tenant release have a token but no user
  // or organisation payload. They can never satisfy the API, so require a
  // fresh sign-in rather than letting the UI half-work.
  const stale = !!state.token && (!state.user || !state.org);
  const role = state.user?.ROLE || "member";
  return (
    <AuthContext.Provider
      value={{
        ...state,
        role,
        isAuthed: !!state.token && !stale,
        stale,
        canAdminister: role === "owner" || role === "admin",
        isOwner: role === "owner",
        login,
        logout,
        setOrg,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
