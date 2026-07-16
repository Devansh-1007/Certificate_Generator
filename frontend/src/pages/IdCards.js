import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";

const IdCards = () => {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/getAllId")
      .then(({ data }) => setCards(data.base64_data_list || []))
      .catch(() => setCards([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
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
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {cards.map((b64, i) => (
            <img key={i} src={`data:image/png;base64,${b64}`} alt={`id ${i + 1}`} className="w-full rounded-lg border border-slate-800" />
          ))}
        </div>
      )}
    </main>
  );
};

export default IdCards;
