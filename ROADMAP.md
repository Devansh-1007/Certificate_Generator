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
1. `pip install -r requirements.txt` (schema/renderer need nothing new; `requests` already present)
2. Run `db/migrations/V1__init.sql` then `V2__template_details.sql` against MySQL.
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

## Next

### Phase 3 — Bulk pipeline + verification agent
- CSV/Excel upload endpoint; anomaly agent (duplicates, casing, missing fields — rapidfuzz already in requirements) proposes fixes; human approves (maker-checker); async batch render to S3; zip download.

### Phase 4 — Evals + verifiable certificates
- Eval set (~50 design prompts); measure schema pass rate, render success, layout validity; publish numbers in README.
- HMAC/Ed25519-signed certificate IDs behind the {VERIFY_URL} QR; public `GET /verify/<id>`.

### Phase 5 — Polish
- Split `main.py` into blueprints (see task.txt middleware note); frontend designer panel with live `/renderPreview`; GitHub Actions CI; deploy (Render/Fly); README architecture diagram + demo GIF.

## Security note
A leaked OpenAI key was removed from `backend/task.txt` — **revoke it** (platform.openai.com). The file is gitignored, so it was never pushed; no history rewrite needed.
