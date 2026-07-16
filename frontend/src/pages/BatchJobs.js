import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Swal from "sweetalert2";
import api from "../api/client";

const STATUS_CLS = {
  PENDING_REVIEW: "bg-amber-500/20 text-amber-300",
  RENDERING: "bg-sky-500/20 text-sky-300",
  DONE: "bg-emerald-500/20 text-emerald-300",
  FAILED: "bg-rose-500/20 text-rose-300",
};

const BatchJobs = () => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api
      .get("/bulk/jobs")
      .then(({ data }) => setJobs(data.JOBS || []))
      .catch(() => setJobs([]))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const download = async (id) => {
    try {
      const res = await api.get(`/bulk/jobs/${id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `certificates_batch_${id}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      Swal.fire({ icon: "error", title: "Download failed", text: err.response?.data?.description || "Not ready", background: "#0f172a", color: "#e2e8f0" });
    }
  };

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="mb-2 font-display text-3xl text-slate-50">Batch jobs</h1>
          <p className="text-sm text-slate-400">History of your bulk certificate runs.</p>
        </div>
        <div className="flex gap-3">
          <button onClick={load} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-500 hover:text-white">
            Refresh
          </button>
          <Link to="/bulk" className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-amber-400">
            + New batch
          </Link>
        </div>
      </div>

      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : jobs.length === 0 ? (
        <p className="text-slate-500">No batch jobs yet — start one from <Link to="/bulk" className="text-amber-400">Bulk</Link>.</p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-900/80 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">#</th>
                <th className="px-4 py-2">Template</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Progress</th>
                <th className="px-4 py-2">Created</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.JOB_ID} className="border-t border-slate-800">
                  <td className="px-4 py-3 text-slate-500">{j.JOB_ID}</td>
                  <td className="px-4 py-3 text-slate-300">{j.TEMPLATE_NAME}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs ${STATUS_CLS[j.STATUS] || "bg-slate-700 text-slate-300"}`}>
                      {j.STATUS}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {j.SUCCEEDED}/{j.TOTAL} ok{j.FAILED ? ` · ${j.FAILED} failed` : ""}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{(j.CREATED_ON || "").slice(0, 16).replace("T", " ")}</td>
                  <td className="px-4 py-3">
                    {j.STATUS === "DONE" && j.SUCCEEDED > 0 && (
                      <button onClick={() => download(j.JOB_ID)} className="text-amber-400 hover:underline">Download zip</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
};

export default BatchJobs;
