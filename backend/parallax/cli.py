"""Command line: `python -m parallax.cli <command>`.

  db-init                 create/upgrade the schema (alembic upgrade head)
  ingest PATH             import research batches (or --packet context.json)
  themes                  recompute theme signals
  seed                    sync personas/departments from roster JSON, register worker agents
  draft                   AI drafts requirements from the strongest themes
  simulate REQ [REQ...]   run Parallax for up to N requirements (waits and prints the result)
  validate [AGENT...]     validate personas against held-out study data
  models                  list models available to the configured key
  serve                   start the API (uvicorn)
  serve-prod              container entrypoint: migrate, sync agents, serve on 0.0.0.0:$PORT
  push-research PATH      zip a research folder and upload it to a deployed backend
  smoke [--full]          check a deployed backend end to end (token from PARALLAX_REMOTE_TOKEN in .env)
"""

import argparse
import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path

from parallax.config import BACKEND_ROOT, get_settings


def _db_init() -> None:
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    from parallax.db import session_scope
    from parallax.policy import active_policy

    with session_scope() as session:
        active_policy(session)
    print("schema up to date")


def _model_check() -> dict:
    """Startup diagnostic for the logs: are the configured model names available to this key?"""
    settings = get_settings()
    configured = sorted({settings.model_fast, settings.model_strong, *settings.judge_models, settings.embedding_model})
    if settings.llm_mode != "openai":
        return {"mode": settings.llm_mode, "configured": configured}
    try:
        from parallax.llm.client import get_llm

        available = set(get_llm().list_models())
    except Exception as error:  # never block startup on a diagnostic
        return {"mode": "openai", "error": repr(error)[:500]}
    return {"mode": "openai", "configured": configured, "missing": [m for m in configured if m not in available],
            "available_gpt": sorted(m for m in available if m.startswith(("gpt-", "o")) and "realtime" not in m)[:60]}


