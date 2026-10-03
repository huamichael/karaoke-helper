#!/usr/bin/env bash
# Backend container start-up.
#
# Installs or updates the Python dependencies from backend/pyproject.toml into
# /opt/venv, then runs the given command (by default uvicorn with --reload).
# If app.main has no `app` yet, uvicorn reports it and keeps watching, so the
# server comes up by itself once the routes are written.
#
# Owner: B.
set -euo pipefail

echo "[backend] uv sync"
uv sync

exec "$@"
