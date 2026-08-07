# NEXT-PROMPT.md — Continue From: the "onboard a client" frontend gap
# (Add Client → Create Filing → Create/Edit/Delete Task → Engagement
# Letter button) is now built across all four phases — code-only,
# unverified, at the requester's explicit instruction to proceed
# code-only in a sandbox with no network/Postgres access rather than
# stopping after Phase 1 — see HANDOFF.md UPDATE 30 for the full
# breakdown. Don't rebuild any of: `GET /users/pending-clients` (new
# endpoint, resolves an accepted client invite to a `user_id` for
# `POST /clients`), `components/dashboard/add-client-modal.tsx`,
# `admin/clients/[id]/page.tsx` (new client overview page — didn't exist
# before), `components/dashboard/new-filing-modal.tsx`,
# `components/dashboard/task-modal.tsx` (create+edit+delete, wired into
# the board), or the engagement-letter button on the client overview
# page. Verify with a live server first, in this order: `alembic upgrade
# head` + `uvicorn`, hit `GET /users/pending-clients` directly; `npm
# install` + `npm run build` (none of the five touched/added `.tsx`
# files have been type-checked); then a full browser click-through
# (invite a client → accept → complete profile → new filing → confirm it
# shows on /admin/calendar → new/edit/delete a task on the board →
# generate + download an engagement letter). No test coverage was added
# for any of it — same "§2g still open" gap prior passes already flagged.
# Next genuinely-not-started gap once this is verified: a "pending client
# invites" list isn't a persistent page section (folded into the Add
# Client modal instead — fine as built, but revisit if product wants it
# more visible), and there's still no way to revoke a sent invite from
# the UI.


# Previously continued from: firm-invoicing module built (code-only,
# unverified, verification explicitly out of scope — see HANDOFF.md UPDATE
# 25). §5's Invoice model, invoice_service/repository, /invoices endpoints,
# and real reports.summary revenue are done — don't rebuild. Verify with a
# live server first (alembic upgrade head, uvicorn, a real create→send→
# mark-paid round trip, then npm run build + browser check of the revenue
# card on /admin/reports). Next gaps: a staff-facing /admin/invoices
# create/list UI (only the reports page consumes the new endpoints so
# far), then the compliance-risk engine and real pytest tests (still zero).

# Previously continued from: reports/analytics page built (code-only,
# unverified — see HANDOFF.md UPDATE 24). `GET /reports/summary` (§2f) had
# no frontend consumer; that gap is now closed — don't rebuild. Verify with
# a live server first (npm run build, log in as staff, load /admin/reports,
# confirm the chart and table match seeded data). Document review panel and
# calendar are still genuinely not started — those are the next frontend
# gaps.

# Previously continued from: settings page built (code-only,
# unverified — see HANDOFF.md UPDATE 23). Was the last genuinely-not-started
# frontend gap noted at the top of this file; that gap is now closed —
# don't rebuild. Covers profile display, a link into forgot-password for
# password changes, and full 2FA setup/enable/disable UI. Verify with a
# live server first (log in, load /settings, run a real 2FA enroll +
# disable round-trip against a real authenticator app or `pyotp` script).

# Previously continued from: messaging UI + password reset UI built
# (code-only, unverified — see HANDOFF.md UPDATE 22). Both backend modules
# (§2d messages, §0u password reset) existed with no frontend consumer;
# that gap is now closed on both — don't rebuild. Verify with a live
# server first (a real message round-trip between a client and their
# accountant; a real password-reset round-trip end to end). Settings page
# is still genuinely not started, that's the next frontend gap.

# Previously continued from: frontend notification bell built
# (code-only, unverified — see HANDOFF.md UPDATE 21). Backend notifications
# module (§2c) existed with no frontend consumer; that gap is closed —
# don't rebuild. Messaging UI (§2d's consumer) is still genuinely not
# started, that's the next frontend gap. Verify with a live server first
# (npm run build, log in, seed a notification row, confirm the bell badge
# count and mark-read/mark-all-read both hit the real endpoints).

