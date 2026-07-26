import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import Alert from "../components/Alert";
import GoogleButton from "../components/GoogleButton";
import { useAuth } from "../context/AuthContext";

const inputCls =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:outline-none";

/** Self-serve tenant creation: organisation + its first owner, in one step. */
const Signup = () => {
  const [form, setForm] = useState({ ORG_NAME: "", FULL_NAME: "", EMAIL: "", PASSWORD: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const { login } = useAuth();
  const navigate = useNavigate();
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (form.PASSWORD.length < 8) return setError("Password must be at least 8 characters.");
    setBusy(true);
    try {
      const { data } = await api.post("/auth/signup", form);
      login(data);
      navigate("/dashboard");
    } catch (err) {
      setError(errorMessage(err, "Could not create your account."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <h1 className="mb-2 font-display text-3xl text-slate-50">Start issuing certificates</h1>
      <p className="mb-8 text-sm text-slate-400">
        Create your organisation — you'll be its owner and can invite your team afterwards.
      </p>

      {error && <Alert kind="error" onClose={() => setError(null)}>{error}</Alert>}

      {/* Google users skip the password entirely; the org name below is used if
          their domain doesn't already belong to an organisation. */}
      <GoogleButton
        text="signup_with"
        orgName={form.ORG_NAME}
        onSuccess={(data) => {
          login(data);
          navigate("/dashboard");
        }}
        onError={(err) => setError(errorMessage(err, "Google sign-up failed."))}
      />

      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Organisation *</label>
          <input required className={inputCls} placeholder="e.g. IIT BHU Robotics Club"
                 value={form.ORG_NAME} onChange={set("ORG_NAME")} />
        </div>
        <div>
          <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Your name</label>
          <input className={inputCls} placeholder="Devansh Choudhary" value={form.FULL_NAME} onChange={set("FULL_NAME")} />
        </div>
        <div>
          <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Work email *</label>
          <input required type="email" className={inputCls} placeholder="you@organisation.com"
                 value={form.EMAIL} onChange={set("EMAIL")} />
          <p className="mt-1 text-xs text-slate-500">
            Use your work domain — colleagues who sign up with the same domain join
            this organisation automatically instead of creating a duplicate.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Password *</label>
          <input required type="password" minLength={8} className={inputCls} placeholder="At least 8 characters"
                 value={form.PASSWORD} onChange={set("PASSWORD")} />
        </div>
        <button disabled={busy}
                className="w-full rounded-lg bg-amber-500 py-2.5 font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50">
          {busy ? "Creating your workspace…" : "Create organisation"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        Already have an account? <Link to="/login" className="text-amber-400">Sign in</Link>
      </p>
    </main>
  );
};

export default Signup;
