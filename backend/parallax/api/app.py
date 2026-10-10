"""FastAPI application. Run: `uvicorn parallax.api.app:app --reload --port 8000`."""

import hmac

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from parallax import __version__
from parallax.api.common import ACTOR_PATTERN
from parallax.api.routers import agents, evidence, governance, requirements, simulations
from parallax.audit import record_event
from parallax.config import get_settings
from parallax.db import get_engine, session_scope

# Everything public lives under /api so the app can share one host with the frontend (frontend "/", API "/api").
UNLOGGED_PREFIXES = ("/api/health", "/api/docs", "/api/openapi.json")
OPEN_PREFIXES = ("/api/health", "/api/docs", "/api/openapi.json")

app = FastAPI(
    title="Parallax API",
    version=__version__,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    description=(
        "Backend for Parallax, a multi-agent decision workflow for BMW successor-vehicle requirements. "
        "Send `X-Actor: pm:<name>` with every request; human-only actions require a `pm:` actor."
    ),
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health", include_in_schema=False)
def health():
    """Readiness probe for nexus: 200 only when the database answers."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("select 1"))
    except Exception:
        return JSONResponse({"status": "starting"}, status_code=503)
    return {"status": "ok", "version": __version__}


@app.middleware("http")
async def access_log(request: Request, call_next):
    """The brief asks for access events in the audit trail, not only changes."""
    response = await call_next(request)
    path = request.url.path
    if request.method != "OPTIONS" and path.startswith("/api") and not path.startswith(UNLOGGED_PREFIXES):
        who = request.headers.get("x-actor") or "pm:anonymous"
        if not ACTOR_PATTERN.match(who):
            who = "user:invalid-actor"

        def write() -> None:
            with session_scope() as session:
                record_event(session, category="access", actor_id=who, action=f"{request.method} {path}",
                             entity_type="http", entity_id=path[:240],
                             meta={"status": response.status_code, "query": str(request.url.query)[:500]})

        try:
            await run_in_threadpool(write)
        except Exception:
            pass  # never fail a request because access logging failed
    return response


@app.middleware("http")
async def bearer_auth(request: Request, call_next):
    """Registered last, so it runs first: unauthenticated calls are rejected (and still access-logged)."""
    settings = get_settings()
    accepted = [t for t in (settings.api_token, settings.cli_token) if t]
    path = request.url.path
    if accepted and request.method != "OPTIONS" and path.startswith("/api") and not path.startswith(OPEN_PREFIXES):
        supplied = request.headers.get("authorization", "").encode()
        ok = False
        for token in accepted:  # constant-time compare against every accepted credential
            ok |= hmac.compare_digest(supplied, f"Bearer {token}".encode())
        if not ok:
            return JSONResponse({"detail": "missing or invalid bearer token"}, status_code=401)
    return await call_next(request)


for module in (governance, evidence, requirements, simulations, agents):
    app.include_router(module.router)
