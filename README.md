# 🌱 Microbiome Tracker v2

A family gut microbiome diversity competition app. Track vegetables, fruits, nuts, and spices you eat each week — compete with family, get AI-powered insights, and receive a weekly summary email.

## Recent Changes

### Weekly email reliability fixes & recovery endpoint

Three issues caused the Saturday 9 PM weekly summary email to fail silently on Fly.io, plus a new automatic recovery mechanism:

1. **Stale DB connections** — Neon PostgreSQL closes idle connections after ~5 minutes. When APScheduler fired the weekly job, the connection pool handed out a dead connection. Fix: `pool_pre_ping=True` on the SQLAlchemy engine (`database.py`), which tests each connection before use and reconnects transparently.

2. **Cold-start misfire** — Fly.io scales to zero when idle. If the container wasn't warm at exactly 9:00 PM Pacific, APScheduler considered the job misfired and silently skipped it. Fix: `misfire_grace_time=300` (5-minute window) on the scheduler job (`main.py`), so the job still fires if the app starts within 5 minutes of the scheduled time.

3. **No recovery path** — When the cron missed, there was no way to send last week's email after the fact. Fix: new `POST /api/admin/send-previous-week-email` endpoint that calls `send_weekly_summary(week_offset=-1)`. The `assemble_email_data` function now accepts a `week_offset` parameter to target any past week.

4. **Startup catch-up** — If the scheduled email fails for any reason (cold start outlasts the grace period, app crash, Fly outage), the next time the app starts (e.g., someone visits on Sunday), it checks whether last week's email was sent and fires it automatically if not. This uses a new `email_sent_at` column on the `Week` model, which also serves as a duplicate-send guard — `send_weekly_summary` checks it before sending and stamps it after success, so the email can never be sent twice for the same week.

Tests added: `week_offset` targeting (3), `email_sent_at` duplicate guard (2), startup catch-up (3), scheduler/DB config guards (3), endpoint integration (4) — 15 new tests total.

### Refactoring (schemas, item_service, email tests)

- **Pydantic v2 `ConfigDict`** — replaced deprecated `class Config: from_attributes = True` inner class with `model_config = ConfigDict(from_attributes=True)` in `EntryResponse`, `WeekResponse`, and `UserResponse`. Silences Pydantic v2 deprecation warnings and is forward-compatible with Pydantic v3.
- **`CANONICAL_MAPPINGS` split into named sub-dicts** (`item_service.py`) — the single flat 100-line dict is now five named dicts (`_REGIONAL_NAMES`, `_ALTERNATE_SPELLINGS`, `_COMMON_TYPOS`, `_BRITISH_EUROPEAN`, `_POLISH_NAMES`) merged into `CANONICAL_MAPPINGS`. Behaviour is unchanged; new synonyms can now be added to the correct category at a glance.
- **Email service test coverage** — added `tests/test_email_service.py` with 11 tests covering `assemble_email_data` (structure, per-person content, leaderboard ordering), `_get_or_cache_spotlight` (cache hit / miss), and `render_email_html` (template output). All AI calls are mocked; no API keys needed.

### Week label format & drawer UX improvements (`index.html`)

- **Human-readable week label:** The header now shows e.g. "Week of March 8th – 14th" instead of ISO dates. Same-month weeks omit the month on the end date; cross-month weeks spell out both (e.g. "March 29th – April 4th"); cross-year weeks include both years (e.g. "December 29th, 2025 – January 4th, 2026").
- **Most-recently-entered first:** Plants are now sorted by entry ID descending in both the logged-in user's own list and other users' drawers, so the newest additions appear at the top.
- **Swipe-to-close with animation:** The drawer now responds to a downward swipe gesture (≥ 80 px) to dismiss it. Closing (via swipe or tapping the overlay) plays a `slideDown`/`fadeOut` animation before the element is removed, matching native sheet behaviour.

### Item normalization improvements (`item_service.py`)

- **Display names are now always lowercase.** Previously, `get_display_name` could return user-typed capitalisation (e.g. "Blueberries"). Now it always returns the lowercase canonical form (e.g. "blueberries"), keeping the database consistent.
- **Accented character overrides.** `_DISPLAY_OVERRIDES` restores accents regardless of how the user typed the item. Supported: `jalapeño`, `açaí`, `yerba maté`, `frisée`, `mâche`. Both paths are covered — typing the accented form (via `CANONICAL_MAPPINGS`) and typing the plain ASCII form (direct override lookup).
- **Expanded canonical mappings** — 30+ new entries in two categories:
  - *British English / European:* courgette → zucchini, beetroot → beet, rocket → arugula, mangetout → snow pea, cos → romaine, sharon fruit → persimmon, clementine / satsuma → mandarin, bok choi → bok choy, capsicum → bell pepper, topinambur → jerusalem artichoke, feldsalat / mâche → mache, and more.
  - *Polish names / spellings:* rukola → arugula, cukinia → zucchini, burak → beet, kolendra → coriander, rozmaryn → rosemary, borowka / borówka → blueberry, malina → raspberry, kalafior → cauliflower, brokoli → broccoli, koliander → coriander.
  - *Curcuma variants:* curcuma / cúrcuma / kurkuma → turmeric (French, Spanish, German/Polish).
