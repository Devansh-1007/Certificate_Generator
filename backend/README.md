# Backend — Flask API

## Layout

```
main.py              entrypoint: app config + blueprint registration
middleware.py        @require_client / @require_admin (JWT)
auth_jwt.py          HS256 issue/decode (sub, name, role, exp)
models.py            Certificate / IdCard / Client
routes/              clientRoutes, certificateRoutes, idRoutes, templateRoutes
templateEngine/      schema.py (JSON Schema + semantic checks), renderer.py (PIL), presets/
aiDesigner/          llm.py (Anthropic/OpenAI/Ollama over HTTP), agent.py (self-correcting loop)
db/migrations/       V1__init.sql, V2__template_details.sql
awsS3.py             S3-compatible storage (R2/B2/MinIO via S3_ENDPOINT_URL)
Env/.env.example     configuration template
```

## Setup

```bash
pip install -r requirements.txt
cp Env/.env.example Env/.env   # fill in values
# run db/migrations/*.sql against MySQL in order
python main.py                 # Swagger UI at /apidocs
pytest -q                      # 16 tests, no DB/network needed
```

## Endpoints

| Method | Route                 | Auth   | Purpose                              |
|--------|-----------------------|--------|--------------------------------------|
| POST   | /loginAdmin           | none   | admin credentials -> admin JWT       |
| POST   | /loginClient          | none   | client credentials -> client JWT     |
| POST   | /registerClient       | admin  | create client (hashed password)      |
| POST   | /generateCertificate  | client | render + upload + persist            |
| GET    | /getCertificate       | client | fetch PNG/PDF                        |
| GET    | /getAllCertificate    | client | gallery (base64 list)                |
| POST   | /generateId           | client | ID card with QR                      |
| GET    | /getId, /getAllId     | client | fetch ID assets                      |
| POST   | /designTemplate       | client | AI agent designs a template          |
| POST   | /renderPreview        | client | render any valid template to PNG     |
| POST   | /saveTemplate         | client | persist template (per-client)        |
| GET    | /templates            | client | list saved templates                 |

## AI designer env

`LLM_PROVIDER=anthropic|openai|ollama`, `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`
(none for ollama), optional `LLM_MODEL`.
