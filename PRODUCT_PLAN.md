# ReelPilot AI — MVP Product and Build Plan

## Product decision

Build **Comment-to-Reel** first: a responsive browser-based SaaS for Instagram professional
accounts that turns repeated audience questions into ranked, editable Reel content
packs.

The MVP is an insight and drafting tool. It will not edit video, read DMs,
predict virality, or publish without explicit creator approval.

## Target user and promise

- Primary user: Indian Instagram creators and small creator agencies.
- Supported content languages: English, Hindi, and Hinglish.
- Input: recent Instagram posts and their comments, or a CSV import while an
  Instagram account is not connected.
- Output: ten ranked Reel ideas, each with three hooks, a 15/30/60-second script,
  caption, CTA, cover text, and supporting audience comments.
- Core promise: "See what your audience keeps asking, then turn it into your next
  Reel in minutes."

## MVP boundaries

### Included

1. Email or Google authentication.
2. Creator profile: niche, audience, tone, language, goals, and banned topics.
3. CSV/manual comment import from day one.
4. Instagram professional-account connection through the official API.
5. Recent media and comment synchronization.
6. Comment cleanup, language detection, deduplication, and semantic clustering.
7. Cluster ranking using frequency, recency, engagement, and creator relevance.
8. AI-generated content packs with structured, editable fields.
9. Evidence view showing which comments led to each idea.
10. Copy and Markdown/PDF export.
11. Feedback controls: useful/not useful, edit, regenerate, archive.
12. Account disconnect and data deletion.

### Deferred

- DMs, automated replies, and automated engagement.
- Direct publishing and scheduling (the architecture will leave room for it).
- Video upload, cutting, captions, voice-over, lip-sync, and rendering.
- YouTube Shorts variants.
- Performance prediction and post-publication analytics.
- Agency workspaces, billing, and team roles.

## User journey

1. Sign up and define creator voice.
2. Import a sample CSV or connect an Instagram professional account.
3. Select a date range or recent posts and start analysis.
4. Watch the analysis job progress.
5. Review ranked audience-question clusters with source comments.
6. Open a cluster and generate a Reel content pack.
7. Edit, regenerate individual fields, copy, or export.
8. Mark the idea as planned, published, or archived.

## Technical architecture

```text
Next.js web app
      |
      v
FastAPI REST API ---- PostgreSQL + pgvector
      |                         |
      +---- Redis job queue ----+
      |
      +---- Meta Instagram API
      +---- OpenAI Responses + Embeddings APIs
      +---- S3-compatible object storage (exports only)
```

### Recommended stack

- Frontend: Next.js, TypeScript, Tailwind CSS, and shadcn/ui.
- Backend: FastAPI, Pydantic, SQLAlchemy, and Alembic.
- Database: PostgreSQL with pgvector.
- Background work: Redis and Dramatiq (sync and analysis must not block requests).
- AI: OpenAI Responses API with Structured Outputs; model IDs configurable by
  environment. Use a low-cost model for cleanup/classification and a stronger
  model for final scripts.
- Testing: Pytest for the API, Vitest for UI logic, and Playwright for the main
  browser journey.
- Local development: Docker Compose for PostgreSQL and Redis; web and API run
  directly for fast reloads.

Start as a modular monolith. Separate services are unnecessary until workload or
team size proves otherwise.

## Core processing pipeline

1. Normalize comment text and remove obvious spam, mentions-only content, and
   duplicates.
2. Detect English, Hindi, Hinglish, or unsupported language.
3. Classify whether a comment contains a question, request, objection, or useful
   topic signal.
4. Create embeddings for useful comments.
5. Cluster by semantic similarity; retain outliers rather than forcing them into
   a topic.
6. Generate a short cluster label and canonical audience question.
7. Rank clusters with a transparent score:

   `0.45 frequency + 0.20 recency + 0.15 engagement + 0.20 creator relevance`

8. Generate a content pack from the cluster, creator profile, and representative
   comments using a strict JSON schema.
9. Store prompt version, model, usage, latency, and output for evaluation.

The score is a product heuristic, not a "viral probability." It should be shown
as an opportunity score with an explanation.

## Initial data model

- `users`: identity and account settings.
- `workspaces`: creator/agency ownership boundary, even before team features.
- `creator_profiles`: niche, tone, languages, audience, goals, banned topics.
- `instagram_accounts`: Instagram identity and connection status.
- `oauth_credentials`: encrypted access token, expiry, scopes, and refresh state.
- `media`: imported Instagram post/Reel metadata.
- `comments`: normalized comment data and source metadata.
- `analysis_runs`: job state, filters, counts, and errors.
- `comment_clusters`: label, canonical question, score, and statistics.
- `cluster_comments`: membership, similarity, and representative flag.
- `reel_ideas`: title, angle, status, and source cluster.
- `content_packs`: hooks, scripts, caption, CTA, hashtags, cover text, and version.
- `generation_events`: model, prompt version, token usage, latency, and feedback.
- `audit_events`: connection, export, deletion, and future publishing actions.