- **New `KNOWN_ITEMS`:** fava bean, snow pea, mandarin, jerusalem artichoke, mache, yerba mate, frisee.

### Production database cleanup (`scripts/merge_plant_names.py`)

Ran against the Neon PostgreSQL database to backfill the above fixes onto historical data:
- 7,382 `item_name` entries lowercased
- 853 entries remapped to their canonical form
- 16 duplicate entries removed
- 4 jalapeño display overrides applied

### Mobile layout fix

Fixed iOS Safari right-edge overflow. Root cause was a combination of missing `overflow-x: hidden` on `html`/`body` and a missing `min-width: 0` on the autocomplete flex item (the long input placeholder was preventing the flex container from shrinking to fit the viewport).

### Test suite

Grew from 56 → 78 tests. Added `test_normalize_maps_british_english`, `test_normalize_maps_polish_names`, extended display-override coverage, and spelling-warning checks for all new mapped variants.

## Stack

| Layer | Local dev | Production |
|-------|-----------|------------|
| Runtime | Docker Compose | Fly.io (shared-cpu-1x, 256 MB) |
| Database | SQLite (named volume) | Neon (free PostgreSQL) |
| Email | AWS SES | AWS SES |
| AI | Anthropic Claude API | Anthropic Claude API |
| Domain | localhost:8000 | microbiome.mikengn.com |

## Quick Start (Local Development)

### 1. Set up environment

```bash
cp .env.example .env
# Edit .env — only ANTHROPIC_API_KEY is required for local dev
# AWS keys are optional (email won't send without them)
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

The app will be available at `http://localhost:8000`. SQLite is created automatically inside a Docker named volume (`app-data`) — no DB setup needed.

### 3. Create initial users

```bash
curl -X POST http://localhost:8000/api/admin/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Mike", "pin": "1234", "gender": "male"}'

curl -X POST http://localhost:8000/api/admin/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Julie", "pin": "1234", "gender": "female"}'

curl -X POST http://localhost:8000/api/admin/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Wika", "pin": "1234", "gender": "female"}'
```

### 4. Import historical data (optional)

Copy the Excel file into the Docker volume first, then run the migration:

```bash
docker cp /path/to/Microbiome_Optimization__Weekly_Plan.xlsx \
  $(docker compose ps -q app):/app/data/

docker compose exec app python -m scripts.migrate_from_gsheets \
  /app/data/Microbiome_Optimization__Weekly_Plan.xlsx
```

### 5. Open the app

Go to `http://localhost:8000`, log in with your name and PIN, and start logging plants!

## Running Tests

Tests use an in-memory SQLite database — no Docker, no API keys required.

### Install test dependencies

```bash
pip install -r requirements-test.txt
```

### Run all tests

```bash
python3 -m pytest
```

### Run a specific file

```bash
python3 -m pytest tests/test_api.py
python3 -m pytest tests/test_items.py
python3 -m pytest tests/test_auth.py
python3 -m pytest tests/test_weeks.py
```

### Verbose output

```bash
python3 -m pytest -v
```

The suite covers 104 tests across five areas:
- **test_auth** — PIN hashing, JWT creation/decoding, login endpoint
- **test_items** — item normalization, spelling suggestions, near-duplicate detection
- **test_weeks** — week boundary calculation (Sunday–Saturday)
- **test_api** — full HTTP integration tests for all endpoints
- **test_email_service** — email data assembly, spotlight caching, HTML rendering, `week_offset` targeting, `send_weekly_summary` passthrough, and scheduler/DB config guards (AI calls mocked)

## Running Without Docker

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

