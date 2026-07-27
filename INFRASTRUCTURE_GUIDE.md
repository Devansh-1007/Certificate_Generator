# CertifyAI Infrastructure — A Beginner's Guide

This explains **every piece of infrastructure** in this project: what it is, why
it exists, and how to set it up yourself. It assumes you have never deployed
anything before.

Read it top to bottom once for understanding, then use it as a checklist.

---

## 1. The mental model

A web app is not one program. It is several separate things that talk to each
other over the network:

```
        Browser (a person)
              |
              v
   ┌──────────────────────┐
   │  FRONTEND  (Vercel)  │   React files: HTML/CSS/JS. Just static files a
   │  certifyai.vercel.app│   browser downloads. Holds NO secrets, NO database.
   └──────────┬───────────┘
              │ HTTPS calls (fetch/axios)
              v
   ┌──────────────────────┐
   │  BACKEND   (Render)  │   Python/Flask. Enforces rules, checks passwords,
   │  api.onrender.com    │   holds the secrets, talks to everything below.
   └───┬────────┬─────┬───┘
       │        │     │
       v        v     v
  ┌────────┐ ┌──────┐ ┌──────────┐
  │ MySQL  │ │  R2  │ │  Groq    │
  │(Aiven) │ │(files)│ │  (LLM)  │
  └────────┘ └──────┘ └──────────┘
   the truth   images   the AI
```

**Why split it up?** Each piece has a different job and different scaling needs:

- The frontend is just files — a CDN can serve them from 100 cities for free.
- The backend must be trusted — it holds the database password and the JWT
  secret. If this logic lived in the browser, anyone could read those secrets by
  pressing F12. **This is the single most important idea in web security.**
- The database must persist — servers restart, disks vanish; the data must not.
- Images/PDFs are large and don't belong in a database — object storage is
  cheaper and faster for blobs.

**The golden rule:** anything in the frontend is public. Anything in the backend
environment is secret. That is why `GOOGLE_CLIENT_ID` is fine to expose but
`MYSQL_PASS` never leaves Render.

---

## 2. Docker — why it exists

**The problem it solves.** "It works on my machine" — your laptop has Python
3.11, MySQL 8, some libraries; the server has different ones; the app breaks.

**What Docker does.** It packages your app *and* its entire environment (OS
libraries, Python version, dependencies) into an **image**. A running copy of an
image is a **container**. The same image runs identically on your laptop and on
Render.

Think of it as a shipping container: the port doesn't care what's inside, only
that the box is a standard size.

### The two ways we use Docker

**(a) As a temporary tool.** In the migration commands you ran:

```powershell
docker run --rm -i mysql:8 mysql -h host -P port -u avnadmin -p"pass" defaultdb
```

