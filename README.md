# CertifyAI — Certificate Generator

Full-stack platform that generates branded certificates and ID cards at scale — with an
**AI agent that designs certificate templates from plain-English descriptions**.

## Highlights

- **AI Template Designer** — a hand-rolled tool-calling agent (Anthropic / OpenAI / Ollama)
  emits template JSON constrained to a schema; every draft is schema-validated,
  layout-checked, and test-rendered, with errors fed back for self-correction.
- **Schema-driven rendering** — templates are data (text / border / line / image / QR
  elements with `{PLACEHOLDER}` substitution), rendered server-side with PIL to PNG + PDF.
- **JWT auth** with client/admin roles; admin-gated client registration.
- **S3-compatible storage** — Cloudflare R2 / Backblaze B2 / MinIO / AWS via one env var.
- **Versioned SQL migrations**, blueprint architecture, middleware-based route protection.

## Architecture

```
frontend/  React 18 + Tailwind (CRA)          backend/   Flask
  src/api        axios client + JWT             main.py            entrypoint
  src/context    auth state                     middleware.py      @require_client/@require_admin
  src/pages      Login/Dashboard/Designer...    routes/            blueprints
                                                templateEngine/    schema + PIL renderer
                                                aiDesigner/        LLM client + agent loop
                                                db/migrations/     V1, V2...
```

## Quickstart

```bash
# 1. Database (MySQL 8 — local install or Docker)
docker run -d --name certdb -e MYSQL_ROOT_PASSWORD=devpass -e MYSQL_DATABASE=certificate -p 3306:3306 mysql:8
mysql -u root -p certificate < backend/db/migrations/V1__init.sql
mysql -u root -p certificate < backend/db/migrations/V2__template_details.sql

# 2. Backend
cd backend
pip install -r requirements.txt
cp Env/.env.example Env/.env    # fill in MySQL, JWT_SECRET, R2 keys, LLM key
python main.py                  # http://localhost:5000  (Swagger at /apidocs)

# 3. Frontend
cd ../frontend
npm install && npm start        # http://localhost:3000
```

## Auth model

- `POST /loginAdmin` — `ADMIN_USER`/`ADMIN_PASSWORD` (.env) → JWT with `role=admin`
- `POST /registerClient` (admin JWT) — creates a client with a hashed password
- `POST /loginClient` — client credentials → JWT with `role=client` (12h expiry)
- Protected routes accept `Authorization: Bearer <jwt>` (or legacy `x-token`)

## Bulk pipeline (maker-checker)

Generate certificates for a whole roster in one pass, with a data-quality gate:

- `POST /bulk/upload` — multipart `file` (CSV / TSV / XLSX) + `TEMPLATE_NAME` + optional
  `MAPPING`. Parses the roster, maps columns to template placeholders, and runs the
  **anomaly agent** (missing / whitespace / casing / exact + fuzzy duplicates via
  rapidfuzz), returning a review report + a cleaned-row preview. Creates a `PENDING_REVIEW` job.
- `GET /bulk/jobs`, `GET /bulk/jobs/<id>` — list / inspect jobs (status, progress, errors).
- `POST /bulk/jobs/<id>/approve` — send back the final, human-approved rows; a background
  worker renders each through the template engine and records it.
- `GET /bulk/jobs/<id>/download` — the rendered certificates as a zip.

## Tests

```bash
cd backend && pytest -q   # template engine, agent self-correction (fake LLM), bulk parser + anomaly agent, JWT auth
```

See [ROADMAP.md](ROADMAP.md) for what's done and what's next
(bulk UI + true async, evals, signed QR verification, CI/deploy).
