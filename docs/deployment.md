# Deployment

This project does not use a Render Blueprint (`render.yaml`) — the backend's
Render Web Service is configured by hand in Render's dashboard instead. This
was a deliberate choice, not an oversight: a Blueprint recreates services
from scratch on every change to the file, which is more moving parts than a
single-developer, free-tier deployment needs. Configuring it by hand once,
in the dashboard, is simpler to reason about and change incrementally.

The full, ordered, step-by-step walkthrough for standing up every piece of
this stack (Neon, Cloudflare R2, Cloudflare Workers, Render, UptimeRobot,
Resend/Sentry/Razorpay, and a staging environment for live-verifying the
firm-scoping RBAC fix before real customer data touches this) is meant to be
run interactively with an assistant that can confirm each step as you
complete it, rather than followed as a static checklist — see `HANDOFF.md`
for the current state of what's built vs. verified before starting.

At a high level, the pieces are:

1. **Neon** — managed Postgres. Two connection strings matter: the pooled
   one (`DATABASE_URL`, for the running app) and the direct one (used only
   for running Alembic migrations — see below).
2. **Cloudflare R2** — S3-compatible object storage for uploaded documents.
   `S3_REGION` should be `auto`, not an AWS region name.
3. **Cloudflare Workers** — hosts the Next.js frontend.
4. **Render** — hosts the FastAPI backend as a single Web Service. No
   Background Worker service exists or is needed — there is no Celery
   worker anymore (see below).
5. **UptimeRobot** — pings `GET /internal/tasks/heartbeat` (not `/health`)
   to keep the free-tier instance warm and to drive the scheduled jobs that
   used to be a Celery beat schedule.
6. **Resend / Sentry / Razorpay** — transactional email, error monitoring,
   and payments respectively.

## No Celery, no Redis, no separate worker

Earlier iterations of this backend used Celery + Redis for background work
(deadline reminders, missing-document escalation, subscription expiry, and
OCR on uploaded documents). Both have been removed entirely, per a
deliberate "stay on free tiers, minimize moving pieces" decision:

- The three previously-scheduled jobs are now plain Python functions,
  run synchronously and inline from `GET /internal/tasks/heartbeat`
  (`app/api/v1/endpoints/internal.py`) whenever enough wall-clock time has
  passed since the last run (tracked in a small `system_state` table so a
  redeploy or cold start doesn't reset an in-memory timer). Point your
  UptimeRobot monitor at this endpoint, with the `X-Internal-Task-Secret`
  header set to your `INTERNAL_TASK_SECRET` value.
- OCR on newly uploaded documents runs via FastAPI's `BackgroundTasks`,
  on the same instance that serves API requests, right after the upload
  request returns. This is a known, accepted risk on a 0.1 vCPU / 512MB
  instance at current scale — see `app/worker/tasks.py` and
  `app/services/ocr_service.py` for the two cheap mitigations in place
  (a file-size threshold that skips auto-OCR above `OCR_MAX_FILE_SIZE_MB`,
  and a lowered PDF render DPI).

Do not reintroduce Docker, Celery, or Redis when extending this — if a
future scale point genuinely needs a real task queue, that's a deliberate
architecture change to make consciously, not something to slip back in
piecemeal.

## Migrations are run manually, not in the build command

`alembic upgrade head` is intentionally **not** part of Render's build
command. It's run by hand — from Render's dashboard shell, or locally
against the direct (non-pooled) Neon connection string — after a deploy,
not during one. This avoids two build processes racing to apply the same
migration if a deploy is ever triggered twice in quick succession (e.g. a
retry), which is a real risk on a platform that doesn't serialize deploys
for you the way a dedicated migration step would.
