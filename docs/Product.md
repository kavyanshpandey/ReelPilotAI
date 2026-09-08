# ReelPilot AI

## Product overview

ReelPilot is an audience intelligence workspace for Instagram creators. It turns
repeated audience questions into ranked content opportunities and editable Reel
content packs.

The product helps a creator answer one practical question: **what should I make
next, based on what my audience is already asking for?**

ReelPilot is an idea and pre-production product. It does not currently record,
edit, render, or publish video Reels.

## The creator problem

Creators often have plenty of comments but no reliable way to identify the
questions that deserve a dedicated post. They manually scan comments, guess what
will perform, and rewrite the same ideas into hooks, scripts, captions, and
hashtags.

ReelPilot makes that process evidence-led. Every ranked opportunity points back to
the audience comments that created the signal.

## What the platform can do today

### Workspace and authentication

- Create an account with email and password.
- Create an isolated creator workspace during signup.
- Protect workspace data with bearer authentication.
- Track monthly workspace quotas.

### Audience data import

- Upload a UTF-8 CSV file of Instagram comments.
- Accept a required `comment` or `text` column.
- Accept optional `username`, `post_id`, `created_at`, and `likes` columns.
- Validate rows and report imported, skipped, and warning counts.
- Store imported comments in the workspace database.

### Audience signal analysis

- Group repeated questions and related topics.
- Rank clusters using mention volume, likes, and opportunity scoring.
- Show representative comments supporting each cluster.
- Provide a canonical audience question for every cluster.
- Use deterministic local analysis for a free offline demo.
- Optionally use OpenAI embeddings for semantic similarity.

### Reel ideas and content studio

For a selected audience signal, ReelPilot generates an editable content pack
containing:

- Cover text
- Three opening hooks
- 15-second, 30-second, and 60-second scripts
- Caption
- Call to action
- Hashtags
- Suggested B-roll shots

Creators can change the language between English, Hindi, and Hinglish, choose a
tone, edit every field, save a draft, generate a new version, or copy the complete
pack into their production workflow.

### AI providers

The current project supports these modes:

| Feature | Provider | Cost | Use |
| --- | --- | --- | --- |
| Comment clustering | Local deterministic provider | Free | Default offline demo |
| Comment embeddings | OpenAI `text-embedding-3-small` | Paid API | Better semantic similarity |
| Content generation | Local template provider | Free | Fastest fallback |
| Content generation | Ollama, for example `qwen2.5:3b` | Free locally | Local AI demo on an 8 GB Mac |
| Content generation | OpenAI Responses API | Paid API | Hosted AI generation |

## What the platform cannot do yet

- It does not create a video file.
- It does not record voice or camera footage.
- It does not automatically edit clips, add music, subtitles, or transitions.
- It does not publish a Reel to Instagram.
- It does not schedule posts.
- It does not provide Instagram reach, follower, or revenue analytics.
- It currently syncs a limited set of recent media and comments through the MVP
  Instagram endpoint.
- It currently supports one connected Instagram account per workspace.
- It does not yet provide background sync jobs or webhooks.
- It is not production-ready for multi-tenant deployment without additional
  security and operational hardening.

The intended workflow is: ReelPilot finds the opportunity and prepares the
creative brief; the creator records and edits the final video in Instagram,
CapCut, Canva, Premiere, or another production tool.

## Typical creator workflow

1. Create a workspace and sign in.
2. Import an Instagram comment CSV, or connect a professional Instagram account
   when Meta integration is configured.
3. Analyse the comments.
4. Review the ranked audience signals and supporting comments.
5. Choose a signal and open Content Studio.
6. Select language and tone.
7. Generate a Reel content pack.
8. Edit the hook, script, caption, CTA, hashtags, and B-roll.
9. Save the draft and copy it into the creator's production workflow.
10. Record, edit, and publish the Reel manually.

## Creator use cases

### Travel creators

Turn repeated questions about budget, safety, routes, hotels, equipment, and
seasonality into a series of practical Reels.

### Beauty and fashion creators

Cluster recurring product, routine, sizing, styling, and comparison questions into
short educational or review formats.

### Fitness creators

Identify repeated questions about exercises, form, nutrition, routines, and
progress expectations, then turn each high-signal topic into a content brief.

### Educators and experts

Use audience questions as a demand map for explainers, myth-busting posts,
checklists, and beginner series.