Breaking this down:
| Part | Meaning |
|---|---|
| `docker run` | start a container |
| `--rm` | delete the container when it finishes (don't accumulate junk) |
| `-i` | keep input open, so we can pipe the `.sql` file into it |
| `mysql:8` | the **image**: official MySQL version 8 |
| everything after | the command to run *inside* the container |

You never installed the MySQL client on Windows. Docker downloaded a tiny Linux
box that already had it, used it for two seconds, and threw it away. That is the
real superpower: **tools without installation**.

**(b) To package our backend.** `backend/Dockerfile` describes how to build our
app's image:

```dockerfile
FROM python:3.11-slim          # start from a small Linux with Python 3.11
WORKDIR /app                   # work in the /app folder inside the container
COPY requirements.txt .        # copy the dependency list in
RUN pip install -r requirements.txt gunicorn   # install them
COPY . .                       # copy the rest of the source
CMD gunicorn --bind 0.0.0.0:$PORT ... main:app # how to start the app
```

Two details worth understanding:

- **Why copy `requirements.txt` before the code?** Docker caches each step. If
  only your Python code changed, the expensive `pip install` layer is reused,
  and the build takes seconds instead of minutes.
- **Why gunicorn instead of `python main.py`?** Flask's built-in server is
  single-threaded and explicitly not for production. Gunicorn runs multiple
  worker processes so several users can be served at once.

### Docker commands worth knowing

```powershell
docker ps                  # what's running right now
docker ps -a               # including stopped containers
docker images              # images downloaded on your machine
docker logs certdb         # output from a container (great for debugging)
docker exec -it certdb bash  # open a shell inside a running container
docker stop certdb         # stop it
docker rm certdb           # delete it
docker system prune        # reclaim disk from unused junk
```

Your local database runs this way:

```powershell
docker run -d --name certdb -e MYSQL_ROOT_PASSWORD=devpass -e MYSQL_DATABASE=certificate -p 3306:3306 mysql:8
```

`-d` = background, `-e` = environment variable, `-p 3306:3306` = forward
port 3306 on your PC to port 3306 inside the container. That port mapping is why
`localhost:3306` reaches it.

⚠️ **Data lives inside the container.** `docker rm certdb` deletes your local
database. For real persistence you'd add a volume (`-v certdata:/var/lib/mysql`).

---

## 3. Aiven — the managed database

**What a database gives you.** Structured, queryable, durable storage with
guarantees: unique constraints, foreign keys, transactions. Our certificates,
users and organisations live here.

**Why not run MySQL myself on a server?** You'd own backups, security patches,
replication, monitoring, disk growth and 3am recovery. Aiven does that; the free
tier is enough for a portfolio project.

**Why not just use the Docker MySQL?** It runs on *your laptop*. When you close
it, the deployed app has no database. Cloud services need a cloud database.

### Setup

1. **aiven.io** → sign up → **Create service** → **MySQL** → Free plan → pick a
   region near you (Mumbai/Singapore for India — closer means lower latency).
2. Wait for status **Running** (a few minutes).
3. From the service **Overview**, copy: Host, Port, User (`avnadmin`), Password,
   Database (`defaultdb`).

Aiven ports are odd numbers like `25196`, not 3306, because many customers share
one cluster and each gets a different port.

### Applying migrations

A **migration** is a `.sql` file that changes the database's structure. They are
numbered (`V1`, `V2`, …) and must run **in order**, because later ones assume
earlier ones ran. This is how a schema evolves without anyone editing tables by
hand and forgetting what they did.

```powershell
cd C:\Users\cdev9\Documents\Projects_placement\C_Generator\Certificate_Generator

$H="mysql-xxx.aivencloud.com"; $P="25196"; $PW="your-password"

Get-Content backend\db\migrations\V1__init.sql -Raw              | docker run --rm -i mysql:8 mysql -h $H -P $P -u avnadmin -p"$PW" --force defaultdb
Get-Content backend\db\migrations\V2__template_details.sql -Raw  | docker run --rm -i mysql:8 mysql -h $H -P $P -u avnadmin -p"$PW" defaultdb
Get-Content backend\db\migrations\V3__batch_jobs.sql -Raw        | docker run --rm -i mysql:8 mysql -h $H -P $P -u avnadmin -p"$PW" defaultdb
Get-Content backend\db\migrations\V4__certificate_verify.sql -Raw| docker run --rm -i mysql:8 mysql -h $H -P $P -u avnadmin -p"$PW" defaultdb
Get-Content backend\db\migrations\V5__multi_tenant.sql -Raw      | docker run --rm -i mysql:8 mysql -h $H -P $P -u avnadmin -p"$PW" defaultdb
Get-Content backend\db\migrations\V6__oauth_and_domains.sql -Raw | docker run --rm -i mysql:8 mysql -h $H -P $P -u avnadmin -p"$PW" defaultdb
```

`Get-Content ... | docker run -i ...` reads the file on Windows and pipes it as
input to the MySQL client inside the container. (PowerShell has no `<` operator,
which is why we pipe instead.)

Verify:

```powershell
docker run --rm mysql:8 mysql -h $H -P $P -u avnadmin -p"$PW" -e "USE defaultdb; SHOW TABLES;"
```

Expect: `ORGANISATIONS`, `USERS`, `CLIENT_DETAILS`, `CERTIFICATE_DETAILS`,
`ID_DETAILS`, `TEMPLATE_DETAILS`, `CERTIFICATE_VERIFY`, `BATCH_JOBS`.

**If a migration errors:** read the message. "Duplicate column" means it already
ran — safe to ignore. "Table doesn't exist" means you skipped an earlier file.

---

## 4. Cloudflare R2 — object storage

**What object storage is.** A place to put *files* (PNG, PDF) and get them back
by key. Not a filesystem, not a database — think "infinite folder with a URL".

**Why not store images in MySQL?** Databases are optimised for small structured
rows. Multi-megabyte blobs bloat them, slow backups and cost more. Every real
product stores blobs separately and keeps only the *link* in the database.

**Why not the server's disk?** Render's free disk is **ephemeral** — wiped on
every deploy and restart. Your certificates would vanish. R2 is durable.

**Why R2 over AWS S3?** R2 speaks the same S3 API, but has a genuinely free
tier (10 GB) with **no egress fees**. Because the API is identical, our code
works with either — we just point `S3_ENDPOINT_URL` at whichever we want. That
is what "S3-compatible" means, and it's why `awsS3.py` needed only a few lines
to support both.

### Setup

1. **dash.cloudflare.com** → **R2** → Create bucket (e.g. `certificate-generator`).
2. **Manage R2 API Tokens** → Create token → permission **Object Read & Write**.
3. Copy: Access Key ID, Secret Access Key, and the **S3 API endpoint**, which
   looks like `https://<account-id>.r2.cloudflarestorage.com`.

⚠️ The endpoint must **not** include the bucket name — the bucket is passed
separately as `BUCKET`. (You hit exactly this bug earlier.)

---

## 5. Render — hosting the backend

**What Render does.** Watches your GitHub repo, builds the Docker image, runs
the container, gives it an HTTPS URL, restarts it if it crashes.

**Why the backend needs a server at all.** It must be always-on, hold secrets
and keep TCP connections to MySQL. Vercel-style static hosting can't do that.

### Setup

1. **render.com** → sign in with GitHub → **New** → **Web Service** → pick the repo.
2. **Root Directory:** `backend` (the Dockerfile lives there).
   **Runtime:** Docker. **Instance:** Free.
3. **Environment** tab → add every variable from `backend/Env/.env.example`:
   MySQL (Aiven values), `JWT_SECRET`, `VERIFY_SECRET`, `ADMIN_USER/PASSWORD`,
   the R2 keys, the Groq key, the asset paths, and
   `BASE_URL=https://<your-service>.onrender.com`.
4. Deploy. Check `https://<service>.onrender.com/apidocs`.

**Free tier gotcha:** the service **sleeps after ~15 minutes idle**, so the first
request afterwards takes ~50 seconds while it wakes. That's why the frontend has
a "may be waking from sleep" message — a real UX consideration, not a bug.

### Environment variables — why they exist

Secrets are **not** in the code, because the code is on public GitHub. Instead
the platform injects them at runtime, and `os.getenv("MYSQL_PASS")` reads them.
Same code, different secrets per environment (your laptop vs production). This
is the "twelve-factor app" principle, and it's why `.env` is in `.gitignore`.

---

## 6. Vercel — hosting the frontend

**What Vercel does.** Runs `npm run build` (React → plain HTML/CSS/JS), then
serves those files from a global CDN with HTTPS.

**Why separate from the backend?** Static files need no server logic; a CDN
serves them from the city nearest each visitor. It's faster and free.

### Setup

1. **vercel.com** → sign in with GitHub → **Add New → Project** → import the repo.
2. **Root Directory:** `frontend`. Framework auto-detects as Create React App.
3. **Environment Variables:** `REACT_APP_API_URL = https://<service>.onrender.com`.
4. Deploy.

**Why the `REACT_APP_` prefix?** Create React App only injects variables with
that prefix into the browser bundle. It's a deliberate guard so you can't leak a
server secret into public JavaScript by accident.

**`frontend/vercel.json`** contains a rewrite sending every path to
`index.html`. Without it, refreshing on `/verify/abc123` returns 404: the CDN
looks for a file at that path, but the route only exists inside React Router.
The rewrite says "serve the app, let JavaScript read the URL."

---

## 7. Google Sign-In — what and why

### The concepts

**Authentication** = who are you. **Authorisation** = what may you do. Google
handles the first; our JWT and roles handle the second.

**Why offer it?** Users hate creating passwords; you avoid storing another
password hash; Google already verified the email address. For a B2B tool this
is table stakes.

### How our flow works (and why it's safe)

```
1. Browser: user clicks "Sign in with Google"
2. Google:  authenticates them, returns an ID TOKEN to the page
              (a JWT signed by Google's private key)
3. Browser: POSTs that token to our backend  ->  /auth/google
4. Backend: downloads Google's PUBLIC keys, verifies the signature,
            checks issuer + audience + expiry + email_verified
5. Backend: only now trusts the email; issues OUR own session JWT
```

**Why verify server-side?** Anyone can POST `{"email":"ceo@company.com"}` to our
API. The ID token is different: it's cryptographically signed by Google and
cannot be forged without Google's private key. Verifying the signature is what
turns an unverified claim into a fact. **Never trust identity data from a
browser without verifying a signature.**

**Why no client secret?** There are several OAuth flows. We use the token flow
for browser apps, where Google hands the token straight to the page. A client
*secret* only exists for server-side flows; a browser can't keep secrets anyway.
The `GOOGLE_CLIENT_ID` is public by design — it identifies the app, it doesn't
authorise anything.

### Setup in Google Cloud Console

1. **console.cloud.google.com** → create/select a project (e.g. "CertifyAI").
2. **APIs & Services → OAuth consent screen**:
   - User type **External** (anyone with a Google account).
   - App name, your support email, developer email → Save.
   - Publishing status stays "Testing" — that's fine, but only test users you
     list can sign in. Add your own Google address under **Test users**, or
     click **Publish app** for anyone.
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   - Application type: **Web application**.
   - **Authorised JavaScript origins** — add both:
     - `http://localhost:3000`
     - `https://<your-project>.vercel.app`
   - Leave **Authorised redirect URIs empty** — our flow doesn't redirect.
   - Create → copy the **Client ID** (ends in `.apps.googleusercontent.com`).
4. **Render** → Environment → add `GOOGLE_CLIENT_ID=<that value>` → save
   (this redeploys automatically).

**What "authorised origin" means:** Google will only issue a token to a page
served from a domain you listed. It stops someone copying your client ID onto
`evil.com` and harvesting sign-ins. If you get *"origin is not allowed"*, this
list is what's wrong — and note that origins must match exactly, including
`https://` and no trailing slash.

### Why the button appears by itself

The frontend asks `GET /auth/config` on load. If the backend reports no client
ID, the button never renders and the password form is the only option. That's
called **feature detection**: one codebase, and the deployment decides what's
available — no rebuild needed to enable Google.

---

## 8. Work-email rules — the product thinking

**The problem.** Devansh signs up with `devansh@acme.com` and creates "Acme".
Tomorrow his colleague signs up with `priya@acme.com` — and gets a *second,
empty* Acme. Now the company's data is split across two tenants. This is one of
the most common SaaS onboarding failures.

**Our fix.** The organisation **claims the owner's email domain**. When Priya
signs in, we look up `acme.com`, find Acme, and add her as a **member** of the
existing organisation.

**Why consumer domains are excluded.** If we did this for `gmail.com`, every
unrelated Gmail user on earth would join one giant "Gmail" organisation and see
each other's certificates. So `gmail.com`, `outlook.com` etc. can never claim or
match a domain — and by default can't create an organisation at all
(`REQUIRE_WORK_EMAIL=true`). They can still be *invited* to one.

Set `REQUIRE_WORK_EMAIL=false` on Render if you want to demo signup with a
personal Gmail account.

---

## 9. Groq — the LLM provider

The AI designer needs a large language model. We don't host one (they need
expensive GPUs); we call an API.

