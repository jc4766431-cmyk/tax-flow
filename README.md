# TaxFlow — Accounting & Tax Firm Automation Platform

Work-in-progress full-stack scaffold: Next.js (App Router, TypeScript,
Tailwind) frontend + FastAPI (Python 3.12, SQLAlchemy 2.0, PostgreSQL)
backend. Runs directly on locally installed services — no Docker, no
Redis, no Celery required (see `docs/deployment.md` for why).

**Start here: [`HANDOFF.md`](./HANDOFF.md)** — a detailed status report and
ordered task list for continuing this build. It covers what's implemented,
what's stubbed, known issues to fix, and the design system already in use.

**Deploying this?** See [`docs/deployment.md`](./docs/deployment.md) — the
Render/Neon/Cloudflare R2/Cloudflare Workers services are configured by
hand in each provider's dashboard, not via a Render Blueprint.

## Quick start

Prerequisite: PostgreSQL 16 installed and running locally (e.g.
`brew install postgresql` / `apt install postgresql`), with a `taxflow`
database and user matching `backend/.env.example`.

```bash
cp backend/.env.example backend/.env        # then set a real SECRET_KEY
cp frontend/.env.local.example frontend/.env.local

cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed_plans              # seeds the 5 billing plan tiers
python -m scripts.seed_demo               # seeds a demo firm/staff/clients/filings (optional, local dev)
uvicorn app.main:app --reload

cd ../frontend
npm install
npm run dev
```

There is no separate worker  process to start — scheduled jobs (deadline
reminders, missing-document escalation, subscription expiry) run inline
from `GET /internal/tasks/heartbeat` when polled, and document OCR runs via
FastAPI `BackgroundTasks` on the same process. See
`app/worker/tasks.py`'s module docstring for the full reasoning.

Backend docs: http://localhost:8000/api/v1/docs
Frontend: http://localhost:3000

See `HANDOFF.md` §1 for first-boot troubleshooting — this has not yet been
run end-to-end in the environment that built it.