### Small businesses and agencies

Create a repeatable comment-to-content workflow across client workspaces. The
current MVP supports the workspace isolation needed for this direction, while
agency account management and billing remain future work.

## Pitch-ready positioning

### One-sentence pitch

ReelPilot turns the questions creators already receive into ranked, ready-to-film
Reel briefs.

### Short pitch

Creators do not need more generic content ideas; they need a clear view of what
their own audience wants next. ReelPilot analyses audience comments, finds the
questions that repeat, ranks the strongest opportunities, and turns each one into
an editable Reel brief with hooks, scripts, captions, CTAs, hashtags, and B-roll.

### Product promise

Every idea starts with evidence from the creator's audience. The creator keeps
control of the voice, edits the draft, and decides what to publish.

### Demo story

Start with a CSV containing real audience comments. Import and analyse it. Open the
highest-ranked question and show the supporting comments. Generate a Hinglish
content pack, edit the hook and CTA, save it, and copy the final brief. End by
showing that the creator now has a reasoned topic and a filmable plan instead of a
blank page.

## Technical architecture

- Web: Next.js, React, TypeScript.
- API: FastAPI and Python.
- Persistence: SQLite by default for local development.
- Optional production database: PostgreSQL with pgvector support in the supplied
  Docker Compose configuration.
- Rate limits: Redis when available, with an in-process fallback.
- Authentication: email/password signup and JWT bearer access tokens.
- Local analysis: deterministic text features and clustering.
- Hosted AI: OpenAI embeddings and Responses API.
- Local AI: Ollama HTTP API for structured content generation.
- Instagram: Meta OAuth and Graph API integration for professional accounts.

## Local demo setup

Use the existing setup guide in [`docs/Setup.md`](./Setup.md).

For a completely free demo, configure:

```env
APP_EMBEDDING_PROVIDER=local
APP_GENERATION_PROVIDER=ollama
APP_OLLAMA_BASE_URL=http://localhost:11434
APP_OLLAMA_MODEL=qwen2.5:3b
```

Install Ollama, download the model, and start it:

```bash
ollama pull qwen2.5:3b
ollama run qwen2.5:3b
```

The model runs locally. On an 8 GB Mac, the 3B quantized model is a practical
demo choice, although generation will be slower than a hosted API. The existing
local template provider remains available as a fallback.

## Live Instagram setup

Live comment sync requires:

- A Meta developer account.
- A Meta app with the relevant Instagram API product.
- An Instagram Professional account.
- Test-role access while the Meta app is in development mode.
- An exact OAuth redirect URI configured in both Meta and `.env`.
- Review and appropriate access approval before connecting unrelated creators in
  production.

The application owner configures the Meta app ID and secret. Each creator
authorizes their own Instagram account through the OAuth connection flow.

## Data and storage

The local default database is `reelpilot.db` in the directory from which the API
starts. It stores users, workspaces, comments, analyses, content packs, usage
records, and the connected Instagram token.

CSV contents are parsed into database rows; the uploaded CSV is not retained as a
separate file by the API.

Before production, replace local SQLite with PostgreSQL, use a managed secret
store, encrypt stored OAuth tokens, add token refresh handling, and configure
backups and deletion controls.

## Product risks and boundaries

- AI output must be reviewed before publication.
- Audience comments are evidence, not guaranteed facts.
- The generated scripts should not invent prices, statistics, or personal claims.
- Local models can be slower and less polished than hosted models.
- Instagram API access depends on Meta account type, permissions, app mode, and
  review status.
- Usage limits and AI provider costs must be monitored when hosted providers are
  enabled.

## Recommended roadmap

### Near term

- Add a first-class live sync button and sync history.
- Add saved content-pack listing and search.
- Add export to Markdown, Notion, and Google Docs.
- Improve empty states and onboarding for new workspaces.
- Add content calendar and status tracking.

### Production readiness

- Move to PostgreSQL and encrypted OAuth token storage.
- Add token refresh and connection health checks.
- Add background sync jobs and webhooks.
- Add structured logging, error monitoring, backups, and audit events.
- Complete Meta review and production OAuth configuration.

### Expansion

- Video brief templates by niche and format.
- Direct integrations with editing and publishing tools.
- Performance feedback from published Reels.
- Multi-account agency workspaces.
- Billing and plan management.