All tenant-owned tables include `workspace_id`. Raw OAuth tokens are never sent to
the browser.

## API surface (first version)

```text
POST   /v1/imports/comments-csv
POST   /v1/integrations/instagram/connect
GET    /v1/integrations/instagram/callback
DELETE /v1/integrations/instagram
POST   /v1/integrations/instagram/sync
POST   /v1/analysis-runs
GET    /v1/analysis-runs/{id}
GET    /v1/analysis-runs/{id}/clusters
GET    /v1/clusters/{id}
POST   /v1/clusters/{id}/content-packs
PATCH  /v1/content-packs/{id}
POST   /v1/content-packs/{id}/regenerate
POST   /v1/content-packs/{id}/export
POST   /v1/feedback
POST   /v1/webhooks/instagram
```

## Delivery milestones

### Milestone 0 — Foundation (2–3 days)

- Monorepo scaffold, local Docker services, configuration, migrations, CI.
- Authentication and workspace isolation.
- Seeded demo creator and representative multilingual comment dataset.
- Health checks, structured logging, and error format.

Exit: a user can sign in and reach an empty dashboard locally and in staging.

### Milestone 1 — Offline vertical slice (4–5 days)

- Creator profile onboarding.
- CSV/manual import.
- Analysis pipeline, clustering, ranking, and evidence view.
- Store repeatable analysis runs.

Exit: sample comments become useful ranked audience questions without Meta access.

### Milestone 2 — Content studio (4–5 days)

- Structured content-pack generation.
- English/Hindi/Hinglish tone controls.
- Field-level editing/regeneration, versions, copy, and export.
- Prompt fixtures and quality evaluation dataset.

Exit: a creator can produce and export a complete content pack.

### Milestone 3 — Instagram integration (5–7 days)

- Meta app, OAuth, encrypted token storage, media/comment sync, pagination,
  retries, rate-limit handling, disconnect, and deletion path.
- Webhook receiver for incremental comment updates if available for the approved
  configuration.
- Keep CSV import as a permanent fallback and demo route.

Exit: a test professional account can connect and analyze real comments.

### Milestone 4 — Beta hardening (3–5 days)

- End-to-end tests, observability, usage caps, privacy policy, terms, support and
  deletion pages, security review, and Meta App Review assets.
- Invite-only beta with 5–10 creators.

Exit: reliable private beta and a measurable App Review use case.

Expected engineering time: roughly 4 weeks for one focused developer, excluding
Meta review time.

## Acceptance criteria

- A new user reaches their first ranked result in under five minutes using CSV.
- A dataset of 500 comments completes asynchronously and can recover from retry.
- Every suggested idea links to supporting source comments.
- Generated content always validates against the content-pack schema.
- Hindi/Hinglish output is editable and does not unexpectedly switch scripts or
  languages.
- No cross-workspace data can be accessed by API identifier guessing.
- Disconnecting Instagram stops sync; deleting the integration removes tokens.
- No publishing action exists without a final, explicit user confirmation.

## Product metrics

- Activation: percentage of users who finish one analysis and open one cluster.
- Time to first useful idea.
- Useful-vote rate and content-pack export rate.
- Percentage of generated fields edited before export.
- Weekly returning creators and new comments analyzed.
- AI cost and sync cost per activated creator.

The north-star metric for the beta is **content packs exported per weekly active
creator**, supported by a useful-vote rate above 60%.

## Risks and mitigations

- **Meta review or permission delays:** ship CSV import first and use owned test
  accounts during development.
- **API change:** isolate Meta calls behind an integration adapter and pin the
  Graph API version in configuration.
- **Weak clusters on small datasets:** show unclustered ideas, confidence, and
  source evidence; never invent audience demand.
- **Generic AI copy:** condition on the creator profile and real comments, retain
  editable fields, and collect feedback.
- **Token and personal-data exposure:** encrypt secrets, minimize stored commenter
  data, redact logs, implement retention and deletion, and verify webhooks.
- **Cost spikes:** cap comments per run, cache embeddings, deduplicate before AI
  calls, and record per-run usage.

## Immediate build order

1. Scaffold `apps/web` and `services/api` plus local PostgreSQL/Redis.
2. Define the OpenAPI contracts and database migrations.
3. Add a synthetic English/Hindi/Hinglish fixture with expected clusters.
4. Implement CSV import and the deterministic parts of the analysis pipeline.
5. Add AI classification/labeling and content generation behind provider
   interfaces with fake implementations for tests.
6. Build the evidence-first dashboard and content editor.
7. Integrate Meta only after the offline vertical slice is working end to end.

## Assumptions to validate during the first beta

- Professional creators will connect their account for this value proposition.
- At least 100 recent comments are enough for useful clustering.
- Creators prefer drafts grounded in their audience over generic trend discovery.
- English/Hindi/Hinglish covers the first reachable customer segment.
- Export is sufficient before direct publishing is approved and trusted.
