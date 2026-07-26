import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Swal from "sweetalert2";
import api from "../api/client";
import { showError } from "../api/errors";

/**
 * The date input gives ISO (yyyy-mm-dd); certificates read better as
 * "15 July 2026", so convert on submit and leave the field free-text-safe.
 */
const formatIssueDate = (iso) => {
  if (!iso) return "";
  const d = new Date(iso + "T00:00:00");
  if (Number.isNaN(d.getTime())) return iso; // typed value we can't parse — pass through
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
};

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
      const DATA = Object.fromEntries(
        Object.entries({ ...rest, ISSUE_DATE: formatIssueDate(rest.ISSUE_DATE) })
          .filter(([, v]) => v)
      );
      const { data } = await api.post("/generateCertificate", {
        CERTIFICATE_NAME,
        TEMPLATE_NAME,
        DATA,
      });
      setResult(data.CERTIFICATE_DETAILS);
    } catch (err) {
      showError(err, "Generation failed");
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
        <div className="sm:col-span-2">
          <label htmlFor="recipient" className="mb-1 block text-xs uppercase tracking-wide text-slate-500">
            Recipient name *
          </label>
          <input id="recipient" required className={inputCls} placeholder="e.g. Happu Singh"
                 value={form.CERTIFICATE_NAME} onChange={set("CERTIFICATE_NAME")} />
        </div>
        <div>
          <label htmlFor="event" className="mb-1 block text-xs uppercase tracking-wide text-slate-500">
            Event / reason <span className="normal-case tracking-normal text-slate-600">(optional)</span>
          </label>
          <input id="event" className={inputCls} placeholder="e.g. Annual Symposium 2026"
                 value={form.EVENT_NAME} onChange={set("EVENT_NAME")} />
        </div>
        <div>
          <label htmlFor="issue-date" className="mb-1 block text-xs uppercase tracking-wide text-slate-500">
            Issue date <span className="normal-case tracking-normal text-slate-600">(optional — defaults to today)</span>
          </label>
          <input
            id="issue-date"
            type="date"
            value={form.ISSUE_DATE}
            onChange={set("ISSUE_DATE")}
            max="2100-12-31"
            className={`${inputCls} [color-scheme:dark]`}
          />
          {form.ISSUE_DATE && (
            <p className="mt-1 text-xs text-slate-500">
              Prints as <span className="text-slate-300">{formatIssueDate(form.ISSUE_DATE)}</span>
            </p>
          )}
        </div>
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
