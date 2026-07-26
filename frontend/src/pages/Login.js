import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import Alert from "../components/Alert";
import { useAuth } from "../context/AuthContext";

const inputCls =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:outline-none";

/** Email + password. The organisation comes from the account, not a form field. */
const Login = () => {
  const [form, setForm] = useState({ EMAIL: "", PASSWORD: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const { login } = useAuth();
  const navigate = useNavigate();
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const { data } = await api.post("/auth/login", form);
      login(data);
      navigate("/dashboard");
    } catch (err) {
      setError(errorMessage(err, "Sign-in failed."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <h1 className="mb-2 font-display text-3xl text-slate-50">Sign in</h1>
      <p className="mb-8 text-sm text-slate-400">Welcome back.</p>

      {error && <Alert kind="error" onClose={() => setError(null)}>{error}</Alert>}

      <form onSubmit={submit} className="space-y-4">
        <input required type="email" className={inputCls} placeholder="you@organisation.com"
               value={form.EMAIL} onChange={set("EMAIL")} />
        <input required type="password" className={inputCls} placeholder="Password"
               value={form.PASSWORD} onChange={set("PASSWORD")} />
        <button disabled={busy}
                className="w-full rounded-lg bg-amber-500 py-2.5 font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50">
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        New here? <Link to="/signup" className="text-amber-400">Create an organisation</Link>
      </p>
    </main>
  );
};

export default Login;