# Previously continued from: engagement letter generation + demo seed
# script built (code-only, unverified — see HANDOFF.md UPDATE 20). Two
# section-5-deferred gaps closed: don't rebuild either; verify with a live
# server first (POST the engagement-letter endpoint for a real client and
# confirm the PDF downloads; run `python -m scripts.seed_demo` against a
# live DB).

# Previously continued from: task-assignee client-role validation +
# TOTP two-factor auth built (code-only, unverified — see HANDOFF.md
# UPDATE 19). POST /firms + stricter /auth/login rate limit from UPDATE 18
# also still just code-only/unverified. Billing/Migrations/Seed still
# Verified Live; WhatsApp Signing still Unverified; Landing Page and Filing
# Timeline are actually built (see repo), despite older notes below.

## Latest pass: task-assignee client-role validation (`task_service.py`)
and TOTP two-factor auth (`pyotp`: `/auth/2fa/setup|enable|disable` +
login enforcement) are now built — see `HANDOFF.md` UPDATE 19. Code-only,
not live-verified: run `alembic upgrade head` / `uvicorn` and confirm (a)
assigning a task to a client-role user gets 400, (b) a full 2FA round-trip
(setup → enable → login requires code → disable) behaves as described.
Don't rebuild either.

## Latest pass: `POST /firms` (+ list/get, super_admin only) and a stricter
`5/minute` limit on `/auth/login` are now built — see `HANDOFF.md` UPDATE 18.
Code-only, not live-verified: run `alembic upgrade head` / `uvicorn` and
confirm (a) a non-super_admin gets 403 from `/firms`, (b) a 6th rapid login
attempt within a minute gets 429. Don't rebuild either.

## Previous pass: OCR pipeline (`process_document_ocr`) and password reset
endpoints built, code-only, not live-verified — see `HANDOFF.md` §0u. Don't
rebuild; verify with a live server + real `tesseract-ocr` binary + a real
uploaded document, and a real SMTP send, before trusting.

The previous pass (see `HANDOFF.md` UPDATE 13 and §0l) was told to run
verification only, then was **explicitly stopped on request** before
starting any coding task — read §0l in full before touching any of this.
Short version:

1. **Migrations, `seed_plans.py`, and the whole billing/subscription
   module are now live-verified** — fresh Postgres, real `uvicorn`, real
   HTTP requests, all passing. Don't re-verify these from scratch; see §0l
   for the exact checks already run and their results (22/22 and 21/21
   passed, zero bugs found).
2. **The WhatsApp webhook signature check is still open** — only
   `WHATSAPP_APP_SECRET`/`WHATSAPP_VERIFY_TOKEN` were set locally and the
   server restarted; no request was ever sent. This is the fastest
   remaining verification item.
3. **The landing page (§3a) and the stamped filing-history timeline are
   completely untouched** — still exactly the state §0k described (four
   orphaned landing files, `app/page.tsx` unedited; filing timeline not
   started at all). Nothing from this pass changed that.

Read, in this order, before writing any code:

1. **`HANDOFF.md`** — read the whole thing. §0l (this pass) and §0k (the
   pass before it) are the two to read most carefully together — §0l only
   covers verification, §0k covers what's actually built-but-inert on the
   frontend. Every other numbered section is unchanged from before.
2. **`STRATEGY_REVIEW.md`** — unchanged, still the source of truth for
   prioritization.

---

## Latest pass: `reports.router` (§2f) and `automation.router` (§2e reminder
CRUD + derived escalation status only) built, code-only, not live-verified —
see `HANDOFF.md` §0s. Both were previously "not started" (the only two
routers still commented out in `app/api/v1/router.py`); don't rebuild,
verify with a live server first (same `alembic upgrade head` / `uvicorn` /
real HTTP request pattern as §0d/§0l/§0r). Still open within §2e:
`dispatch_due_reminders` / `escalate_overdue_document_requests` in
`app/worker/tasks.py` are still `TODO` stubs, not wired to
`NotificationChannelSender` — that's the next automation task, not a redo.

