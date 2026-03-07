"""
Claude AI service — generates personalized email content.

Replaces OpenAI with the Anthropic Claude API for:
- Short personalized praise per person
- Gut microbiome quips
- Veggie spotlight with fun facts
- Suggestions to try new items or revisit old favorites
"""
import os
import logging
import json
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"


async def call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    """Make an async call to the Claude API."""
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — returning placeholder")
        return "[AI content placeholder — set ANTHROPIC_API_KEY]"

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


SYSTEM_PROMPT = """You are the friendly, witty narrator of a family gut microbiome competition.
Three family members — Mike, Julie, and Wika — track how many different vegetables, fruits,
nuts, and spices they eat each week. Your tone is warm, playful, and encouraging — like a
fun nutritionist friend who also loves puns. Keep responses concise and punchy.
Never use markdown formatting — no asterisks, no bold, no bullet points. Plain text only."""


async def generate_person_praise(name: str, count: int, veggie_list: list[str]) -> str:
    """Generate a short (2-3 sentence) personalized praise for the person's week."""
    prompt = f"""{name} ate {count} different plants this week: {', '.join(veggie_list)}.
Write 2-3 short, fun sentences praising their gut microbiome diversity this week.
Be specific — reference 1-2 items from their list. No bullet points, just flowing text."""
    return await call_claude(SYSTEM_PROMPT, prompt, max_tokens=200)


async def generate_gut_quip(name: str, count: int) -> str:
    """Generate a fun one-liner about their gut flora status."""
    prompt = f"""{name} ate {count} different plants this week.
Write ONE witty sentence about how their gut microbiome is doing right now.
Think: fun metaphor or personification of gut bacteria. Keep it under 25 words."""
    return await call_claude(SYSTEM_PROMPT, prompt, max_tokens=80)


async def generate_veggie_spotlight(veggie: str) -> dict:
    """Generate a fun fact and brief benefit for a specific veggie/fruit/spice."""
    prompt = f"""For the plant/spice "{veggie}", provide:
1. One surprising or fun fact (1 sentence)
2. One key health benefit for gut microbiome (1 sentence)

Respond in JSON format: {{"fun_fact": "...", "benefit": "..."}}
No markdown, just raw JSON."""
    
    text = await call_claude(SYSTEM_PROMPT, prompt, max_tokens=200)
    try:
        # Try to parse JSON from the response
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        return {"fun_fact": f"{veggie.title()} is a great addition to your diet!", "benefit": "Supports gut diversity."}


async def generate_suggestion(
    name: str,
    current_week_items: list[str],
    historical_items: list[str],
) -> str:
    """Suggest something new to try, or something they haven't eaten in a while."""
    recent_set = set(current_week_items)
    old_favorites = [item for item in historical_items if item not in recent_set]
    old_sample = old_favorites[:20] if old_favorites else []

    prompt = f"""{name} ate these plants this week: {', '.join(current_week_items)}.
In past weeks, they also used to eat: {', '.join(old_sample) if old_sample else 'not much historical data yet'}.

Write 1-2 short sentences either:
- Suggesting a NEW plant they haven't tried, explaining why it pairs well with what they already eat, OR
- Encouraging them to revisit something from their past list they haven't had in a while.

Be specific and practical. No bullet points."""
    return await call_claude(SYSTEM_PROMPT, prompt, max_tokens=150)


async def generate_no_veggies_encouragement(name: str) -> str:
    """Generate encouragement for someone who didn't log any veggies this week."""
    prompt = f"""{name} didn't log any plants this week.
Write 2 short, gentle, encouraging sentences motivating them to try some veggies next week.
Be warm, not judgmental. Maybe joke that their gut bacteria are sending an SOS."""
    return await call_claude(SYSTEM_PROMPT, prompt, max_tokens=150)
