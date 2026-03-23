"""
Microbiome Tracker v2 — Main FastAPI Application
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .database import engine, Base, get_db
from .routers import auth, entries, weeks, admin, leaderboard
from .services.email_service import send_weekly_summary, check_and_send_missed_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and start scheduler
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Schedule weekly email: Saturday 9 PM Pacific (US/Pacific = UTC-8 or UTC-7)
    scheduler.add_job(
        send_weekly_summary,
        CronTrigger(day_of_week="sat", hour=21, minute=0, timezone="US/Pacific"),
        id="weekly_summary_email",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.start()
    logger.info("Scheduler started — weekly email set for Saturday 9 PM Pacific")

    # Startup catch-up: if last week's email never sent, send it now
    try:
        await check_and_send_missed_email()
    except Exception as e:
        logger.error(f"Startup catch-up failed: {e}")

    yield
    
    # Shutdown
    scheduler.shutdown()
    await engine.dispose()


app = FastAPI(
    title="Microbiome Tracker",
    description="Family gut microbiome diversity tracker",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow the React frontend in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(entries.router, prefix="/api/entries", tags=["entries"])
app.include_router(weeks.router, prefix="/api/weeks", tags=["weeks"])
app.include_router(leaderboard.router, prefix="/api/leaderboard", tags=["leaderboard"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# Serve static files (built React app) — mounted last so API routes take priority
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
