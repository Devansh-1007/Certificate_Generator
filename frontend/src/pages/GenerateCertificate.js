import { useState } from "react";
import Swal from "sweetalert2";
import api from "../api/client";

const GenerateCertificate = () => {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setResult(null);
    try {
      const { data } = await api.post("/generateCertificate", { CERTIFICATE_NAME: name });
      setResult(data.CERTIFICATE_DETAILS);
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
      <h1 className="mb-2 font-display text-3xl text-slate-50">Generate certificate</h1>
      <p className="mb-8 text-sm text-slate-400">The recipient name is drawn onto the template and exported as PNG + PDF.</p>
      <form onSubmit={submit} className="flex gap-3">
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Recipient name"
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:outline-none"
        />
        <button disabled={busy} className="rounded-lg bg-amber-500 px-6 font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50">
          {busy ? "Rendering…" : "Generate"}
        </button>
      </form>

      {result && (
        <div className="mt-10 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="mb-4 font-semibold text-slate-100">{result.CERTIFICATE_NAME}</h2>
          {result.BASE64 && (
            <img src={`data:image/png;base64,${result.BASE64}`} alt="certificate" className="mb-4 rounded-lg border border-slate-800" />
          )}
          <div className="flex gap-4 text-sm">
            {result.IMAGE_URL && <a className="text-amber-400 hover:underline" href={result.IMAGE_URL} target="_blank" rel="noreferrer">Open PNG</a>}
            {result.PDF_URL && <a className="text-amber-400 hover:underline" href={result.PDF_URL} target="_blank" rel="noreferrer">Open PDF</a>}
          </div>
        </div>
      )}
    </main>
  );
};

export default GenerateCertificate;
