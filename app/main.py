import asyncio
import logging
import secrets
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from app import db
from app.config import settings

logger = logging.getLogger("app")
DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "dist"


def start_poller() -> None:
    """Run the Gmail poller on its own thread with its own event loop.

    The poller makes blocking Gmail and database calls, so sharing the web server's loop would
    stall the dashboard while an email is processed. One loop for the poller's whole life also
    keeps the cached model client working (see app/poller.py).
    """
    from app.poller import run

    threading.Thread(target=asyncio.run, args=(run(),), name="poller", daemon=True).start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.poller_enabled:
        start_poller()
    else:
        logger.info("Poller disabled (POLLER_ENABLED=false)")
    yield


app = FastAPI(title="AI customer support", lifespan=lifespan)
basic = HTTPBasic()


def require_login(credentials: HTTPBasicCredentials = Depends(basic)) -> None:
    if not settings.dashboard_password:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Set DASHBOARD_PASSWORD to use the dashboard")
    user_ok = secrets.compare_digest(credentials.username.encode(), settings.dashboard_username.encode())
    password_ok = secrets.compare_digest(credentials.password.encode(), settings.dashboard_password.encode())
    if not (user_ok and password_ok):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Wrong username or password", headers={"WWW-Authenticate": "Basic"}
        )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


api = APIRouter(prefix="/api", dependencies=[Depends(require_login)])


@api.get("/summary")
def summary() -> dict:
    return db.summary()


@api.get("/events")
def events(status: Literal["processing", "processed", "skipped", "failed"] | None = None, limit: int = 100):
    return db.list_events(status, min(limit, 500))


@api.get("/tickets")
def tickets(status: Literal["open", "answered", "escalated"] | None = None, limit: int = 100):
    return db.list_tickets(status, min(limit, 500))


@api.get("/tickets/{ticket_id}")
def ticket(ticket_id: int):
    found = db.get_ticket(ticket_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return found


@api.get("/knowledge-base")
def knowledge_base():
    return db.list_knowledge_base()


class KnowledgeBaseUpdate(BaseModel):
    content: str


@api.put("/knowledge-base/{entry_id}")
def update_knowledge_base(entry_id: int, body: KnowledgeBaseUpdate):
    if not body.content.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Content cannot be empty")
    updated = db.update_knowledge_base(entry_id, body.content.strip())
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entry not found")
    # The classifier caches the product lists; drop the cache so edits apply to the next email.
    from app.ai.classifier import product_reference

    product_reference.cache_clear()
    return updated


app.include_router(api)


@app.get("/{path:path}", include_in_schema=False, dependencies=[Depends(require_login)])
def dashboard(path: str):
    """Serve the built React app. Unknown paths get index.html so client-side links work."""
    if path.startswith("api/"):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    index = DASHBOARD_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dashboard not built. Run: cd dashboard && npm run build")
    file = (DASHBOARD_DIR / path).resolve()
    if path and file.is_file() and file.is_relative_to(DASHBOARD_DIR):
        return FileResponse(file)
    return FileResponse(index)
