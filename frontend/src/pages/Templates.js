import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Swal from "sweetalert2";
import api from "../api/client";

const swalCfg = { background: "#0f172a", color: "#e2e8f0" };

const Templates = () => {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState(null); // {name, base64}
  const [busy, setBusy] = useState(false);

  const load = () => {
    setLoading(true);
    api
      .get("/templates")
      .then(({ data }) => setTemplates(data.TEMPLATES || []))
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const showPreview = async (t) => {
    setBusy(true);
    setPreview(null);
    try {
      const { data } = await api.post("/renderPreview", { TEMPLATE: t.TEMPLATE, DATA: {} });
      setPreview({ name: t.TEMPLATE_NAME, base64: data.BASE64 });
    } catch (err) {
      Swal.fire({ icon: "error", title: "Preview failed", text: err.response?.data?.description || String(err), ...swalCfg });
    } finally {
      setBusy(false);
    }
  };

  const remove = async (name) => {
    const confirm = await Swal.fire({
      icon: "warning", title: "Delete template?", text: name,
      showCancelButton: true, confirmButtonText: "Delete", confirmButtonColor: "#e11d48", ...swalCfg,
    });
    if (!confirm.isConfirmed) return;
    try {
      await api.delete(`/templates/${encodeURIComponent(name)}`);
      if (preview?.name === name) setPreview(null);
      load();
    } catch (err) {
      Swal.fire({ icon: "error", title: "Delete failed", text: err.response?.data?.description || String(err), ...swalCfg });
    }
  };

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="mb-2 font-display text-3xl text-slate-50">Templates</h1>
          <p className="text-sm text-slate-400">
            Your saved designs. Create more in the <Link to="/designer" className="text-amber-400">AI Designer</Link>.
          </p>
        </div>
        <Link to="/designer" className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-amber-400">
          + New template
        </Link>
      </div>

      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : templates.length === 0 ? (
        <p className="text-slate-500">No saved templates yet — design one and hit “Save template”.</p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <ul className="space-y-2">
              {templates.map((t) => (
                <li key={t.TEMPLATE_NAME} className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3">
                  <div>
                    <p className="font-medium text-slate-100">{t.TEMPLATE_NAME}</p>
                    <p className="text-xs text-slate-500">updated {(t.UPDATED_ON || "").slice(0, 10)}</p>
                  </div>
                  <div className="flex gap-3 text-xs">
                    <button onClick={() => showPreview(t)} className="text-sky-400 hover:underline">Preview</button>
                    <Link to="/generate-certificate" className="text-amber-400 hover:underline">Use</Link>
                    <button onClick={() => remove(t.TEMPLATE_NAME)} className="text-rose-400 hover:underline">Delete</button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div className="lg:col-span-3">
            {busy && <p className="animate-pulse text-slate-500">Rendering preview…</p>}
            {preview && (
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <p className="mb-3 text-sm text-slate-300">{preview.name}</p>
                <img src={`data:image/png;base64,${preview.base64}`} alt="template preview" className="rounded-lg border border-slate-800" />
              </div>
            )}
            {!preview && !busy && <p className="text-slate-600">Select a template to preview it.</p>}
          </div>
        </div>
      )}
    </main>
  );
};

export default Templates;
