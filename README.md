# TaxFlow — Accounting & Tax Firm Automation Platform

Work-in-progress full-stack scaffold: Next.js (App Router, TypeScript,
Tailwind) frontend + FastAPI (Python 3.12, SQLAlchemy 2.0, PostgreSQL,
Celery/Redis) backend. Runs directly on locally installed services — no
Docker required.

**Start here: [`HANDOFF.md`](./HANDOFF.md)** — a detailed status report and
ordered task list for continuing this build. It covers what's implemented,
what's stubbed, known issues to fix, and the design system already in use.

## Quick start

Prerequisites: PostgreSQL 16 and Redis 7 installed and running locally
(e.g. `brew install postgresql redis` / `apt install postgresql redis-server`),
with a `taxflow` database and user matching `backend/.env.example`.

```bash
cp backend/.env.example backend/.env        # then set a real SECRET_KEY
cp frontend/.env.local.example frontend/.env.local

cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic revision --autogenerate -m "initial schema" && alembic upgrade head
python -m scripts.seed_plans              # seeds the 5 billing plan tiers
python -m scripts.seed_demo               # seeds a demo firm/staff/clients/filings (optional, local dev)
uvicorn app.main:app --reload &

celery -A app.worker.celery_app worker --loglevel=info &
celery -A app.worker.celery_app beat --loglevel=info &

cd ../frontend
npm install
npm run dev
```

Backend docs: http://localhost:8000/api/v1/docs
Frontend: http://localhost:3000

See `HANDOFF.md` §1 for first-boot troubleshooting — this has not yet been
run end-to-end in the environment that built it.
