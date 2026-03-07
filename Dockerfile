FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Ensure static directory exists
RUN mkdir -p /app/backend/static

# Environment defaults (override at runtime)
ENV DATABASE_URL=sqlite+aiosqlite:///./data/microbiome.db
ENV SECRET_KEY=change-me-in-production
ENV PIN_SALT=change-me-in-production
ENV AWS_REGION=us-west-2
ENV EMAIL_FROM="Gut Microbiome Weekly <microbiome@mikengn.com>"
ENV EMAIL_TO=microbiome@mikengn.com
ENV ANTHROPIC_API_KEY=""

# Create data directory for SQLite (if used)
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
