import { useState } from "react";
import Swal from "sweetalert2";
import api from "../api/client";

const inputCls =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:outline-none";

const Register = () => {
  const [form, setForm] = useState({ CLIENT_ID: "", CLIENT_NAME: "", PASSWORD: "" });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/registerClient", form);
      Swal.fire({
        icon: "success",
        title: "Client registered",
        text: data.description,
        background: "#0f172a",
        color: "#e2e8f0",
      });
      setForm({ CLIENT_ID: "", CLIENT_NAME: "", PASSWORD: "" });
    } catch (err) {
      Swal.fire({
        icon: "error",
        title: "Registration failed",
        text: err.response?.data?.description || "Admin token required",
        background: "#0f172a",
        color: "#e2e8f0",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto max-w-md px-6 py-20">
      <h1 className="mb-2 font-display text-3xl text-slate-50">Register a client</h1>
      <p className="mb-8 text-sm text-slate-400">Admin only — creates a client account that can sign in and generate certificates.</p>
      <form onSubmit={submit} className="space-y-4">
        <input required className={inputCls} placeholder="Client ID" value={form.CLIENT_ID} onChange={set("CLIENT_ID")} />
        <input required className={inputCls} placeholder="Client name" value={form.CLIENT_NAME} onChange={set("CLIENT_NAME")} />
        <input required type="password" className={inputCls} placeholder="Password" value={form.PASSWORD} onChange={set("PASSWORD")} />
        <button disabled={busy} className="w-full rounded-lg bg-amber-500 py-2.5 font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50">
          {busy ? "Registering..." : "Register client"}
        </button>
      </form>
    </main>
  );
};

export default Register;
