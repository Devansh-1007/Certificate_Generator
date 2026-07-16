# Deployment guide (all free tiers)

Stack: **Render** (backend, Docker) · **Aiven** free MySQL · **Cloudflare R2** (storage) ·
**Groq** (LLM) · **Vercel** (frontend).

## 1. Push to GitHub
```bash
git push origin main
```
CI (.github/workflows/ci.yml) runs 45 tests + the eval gate on every push.

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

## 5. Smoke test
Admin login → register client → client login → generate certificate → open the QR's
/verify link in an incognito window → bulk-upload backend/sample_roster.csv.

## 6. Publish eval numbers
```bash
cd backend && python -m evals.run_evals        # against your Groq key
```
Copy the pass rates from evals/results/latest.md into README.md.
