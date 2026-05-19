FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# OS deps: tini for clean signal handling
RUN apt-get update && apt-get install -y --no-install-recommends \
        tini \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY app/         /app/app/
COPY tools/       /app/tools/
COPY system_prompts/ /app/system_prompts/
COPY workflows/   /app/workflows/

# Persistent storage for Telethon session + SQLite + Claude CLI auth
VOLUME ["/app/data", "/root/.claude"]

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "app.supervisor"]
