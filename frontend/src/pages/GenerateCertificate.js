import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Swal from "sweetalert2";
import api from "../api/client";

const inputCls =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:outline-none";

const GenerateCertificate = () => {
  const [templates, setTemplates] = useState([]);
  const [form, setForm] = useState({
    CERTIFICATE_NAME: "",
    TEMPLATE_NAME: "Classic Achievement",
    EVENT_NAME: "",
    ISSUE_DATE: "",
    SIGNATORY_NAME: "",
    SIGNATORY_TITLE: "",
  });
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    api.get("/templates")
      .then(({ data }) => setTemplates(data.TEMPLATES || []))
      .catch(() => setTemplates([]));
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setResult(null);
    try {
      const { CERTIFICATE_NAME, TEMPLATE_NAME, ...rest } = form;
      const DATA = Object.fromEntries(Object.entries(rest).filter(([, v]) => v));
      const { data } = await api.post("/generateCertificate", {
        CERTIFICATE_NAME,
        TEMPLATE_NAME,
        DATA,
      });
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
    <main className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="mb-2 font-display text-3xl text-slate-50">Generate certificate</h1>
      <p className="mb-8 text-sm text-slate-400">
        Pick a template, fill in the details, and the server renders PNG + PDF. Design new
        templates in the <Link to="/designer" className="text-amber-400">AI Designer</Link>.
      </p>

      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Template</label>
          <select className={inputCls} value={form.TEMPLATE_NAME} onChange={set("TEMPLATE_NAME")}>
            <option value="Classic Achievement">Classic Achievement (default)</option>
            {templates.map((t) => (
              <option key={t.TEMPLATE_NAME} value={t.TEMPLATE_NAME}>{t.TEMPLATE_NAME}</option>
            ))}
          </select>
        </div>
        <input required className={`${inputCls} sm:col-span-2`} placeholder="Recipient name *" value={form.CERTIFICATE_NAME} onChange={set("CERTIFICATE_NAME")} />
        <input className={inputCls} placeholder="Event / reason (optional)" value={form.EVENT_NAME} onChange={set("EVENT_NAME")} />
        <input className={inputCls} placeholder="Issue date (optional, e.g. 15 July 2026)" value={form.ISSUE_DATE} onChange={set("ISSUE_DATE")} />
        <input className={inputCls} placeholder="Signatory name (optional)" value={form.SIGNATORY_NAME} onChange={set("SIGNATORY_NAME")} />
        <input className={inputCls} placeholder="Signatory title (optional)" value={form.SIGNATORY_TITLE} onChange={set("SIGNATORY_TITLE")} />
        <button
          disabled={busy}
          className="rounded-lg bg-amber-500 py-2.5 font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50 sm:col-span-2"
        >
          {busy ? "Rendering…" : "Generate certificate"}
        </button>
      </form>

      {result && (
        <div className="mt-10 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-slate-100">{result.CERTIFICATE_NAME}</h2>
            <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-400">{result.TEMPLATE}</span>
          </div>
          {result.BASE64 && (
            <img src={`data:image/png;base64,${result.BASE64}`} alt="certificate" className="mb-4 rounded-lg border border-slate-800" />
          )}
          <div className="flex flex-wrap gap-4 text-sm">
            {result.IMAGE_URL && <a className="text-amber-400 hover:underline" href={result.IMAGE_URL} target="_blank" rel="noreferrer">Open PNG</a>}
            {result.PDF_URL && <a className="text-amber-400 hover:underline" href={result.PDF_URL} target="_blank" rel="noreferrer">Open PDF</a>}
            {result.CERT_UID && (
              <a className="text-sky-400 hover:underline" href={`/verify/${result.CERT_UID}`} target="_blank" rel="noreferrer">
                Verification page
              </a>
            )}
            {!result.IMAGE_URL && <span className="text-slate-500">Object storage not configured — image shown from local render.</span>}
          </div>
          {result.CERT_UID && (
            <p className="mt-2 text-xs text-slate-500">
              Certificate ID <code className="text-slate-400">{result.CERT_UID}</code> — the QR on the certificate links here.
            </p>
          )}
        </div>
      )}
    </main>
  );
};

export default GenerateCertificate;
