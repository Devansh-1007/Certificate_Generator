# Certificate Generator — AI Platform Roadmap

## Done (this pass)

### Phase 1 — Schema-driven template engine
- `backend/templateEngine/schema.py` — JSON Schema for templates (text/rect/line/image/qr elements, {PLACEHOLDER} substitution) + semantic validation (bounds checks) with actionable error strings.
- `backend/templateEngine/renderer.py` — renders any valid template with PIL: alignment, shrink-to-fit for long names (`maxWidth`), QR codes, fonts from `Templates/Fonts`.
- `backend/templateEngine/presets/default_certificate.json` — formal landscape preset (1600x1130) with verify-QR.
- `backend/MysqlTemplateTable.sql` — `TEMPLATE_DETAILS` table (per-client templates, JSON column).

### Phase 2 — AI template designer (agentic loop)
- `backend/aiDesigner/llm.py` — provider-agnostic tool-calling client over plain HTTP: Anthropic / OpenAI / Ollama via `LLM_PROVIDER`, `LLM_MODEL` env vars.
- `backend/aiDesigner/agent.py` — hand-rolled agent loop: `emit_template` tool constrained to the schema; every draft is schema-validated, layout-checked, and **test-rendered**; failures are fed back for self-correction (max 3 attempts); full trace returned.
- `backend/templateRoutes.py` — `/designTemplate`, `/renderPreview`, `/saveTemplate`, `GET /templates` (existing x-client-id/x-token auth); registered as a blueprint in `main.py`.
- `backend/test_template_engine.py` — 12 pytest cases incl. agent self-correction with a fake LLM (no network). All passing.

### Setup
1. `pip install -r requirements.txt` (bulk Excel parsing adds `openpyxl`; CSV needs nothing extra)
2. Run `db/migrations/V1__init.sql`, `V2__template_details.sql`, `V3__batch_jobs.sql`, then `V4__certificate_verify.sql` against MySQL.
3. Env: `LLM_PROVIDER=anthropic|openai|ollama`, matching API key (`ANTHROPIC_API_KEY`/`OPENAI_API_KEY`), optional `LLM_MODEL`.
4. `pytest backend/test_template_engine.py -v`

### Architecture restructure (task.txt item — done)
- `backend/routes/` — blueprints: `clientRoutes` (login unprotected, register admin-only), `certificateRoutes`, `idRoutes`, `templateRoutes`; `main.py` is now a slim entrypoint.
- `backend/middleware.py` — `@require_client` / `@require_admin` decorators (protected vs unprotected routes).
- `backend/models.py` — Certificate / IdCard / Client domain objects.
- `backend/db/migrations/` — versioned SQL: `V1__init.sql`, `V2__template_details.sql`.
- `backend/awsS3.py` — S3-compatible storage: set `S3_ENDPOINT_URL` (+ keys) for Cloudflare R2/B2/MinIO; unset = AWS. Presigned URLs no longer stripped of their signature.
- `backend/Env/.env.example` — full env template (MySQL, R2, admin token, LLM provider).
- Bug fixes found during the split: `generateID()` was called with 4 args but takes 3; dead `tkinter` import removed.

### Phase 3 — Bulk pipeline + anomaly agent (maker-checker)
- `backend/bulk/parser.py` — pure, offline-testable roster handling: parse CSV / TSV / XLSX (openpyxl); map roster headers to template placeholders (explicit `MAPPING` or normalized-name auto-match); **anomaly agent** flags `missing` / `whitespace` / `casing` / `duplicate_exact` / `duplicate_near` (rapidfuzz, ≥88% similarity) and proposes fixes; `suggest_rows` pre-applies only the safe fixes (whitespace, casing) for a cleaned preview.
- `backend/bulk/jobs.py` — job orchestration + **request-free** DB helpers; `start_render` spawns a daemon thread that renders each approved row through the template engine, records it in `CERTIFICATE_DETAILS`, tracks per-row progress, and zips the outputs. Storage/DB stay optional-friendly (missing bucket degrades to local files).
- `backend/certificates.py` — extracted `render_certificate()` returning a plain dict (no Flask context) so batch rendering is thread-safe; `generateCert` is now a thin `jsonify` wrapper.
- `backend/routes/bulkRoutes.py` — `POST /bulk/upload` (multipart) → review; `GET /bulk/jobs`, `GET /bulk/jobs/<id>`; `POST /bulk/jobs/<id>/approve` (maker-checker, sends back the final edited rows) → background render; `GET /bulk/jobs/<id>/download` → zip.
- `backend/db/migrations/V3__batch_jobs.sql` — `BATCH_JOBS` table (status, progress counters, rows/anomalies/errors JSON, zip path).
- `backend/test_bulk.py` — 18 pytest cases for parsing, mapping, and every anomaly type (no DB/network). All passing.

### Phase 3.5 — Full-fledged UI (every endpoint wired)
- New pages: public **Verify** (`/verify/:id`, genuine/tampered/revoked banner), **My certificates** (download PNG/PDF, verify link, revoke/reinstate), **Templates** manager (preview + delete), **ID cards** gallery, **Batch jobs** history (progress + zip download), and the bulk upload→review→progress→download flow.
- Dashboard revamped with a live `/stats` strip; Navbar expanded; verify link + certificate ID surfaced on the single-cert result.

### Phase 4 — Evals + verifiable certificates
- `backend/verification.py` — HMAC-SHA256 signed, unguessable certificate UIDs (keyed by `VERIFY_SECRET`); request-free DB helpers; `public_result` returns genuine / tampered / revoked / not_found. Wired into the single-cert route and the bulk worker so the QR encodes `{BASE_URL}/verify/<uid>`.
- `backend/routes/verifyRoutes.py` — public `GET /verify/<uid>`; client `GET /myCertificates`, `POST /revokeCertificate/<uid>`, `POST /reinstateCertificate/<uid>`.
- `backend/routes/accountRoutes.py` — `GET /stats`, `DELETE /templates/<name>`.
- `backend/db/migrations/V4__certificate_verify.sql` — `CERTIFICATE_VERIFY` table (uid, fields, signature, status).
- `backend/evals/` — ~30-prompt design eval set + `run_evals.py` scoring agent success / schema-valid / render-ok / layout-ok, writing `results/latest.{json,md}`; offline `--fake` mode, `--min-pass` gate for CI.
- `backend/test_verification.py` — 8 offline tests (sign determinism, tamper, revoke, not-found).

### Phase 5 — Ship (done)
- `.github/workflows/ci.yml` — pytest (45 tests) + eval gate (`--fake --min-pass 100`) on every push; frontend build check.
- `backend/Dockerfile` — fixed (was Django `manage.py`!); gunicorn, PORT-aware for Render/Fly.
- `DEPLOYMENT.md` — free-tier deploy: Render (backend Docker) + Aiven MySQL + R2 + Groq + Vercel (frontend, SPA rewrites).

## Backlog (nice-to-haves, post-ship)
- Publish real eval numbers (run `python -m evals.run_evals` with the Groq key) in the README.
- Swap the bulk daemon thread for RQ/Celery if batch sizes outgrow classroom/event scale.
- Refresh-token flow (current JWTs simply expire at 12h); rate limiting on public /verify.
- Architecture diagram + demo GIF in the README.

## Security note
A leaked OpenAI key was removed from `backend/task.txt` — **revoke it** (platform.openai.com). The file is gitignored, so it was never pushed; no history rewrite needed.
