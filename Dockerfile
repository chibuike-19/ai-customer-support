# Stage 1: build the React dashboard.
FROM node:22-alpine AS dashboard
WORKDIR /dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci
COPY dashboard/ ./
RUN npm run build

# Stage 2: the Python app, which serves the API, the built dashboard, and runs the poller.
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.7.8 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app

# Install dependencies first so code changes don't reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app/ app/
COPY knowledge_base/ knowledge_base/
COPY scripts/seed_knowledge_base.py scripts/
COPY --from=dashboard /dashboard/dist dashboard/dist

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
# Hosts like Railway, Render and Cloud Run set $PORT; default to 8000.
# One worker only: each worker would start its own poller.
CMD ["sh", "-c", "fastapi run app/main.py --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
