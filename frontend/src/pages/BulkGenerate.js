import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import { errorMessage, showError } from "../api/errors";
import Alert from "../components/Alert";

const inputCls =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:outline-none";

// anomaly type -> badge colour + short label
const BADGE = {
  missing: ["bg-rose-500/20 text-rose-300", "missing"],
  whitespace: ["bg-sky-500/20 text-sky-300", "spacing"],
  casing: ["bg-amber-500/20 text-amber-300", "casing"],
  duplicate_exact: ["bg-rose-500/20 text-rose-300", "duplicate"],
  duplicate_near: ["bg-fuchsia-500/20 text-fuchsia-300", "near-dup"],
};

const BulkGenerate = () => {
  const [templates, setTemplates] = useState([]);
  const [templateName, setTemplateName] = useState("Classic Achievement");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);

  const [step, setStep] = useState("upload"); // upload | review | progress | done
  const [review, setReview] = useState(null); // upload response
  const [rows, setRows] = useState([]); // editable rows
  const [job, setJob] = useState(null); // polled job detail
  const [error, setError] = useState(null); // inline banner (keeps context visible)
  const pollRef = useRef(null);

  useEffect(() => {
    api.get("/templates").then(({ data }) => setTemplates(data.TEMPLATES || [])).catch(() => {});
    return () => clearInterval(pollRef.current);
  }, []);

  // ---- upload ----
  const downloadRosterTemplate = async () => {
    try {
      const res = await api.get("/bulk/template", {
        params: { TEMPLATE_NAME: templateName },
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `roster-template.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      showError(err, "Couldn't download the template");
    }
  };

  const upload = async (e) => {
    e.preventDefault();
    setError(null);
    if (!file) return setError("Choose a CSV, TSV or Excel file first.");
    const ok = /\.(csv|tsv|txt|xlsx|xlsm)$/i.test(file.name);
    if (!ok) return setError(`"${file.name}" isn't a supported format. Upload .csv, .tsv or .xlsx.`);
    if (file.size > 5 * 1024 * 1024) return setError("File is larger than 5 MB — split the roster.");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("TEMPLATE_NAME", templateName);
      const { data } = await api.post("/bulk/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setReview(data);
      setRows(data.SUGGESTED_ROWS.map((r) => ({ ...r }))); // start from cleaned rows
      setStep("review");
    } catch (err) {
      setError(errorMessage(err, "Upload failed."));
    } finally {
      setBusy(false);
    }
  };

  // group anomalies by row for quick lookup
  const anomaliesByRow = (review?.REPORT?.anomalies || []).reduce((acc, a) => {
    (acc[a.row] = acc[a.row] || []).push(a);
    return acc;
  }, {});

  const editCell = (i, col) => (e) => {
    const next = rows.slice();
    next[i] = { ...next[i], [col]: e.target.value };
    setRows(next);
  };

  const resetToOriginal = () => setRows(review.ROWS.map((r) => ({ ...r })));

  // ---- approve + poll ----
  const approve = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/bulk/jobs/${review.JOB_ID}/approve`, { ROWS: rows });
      setStep("progress");
      setJob({ STATUS: "RENDERING", TOTAL: data.TOTAL, PROCESSED: 0, SUCCEEDED: 0, FAILED: 0 });
      pollRef.current = setInterval(poll, 1200);
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  };

  const poll = async () => {
    try {
      const { data } = await api.get(`/bulk/jobs/${review.JOB_ID}`);
      setJob(data.JOB);
      if (data.JOB.STATUS === "DONE" || data.JOB.STATUS === "FAILED") {
        clearInterval(pollRef.current);
        setStep("done");
      }
    } catch {
      clearInterval(pollRef.current);
    }
  };

  const download = async () => {
    try {
      const res = await api.get(`/bulk/jobs/${review.JOB_ID}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `certificates_batch_${review.JOB_ID}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      showError(err, "Download failed");
    }
  };

  const restart = () => {
    clearInterval(pollRef.current);
    setStep("upload");
    setReview(null);
    setRows([]);
    setJob(null);
    setFile(null);
  };

  const columns = review ? review.PLACEHOLDERS : [];
  const counts = review?.REPORT?.counts || {};

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="mb-2 font-display text-3xl text-slate-50">Bulk certificates</h1>
      <p className="mb-8 text-sm text-slate-400">
        Upload a roster (CSV / Excel). The anomaly agent flags duplicates, casing and missing
        fields for you to review before rendering — safe fixes are pre-applied. Design templates
        in the <Link to="/designer" className="text-amber-400">AI Designer</Link>.
      </p>

      {/* stepper */}
      <div className="mb-8 flex gap-2 text-xs">
        {["upload", "review", "progress", "done"].map((s, i) => (
          <span
            key={s}
            className={`rounded-full px-3 py-1 capitalize ${
              step === s ? "bg-amber-500 text-slate-950" : "bg-slate-800 text-slate-400"
            }`}
          >
            {i + 1}. {s}
          </span>
        ))}
      </div>

      {/* STEP 1 — upload */}
      {error && (
        <Alert kind="error" title="Couldn't process that file" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {step === "upload" && (
        <form onSubmit={upload} className="grid max-w-xl gap-4">
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Template</label>
            <select className={inputCls} value={templateName} onChange={(e) => setTemplateName(e.target.value)}>
              <option value="Classic Achievement">Classic Achievement (default)</option>
              {templates.map((t) => (
                <option key={t.TEMPLATE_NAME} value={t.TEMPLATE_NAME}>{t.TEMPLATE_NAME}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Roster file (.csv / .xlsx)</label>
            <input
              type="file"
              accept=".csv,.tsv,.xlsx,.xlsm"
              onChange={(e) => setFile(e.target.files[0])}
              className="block w-full text-sm text-slate-400 file:mr-4 file:rounded-lg file:border-0 file:bg-amber-500 file:px-4 file:py-2 file:font-semibold file:text-slate-950 hover:file:bg-amber-400"
            />
            <p className="mt-2 text-xs leading-relaxed text-slate-500">
              Accepts .csv, .tsv and .xlsx (max 5 MB, 2000 rows). The delimiter is detected
              automatically (comma, semicolon, tab or pipe) and title rows above the header are skipped.
              Columns are matched to template fields by name, common synonyms
              (&ldquo;Full Name&rdquo;, &ldquo;Candidate&rdquo;, &ldquo;Course&rdquo;) and fuzzy matching —
              you&rsquo;ll see exactly what matched on the next screen.
            </p>
            <button
              type="button"
              onClick={downloadRosterTemplate}
              className="mt-3 text-sm font-medium text-amber-400 hover:underline"
            >
              ↓ Download a ready-to-fill CSV for this template
            </button>
          </div>
          <button disabled={busy} className="rounded-lg bg-amber-500 py-2.5 font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50">
            {busy ? "Analysing…" : "Upload & review"}
          </button>
        </form>
      )}

      {/* STEP 2 — review */}
      {step === "review" && review && (
        <div>
          {review.MAPPING_REPORT && review.MAPPING_REPORT.length > 0 && (
            <div className="mb-5 rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
              <h3 className="mb-3 text-sm font-semibold text-slate-200">Detected columns</h3>
              <div className="flex flex-wrap gap-2 text-xs">
                {review.MAPPING_REPORT.map((m) => {
                  const cls = !m.PLACEHOLDER
                    ? "border-slate-700 bg-slate-800/60 text-slate-500"
                    : m.METHOD === "exact" || m.METHOD === "manual"
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
                    : "border-amber-500/40 bg-amber-500/10 text-amber-200";
                  return (
                    <span key={m.HEADER} className={`rounded-lg border px-2.5 py-1.5 ${cls}`}>
                      <span className="font-mono">{m.HEADER}</span>
                      {m.PLACEHOLDER ? (
                        <>
                          {" → "}
                          <span className="font-mono">{m.PLACEHOLDER}</span>
                          {m.METHOD !== "exact" && m.METHOD !== "manual" && (
                            <span className="opacity-70"> ({m.METHOD} {m.CONFIDENCE}%)</span>
                          )}
                        </>
                      ) : (
                        <span className="opacity-70"> · ignored</span>
                      )}
                    </span>
                  );
                })}
              </div>
              {review.UNMAPPED && review.UNMAPPED.length > 0 && (
                <p className="mt-3 text-xs text-amber-300/90">
                  No column found for: <span className="font-mono">{review.UNMAPPED.join(", ")}</span> —
                  these fall back to defaults on every certificate.
                </p>
              )}
            </div>
          )}

          <div className="mb-5 flex flex-wrap items-center gap-3">
            <span className="text-sm text-slate-300">
              {review.REPORT.total_rows} rows · {review.REPORT.anomaly_count} findings
            </span>
            {Object.entries(counts).map(([type, n]) => {
              const [cls, label] = BADGE[type] || ["bg-slate-700 text-slate-300", type];
              return (
                <span key={type} className={`rounded-full px-3 py-1 text-xs ${cls}`}>
                  {n} {label}
                </span>
              );
            })}
            <button onClick={resetToOriginal} className="ml-auto text-xs text-slate-400 hover:text-slate-200 underline">
              Reset to original values
            </button>
          </div>

          {review.UNMAPPED_PLACEHOLDERS.length > 0 && (
            <p className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs text-amber-200">
              No roster column mapped to: {review.UNMAPPED_PLACEHOLDERS.join(", ")}. These fall back
              to template defaults.
            </p>
          )}

          <div className="overflow-x-auto rounded-2xl border border-slate-800">
            <table className="w-full text-sm">
              <thead className="bg-slate-900/80 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2">#</th>
                  {columns.map((c) => (
                    <th key={c} className="px-3 py-2">
                      {c}
                      {c === review.NAME_FIELD && <span className="ml-1 text-amber-400">•</span>}
                    </th>
                  ))}
                  <th className="px-3 py-2">Findings</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => {
                  const flags = anomaliesByRow[i] || [];
                  const hasHigh = flags.some((f) => f.severity === "high");
                  return (
                    <tr key={i} className={`border-t border-slate-800 ${hasHigh ? "bg-rose-500/5" : ""}`}>
                      <td className="px-3 py-2 text-slate-500">{i + 1}</td>
                      {columns.map((c) => (
                        <td key={c} className="px-2 py-1.5">
                          <input
                            value={row[c] || ""}
                            onChange={editCell(i, c)}
                            className="w-full min-w-[8rem] rounded border border-transparent bg-transparent px-2 py-1 text-slate-200 hover:border-slate-700 focus:border-amber-500 focus:outline-none"
                          />
                        </td>
                      ))}
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {flags.map((f, k) => {
                            const [cls, label] = BADGE[f.type] || ["bg-slate-700 text-slate-300", f.type];
                            return (
                              <span key={k} title={f.message} className={`cursor-help rounded px-1.5 py-0.5 text-[10px] ${cls}`}>
                                {label}
                              </span>
                            );
                          })}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-6 flex items-center gap-4">
            <button onClick={approve} disabled={busy} className="rounded-lg bg-amber-500 px-6 py-2.5 font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50">
              {busy ? "Starting…" : `Approve & generate ${rows.length} certificates`}
            </button>
            <button onClick={restart} className="text-sm text-slate-400 hover:text-slate-200">Cancel</button>
          </div>
        </div>
      )}

      {/* STEP 3 — progress */}
      {step === "progress" && job && (
        <div className="max-w-xl">
          <p className="mb-3 text-slate-300">Rendering certificates…</p>
          <div className="h-3 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full bg-amber-500 transition-all"
              style={{ width: `${job.TOTAL ? (job.PROCESSED / job.TOTAL) * 100 : 0}%` }}
            />
          </div>
          <p className="mt-3 text-sm text-slate-400">
            {job.PROCESSED} / {job.TOTAL} · {job.SUCCEEDED} ok · {job.FAILED} failed
          </p>
        </div>
      )}

      {/* STEP 4 — done */}
      {step === "done" && job && (
        <div className="max-w-xl rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="mb-2 font-semibold text-slate-100">
            Batch {job.STATUS === "DONE" ? "complete" : "finished with errors"}
          </h2>
          <p className="mb-5 text-sm text-slate-400">
            {job.SUCCEEDED} certificate{job.SUCCEEDED === 1 ? "" : "s"} rendered
            {job.FAILED > 0 && `, ${job.FAILED} failed`}.
          </p>

          {Array.isArray(job.ERRORS_JSON) && job.ERRORS_JSON.length > 0 && (
            <ul className="mb-5 max-h-40 overflow-y-auto rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 text-xs text-rose-200">
              {job.ERRORS_JSON.map((e, i) => (
                <li key={i}>Row {e.row} ({e.name}): {e.error}</li>
              ))}
            </ul>
          )}

          <div className="flex gap-4">
            {job.SUCCEEDED > 0 && (
              <button onClick={download} className="rounded-lg bg-amber-500 px-6 py-2.5 font-semibold text-slate-950 hover:bg-amber-400">
                Download zip
              </button>
            )}
            <button onClick={restart} className="rounded-lg border border-slate-700 px-6 py-2.5 text-slate-300 hover:border-slate-500 hover:text-white">
              New batch
            </button>
          </div>
        </div>
      )}
    </main>
  );
};

export default BulkGenerate;