## Latest pass: `dispatch_due_reminders` and `escalate_overdue_document_requests`
in `app/worker/tasks.py` (§2e's remaining gap) are now implemented, code-only,
not live-verified — see `HANDOFF.md` UPDATE 17. Don't rebuild; verify with a
real Celery worker + seeded `Reminder`/overdue-checklist data first.

## Previous pass: Notifications module (§2c) + Messages module (§2d) built,
code-only, not live-verified — see `HANDOFF.md` §0r. Both were previously
"not started"; don't rebuild, verify with a live server first (same
`alembic upgrade head` / `uvicorn` / real HTTP request pattern as §0d/§0l).

## What NOT to redo

- **Migrations / `seed_plans.py` / billing module** (§0l) — genuinely
  live-verified this pass. Don't re-run `alembic upgrade head` from
  scratch or re-write `verify_billing_flow.py`; it exists at
  `backend/verify_billing_flow.py` and passed 21/21. Re-run it only if you
  change billing code.
- **Everything §0a–§0j already covered** — still true, see each lettered
  subsection for live-verified vs. code-reviewed-only status.
- **The four landing-page files and `seed_plans.py` itself** (§0k) — exist,
  don't redo them, see item 2 below for what's actually left.

## What's built but genuinely unverified — verify before trusting, don't rebuild

**1. WhatsApp webhook signature verification (§0i part 1) — closest to
done, finish this first.** `WHATSAPP_APP_SECRET` support in
`verify_signature()` is written; what's missing is actually exercising it:
set `WHATSAPP_APP_SECRET`/`WHATSAPP_VERIFY_TOKEN` in a local `.env` (not
shipped — delete before packaging, same as every prior pass), boot
`uvicorn`, and write `verify_whatsapp_flow.py` (follows
`verify_firm_scoping.py`/`verify_billing_flow.py`'s PASS/FAIL pattern):
- Correctly HMAC-SHA256-signed POST body → 200.
- Wrong-signature POST → 403, rejected **before** payload parsing.
- Missing `X-Hub-Signature-256` header → 403 (once the secret is set —
  confirm the no-op-with-warning fallback still applies when it's unset,
  per §0h/§0i's design).
- The `GET` handshake: correct `hub.verify_token` → 200 + echoed
  `hub.challenge`; wrong token → 403.

**2. Full webhook processing flow (§0h)** — still entirely unverified
beyond signing. Once signing is confirmed, POST a synthetic Meta-shaped
payload and confirm: a seeded client's phone number matches correctly, an
unmatched phone number produces an `UNMATCHED` row without raising, and a
document is actually created via `DocumentService.register_document`.

**3. §0j's frontend work (client portal, accountant dashboard, client
table, Kanban board, error boundary)** — still the fastest remaining
frontend checkpoint once you get to frontend verification: `npm install`,
`npm run build`, then a real browser session (register/login as seeded
users, exercise search/pagination/drag-drop, force an error).

**5. The landing page (§3a) is now built (see `HANDOFF.md` §0n) —
`personas.tsx`, `pricing.tsx`, `faq.tsx`, `footer.tsx` added and
`app/page.tsx` wired up. Code-only, same `npm install`/`npm run
build`/browser caveat as everything else in this list — verify before
trusting, don't rebuild.**

**4. `verify_dashboard_flow.py` still doesn't exist** — the natural script
for item 3 above.

## What to build this pass, in priority order

### Must build before launch (in this order)
1. **If your pass is allowed to run verification/tests:** finish the
   WhatsApp signing check (item 1 above) first — it's the smallest
   remaining gap and the env/server setup is already halfway done.
2. **Finish the landing page (§3a) — this is the actual next coding task,
   not a fresh start, and is untouched by this pass.** In order:
   - Read `components/ui/stamp-seal.tsx`, `components/landing/hero.tsx`,
     `components/landing/features.tsx`, and
     `components/landing/how-it-works.tsx` first — they're written, don't
     redo them, just pick up from them. Re-read them once yourself before
     trusting them — their own "sanity check" was a crude bracket-balance
     script, not a real TypeScript check, and that still hasn't changed.
   - Build the three missing sections: `components/landing/personas.tsx`
     (the `#testimonials` anchor `components/landing/navbar.tsx` already
     links to — build as honest persona/segment cards, not fabricated
     customer quotes, per §0k's note on why), a pricing section (static
     copy matching the five tiers `seed_plans.py` seeds — now confirmed
     live-correct per §0l, so the copy can trust those exact numbers), and
     an FAQ section (a plain `useState`-based disclosure — no radix
     accordion, same reasoning as before).
   - Add a simple footer.
   - Only then edit `app/page.tsx` itself: import `Navbar` (already
     exists, unused) + `Hero` + `Features` + `HowItWorks` + the three new
     sections + the footer, replacing the `create-next-app` default for
     real. Don't consider §3a done until this happens.
3. **The stamped filing-history timeline (§3d, §4) — now built, see
   `HANDOFF.md` §0m.** `components/dashboard/filing-timeline.tsx` exists
   and is wired into `app/(dashboard)/dashboard/page.tsx` (expand a filing
   row). Built code-only, no `npm install`/`npm run build`/browser session
   run — verify that before trusting it, don't rebuild it from scratch.

### Should build in first 6 months (only after the above is real and verified)
- ~~Billing/invoicing + payments module for the firm's own clients (§5 —
  distinct from the subscription billing verified in §0l, don't
  conflate).~~ Built, code-only — see `HANDOFF.md` UPDATE 25. No payment
  gateway (manual mark-paid only, by design) and no staff-facing
  create/list UI yet — that UI is the remaining gap, not the backend.
