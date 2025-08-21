# Build stage
FROM python:3.12-slim-bookworm as builder

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -b /usr/local/bin && \
    uv add --user --no-build -r uv.lock

# Runtime stage
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=web/app.py \
    FLASK_ENV=production \
    PATH="/home/appuser/.local/bin:${PATH}"

RUN useradd -m appuser
WORKDIR /app

COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

USER appuser

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--worker-class", "gevent", "web.app:app"]
