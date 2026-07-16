import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const features = [
  ["AI Template Designer", "Describe a certificate in plain English — an agent designs, validates, and previews it."],
  ["Bulk from a roster", "Upload a CSV/Excel — an anomaly agent flags duplicates, casing and typos before you batch-render."],
  ["Cryptographically verifiable", "Each certificate carries a signed QR; a public page confirms genuine, tampered, or revoked."],
  ["One-click generation", "Render certificates and ID cards to PNG + PDF, stored on S3-compatible object storage."],
];

const Home = () => {
  const { isAuthed } = useAuth();
  return (
    <main className="mx-auto max-w-6xl px-6">
      <section className="py-24 text-center">
        <p className="mb-3 text-sm uppercase tracking-[0.3em] text-amber-400">Certificate platform</p>
        <h1 className="font-display text-5xl leading-tight text-slate-50 sm:text-6xl">
          Design certificates with <span className="text-amber-400">plain English</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-400">
          CertifyAI generates branded certificates and ID cards at scale — templates are designed
          by an AI agent, validated against a schema, and rendered server-side.
        </p>
        <div className="mt-10 flex justify-center gap-4">
          <Link
            to={isAuthed ? "/designer" : "/login"}
            className="rounded-xl bg-amber-500 px-6 py-3 font-semibold text-slate-950 hover:bg-amber-400"
          >
            {isAuthed ? "Open AI Designer" : "Get started"}
          </Link>
          <Link
            to={isAuthed ? "/dashboard" : "/login"}
            className="rounded-xl border border-slate-700 px-6 py-3 font-semibold text-slate-200 hover:border-slate-500"
          >
            Dashboard
          </Link>
        </div>
      </section>
      <section className="grid gap-6 pb-24 sm:grid-cols-2 lg:grid-cols-4">
        {features.map(([title, body]) => (
          <div key={title} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h3 className="mb-2 font-semibold text-slate-100">{title}</h3>
            <p className="text-sm leading-relaxed text-slate-400">{body}</p>
          </div>
        ))}
      </section>
    </main>
  );
};

export default Home;