**Why Groq:** free tier, very fast, and it speaks the **OpenAI-compatible API**
format. Our `aiDesigner/llm.py` therefore works with Groq, OpenAI, Google Gemini
or a local Ollama by changing `OPENAI_BASE_URL` — no code change. Writing
against a de-facto standard interface instead of one vendor's SDK is a small
design decision with a big payoff.

Get a key at **console.groq.com** → API Keys, then on Render:

```
LLM_PROVIDER=openai
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY=gsk_...
LLM_MODEL=llama-3.3-70b-versatile
```

**Rate limits:** free tiers cap tokens per minute. Our client retries with
exponential backoff and honours `Retry-After`, then returns HTTP 429 with a
readable message rather than a crash. Handling rate limits properly is what
separates a demo from a product.

---

## 10. GitHub Actions — CI/CD

- **CI** (Continuous Integration): every push runs the tests automatically, so
  broken code is caught in minutes rather than by a user.
- **CD** (Continuous Deployment): if the tests pass, the new version ships
  automatically.

Our pipeline (`.github/workflows/ci.yml`), in order:

| Job | Does | Blocks deploy? |
|---|---|---|
| `backend` | 91 offline tests + the AI-agent eval gate | yes |
| `frontend` | production build | yes |
| `deploy` | triggers Render + Vercel deploy hooks (main only) | — |
| `smoke` | polls `/apidocs/` until it answers 200 | fails the run if prod is unhealthy |

