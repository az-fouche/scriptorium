# syntax=docker/dockerfile:1

FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for scientific stack and SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsqlite3-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY webapp/requirements.txt ./webapp-requirements.txt
COPY config/requirements.txt ./indexer-requirements.txt

# Install only what the webapp needs for runtime by default; indexer deps are optional
RUN pip install -r webapp-requirements.txt

# Copy project
COPY . .

# Ensure database path exists (mounted or baked)
RUN mkdir -p webapp/databases && \
    if [ -f webapp/databases/books.db ]; then echo "DB present"; else echo "No DB bundled"; fi

# Expose Flask default port
EXPOSE 5000

# Environment defaults for production
ENV FLASK_DEBUG=false \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5000 \
    SECRET_KEY=change-me

# Start with Gunicorn
CMD ["gunicorn", "webapp.wsgi:application", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120"]


