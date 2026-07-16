import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../api/client";

const REASON = {
  not_found: ["Not found", "No certificate matches this code. It may be mistyped or never issued."],
  tampered: ["Tampered", "This certificate's details don't match its signature — treat it as invalid."],
  revoked: ["Revoked", "This certificate was issued but has since been revoked by the issuer."],
};

const Row = ({ label, value }) =>
  value ? (
    <div className="flex justify-between gap-6 border-t border-slate-800 py-2 text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="text-right text-slate-200">{value}</span>
    </div>
  ) : null;

const Verify = () => {
  const { id } = useParams();
  const [state, setState] = useState({ loading: true });

  useEffect(() => {
    api
      .get(`/verify/${id}`)
      .then(({ data }) => setState({ loading: false, data }))
      .catch((err) =>
        setState({ loading: false, data: err.response?.data || { valid: false, reason: "not_found" } })
      );
  }, [id]);

  const { loading, data } = state;
  const valid = data?.valid;
  const [title, blurb] = valid ? ["Genuine", ""] : REASON[data?.reason] || ["Invalid", ""];

  return (
    <main className="mx-auto max-w-lg px-6 py-16">
      <Link to="/" className="mb-8 block text-center font-display text-2xl tracking-wide text-amber-400">
        Certify<span className="text-slate-100">AI</span>
      </Link>

      {loading ? (
        <p className="text-center text-slate-500">Verifying…</p>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
          <div
            className={`px-6 py-8 text-center ${
              valid ? "bg-emerald-500/10" : "bg-rose-500/10"
            }`}
          >
            <div
              className={`mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full text-2xl ${
                valid ? "bg-emerald-500 text-slate-950" : "bg-rose-500 text-white"
              }`}
            >
              {valid ? "✓" : "!"}
            </div>
            <h1 className={`font-display text-2xl ${valid ? "text-emerald-300" : "text-rose-300"}`}>
              {valid ? "Verified certificate" : title}
            </h1>
            {!valid && blurb && <p className="mx-auto mt-2 max-w-xs text-sm text-slate-400">{blurb}</p>}
          </div>

          {data?.recipient && (
            <div className="px-6 py-5">
              <Row label="Recipient" value={data.recipient} />
              <Row label="Event / reason" value={data.event} />
              <Row label="Issue date" value={data.issue_date} />
              <Row label="Issuer" value={data.issuer} />
              <Row label="Certificate ID" value={data.uid} />
            </div>
          )}
        </div>
      )}

      <p className="mt-6 text-center text-xs text-slate-600">
        Verification is cryptographically signed — details that don't match the signature are flagged.
      </p>
    </main>
  );
};

export default Verify;
