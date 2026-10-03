#!/usr/bin/env bash
# Backend container start-up.
#
# Installs or updates the Python dependencies from backend/pyproject.toml into
# /opt/venv, then runs the given command (by default uvicorn with --reload).
# If that command is not installed yet, it prints what to do and waits, so the
# container stays usable. If app.main has no `app` yet, uvicorn reports it and
# keeps watching, so the server comes up by itself once the routes are written.
#
# Owner: B.
set -euo pipefail

echo "[backend] uv sync"
uv sync

if ! command -v "$1" >/dev/null 2>&1; then
  echo "[backend] '$1' is not installed yet. Add it to backend/pyproject.toml"
  echo "[backend] (task B's kickoff deliverable), then: docker compose restart backend"
  exec sleep infinity
fi

exec "$@"
