import { useCallback, useEffect, useRef, useState } from "react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import Alert from "../components/Alert";

/* ------------------------------------------------------------------ *
 * Small presentational helpers — charts are hand-rolled SVG so the
 * dashboard adds no charting dependency to the bundle.
 * ------------------------------------------------------------------ */

const DOT = {
  up: "bg-emerald-400",
  degraded: "bg-amber-400",
  down: "bg-rose-500",
};

const fmtDuration = (s) => {
  if (!s && s !== 0) return "—";
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  return `${m}m ${Math.floor(s % 60)}s`;
};

const fmtTime = (t) => new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

const Stat = ({ label, value, sub, tone = "text-slate-100" }) => (
  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
    <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
    <p className={`mt-1 font-display text-2xl ${tone}`}>{value}</p>
    {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
  </div>
);

/** Grouped bars: total requests with the error portion highlighted. */
const TrafficChart = ({ series }) => {
  const max = Math.max(1, ...series.map((p) => p.REQUESTS));
  const W = 720, H = 160, gap = 2;
  const bw = Math.max(1, W / series.length - gap);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Requests per bucket">
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <line key={f} x1="0" x2={W} y1={H - f * H} y2={H - f * H} stroke="#1e293b" strokeWidth="1" />
      ))}
      {series.map((p, i) => {
        const h = (p.REQUESTS / max) * (H - 8);
        const eh = (p.ERRORS / max) * (H - 8);
        const x = i * (bw + gap);
        return (
          <g key={p.T}>
            <rect x={x} y={H - h} width={bw} height={h} fill="#38bdf8" opacity="0.65" rx="1">
              <title>{`${fmtTime(p.T)} · ${p.REQUESTS} req · ${p.ERRORS} errors · p95 ${p.P95_MS}ms`}</title>
            </rect>
            {p.ERRORS > 0 && <rect x={x} y={H - eh} width={bw} height={eh} fill="#f43f5e" rx="1" />}
          </g>
        );
      })}
    </svg>
  );
};

