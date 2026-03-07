# 🌱 Microbiome Tracker v2

A family gut microbiome diversity competition app. Track vegetables, fruits, nuts, and spices you eat each week — compete with family, get AI-powered insights, and receive a weekly summary email.

## What's New in v2

- **Real web app** replacing Google Sheets — mobile-friendly, fast, works on any device
- **Smart duplicate detection** — catches exact matches, near-duplicates ("strawberry" vs "strawberries"), and spelling errors
- **Claude AI-powered weekly emails** — personalized praise, gut quips, veggie spotlights, and suggestions
- **Docker deployment** — one container, easy to deploy on AWS App Runner
- **Historical data** — migrated from 2+ years of Google Sheets data

## Quick Start (Local Development)

### 1. Set up environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

The app will be available at `http://localhost:8000`.

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

```bash
docker compose exec app python -m scripts.migrate_from_gsheets /app/data/Microbiome_Optimization__Weekly_Plan.xlsx
```

### 5. Open the app

Go to `http://localhost:8000`, log in with your name and PIN, and start logging plants!

## Running Without Docker

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

uvicorn backend.app.main:app --reload --port 8000
```

## Deploying to AWS App Runner

### Step 1: Push Docker image to ECR

```bash
aws ecr create-repository --repository-name microbiome-tracker --region us-west-2

aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com

docker build -t microbiome-tracker .
docker tag microbiome-tracker:latest <ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/microbiome-tracker:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/microbiome-tracker:latest
```

### Step 2: Create App Runner service

1. **AWS Console → App Runner → Create service**
2. Source: **Container registry → Amazon ECR**, select your image
3. Service settings: Port `8000`, CPU `0.25 vCPU`, Memory `0.5 GB`
4. Add environment variables from `.env.example`
5. Click **Create & deploy**

### Step 3: Point your domain

1. In App Runner → **Custom domains → Link domain**
2. Enter `microbiome.mikengn.com`
3. Add the CNAME records App Runner gives you in your DNS provider
4. Wait for validation

### Step 4: IAM role for SES (recommended)

Create an IAM role with `AmazonSESFullAccess`, attach it as the App Runner **Instance role**, and remove AWS key env vars.

## Architecture

```
Docker Container
├── FastAPI backend
│   ├── /api/auth        — PIN login + JWT
│   ├── /api/entries     — CRUD + dedup + spelling check
│   ├── /api/leaderboard — weekly standings
│   ├── /api/weeks       — week management
│   ├── /api/admin       — user management + test email
│   └── APScheduler      — Saturday 9PM Pacific cron
├── React SPA (static)
├── SQLite (dev) / PostgreSQL (prod)
├── AWS SES (email)
└── Claude API (AI content)
```

## Weekly Email Content (per person)

- 🏆 Leaderboard standings
- Short personalized praise (2-3 sentences)
- 🦠 Gut microbiome quip (1 witty sentence)
- Plant list for the week
- ✨ Veggie spotlight — fun fact + health benefit (cached in DB)
- 💡 Suggestion — try something new or revisit an old favorite
