# Deployment guide (all free tiers)

Stack: **Render** (backend, Docker) · **Aiven** free MySQL · **Cloudflare R2** (storage) ·
**Groq** (LLM) · **Vercel** (frontend).

## 1. Push to GitHub
```bash
git push origin main
```

### CI/CD pipeline (.github/workflows/ci.yml)
Every push to `main` runs, in order:

| Job | What it does | Blocks deploy? |
|---|---|---|
| `backend` | 52 offline pytest cases + agent eval gate (`--fake --min-pass 1.0`); uploads the eval report as an artifact | yes |
| `frontend` | production `npm run build` | yes |
| `deploy` | POSTs the Render + Vercel deploy hooks (main branch only) | — |
| `smoke` | waits for the new build, polls `/apidocs/` until it returns 200 | fails the run if prod is unhealthy |

Pull requests run the two test jobs only — never deploy. `concurrency` cancels
an in-flight run when a newer commit lands, so two builds can't race to prod.

**Gating deploys on tests (recommended).** Out of the box Render and Vercel
auto-deploy on push, which ships even when tests fail. To make deploys
test-gated:

1. Render → service → Settings → Build & Deploy → **Auto-Deploy: Off**, then
   copy the **Deploy Hook** URL.
2. Vercel → project → Settings → Git → **Ignored Build Step**: `exit 0` for hook-only,
   and Settings → Git → Deploy Hooks → create one for `main`.
3. GitHub → repo Settings → Secrets and variables → Actions → add:
   - `RENDER_DEPLOY_HOOK_URL`
   - `VERCEL_DEPLOY_HOOK_URL`
   - `BACKEND_URL` (e.g. `https://certifyai-api.onrender.com`) for the smoke test

If those secrets are absent the workflow simply logs that it's relying on the
platforms' own auto-deploy — nothing breaks.

## 2. Database — Aiven free MySQL
1. aiven.io → create free MySQL service → copy host/port/user/password.
2. Create the schema: connect with any MySQL client and run, in order,
   `backend/db/migrations/V1__init.sql` … `V4__certificate_verify.sql`
   (skip the CREATE DATABASE line; use Aiven's `defaultdb` or create `certificate`).

## 3. Backend — Render web service
1. render.com → New → Web Service → connect the GitHub repo.
2. Root directory: `backend`, runtime: **Docker** (uses backend/Dockerfile).
3. Environment variables (same names as Env/.env.example):
   `MYSQL_HOST/PORT/USER/PASS/DB` (Aiven values), `JWT_SECRET`, `VERIFY_SECRET`,
   `ADMIN_USER`, `ADMIN_PASSWORD`, `BASE_URL=https://<your-service>.onrender.com`,
   `BUCKET`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_REGION=auto`,
   `LLM_PROVIDER=openai`, `OPENAI_BASE_URL=https://api.groq.com/openai/v1`,
   `OPENAI_API_KEY`, `LLM_MODEL=llama-3.3-70b-versatile`,
   plus the asset paths from .env.example (BASE_CERT_PATH, FONT_PATH, ALL_* — relative paths work).
4. Deploy; check `https://<service>.onrender.com/apidocs`.

Note: Render's free tier has an ephemeral disk — that's fine, R2 is the durable store;
local files are just a render cache. Free instances sleep after idle (first request is slow).

## 4. Frontend — Vercel
1. vercel.com → import repo → root directory `frontend` (framework: Create React App).
2. Env var: `REACT_APP_API_URL=https://<your-service>.onrender.com`.
3. Deploy. For React Router deep links (e.g. /verify/abc), add `frontend/vercel.json`:
   ```json
   { "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
   ```

## 4b. Google sign-in (optional)
1. Google Cloud Console -> APIs & Services -> **Credentials** -> Create
   credentials -> **OAuth client ID** -> Web application.
2. Under *Authorised JavaScript origins* add your frontend origins:
   `https://<project>.vercel.app` and `http://localhost:3000`.
   (No redirect URI or client secret: Google Identity Services returns an ID
   token to the page, and the backend verifies it against Google's JWKS.)
3. Copy the client ID into Render as `GOOGLE_CLIENT_ID`, then redeploy.
   The Google button appears automatically — the sign-in page asks
   `/auth/config` whether it is configured.

**Work-email policy.** `REQUIRE_WORK_EMAIL=true` (default) stops consumer
addresses from creating organisations, which keeps one tenant per company.
An organisation claims its owner's domain, so colleagues signing in later join
it as members rather than creating duplicates. Set the flag to `false` for
demos where gmail accounts should be able to create organisations.

## 5. Smoke test
Admin login → register client → client login → generate certificate → open the QR's
/verify link in an incognito window → bulk-upload backend/sample_roster.csv.

## 6. Publish eval numbers
```bash
cd backend && python -m evals.run_evals        # against your Groq key
```
Copy the pass rates from evals/results/latest.md into README.md.