**Why tests must run offline.** CI has no database, no R2, no API keys. Our
tests use fakes and temp folders, so they're fast and deterministic. A test that
needs the internet is a test that fails randomly.

To make the gate real, turn **off** auto-deploy on Render/Vercel and add
`RENDER_DEPLOY_HOOK_URL`, `VERCEL_DEPLOY_HOOK_URL` and `BACKEND_URL` as GitHub
repo secrets. Otherwise both platforms deploy on push regardless of test results.

---

## 11. Putting it together — first deploy checklist

```
[ ] 1. Docker Desktop running
[ ] 2. Aiven MySQL created; host/port/password copied
[ ] 3. Migrations V1..V6 applied in order; SHOW TABLES verified
[ ] 4. Cloudflare R2 bucket + API token created
[ ] 5. Groq API key created
[ ] 6. git push origin main   -> GitHub Actions green
[ ] 7. Render web service: root=backend, runtime=Docker, all env vars set
[ ] 8. Render URL opens /apidocs
[ ] 9. Vercel project: root=frontend, REACT_APP_API_URL set
[ ] 10. Google Cloud OAuth client ID -> GOOGLE_CLIENT_ID on Render (optional)
[ ] 11. Smoke test: sign up -> generate a certificate -> open the QR verify
        link in an incognito window -> bulk upload sample_roster.csv
```

