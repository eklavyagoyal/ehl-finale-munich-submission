#!/usr/bin/env bash
# Project-local Postgres cluster (no system service): data in backend/.pgdata, port 5433, localhost only.
#   scripts/db.sh init | start | stop | status | psql | reset-test
set -euo pipefail
# Postgres on macOS refuses to start ("postmaster became multithreaded") without a valid locale.
export LC_ALL="${LC_ALL:-en_US.UTF-8}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PGDATA="${PGDATA:-$HERE/.pgdata}"
PORT="${PARALLAX_PGPORT:-5433}"
BIN="${PG_BIN:-$(dirname "$(command -v postgres || echo /opt/homebrew/opt/postgresql@16/bin/postgres)")}"

case "${1:-}" in
  init)
    if [ ! -d "$PGDATA" ]; then
      "$BIN/initdb" -D "$PGDATA" -U parallax --auth=trust --encoding=UTF8 >/dev/null
      echo "listen_addresses = 'localhost'" >> "$PGDATA/postgresql.conf"
    fi
    "$BIN/pg_ctl" -D "$PGDATA" -o "-p $PORT -k /tmp" -l "$PGDATA/server.log" -w start || true
    "$BIN/createdb" -h localhost -p "$PORT" -U parallax parallax 2>/dev/null || true
    "$BIN/createdb" -h localhost -p "$PORT" -U parallax parallax_test 2>/dev/null || true
    echo "Postgres ready on localhost:$PORT (databases: parallax, parallax_test)"
    ;;
  start) "$BIN/pg_ctl" -D "$PGDATA" -o "-p $PORT -k /tmp" -l "$PGDATA/server.log" -w start ;;
  stop) "$BIN/pg_ctl" -D "$PGDATA" -w stop ;;
  status) "$BIN/pg_ctl" -D "$PGDATA" status ;;
  psql) exec "$BIN/psql" -h localhost -p "$PORT" -U parallax "${2:-parallax}" ;;
  reset-test)
    "$BIN/dropdb" -h localhost -p "$PORT" -U parallax --if-exists parallax_test
    "$BIN/createdb" -h localhost -p "$PORT" -U parallax parallax_test
    ;;
  *) echo "usage: $0 init|start|stop|status|psql [db]|reset-test"; exit 1 ;;
esac