- The compliance-risk engine (`STRATEGY_REVIEW.md` Phase 5 idea #2).
- ~~Notifications, messaging, automation-center reminder delivery (HANDOFF
  §2c–§2e) — generalize `NotificationChannelSender` (built for WhatsApp) to
  cover email/SMS too.~~ `EmailSender` built §0p, `SMSSender` (Twilio) built
  this pass, code-only — see `HANDOFF.md` §0q. Both channel senders now
  exist. Not yet wired into any reminder/automation dispatch (that system
  doesn't exist yet either — that's the remaining gap, not the senders).
  Neither verified against a real SMTP server / Twilio account.
- ~~Document upload UI on the client portal (react-dropzone, still not
  installed) and the checklist view driven by §2a's backend work.~~ Built
  this pass, code-only — see `HANDOFF.md` §0p. `react-dropzone` added to
  `package.json` but `npm install` not run. Verify with a real
  `npm install`/`npm run build`/browser session (drop a file, confirm the
  S3 PUT and `POST /documents` both succeed, confirm checklist re-fetches)
  before trusting it.
- ~~A Celery task to expire subscriptions past `current_period_end` /
  actually cancel `cancel_at_period_end` subscriptions on schedule.~~ Built
  this pass, code-only — see `HANDOFF.md` §0o. Verify against a real
  Postgres/Redis/Celery worker before trusting it.
- Tests (HANDOFF §2g) — still zero real `pytest` tests exist anywhere
  (the `verify_*.py` scripts are live-request smoke checks, not a test
  suite).

### Nice to have — do not pull forward
AI document-review diffing, client health/revenue-leakage scoring, deeper
partner analytics — same reasoning as before, these need real customer
usage data.

### Ignore completely
Global/multi-country expansion, vague "predictive analytics" framing,
Docker/infra migrations, white-label/enterprise tier work, wiring up an
actual payment gateway without asking first, adding `@dnd-kit/core` to the
Kanban board without confirming the install works in your environment,
adding a radix-based accordion for the FAQ section instead of a plain
`useState` disclosure — unchanged from before.

---

## The rule this project has followed so far — keep following it

Same three things, every pass, in order: (1) verify claims live if your
environment and instructions allow it, or say plainly if they don't; (2)
write down every bug found and fixed, in the same terse §0-lettered-
subsection style; (3) update `HANDOFF.md` with a new UPDATE note and
lettered subsection, then **zip the entire project and return it** — don't
hand back a diff or a partial tree.

This pass (the one that produced `HANDOFF.md` §0l) was told to run
verification only and was then explicitly stopped on request before
starting any coding task — not a session limit, not a natural checkpoint.
That's a legitimate reason to stop, and the honest thing to write down is
exactly what got verified (migrations, seed script, the whole billing
module — all live, all passing) versus what's still just "set up but not
run" (WhatsApp signing) versus what's completely untouched (landing page,
filing timeline). If you're told to stop early too, do the same.
