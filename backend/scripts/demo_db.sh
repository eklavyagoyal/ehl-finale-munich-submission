#!/usr/bin/env bash
# Builds the `parallax_demo` database for frontend work: synthetic fixtures only (texts start with
# "SYNTHETIC"/"EXAMPLE"), mock LLM, one finished Parallax run. Built only through the CLI, so the
# audit trail is clean. Serve it with:  scripts/demo_db.sh serve   (http://127.0.0.1:8001)
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"
BIN="${PG_BIN:-/opt/homebrew/opt/postgresql@16/bin}"
export PARALLAX_DATABASE_URL="postgresql+psycopg://parallax@localhost:5433/parallax_demo"
export PARALLAX_LLM_MODE=mock PARALLAX_PERSONA_ENGINE=direct PARALLAX_ALLOW_UNREVIEWED_EVIDENCE_FOR_LLM=true
export PARALLAX_RESEARCH_ROOT="$HERE/tests/fixtures/research"
PY="$HERE/.venv/bin/python"

if [ "${1:-build}" = "serve" ]; then
  exec "$PY" -m parallax.cli serve --port "${2:-8001}"
fi

"$BIN/dropdb" -h localhost -p 5433 -U parallax --if-exists parallax_demo
"$BIN/createdb" -h localhost -p 5433 -U parallax parallax_demo
"$PY" -m parallax.cli db-init
"$PY" -m parallax.cli seed >/dev/null
"$PY" -m parallax.cli ingest "$HERE/tests/fixtures/batches" >/dev/null
"$PY" -m parallax.cli themes --include-examples --include-pending-claims >/dev/null
"$PY" -m parallax.cli draft --market US --limit 4 >/dev/null
"$PY" -m parallax.cli simulate REQ-G60-0001 REQ-G60-0002 REQ-G60-0003
echo "parallax_demo ready. Serve: scripts/demo_db.sh serve"