def _smoke(url: str, token: str | None, actor: str, full: bool) -> int:
    """The frontend's critical path against a deployed backend. Prints PASS/FAIL per step, never the token."""
    import httpx

    base = url.rstrip("/")
    headers = {"X-Actor": actor, **({"Authorization": f"Bearer {token}"} if token else {})}
    client = httpx.Client(base_url=base, headers=headers, timeout=60)
    failures = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)

    r = httpx.get(f"{base}/api/health", timeout=20)
    check("health (open)", r.status_code == 200, str(r.status_code))
    check("auth enforced", httpx.get(f"{base}/api/meta", timeout=20).status_code == 401)
    check("openapi public", httpx.get(f"{base}/api/openapi.json", timeout=20).status_code == 200)
    meta = client.get("/api/meta")
    check("meta with token", meta.status_code == 200, f"{meta.status_code}" + (" (set PARALLAX_REMOTE_TOKEN in backend/.env)" if meta.status_code == 401 else ""))
    if meta.status_code != 200:
        return 1
    m = meta.json()
    print(f"      llm_mode={m['llm_mode']} engine={m['persona_engine']} counts={m['counts']}")
    models = client.get("/api/llm/models").json()
    check("models available", not models.get("missing") and not models.get("error"), str(models.get("missing") or models.get("error") or ""))
    personas = client.get("/api/agents", params={"kind": "market_persona"}).json()
    departments = client.get("/api/agents", params={"kind": "department"}).json()
    check("roster", len([a for a in personas if a["active"]]) == 12 and len([a for a in departments if a["active"]]) >= 6,
          f"{len(personas)} personas, {len(departments)} departments")
    for path in ("/api/tasks", "/api/requirements", "/api/coverage", "/api/audit", "/api/learning/decisions", "/api/themes"):
        r = client.get(path)
        check(f"GET {path}", r.status_code == 200, str(r.status_code))
    reqs = client.get("/api/requirements").json()
    if reqs:
        detail = client.get(f"/api/requirements/{reqs[0]['id']}")
        check("requirement detail", detail.status_code == 200 and "scores" in detail.json(), reqs[0]["id"])
    else:
        print("      no requirements yet (ingest data, build themes, draft)")
    if full and reqs:
        run = client.post("/api/simulations", json={"requirement_ids": [reqs[0]["id"]]}).json()
        print(f"      run {run['id']} started", flush=True)
        status = "queued"
        for _ in range(240):
            status = client.get(f"/api/simulations/{run['id']}").json()["run"]["status"]
            if status not in ("queued", "running"):
                break
            time.sleep(5)
        check("simulation", status == "completed", status)
        results = client.get(f"/api/simulations/{run['id']}/results").json()["requirements"][reqs[0]["id"]]
        check("simulation outputs", bool(results["persona_responses"] and results["department_memos"] and results["recommendation"]),
              f"{len(results['persona_responses'])} persona, {len(results['department_memos'])} dept, "
              f"{len(results['votes'])} votes")
    print(f"{'OK' if not failures else str(failures) + ' FAILED'}  {base}")
    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="parallax", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("db-init")
    p = sub.add_parser("ingest")
    p.add_argument("path", type=Path)
    p.add_argument("--packet", action="store_true", help="PATH is a context.json packet")
    p.add_argument("--research-root", type=Path, default=None)
    p = sub.add_parser("themes")
    p.add_argument("--include-examples", action="store_true")
    p.add_argument("--include-pending-claims", action="store_true")
    sub.add_parser("seed")
    p = sub.add_parser("draft")
    p.add_argument("--market", default=None)
    p.add_argument("--limit", type=int, default=5)
    p = sub.add_parser("simulate")
    p.add_argument("requirement_ids", nargs="+")
    p.add_argument("--challenge", default=None)
    p.add_argument("--engine", choices=["tinytroupe", "direct"], default=None)
    p = sub.add_parser("validate")
    p.add_argument("agent_ids", nargs="*")
    p.add_argument("--include-examples", action="store_true")
    sub.add_parser("models")
    p = sub.add_parser("serve")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--reload", action="store_true")
    sub.add_parser("serve-prod")
    p = sub.add_parser("push-research")
    p.add_argument("path", type=Path, help="research folder with schema.json, catalog/, decision-model.json, batches/")
    p.add_argument("--url", default=None, help="backend base URL (default PARALLAX_REMOTE_URL)")
    p.add_argument("--token", default=None, help="bearer token (default PARALLAX_REMOTE_TOKEN from .env)")
    p.add_argument("--actor", default="pm:cli")
    p = sub.add_parser("smoke")
    p.add_argument("--url", default=None)
    p.add_argument("--full", action="store_true", help="also run one simulation (real LLM cost in openai mode)")
    p.add_argument("--actor", default="pm:smoke")
    args = parser.parse_args(argv)
    settings = get_settings()
    actor = "system:cli"

    if args.command == "db-init":
        _db_init()
        return 0
    if args.command == "serve":
        import uvicorn

        uvicorn.run("parallax.api.app:app", host=args.host, port=args.port, reload=args.reload)
        return 0
    if args.command == "serve-prod":
        import uvicorn

        from parallax.agents.roster import seed_agents
        from parallax.db import session_scope

        _db_init()
        with session_scope() as session:
            print(json.dumps({"agents": seed_agents(session, "system:startup")}), flush=True)
        print(json.dumps({"llm_check": _model_check()}), flush=True)
        uvicorn.run("parallax.api.app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")),
                    proxy_headers=True, forwarded_allow_ips="*")
        return 0
    if args.command == "smoke":
        return _smoke(args.url or settings.remote_url, settings.remote_token, args.actor, args.full)
    if args.command == "push-research":
        import httpx

        args.url = args.url or settings.remote_url
        args.token = args.token or settings.remote_token
        root = args.path.resolve()
        if not (root / "schema.json").exists():
            print(f"{root} has no schema.json", file=sys.stderr)
            return 1
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in root.rglob("*"):
                if path.is_file() and (path.suffix in (".json", ".jsonl")) and "outputs" not in path.parts:
                    zf.write(path, Path("research") / path.relative_to(root))
        headers = {"X-Actor": args.actor}
        if args.token:
            headers["Authorization"] = f"Bearer {args.token}"
        response = httpx.post(f"{args.url.rstrip('/')}/api/ingest/upload", headers=headers, timeout=600,
                              files={"file": ("research.zip", buffer.getvalue(), "application/zip")})
        print(response.status_code, response.text[:2000])
        return 0 if response.is_success else 1
    if args.command == "models":
        from parallax.llm.client import get_llm

        print("\n".join(get_llm().list_models()))
        return 0

    from parallax.db import session_scope

    if args.command == "ingest":
        from parallax import ingest

        with session_scope() as session:
            run = (ingest.import_packet(session, args.path, actor) if args.packet else
                   ingest.import_batches(session, args.path, args.research_root or settings.research_root, actor))
            print(json.dumps(run.counts, indent=2))
        return 0
    if args.command == "themes":
        from parallax.themes import build_themes

        with session_scope() as session:
            print(json.dumps(build_themes(session, target_model=settings.target_model, include_examples=args.include_examples,
                                          allow_unreviewed_for_llm=settings.allow_unreviewed_evidence_for_llm,
                                          include_pending_claims=args.include_pending_claims), indent=2))
        return 0
    if args.command == "seed":
        from parallax.agents.roster import seed_agents

        with session_scope() as session:
            print(json.dumps(seed_agents(session, actor), indent=2))
        return 0
    if args.command == "draft":
        from parallax.agents.drafter import draft_requirements
        from parallax.llm.client import get_llm
        from parallax.themes import latest_snapshot_id

        with session_scope() as session:
            snapshot = latest_snapshot_id(session, settings.target_model)
            if snapshot is None:
                print("no theme snapshot; run `themes` first", file=sys.stderr)
                return 1
            print(json.dumps(draft_requirements(session, get_llm(), target_model=settings.target_model, snapshot_id=snapshot,
                                                market=args.market, limit=args.limit, actor_id=actor), indent=2, default=str))
        return 0
    if args.command in ("simulate", "validate"):
        from parallax.models import SimRun
        from parallax.orchestrator import create_run, execute, execute_validation

        with session_scope() as session:
            if args.command == "simulate":
                run = create_run(session, requirement_ids=args.requirement_ids, actor_id=actor, challenge=args.challenge,
                                 options={"persona_engine": args.engine} if args.engine else {})
            else:
                run = create_run(session, requirement_ids=[], actor_id=actor, kind="validation",
                                 options={"agent_ids": args.agent_ids or None, "include_examples": args.include_examples})
            run_id = run.id
        started = time.time()
        (execute if args.command == "simulate" else execute_validation)(run_id)
        with session_scope() as session:
            run = session.get(SimRun, run_id)
            print(json.dumps({"run_id": str(run.id), "status": run.status, "error": run.error, "progress": run.progress,
                              "llm_calls": run.llm_calls, "seconds": round(time.time() - started, 1)}, indent=2, default=str))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
