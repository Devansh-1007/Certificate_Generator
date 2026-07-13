import { useState } from "react";
import Swal from "sweetalert2";
import api from "../api/client";

const swalCfg = { background: "#0f172a", color: "#e2e8f0" };

const TemplateDesigner = () => {
  const [prompt, setPrompt] = useState("");
  const [template, setTemplate] = useState(null);
  const [preview, setPreview] = useState(null);
  const [attempts, setAttempts] = useState(null);
  const [busy, setBusy] = useState(false);

  const design = async (e) => {
    e.preventDefault();
    setBusy(true);
    setTemplate(null);
    setPreview(null);
    try {
      const { data } = await api.post("/designTemplate", { PROMPT: prompt });
      setTemplate(data.TEMPLATE);
      setAttempts(data.ATTEMPTS);
      const res = await api.post("/renderPreview", { TEMPLATE: data.TEMPLATE, DATA: {} });
      setPreview(res.data.BASE64);
    } catch (err) {
      Swal.fire({ icon: "error", title: "Design failed", text: err.response?.data?.description || String(err), ...swalCfg });
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    try {
      const { data } = await api.post("/saveTemplate", { TEMPLATE: template });
      Swal.fire({ icon: "success", title: "Template saved", text: data.TEMPLATE_NAME, ...swalCfg });
    } catch (err) {
      Swal.fire({ icon: "error", title: "Save failed", text: err.response?.data?.description || String(err), ...swalCfg });
    }
  };

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="mb-2 font-display text-3xl text-slate-50">AI Template Designer</h1>
      <p className="mb-8 max-w-2xl text-sm text-slate-400">
        Describe the certificate you want. An agent designs the template, validates it against the
        schema, test-renders it, and self-corrects until it passes.
      </p>

      <form onSubmit={design} className="flex flex-col gap-3 sm:flex-row">
        <input
          required
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder='e.g. "formal gold-bordered certificate for a hackathon, with a verification QR"'
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:outline-none"
        />
        <button disabled={busy} className="rounded-lg bg-amber-500 px-6 py-2.5 font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50">
          {busy ? "Designing…" : "Design"}
        </button>
      </form>

      {busy && <p className="mt-8 animate-pulse text-slate-500">The agent is designing and validating your template…</p>}

      {preview && (
        <div className="mt-10 grid gap-6 lg:grid-cols-5">
          <div className="lg:col-span-3">
            <img src={`data:image/png;base64,${preview}`} alt="template preview" className="rounded-xl border border-slate-800" />
            <p className="mt-2 text-xs text-slate-500">Validated in {attempts} attempt{attempts > 1 ? "s" : ""}. Placeholders shown as [NAME].</p>
          </div>
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-100">Template JSON</h3>
              <button onClick={save} className="rounded-lg bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-500">
                Save template
              </button>
            </div>
            <pre className="mt-3 max-h-96 overflow-auto rounded-xl border border-slate-800 bg-slate-900 p-4 text-xs text-slate-300">
              {JSON.stringify(template, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </main>
  );
};

export default TemplateDesigner;
