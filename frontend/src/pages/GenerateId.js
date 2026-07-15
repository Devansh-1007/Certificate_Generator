import { useState } from "react";
import Swal from "sweetalert2";
import api from "../api/client";

const inputCls =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:outline-none";

const GenerateId = () => {
  const [form, setForm] = useState({ ID_NAME: "", ORG_NAME: "" });
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setResult(null);
    try {
      const { data } = await api.post("/generateId", form);
      setResult(data.ID_DETAILS);
    } catch (err) {
      Swal.fire({
        icon: "error",
        title: "Generation failed",
        text: err.response?.data?.description || String(err),
        background: "#0f172a",
        color: "#e2e8f0",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="mb-2 font-display text-3xl text-slate-50">Generate ID card</h1>
      <p className="mb-8 text-sm text-slate-400">Portrait ID card with a verification QR, exported as PNG + PDF.</p>
      <form onSubmit={submit} className="grid gap-4">
        <input required className={inputCls} placeholder="Holder name *" value={form.ID_NAME} onChange={set("ID_NAME")} />
        <input className={inputCls} placeholder="Organization name (optional, shown in the header)" value={form.ORG_NAME} onChange={set("ORG_NAME")} />
        <button disabled={busy} className="rounded-lg bg-amber-500 py-2.5 font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50">
          {busy ? "Rendering…" : "Generate ID card"}
        </button>
      </form>
      {result && (
        <div className="mt-10 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="mb-4 font-semibold text-slate-100">{result.ID_NAME}</h2>
          {result.BASE64 && (
            <img src={`data:image/png;base64,${result.BASE64}`} alt="id card" className="mx-auto mb-4 w-72 rounded-lg border border-slate-800" />
          )}
          <div className="flex justify-center gap-4 text-sm">
            {result.IMAGE_URL && <a className="text-amber-400 hover:underline" href={result.IMAGE_URL} target="_blank" rel="noreferrer">Open PNG</a>}
            {result.PDF_URL && <a className="text-amber-400 hover:underline" href={result.PDF_URL} target="_blank" rel="noreferrer">Open PDF</a>}
          </div>
        </div>
      )}
    </main>
  );
};

export default GenerateId;
