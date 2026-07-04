FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install git (required for repository checkout/analysis) and other utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY scripts ./scripts
COPY main.py ./main.py

RUN pip install --no-cache-dir .

# Create cache directory for git worktrees
RUN mkdir -p /app/.archon_cache/worktrees

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]