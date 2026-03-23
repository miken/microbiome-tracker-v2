"""
Email service — weekly summary email via AWS SES.

Assembles per-person data, calls Claude for content, renders HTML, and sends.
"""
import os
import random
import logging
import datetime
from typing import Optional

import boto3
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models import User, Week, Entry, VeggieBenefitsCache
from ..services.week_service import get_current_week_dates
from ..services import ai_service

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "Gut Microbiome Weekly <microbiome@mikengn.com>")
EMAIL_TO = os.environ.get("EMAIL_TO", "microbiome@mikengn.com")
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")


def _get_ses_client():
    """Create SES client — uses instance role in production, env vars locally."""
    kwargs = {"region_name": AWS_REGION}
    if os.environ.get("AWS_ACCESS_KEY"):
        kwargs["aws_access_key_id"] = os.environ["AWS_ACCESS_KEY"]
        kwargs["aws_secret_access_key"] = os.environ["AWS_SECRET_KEY"]
    return boto3.client("ses", **kwargs)


async def _get_historical_items(db: AsyncSession, user_id: int, current_week_id: int) -> list[str]:
    """Get all distinct normalized item names a user has eaten in prior weeks."""
    result = await db.execute(
        select(Entry.item_name_normalized)
        .where(Entry.user_id == user_id, Entry.week_id != current_week_id)
        .distinct()
    )
    return [row[0] for row in result.all()]


async def _get_or_cache_spotlight(db: AsyncSession, veggie: str) -> dict:
    """Check cache first, call Claude if not cached."""
    result = await db.execute(
        select(VeggieBenefitsCache).where(VeggieBenefitsCache.item_name_normalized == veggie)
    )
    cached = result.scalar_one_or_none()

    if cached and cached.fun_fact:
        return {"fun_fact": cached.fun_fact, "benefit": cached.benefits_html or ""}

    # Call Claude
    spotlight = await ai_service.generate_veggie_spotlight(veggie)

    if cached:
        cached.fun_fact = spotlight.get("fun_fact", "")
        cached.benefits_html = spotlight.get("benefit", "")
    else:
        new_cache = VeggieBenefitsCache(
            item_name_normalized=veggie,
            fun_fact=spotlight.get("fun_fact", ""),
            benefits_html=spotlight.get("benefit", ""),
        )
        db.add(new_cache)
    await db.commit()

    return spotlight


async def assemble_email_data(db: AsyncSession, week_offset: int = 0) -> dict:
    """Build the full email data structure for all active users.
    
    week_offset: 0 = current week, -1 = last week, etc.
    """
    # Get target week
    start_date, end_date = get_current_week_dates()
    if week_offset:
        start_date += datetime.timedelta(weeks=week_offset)
        end_date += datetime.timedelta(weeks=week_offset)
    week_result = await db.execute(select(Week).where(Week.start_date == start_date))
    week = week_result.scalar_one_or_none()

    if not week:
        logger.warning("No active week found — skipping email")
        return {}

    # Get all active users
    users_result = await db.execute(select(User).where(User.is_active == True))
    users = list(users_result.scalars().all())
    random.shuffle(users)

    persons = []
    for user in users:
        person = {"name": user.name}

        # Get their entries for this week
        entries_result = await db.execute(
            select(Entry)
            .where(Entry.user_id == user.id, Entry.week_id == week.id)
            .order_by(Entry.created_at)
        )
        entries = list(entries_result.scalars().all())
        count = len(entries)
        person["veggie_count"] = count

        if count > 0:
            item_names = [e.item_name for e in entries]
            normalized_names = [e.item_name_normalized for e in entries]

            person["veggie_list"] = ", ".join(item_names)
            person["praise"] = await ai_service.generate_person_praise(user.name, count, item_names)
            person["gut_quip"] = await ai_service.generate_gut_quip(user.name, count)

            # Veggie spotlight
            picked = random.choice(normalized_names)
            person["picked_veggie"] = picked
            spotlight = await _get_or_cache_spotlight(db, picked)
            person["fun_fact"] = spotlight.get("fun_fact", "")
            person["benefit"] = spotlight.get("benefit", "")

            # Suggestion
            historical = await _get_historical_items(db, user.id, week.id)
            person["suggestion"] = await ai_service.generate_suggestion(
                user.name, normalized_names, historical
            )
        else:
            person["praise"] = await ai_service.generate_no_veggies_encouragement(user.name)
            person["gut_quip"] = ""
            person["picked_veggie"] = ""
            person["fun_fact"] = ""
            person["benefit"] = ""
            person["suggestion"] = ""
            person["veggie_list"] = ""

        persons.append(person)

    # Sort by count descending for leaderboard in email
    persons_sorted = sorted(persons, key=lambda p: p["veggie_count"], reverse=True)
    for i, p in enumerate(persons_sorted):
        p["rank"] = i + 1

    return {
        "persons": persons,
        "leaderboard": persons_sorted,
        "week_label": f"{start_date.strftime('%-m/%-d')} – {end_date.strftime('%-m/%-d')}",
    }