/** p95 latency over the same buckets. */
const LatencyChart = ({ series }) => {
  const max = Math.max(1, ...series.map((p) => p.P95_MS));
  const W = 720, H = 120;
  const pts = series.map((p, i) => {
    const x = (i / Math.max(1, series.length - 1)) * W;
    const y = H - (p.P95_MS / max) * (H - 10) - 4;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="p95 latency">
      <polyline points={pts.join(" ")} fill="none" stroke="#fbbf24" strokeWidth="2" />
      <polyline points={`0,${H} ${pts.join(" ")} ${W},${H}`} fill="#fbbf24" opacity="0.08" />
      <text x="4" y="12" fill="#64748b" fontSize="10">{`peak ${max} ms`}</text>
    </svg>
  );
};

/* ------------------------------------------------------------------ */

const AdminConsole = () => {
  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [db, setDb] = useState(null);
  const [clients, setClients] = useState([]);
  const [error, setError] = useState(null);
  const [window_, setWindow_] = useState(900);
  const [auto, setAuto] = useState(true);
  const [loadedAt, setLoadedAt] = useState(null);
  const timer = useRef(null);

  const load = useCallback(async () => {
    try {
      const [h, m, d, c] = await Promise.allSettled([
        api.get("/admin/health"),
        api.get("/admin/metrics", { params: { WINDOW: window_ } }),
        api.get("/admin/database"),
        api.get("/admin/clients"),
      ]);
      if (h.status === "fulfilled") setHealth(h.value.data);
      if (m.status === "fulfilled") setMetrics(m.value.data);
      // A down database is a legitimate reading, not a page failure.
      setDb(d.status === "fulfilled" ? d.value.data : { STATUS: "down", description: errorMessage(d.reason) });
      if (c.status === "fulfilled") setClients(c.value.data.CLIENTS || []);
      setError(h.status === "rejected" ? errorMessage(h.reason) : null);
      setLoadedAt(new Date());
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [window_]);

  useEffect(() => {
    load();
    if (auto) {
      timer.current = setInterval(load, 15000);
      return () => clearInterval(timer.current);
    }
    return undefined;
  }, [load, auto]);

  const series = metrics?.SERIES || [];

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl text-slate-50">Operations console</h1>
          <p className="text-sm text-slate-400">
            Live service health, traffic and database state.
            {loadedAt && <span className="text-slate-600"> · updated {loadedAt.toLocaleTimeString()}</span>}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <select
            value={window_}
            onChange={(e) => setWindow_(Number(e.target.value))}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-slate-200"
          >
            <option value={900}>Last 15 min</option>
            <option value={3600}>Last hour</option>
            <option value={21600}>Last 6 hours</option>
            <option value={86400}>Last 24 hours</option>
          </select>
          <button
            onClick={() => setAuto((a) => !a)}
            className={`rounded-lg border px-3 py-1.5 ${
              auto ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-slate-700 text-slate-400"
            }`}
          >
            {auto ? "Auto-refresh on" : "Auto-refresh off"}
          </button>
          <button onClick={load} className="rounded-lg bg-amber-500 px-4 py-1.5 font-semibold text-slate-950 hover:bg-amber-400">
            Refresh
          </button>
        </div>
      </div>

      {error && <Alert kind="error" title="Couldn't reach the API" onClose={() => setError(null)}>{error}</Alert>}

      {/* component health */}
      <section className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Overall</p>
          <p className="mt-1 flex items-center gap-2 font-display text-2xl capitalize text-slate-100">
            <span className={`h-2.5 w-2.5 rounded-full ${DOT[health?.STATUS] || "bg-slate-600"}`} />
            {health?.STATUS || "…"}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">API up {fmtDuration(metrics?.UPTIME_SECONDS)}</p>
        </div>
        {(health?.CHECKS || []).map((c) => (
          <div key={c.COMPONENT} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">{c.COMPONENT}</p>
            <p className="mt-1 flex items-center gap-2 font-display text-2xl text-slate-100">
              <span className={`h-2.5 w-2.5 rounded-full ${DOT[c.STATUS]}`} />
              {c.LATENCY_MS} ms
            </p>
            <p className="mt-0.5 truncate text-xs text-slate-500" title={c.DETAIL}>{c.DETAIL || c.STATUS}</p>
          </div>
        ))}
      </section>

      {/* request metrics */}
      <section className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Requests" value={metrics?.TOTAL_REQUESTS ?? "—"} sub="in window" />
        <Stat
          label="Error rate"
          value={metrics ? `${metrics.ERROR_RATE}%` : "—"}
          sub={`${metrics?.SERVER_ERROR_COUNT ?? 0} server errors`}
          tone={metrics?.ERROR_RATE > 5 ? "text-rose-300" : "text-emerald-300"}
        />
        <Stat label="p95 latency" value={metrics ? `${metrics.P95_MS} ms` : "—"} sub={`p50 ${metrics?.P50_MS ?? "—"} ms`} />
        <Stat label="Peak latency" value={metrics ? `${metrics.P99_MS} ms` : "—"} sub="p99" />
      </section>

      <section className="mb-6 grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="mb-2 text-sm font-semibold text-slate-200">
            Traffic <span className="font-normal text-slate-500">· blue = requests, red = errors</span>
          </h2>
          {series.length ? <TrafficChart series={series} /> : <p className="py-10 text-center text-sm text-slate-600">No traffic yet</p>}
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="mb-2 text-sm font-semibold text-slate-200">
            Latency <span className="font-normal text-slate-500">· p95 per bucket</span>
          </h2>
          {series.length ? <LatencyChart series={series} /> : <p className="py-10 text-center text-sm text-slate-600">No samples yet</p>}
        </div>
      </section>

      {/* database */}
      <section className="mb-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-slate-200">Database</h2>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${DOT[db?.STATUS] || "bg-slate-600"}`} />
              {db?.VERSION || db?.STATUS || "…"}
            </span>
            {db?.UPTIME_SECONDS != null && <span>uptime {fmtDuration(db.UPTIME_SECONDS)}</span>}
            {db?.CONNECTIONS != null && <span>{db.CONNECTIONS} connections</span>}
            {db?.SCHEMA && <span className="font-mono">{db.SCHEMA}</span>}
          </div>
        </div>
        {db?.STATUS === "down" ? (
          <p className="text-sm text-rose-300">{db.description}</p>
        ) : (
          <>
            {db && !db.MIGRATIONS_APPLIED && (
              <p className="mb-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                Some tables are missing — run the pending migrations in <span className="font-mono">db/migrations/</span>.
              </p>
            )}
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {(db?.TABLES || []).map((t) => (
                <div key={t.TABLE} className="flex items-center justify-between rounded-lg border border-slate-800 px-3 py-2">
                  <span className={`font-mono text-xs ${t.PRESENT ? "text-slate-300" : "text-rose-400 line-through"}`}>
                    {t.TABLE}
                  </span>
                  <span className="text-xs text-slate-500">
                    {t.PRESENT ? `${t.ROWS} rows · ${t.SIZE_KB} KB` : "missing"}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      {/* endpoints + incidents */}
      <section className="mb-6 grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-200">Busiest endpoints</h2>
          {metrics?.ENDPOINTS?.length ? (
            <table className="w-full text-xs">
              <thead className="text-left uppercase tracking-wide text-slate-500">
                <tr><th className="pb-2">Path</th><th className="pb-2 text-right">Calls</th><th className="pb-2 text-right">Err</th><th className="pb-2 text-right">Avg</th></tr>
              </thead>
              <tbody>
                {metrics.ENDPOINTS.map((e) => (
                  <tr key={e.PATH} className="border-t border-slate-800/70">
                    <td className="py-1.5 font-mono text-slate-300">{e.PATH}</td>
                    <td className="py-1.5 text-right text-slate-400">{e.COUNT}</td>
                    <td className={`py-1.5 text-right ${e.ERRORS ? "text-rose-300" : "text-slate-600"}`}>{e.ERRORS}</td>
                    <td className="py-1.5 text-right text-slate-400">{e.AVG_MS} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="text-sm text-slate-600">No requests recorded yet.</p>}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-200">Incidents &amp; recent errors</h2>
          {metrics?.INCIDENTS?.length > 0 && (
            <ul className="mb-3 space-y-1.5">
              {metrics.INCIDENTS.map((i, n) => (
                <li key={n} className="flex items-center gap-2 text-xs">
                  <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[i.STATUS] || "bg-slate-600"}`} />
                  <span className="text-slate-400">{fmtTime(i.T)}</span>
                  <span className="capitalize text-slate-200">{i.COMPONENT} {i.STATUS}</span>
                  <span className="truncate text-slate-600">{i.DETAIL}</span>
                </li>
              ))}
            </ul>
          )}
          {metrics?.RECENT_ERRORS?.length ? (
            <ul className="space-y-1.5">
              {metrics.RECENT_ERRORS.map((e, n) => (
                <li key={n} className="flex items-center gap-2 text-xs">
                  <span className="rounded bg-rose-500/20 px-1.5 py-0.5 font-mono text-rose-300">{e.STATUS}</span>
                  <span className="text-slate-500">{fmtTime(e.T)}</span>
                  <span className="font-mono text-slate-300">{e.METHOD} {e.PATH}</span>
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-slate-600">No errors in this window.</p>}
        </div>
      </section>

      {/* clients */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-200">Registered clients ({clients.length})</h2>
        {clients.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="pb-2">Client</th><th className="pb-2">Name</th><th className="pb-2">Created</th>
                  <th className="pb-2 text-right">Certificates</th><th className="pb-2 text-right">ID cards</th><th className="pb-2 text-right">Templates</th>
                </tr>
              </thead>
              <tbody>
                {clients.map((c) => (
                  <tr key={c.CLIENT_ID} className="border-t border-slate-800/70">
                    <td className="py-2 font-mono text-slate-200">{c.CLIENT_ID}</td>
                    <td className="py-2 text-slate-400">{c.CLIENT_NAME}</td>
                    <td className="py-2 text-slate-500">{(c.CREATED_ON || "").slice(0, 16)}</td>
                    <td className="py-2 text-right text-slate-300">{c.CERTIFICATES}</td>
                    <td className="py-2 text-right text-slate-300">{c.ID_CARDS}</td>
                    <td className="py-2 text-right text-slate-300">{c.TEMPLATES}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p className="text-sm text-slate-600">No clients registered yet.</p>}
      </section>
    </main>
  );
};

export default AdminConsole;
