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
    p.add_argument("--url", required=True, help="backend base URL, e.g. https://parallax-api.dehlwes.net")
    p.add_argument("--token", default=os.environ.get("PARALLAX_REMOTE_TOKEN"), help="bearer token (or PARALLAX_REMOTE_TOKEN)")
    p.add_argument("--actor", default="pm:cli")
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
        uvicorn.run("parallax.api.app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")),
                    proxy_headers=True, forwarded_allow_ips="*")
        return 0
    if args.command == "push-research":
        import httpx

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