def render_email_html(email_data: dict) -> str:
    """Render the Jinja2 HTML email template."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    template = env.get_template("weekly_summary.html")
    return template.render(**email_data)


async def send_weekly_summary(week_offset: int = 0):
    """Main entry point — called by the scheduler every Saturday."""
    logger.info("Starting weekly summary email generation...")

    # Determine which week we're targeting
    start_date, end_date = get_current_week_dates()
    if week_offset:
        start_date += datetime.timedelta(weeks=week_offset)
        end_date += datetime.timedelta(weeks=week_offset)

    # Check if email was already sent for this week (prevents double-sends)
    async with async_session() as db:
        week_result = await db.execute(select(Week).where(Week.start_date == start_date))
        week = week_result.scalar_one_or_none()
        if week and week.email_sent_at:
            logger.info(f"Email already sent for week {start_date} at {week.email_sent_at} — skipping")
            return

    async with async_session() as db:
        email_data = await assemble_email_data(db, week_offset=week_offset)

    if not email_data:
        logger.warning("No email data — skipping send")
        return

    html_content = render_email_html(email_data)
    week_label = email_data["week_label"]

    ses = _get_ses_client()
    try:
        response = ses.send_email(
            Destination={"ToAddresses": [EMAIL_TO]},
            Message={
                "Body": {"Html": {"Charset": "UTF-8", "Data": html_content}},
                "Subject": {
                    "Charset": "UTF-8",
                    "Data": f"Weekly Gut Microbiome Digest – {week_label} Summary",
                },
            },
            Source=EMAIL_FROM,
        )
        logger.info(f"Email sent! MessageId: {response['MessageId']}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise

    # Stamp the week as sent
    async with async_session() as db:
        week_result = await db.execute(select(Week).where(Week.start_date == start_date))
        week = week_result.scalar_one_or_none()
        if week:
            week.email_sent_at = datetime.datetime.utcnow()
            await db.commit()
            logger.info(f"Marked week {start_date} email_sent_at = {week.email_sent_at}")


async def check_and_send_missed_email():
    """Startup catch-up: if the most recent completed week's email never sent, send it now.

    Called once during app startup (lifespan). The email_sent_at guard inside
    send_weekly_summary prevents double-sends if the scheduler also fires.
    """
    today = get_current_week_dates()[0]  # start of current week (Sunday)
    prev_week_start = today - datetime.timedelta(weeks=1)

    async with async_session() as db:
        result = await db.execute(select(Week).where(Week.start_date == prev_week_start))
        prev_week = result.scalar_one_or_none()

    if not prev_week:
        logger.info("Startup catch-up: no previous week row — nothing to recover")
        return

    if prev_week.email_sent_at:
        logger.info(f"Startup catch-up: previous week ({prev_week_start}) email already sent at {prev_week.email_sent_at}")
        return

    # Email was never sent for last week — send it now
    logger.warning(f"Startup catch-up: previous week ({prev_week_start}) email was never sent — sending now")
    await send_weekly_summary(week_offset=-1)
