# ReelPilot AI

ReelPilot is a web application that turns repeated Instagram audience questions
into ranked, editable Reel content packs. See [PRODUCT_PLAN.md](./PRODUCT_PLAN.md)
for scope and milestones.

## Repository layout

```text
apps/web/       Next.js web application
services/api/   FastAPI backend
```

## Local development

Requirements: Node.js 22+ and Python 3.11+. Docker is optional until PostgreSQL
or Redis is enabled; local development uses SQLite by default.

```bash
cp .env.example .env
npm install
npm run dev
```

In a second terminal:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e 'services/api[dev]'
uvicorn reelpilot.main:app --app-dir services/api --reload
```

Open the web app at http://localhost:3000 and the API documentation at
http://localhost:8000/docs.

## Try the analysis flow

1. Open the dashboard and select **Import comments**.
2. Download and upload the included sample CSV.
3. Select **Analyse comments**.
4. The dashboard will replace its demonstration data with persisted, ranked
   clusters from the import.

The default `APP_EMBEDDING_PROVIDER=auto` uses OpenAI `text-embedding-3-small`
when `OPENAI_API_KEY` is present. Without a key it uses the deterministic local
provider, so the complete flow works offline. Set `APP_EMBEDDING_PROVIDER=local`
to force offline analysis.

Authentication is email/password-based for this MVP. Signup creates a user and
isolated creator workspace; the API returns a bearer token used by protected
routes. Monthly defaults are 1,000 imported comments, 100 analyses, and 50
content generations per workspace. Redis is used for distributed request limits;
the API falls back to a process-local limiter if Redis is unavailable.

To use PostgreSQL instead of SQLite, start the services with `docker compose up -d`
and set the PostgreSQL `APP_DATABASE_URL` shown in `.env.example`.

## Connect Instagram (MVP)

Create a Meta developer app with an Instagram professional-account product, then
set `APP_INSTAGRAM_APP_ID`, `APP_INSTAGRAM_APP_SECRET`, and the exact callback URL
(`http://localhost:8000/v1/instagram/callback`) in `.env`. After signing in, click
**Connect Instagram** in the dashboard. ReelPilot stores the connected account and
offers these authenticated endpoints:

```text
GET  /v1/instagram/account       current connection status
POST /v1/instagram/sync-comments import comments from the latest 25 media items
```

The sync creates a normal workspace-scoped import batch, so it can immediately be
analysed by the existing clustering flow and is counted against the monthly quota.
Meta permissions, app review, and a professional Instagram account are required for
the live API path; without credentials, the rest of the local CSV/demo flow remains
available.
