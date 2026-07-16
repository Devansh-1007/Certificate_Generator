import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

const actions = [
  ["/generate-certificate", "Generate certificate", "Render a named certificate to PNG + PDF, with a verification QR."],
  ["/bulk", "Bulk from roster", "Upload a CSV/Excel — review anomalies, batch-render, download a zip."],
  ["/generate-id", "Generate ID card", "Portrait ID card with an embedded QR code."],
  ["/designer", "AI Template Designer", "Describe a design — the agent builds and validates the template."],
  ["/certificates", "My certificates", "Browse, download, verify, or revoke issued certificates."],
  ["/templates", "Templates", "Preview, reuse, or delete your saved designs."],
];

const STAT_META = [
  ["certificates", "Certificates", "/certificates"],
  ["verifiable", "Verifiable", "/certificates"],
  ["ids", "ID cards", "/id-cards"],
  ["templates", "Templates", "/templates"],
  ["batches", "Batch jobs", "/batch-jobs"],
];

const Dashboard = () => {
  const { clientId } = useAuth();
  const [stats, setStats] = useState(null);
  const [certs, setCerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/stats").then(({ data }) => setStats(data.STATS)).catch(() => setStats(null));
    api
      .get("/getAllCertificate")
      .then(({ data }) => setCerts(data.base64_data_list || []))
      .catch(() => setCerts([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="font-display text-3xl text-slate-50">Welcome, {clientId}</h1>

      {/* stat strip */}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {STAT_META.map(([key, label, to]) => (
          <Link key={key} to={to} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition hover:border-amber-500/50">
            <p className="font-display text-2xl text-amber-400">{stats ? stats[key] ?? 0 : "—"}</p>
            <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
          </Link>
        ))}
      </div>

      {/* actions */}
      <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {actions.map(([to, title, body]) => (
          <Link key={to} to={to} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 transition hover:border-amber-500/50">
            <h3 className="mb-2 font-semibold text-slate-100">{title}</h3>
            <p className="text-sm text-slate-400">{body}</p>
          </Link>
        ))}
      </div>

      <h2 className="mt-14 mb-4 font-display text-2xl text-slate-100">Recent certificates</h2>
      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : certs.length === 0 ? (
        <p className="text-slate-500">Nothing generated yet — start with a certificate.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {certs.slice(0, 12).map((b64, i) => (
            <img key={i} src={`data:image/png;base64,${b64}`} alt={`certificate ${i + 1}`} className="rounded-lg border border-slate-800" />
          ))}
        </div>
      )}
    </main>
  );
};

export default Dashboard;
