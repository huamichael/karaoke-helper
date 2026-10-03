#!/usr/bin/env bash
# Frontend container start-up.
#
# With arguments, runs them (for example `npm create vite@latest`).
# Without arguments: if frontend/package.json exists, installs packages and starts
# the Vite dev server on 0.0.0.0:5173. If it does not exist yet, prints how to
# scaffold the project and waits, so the container stays usable.
#
# Owner: B (repo tooling).
set -euo pipefail

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

if [ ! -f package.json ]; then
  echo "[frontend] frontend/package.json does not exist yet."
  echo "[frontend] Scaffold it once with:"
  echo "[frontend]   docker compose run --rm frontend npm create vite@latest . -- --template react-ts"
  echo "[frontend] then restart: docker compose restart frontend"
  exec sleep infinity
fi

echo "[frontend] npm install"
if [ -f package-lock.json ]; then npm ci; else npm install; fi

exec npm run dev -- --host 0.0.0.0 --port 5173
