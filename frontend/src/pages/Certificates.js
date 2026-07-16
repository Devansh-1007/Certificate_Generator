import { useEffect, useState } from "react";
import Swal from "sweetalert2";
import api from "../api/client";

const swalCfg = { background: "#0f172a", color: "#e2e8f0" };

const STATUS_CLS = {
  VALID: "bg-emerald-500/20 text-emerald-300",
  REVOKED: "bg-rose-500/20 text-rose-300",
};

const Certificates = () => {
  const [certs, setCerts] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api
      .get("/myCertificates")
      .then(({ data }) => setCerts(data.CERTIFICATES || []))
      .catch(() => setCerts([]))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const download = async (name, ext) => {
    try {
      const res = await api.get("/getCertificate", {
        params: { CERTIFICATE_NAME: name, EXTENSION: ext },
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${name}.${ext === "pdf" ? "pdf" : "png"}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      Swal.fire({ icon: "error", title: "Download failed", text: "File not found on server.", ...swalCfg });
    }
  };

  const toggleRevoke = async (c) => {
    const revoking = c.STATUS !== "REVOKED";
    const confirm = await Swal.fire({
      icon: "warning",
      title: revoking ? "Revoke certificate?" : "Reinstate certificate?",
      text: `${c.RECIPIENT_NAME} · ${c.CERT_UID}`,
      showCancelButton: true,
      confirmButtonText: revoking ? "Revoke" : "Reinstate",
      confirmButtonColor: revoking ? "#e11d48" : "#059669",
      ...swalCfg,
    });
    if (!confirm.isConfirmed) return;
    try {
      await api.post(`/${revoking ? "revoke" : "reinstate"}Certificate/${c.CERT_UID}`);
      load();
    } catch (err) {
      Swal.fire({ icon: "error", title: "Failed", text: err.response?.data?.description || String(err), ...swalCfg });
    }
  };

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="mb-2 font-display text-3xl text-slate-50">My certificates</h1>
      <p className="mb-8 text-sm text-slate-400">
        Every issued certificate is verifiable via its public link. Revoke any that should no longer be trusted.
      </p>

      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : certs.length === 0 ? (
        <p className="text-slate-500">No verifiable certificates yet — generate one to see it here.</p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-900/80 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Recipient</th>
                <th className="px-4 py-2">Event</th>
                <th className="px-4 py-2">Issued</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {certs.map((c) => (
                <tr key={c.CERT_UID} className="border-t border-slate-800">
                  <td className="px-4 py-3 text-slate-200">{c.RECIPIENT_NAME}</td>
                  <td className="px-4 py-3 text-slate-400">{c.EVENT_NAME || "—"}</td>
                  <td className="px-4 py-3 text-slate-500">{(c.CREATED_ON || "").slice(0, 10)}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs ${STATUS_CLS[c.STATUS] || "bg-slate-700 text-slate-300"}`}>
                      {c.STATUS}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-3 text-xs">
                      <a href={`/verify/${c.CERT_UID}`} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline">
                        Verify
                      </a>
                      <button onClick={() => download(c.RECIPIENT_NAME, "img")} className="text-amber-400 hover:underline">PNG</button>
                      <button onClick={() => download(c.RECIPIENT_NAME, "pdf")} className="text-amber-400 hover:underline">PDF</button>
                      <button onClick={() => toggleRevoke(c)} className={c.STATUS === "REVOKED" ? "text-emerald-400 hover:underline" : "text-rose-400 hover:underline"}>
                        {c.STATUS === "REVOKED" ? "Reinstate" : "Revoke"}
                      </button>
                    </div>
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

export default Certificates;
