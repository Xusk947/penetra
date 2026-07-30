# Backend: LangGraph agent API server (frontdesk/orchestrator + reports API).
# Runs `langgraph dev` in server mode (no reload) so the custom checkpointer,
# the mounted reports_api (http.app in langgraph.json) and all graphs behave
# exactly like the local setup documented in AGENTS.md.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Docker CLI only (the daemon is the HOST daemon via the mounted
# /var/run/docker.sock) — required by tools/recon/nmap.py and
# tools/sandbox/python.py, which shell out to `docker run`.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
       https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Full source (pyproject.toml, agents/, tools/, db/, services/, langgraph.json,
# checkpointer.py, reports_api.py, cwe_list.csv). `.venv`, `.env`, `data/` and
# `reports/` are excluded via .dockerignore.
COPY . .

# `.[dev]` pulls in langgraph-cli[inmem], which provides the `langgraph dev`
# API server used as the runtime. Playwright chromium is needed by the browser
# tool and the PDF reporter.
RUN pip install ".[dev]" \
    && playwright install --with-deps chromium \
    && touch .env \
    && mkdir -p /app/data /app/reports /app/.langgraph_api

# Persistent state expected to be mounted as volumes by the compose stack:
#   /app/data            -> backend-data (SQLite checkpoints + reports DB)
#   /app/reports         -> backend-reports (markdown/PDF reports + run logs)
#   /app/.langgraph_api  -> backend-langgraph-api (thread/run registry)

EXPOSE 2024

CMD ["langgraph", "dev", "--no-browser", "--no-reload", "--host", "0.0.0.0", "--port", "2024"]