uvicorn backend.app.main:app --reload --port 8000
```

## Production Deployment (Fly.io + Neon)

### Overview

- **Fly.io** hosts the Docker container at `microbiome.mikengn.com`
- **Neon** provides free serverless PostgreSQL
- Deploys automatically on `fly deploy`; scales to zero when idle (cold start ~2–4s)

### Deploy a new version

```bash
fly deploy
```

That's it — Fly builds the Docker image and does a rolling deploy.

### Environment / secrets

All secrets are stored in Fly (not in `.env`). To view or update them:

```bash
fly secrets list
fly secrets set KEY=value
```

Required secrets:

| Secret | Description |
|--------|-------------|
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key (random hex, never change after launch) |
| `PIN_SALT` | PIN hashing salt (random hex, never change after launch) |
| `ANTHROPIC_API_KEY` | Claude API key for AI email content |
| `AWS_ACCESS_KEY` | AWS SES sending (optional if using IAM role) |
| `AWS_SECRET_KEY` | AWS SES sending (optional if using IAM role) |
| `AWS_REGION` | e.g. `us-west-2` |
| `EMAIL_FROM` | Sender address shown in emails |
| `EMAIL_TO` | Recipient address for weekly summary |

> ⚠️ **Never rotate `SECRET_KEY` or `PIN_SALT` in production.** Doing so invalidates all existing JWTs (users get logged out) and breaks all stored PIN hashes (users can't log in).

### Custom domain

The domain is managed in Squarespace DNS with a CNAME pointing to Fly's endpoint. To re-verify or add a new domain:

```bash
fly certs add microbiome.mikengn.com
# Follow the DNS instructions Fly prints
```

### SSH into the production container

```bash
fly ssh console
```

### View production logs

```bash
fly logs
```

## Admin Scripts

These scripts run against whichever database `DATABASE_URL` points to. Run them locally for Neon, or via `fly ssh console` inside the container.

### Migrate historical data from Google Sheets export

```bash
# Against local SQLite (Docker):
docker compose exec app python -m scripts.migrate_from_gsheets /app/data/file.xlsx

# Against Neon (locally — requires asyncpg installed):
DATABASE_URL="postgresql://..." python3 -m scripts.migrate_from_gsheets /path/to/file.xlsx
```

The Excel export from Google Sheets strips `/` from sheet names (e.g. "Plants - 3/1" → "Plants - 31"). The script handles date resolution automatically using B1 cell validation.

### Change a user's PIN

There is no in-app PIN change UI. Use this script:

```bash
# Via fly ssh console (recommended — secrets already loaded):
fly ssh console
python3 -m scripts.set_pin Julie newpin
python3 -m scripts.set_pin Mike newpin
python3 -m scripts.set_pin Wika newpin
exit

# Or locally against Neon:
DATABASE_URL="postgresql://..." PIN_SALT="..." python3 -m scripts.set_pin Julie newpin
```

## Architecture

```
Fly.io Container
├── FastAPI backend
│   ├── /api/auth        — PIN login + JWT (90-day tokens)
│   ├── /api/entries     — CRUD + exact/near-duplicate + spelling check
│   ├── /api/leaderboard — weekly standings for all users
│   ├── /api/weeks       — week management (Sunday–Saturday)
│   ├── /api/admin       — user management + trigger test email
│   └── APScheduler      — Saturday 9 PM Pacific weekly email (+ startup catch-up)
├── React SPA (single static index.html, served by FastAPI)
├── SQLite (local dev) / Neon PostgreSQL (production)
├── AWS SES (outbound email)
└── Anthropic Claude API (AI-generated email content)
```

### Key design decisions

- **Weeks run Sunday–Saturday** to match the original Google Sheets cadence
- **Item normalization** lowercases, strips punctuation, singularizes plurals, and applies canonical mappings (regional names, British English, Polish) before dedup checks; accented characters (jalapeño, açaí, mâche, etc.) are restored via display overrides
- **Near-duplicate threshold** is SequenceMatcher ratio ≥ 0.80; users can override with `?force=true`
- **JWT tokens** are 90-day for convenience (family app, not a security product)
- **AI email content** is cached per veggie in `veggie_benefits_cache` table to avoid redundant API calls
- **`SECRET_KEY` and `PIN_SALT`** are fixed at first deploy — rotating either breaks all user sessions and stored hashes

## Weekly Email Content (per person)

- 🏆 Leaderboard standings
- Short personalized praise (2–3 sentences, AI-generated)
- 🦠 Gut microbiome quip (1 witty sentence, AI-generated)
- Plant list for the week
- ✨ Veggie spotlight — fun fact + health benefit (AI-generated, cached)
- 💡 Suggestion — try something new or revisit an old favourite

To trigger a test email without waiting for Saturday:

```bash
# Get a token first
TOKEN=$(curl -s -X POST https://microbiome.mikengn.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"name":"Mike","pin":"yourpin"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Send current week's email (test)
curl -X POST https://microbiome.mikengn.com/api/admin/send-test-email \
  -H "Authorization: Bearer $TOKEN"

# Send PREVIOUS week's email (recovery after a missed cron)
curl -X POST https://microbiome.mikengn.com/api/admin/send-previous-week-email \
  -H "Authorization: Bearer $TOKEN"
```