---

## 12. Debugging: where to look

| Symptom | Most likely cause | Where to look |
|---|---|---|
| "Can't connect to MySQL on localhost" | `MYSQL_HOST` still `localhost` on Render | Render → Environment |
| "Unknown column X" | a migration didn't run | re-run migrations; `SHOW COLUMNS` |
| Login works, other calls 401 | old JWT after changing `JWT_SECRET` | sign out and back in |
| First request takes 50s | Render free tier woke from sleep | normal |
| Google button missing | `GOOGLE_CLIENT_ID` not set | `GET /auth/config` |
| "origin is not allowed" | domain not in authorised origins | Google Console |
| Images don't load | R2 endpoint includes the bucket name | `S3_ENDPOINT_URL` |
| 429 from the designer | LLM tokens-per-minute exceeded | wait a minute, or use a smaller model |

**How to read logs.** Render → your service → **Logs** shows every request and
traceback live. That single panel answers most "why is it broken" questions —
and the app's own `/admin` console shows health, latency and DB state without
leaving the product.

---

## 13. Vocabulary

| Term | Meaning |
|---|---|
| **Image / container** | the packaged app / a running copy of it |
| **Environment variable** | config injected at runtime, kept out of the code |
| **Migration** | a versioned SQL file that evolves the schema |
| **Object storage** | file storage addressed by key (R2, S3) |
| **JWT** | a signed token carrying claims; tamper-evident, not secret |
| **OAuth / ID token** | delegated login; a signed statement of who the user is |
| **CDN** | servers worldwide caching static files near users |
| **CI/CD** | automated testing / automated releasing |
| **Multi-tenant** | one deployment serving many isolated customers |
| **Ephemeral disk** | storage wiped on restart — never keep data there |
| **Rate limit** | a cap on requests per period; handle with backoff |

---

## 14. What to say in an interview

You didn't just "make a website". You can now defend:

- a **containerised** Flask service deployed on managed infrastructure, with a
  CDN-hosted SPA and a managed MySQL instance;
- **secrets management** via environment variables — nothing sensitive in git;
- **versioned migrations** with a data-preserving multi-tenant conversion;
- **S3-compatible storage abstraction**, so the provider is a config value;
- **OAuth with server-side ID-token verification**, and why the browser's word
  is never enough;
- **multi-tenant isolation** where `org_id` comes from a verified token, never
  from the request;
- **CI/CD gated on tests and AI evals**, with a post-deploy smoke check;
- **graceful degradation** — rate limits, cold starts and a missing provider
  produce clear messages instead of stack traces.

The failures you debugged along the way (a Kafka service created instead of
MySQL, a missing column, a garbage-collected DB connection, an S3 endpoint with
the bucket glued on) are worth more in an interview than the successes. Real
engineering is mostly this.
