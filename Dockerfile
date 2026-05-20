FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# OS deps: tini for clean signal handling
RUN apt-get update && apt-get install -y --no-install-recommends \
        tini \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root runtime user (matches docker-compose `user: 10001:10001`).
# Using a high, fixed UID keeps host-side bind-mounts in `data/` predictable.
RUN groupadd --system --gid 10001 appuser \
 && useradd  --system --uid 10001 --gid 10001 --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser

WORKDIR /app

# Python deps — installed as root into the global site-packages, then we drop
# privileges. Standard, well-understood pattern.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY app/         /app/app/
COPY tools/       /app/tools/
COPY system_prompts/ /app/system_prompts/
COPY workflows/   /app/workflows/

# Persistent storage for Telethon session + SQLite + Claude CLI auth
RUN mkdir -p /app/data /home/appuser/.claude \
 && chown -R appuser:appuser /app /home/appuser
VOLUME ["/app/data", "/home/appuser/.claude"]

EXPOSE 8000
USER appuser

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "app.supervisor"]
