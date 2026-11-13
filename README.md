# AI customer support

## Dashboard

A React + shadcn/ui dashboard (tickets, events, knowledge base) served by FastAPI under HTTP Basic auth.
Set `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` in `.env`; the API returns 503 until a password is set.

Local development (two terminals):

```sh
POLLER_ENABLED=false uv run fastapi dev app/main.py   # API on :8000
cd dashboard && npm install && npm run dev            # UI on :5173, proxies /api to :8000
```

To serve the built dashboard from FastAPI: `cd dashboard && npm run build`, then open http://localhost:8000.

Knowledge base edits made in the dashboard apply to the next email. Running
`scripts/seed_knowledge_base.py` overwrites them with the markdown files.

## Docker

One container runs the web app, the dashboard and the Gmail poller (on a background thread).

```sh
docker compose up --build          # or: docker build -t ai-support . && docker run --env-file .env -p 8000:8000 ai-support
```

Secrets come from environment variables only; `.env` and `credentials.json` are excluded from the image.
Run exactly one container with `POLLER_ENABLED=true`, otherwise several pollers compete for the same inbox.

## Deploying to Railway

`railway.json` pins one replica in the EU region, never sleeps, and health-checks `/health`.

```sh
railway login
railway init --name ai-customer-support   # once
railway up                                # build and deploy this folder
railway domain                            # once: get a https://*.up.railway.app address
```

Set the variables from `.env` in the Railway service (Variables tab or `railway variables --set`).
Stop any local poller once the Railway one is running.
