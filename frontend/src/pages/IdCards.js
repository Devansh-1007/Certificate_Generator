import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Swal from "sweetalert2";
import api from "../api/client";

const swalCfg = { background: "#0f172a", color: "#e2e8f0" };

const IdCards = () => {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/idCards")
      .then(({ data }) => setCards(data.ID_CARDS || []))
      .catch(() => setCards([]))
      .finally(() => setLoading(false));
  }, []);

  const download = async (name, ext) => {
    try {
      const res = await api.get("/getId", {
        params: { ID_NAME: name, EXTENSION: ext },
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

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="mb-2 font-display text-3xl text-slate-50">ID cards</h1>
          <p className="text-sm text-slate-400">Every ID card you've generated.</p>
        </div>
        <Link to="/generate-id" className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-amber-400">
          + New ID card
        </Link>
      </div>

      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : cards.length === 0 ? (
        <p className="text-slate-500">No ID cards yet — generate one to see it here.</p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-900/80 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Holder</th>
                <th className="px-4 py-2">Created</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {cards.map((c) => (
                <tr key={c.ID_NAME} className="border-t border-slate-800/70">
                  <td className="px-4 py-3 font-medium text-slate-100">{c.ID_NAME}</td>
                  <td className="px-4 py-3 text-slate-400">{c.CREATED_ON}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => download(c.ID_NAME, "img")} className="mr-3 text-amber-400 hover:underline">PNG</button>
                    <button onClick={() => download(c.ID_NAME, "pdf")} className="text-amber-400 hover:underline">PDF</button>
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

export default IdCards;
