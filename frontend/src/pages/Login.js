import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import Swal from "sweetalert2";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

const inputCls =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:outline-none";

const Login = () => {
  const [mode, setMode] = useState("client");
  const [form, setForm] = useState({ CLIENT_ID: "", CLIENT_NAME: "", PASSWORD: "" });
  const [busy, setBusy] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "client") {
        const { data } = await api.post("/loginClient", form);
        login(data.access_token, form.CLIENT_ID, data.role || "client");
      } else {
        const { data } = await api.post("/loginAdmin", {
          USERNAME: form.CLIENT_ID,
          PASSWORD: form.PASSWORD,
        });
        login(data.access_token, form.CLIENT_ID, "admin");
      }
      navigate("/dashboard");
    } catch (err) {
      Swal.fire({
        icon: "error",
        title: "Login failed",
        text: err.response?.data?.error || "Check your credentials",
        background: "#0f172a",
        color: "#e2e8f0",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto flex max-w-md flex-col px-6 py-20">
      <h1 className="mb-2 font-display text-3xl text-slate-50">Sign in</h1>
      <p className="mb-8 text-sm text-slate-400">
        {mode === "client" ? "Client account issued by an admin." : "Admin credentials from server config."}
      </p>
      <div className="mb-6 grid grid-cols-2 rounded-lg border border-slate-800 p-1 text-sm">
        {["client", "admin"].map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`rounded-md py-1.5 capitalize ${mode === m ? "bg-amber-500 font-medium text-slate-950" : "text-slate-400"}`}
          >
            {m}
          </button>
        ))}
      </div>
      <form onSubmit={submit} className="space-y-4">
        <input required className={inputCls} placeholder={mode === "client" ? "Client ID" : "Admin username"} value={form.CLIENT_ID} onChange={set("CLIENT_ID")} />
        {mode === "client" && (
          <input required className={inputCls} placeholder="Client name" value={form.CLIENT_NAME} onChange={set("CLIENT_NAME")} />
        )}
        <input required type="password" className={inputCls} placeholder="Password" value={form.PASSWORD} onChange={set("PASSWORD")} />
        <button
          disabled={busy}
          className="w-full rounded-lg bg-amber-500 py-2.5 font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50"
        >
          {busy ? "Signing in..." : "Sign in"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">
        Need a client account? Ask an admin, or <Link to="/register" className="text-amber-400">register one</Link> if you are the admin.
      </p>
    </main>
  );
};

export default Login;
