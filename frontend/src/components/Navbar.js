import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Navbar = () => {
  const { isAuthed, user, org, role, canAdminister, logout } = useAuth();
  const navigate = useNavigate();

  const link = "text-slate-300 transition hover:text-white";

  return (
    <nav className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link to="/" className="font-display text-xl tracking-wide text-amber-400">
          Certify<span className="text-slate-100">AI</span>
        </Link>

        <div className="flex items-center gap-5 text-sm">
          {isAuthed ? (
            <>
              {/* Every member can use the product — no dead-end links. */}
              <Link to="/dashboard" className={link}>Dashboard</Link>
              <Link to="/certificates" className={link}>Certificates</Link>
              <Link to="/bulk" className={link}>Bulk</Link>
              <Link to="/designer" className={link}>Designer</Link>
              {canAdminister && (
                <>
                  <Link to="/team" className="text-amber-400 hover:text-amber-300">Team</Link>
                  <Link to="/admin" className="text-amber-400 hover:text-amber-300">Console</Link>
                </>
              )}
              <span className="hidden rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-400 sm:inline">
                {org?.NAME || "Organisation"} · {role}
              </span>
              <button
                onClick={() => { logout(); navigate("/"); }}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:border-slate-500 hover:text-white"
                title={user?.EMAIL}
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className={link}>Sign in</Link>
              <Link
                to="/signup"
                className="rounded-lg bg-amber-500 px-4 py-1.5 font-medium text-slate-950 hover:bg-amber-400"
              >
                Start free
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
