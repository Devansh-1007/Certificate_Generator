import { useCallback, useEffect, useState } from "react";
import api from "../api/client";
import { errorMessage, showSuccess } from "../api/errors";
import Alert from "../components/Alert";
import { useAuth } from "../context/AuthContext";

const inputCls =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:outline-none";

const ROLE_BADGE = {
  owner: "bg-amber-500/20 text-amber-300",
  admin: "bg-sky-500/20 text-sky-300",
  member: "bg-slate-700 text-slate-300",
};

/** Organisation settings + membership. Owners/admins only (route-guarded). */
const Team = () => {
  const { org, isOwner, setOrg, user } = useAuth();
  const [members, setMembers] = useState([]);
  const [usage, setUsage] = useState(null);
  const [profile, setProfile] = useState({ NAME: "", BRAND_COLOR: "" });
  const [invite, setInvite] = useState({ EMAIL: "", FULL_NAME: "", PASSWORD: "", ROLE: "member" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [o, m] = await Promise.all([api.get("/auth/organisation"), api.get("/auth/members")]);
      setProfile({
        NAME: o.data.ORGANISATION?.NAME || "",
        BRAND_COLOR: o.data.ORGANISATION?.BRAND_COLOR || "",
      });
      setUsage(o.data.USAGE);
      setOrg(o.data.ORGANISATION);
      setMembers(m.data.MEMBERS || []);
    } catch (err) {
      setError(errorMessage(err));
    }
    // setOrg identity is stable enough here; refetching on every render would loop
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { load(); }, [load]);

  const saveProfile = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.patch("/auth/organisation", profile);
      setOrg(data.ORGANISATION);
      showSuccess("Organisation updated");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const addMember = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/auth/members", invite);
      setInvite({ EMAIL: "", FULL_NAME: "", PASSWORD: "", ROLE: "member" });
      showSuccess("Teammate added", "Share the password with them to sign in.");
      load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const patchMember = async (id, body) => {
    try {
      const { data } = await api.patch(`/auth/members/${id}`, body);
      setMembers(data.MEMBERS || []);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="mb-1 font-display text-3xl text-slate-50">{org?.NAME || "Organisation"}</h1>
      <p className="mb-8 text-sm text-slate-400">
        Plan <span className="text-slate-300">{org?.PLAN || "free"}</span>
        {org?.SLUG && <span className="text-slate-600"> · {org.SLUG}</span>}
      </p>

      {error && <Alert kind="error" onClose={() => setError(null)}>{error}</Alert>}

      {usage && (
        <section className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {[
            ["Certificates", usage.CERTIFICATES], ["ID cards", usage.ID_CARDS],
            ["Templates", usage.TEMPLATES], ["Batches", usage.BATCHES], ["Members", usage.MEMBERS],
          ].map(([label, n]) => (
            <div key={label} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
              <p className="mt-1 font-display text-2xl text-slate-100">{n}</p>
            </div>
          ))}
        </section>
      )}

      <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="mb-4 text-sm font-semibold text-slate-200">Organisation profile</h2>
        <form onSubmit={saveProfile} className="grid gap-3 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Name</label>
            <input className={inputCls} value={profile.NAME}
                   onChange={(e) => setProfile({ ...profile, NAME: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Brand colour</label>
            <div className="flex gap-2">
              <input className={inputCls} placeholder="#B08D57" value={profile.BRAND_COLOR}
                     onChange={(e) => setProfile({ ...profile, BRAND_COLOR: e.target.value })} />
              <span className="h-9 w-9 shrink-0 rounded-lg border border-slate-700"
                    style={{ background: /^#[0-9A-Fa-f]{6}$/.test(profile.BRAND_COLOR) ? profile.BRAND_COLOR : "transparent" }} />
            </div>
          </div>
          <button disabled={busy}
                  className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50 sm:col-span-3 sm:justify-self-start">
            Save changes
          </button>
        </form>
      </section>

      <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="mb-1 text-sm font-semibold text-slate-200">Add a teammate</h2>
        <p className="mb-4 text-xs text-slate-500">
          They sign in with this email and password; anyone in the organisation can issue certificates.
        </p>
        <form onSubmit={addMember} className="grid gap-3 sm:grid-cols-4">
          <input required type="email" className={inputCls} placeholder="teammate@org.com"
                 value={invite.EMAIL} onChange={(e) => setInvite({ ...invite, EMAIL: e.target.value })} />
          <input className={inputCls} placeholder="Name (optional)"
                 value={invite.FULL_NAME} onChange={(e) => setInvite({ ...invite, FULL_NAME: e.target.value })} />
          <input required type="password" minLength={8} className={inputCls} placeholder="Temp password (8+)"
                 value={invite.PASSWORD} onChange={(e) => setInvite({ ...invite, PASSWORD: e.target.value })} />
          <div className="flex gap-2">
            <select className={inputCls} value={invite.ROLE}
                    onChange={(e) => setInvite({ ...invite, ROLE: e.target.value })}>
              <option value="member">Member</option>
              <option value="admin">Admin</option>
              {isOwner && <option value="owner">Owner</option>}
            </select>
            <button disabled={busy} className="rounded-lg bg-amber-500 px-4 text-sm font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50">
              Add
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="mb-4 text-sm font-semibold text-slate-200">Members ({members.length})</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
              <tr><th className="pb-2">Email</th><th className="pb-2">Name</th><th className="pb-2">Role</th>
                  <th className="pb-2">Last login</th><th className="pb-2 text-right">Actions</th></tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.USER_ID} className="border-t border-slate-800/70">
                  <td className="py-2 text-slate-200">
                    {m.EMAIL}
                    {m.USER_ID === user?.USER_ID && <span className="ml-2 text-xs text-slate-500">(you)</span>}
                  </td>
                  <td className="py-2 text-slate-400">{m.FULL_NAME || "—"}</td>
                  <td className="py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${ROLE_BADGE[m.ROLE]}`}>{m.ROLE}</span>
                    {m.STATUS !== "active" && <span className="ml-2 text-xs text-rose-300">{m.STATUS}</span>}
                  </td>
                  <td className="py-2 text-xs text-slate-500">{(m.LAST_LOGIN_ON || "never").slice(0, 16)}</td>
                  <td className="py-2 text-right">
                    {isOwner && m.USER_ID !== user?.USER_ID && (
                      <>
                        <select
                          value={m.ROLE}
                          onChange={(e) => patchMember(m.USER_ID, { ROLE: e.target.value })}
                          className="mr-2 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300"
                        >
                          <option value="member">member</option>
                          <option value="admin">admin</option>
                          <option value="owner">owner</option>
                        </select>
                        <button
                          onClick={() => patchMember(m.USER_ID, { STATUS: m.STATUS === "active" ? "suspended" : "active" })}
                          className="text-xs text-rose-300 hover:underline"
                        >
                          {m.STATUS === "active" ? "Suspend" : "Restore"}
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
};

export default Team;
