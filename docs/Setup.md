# ReelPilot MVP setup

This guide runs the web app and API locally, then optionally connects a Meta
Instagram professional account. CSV imports and local analysis work without
Meta or OpenAI credentials.

## Requirements

- Node.js 22+
- Python 3.11+
- npm
- Meta Developer account (only for Instagram sync)

## Install

From the project root:

```bash
cp .env.example .env
npm install
python3 -m venv .venv
. .venv/bin/activate
pip install -e 'services/api[dev]'
```

Set a long random `APP_AUTH_SECRET` in `.env`. Never commit `.env`.

## Run locally

Terminal 1:

```bash
. .venv/bin/activate
uvicorn reelpilot.main:app --app-dir services/api --reload --port 8000
```

Terminal 2:

```bash
npm run dev
```

Open <http://localhost:3000>; API docs are at <http://localhost:8000/docs>.
Create an account, upload `fixtures/sample_comments.csv`, analyse it, and open
a cluster to generate a content pack.

## Environment

The default `.env` uses SQLite and an in-memory rate-limit fallback:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
APP_DATABASE_URL=sqlite:///./reelpilot.db
APP_REDIS_URL=redis://localhost:6379/0
APP_AUTH_SECRET=replace-with-a-long-random-secret
APP_MAX_COMMENTS_PER_MONTH=1000
APP_MAX_ANALYSES_PER_MONTH=100
APP_MAX_GENERATIONS_PER_MONTH=50
```

OpenAI is optional. Without `OPENAI_API_KEY`, the deterministic local provider
keeps analysis usable offline.

For a free local language model demo, install [Ollama](https://ollama.com/download),
run `ollama pull qwen2.5:3b`, and set these values in `.env`:

```env
APP_EMBEDDING_PROVIDER=local
APP_GENERATION_PROVIDER=ollama
APP_OLLAMA_BASE_URL=http://localhost:11434
APP_OLLAMA_MODEL=qwen2.5:3b
```

This keeps clustering local and uses Ollama only to generate Reel content packs.
The 3B quantized model is a practical choice for an 8 GB Mac; generation will be
slower than a hosted API.

## Instagram / Meta setup

1. Create an app at [Meta for Developers](https://developers.facebook.com/).
2. Add the Instagram API product supporting professional-account login and
   comment management.
3. Add your Instagram professional account as an app role/tester while the app
   is in development mode.
4. Add this exact redirect URI in the Meta product settings:

   ```text
   http://localhost:8000/v1/instagram/callback
   ```

5. Add the credentials to `.env`:

   ```env
   APP_INSTAGRAM_APP_ID=your-meta-app-id
   APP_INSTAGRAM_APP_SECRET=your-meta-app-secret
   APP_INSTAGRAM_REDIRECT_URI=http://localhost:8000/v1/instagram/callback
   APP_INSTAGRAM_API_VERSION=v22.0
   ```

6. Restart the API, sign in, and click **Connect Instagram** in the dashboard.
   Meta will authorize that creator's account and redirect back to ReelPilot.

The Meta app ID/secret are configured once by the application owner. Each
creator authorizes their own account through OAuth; creators do not paste API
tokens into ReelPilot. The current MVP stores one connected account per
workspace.

After connecting, the API provides:

```text
GET  /v1/instagram/account
POST /v1/instagram/sync-comments
```

`sync-comments` reads comments from the latest 25 media items, creates a normal
workspace-scoped import batch, and applies the monthly comment quota. The batch
can immediately use the existing analysis flow.

In Meta development mode, only app roles/testers can authorize the app. Before
opening it to unrelated creators, complete the App Review and Business
Verification steps requested in the Meta console. For production, use an HTTPS
callback and set `APP_INSTAGRAM_REDIRECT_URI` to the exact same URL in both the
Meta console and `.env`.

## Optional PostgreSQL and Redis

```bash
docker compose up -d
```

Set the PostgreSQL URL shown in `.env.example`. Redis enables shared rate limits
across API workers; without it, limits are process-local.

## Verification

```bash
.venv/bin/ruff check services/api
.venv/bin/pytest -q
npm run lint
npm run typecheck
npm run build
```

## MVP status

The functional MVP is complete: authentication, workspace isolation, quotas and
rate limits, CSV import, comment clustering, ranked questions, content-pack
generation/editing, Instagram OAuth connection, live comment sync, and the
responsive web dashboard.

Production hardening remains optional: Meta review, HTTPS deployment, encrypted
token storage/secrets management, background sync jobs, token refresh handling,
webhooks, multiple accounts per agency workspace, and billing.
