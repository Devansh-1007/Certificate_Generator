import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Navbar = () => {
  const { isAuthed, clientId, role, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <nav className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link to="/" className="font-display text-xl tracking-wide text-amber-400">
          Certify<span className="text-slate-100">AI</span>
        </Link>
        <div className="flex items-center gap-5 text-sm">
          {isAuthed ? (
            <>
              <Link to="/dashboard" className="text-slate-300 hover:text-white">Dashboard</Link>
              <Link to="/designer" className="text-slate-300 hover:text-white">AI Designer</Link>
              {role === "admin" && (
                <Link to="/register" className="text-amber-400 hover:text-amber-300">Register client</Link>
              )}
              <span className="hidden rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-400 sm:inline">
                {clientId} · {role}
              </span>
              <button
                onClick={() => { logout(); navigate("/"); }}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:border-slate-500 hover:text-white"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="rounded-lg bg-amber-500 px-4 py-1.5 font-medium text-slate-950 hover:bg-amber-400"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
