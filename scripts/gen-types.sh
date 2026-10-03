#!/usr/bin/env bash
# Regenerate the frontend's API types.
#
# Reads the running backend's /openapi.json and writes frontend/src/api/types.ts
# with openapi-typescript. Run it whenever backend/app/schemas.py changes.
#
#   scripts/gen-types.sh                       # backend at $VITE_API_URL or http://localhost:8000
#   scripts/gen-types.sh http://backend:8000   # inside Docker:
#   docker compose run --rm frontend ../scripts/gen-types.sh http://backend:8000
#
# Owner: A. Spec: docs/tasks/frontend.md.
set -euo pipefail

API_URL="${1:-${VITE_API_URL:-http://localhost:8000}}"
FRONTEND="$(cd "$(dirname "${BASH_SOURCE[0]}")/../frontend" && pwd)"
OUT="$FRONTEND/src/api/types.ts"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

cd "$FRONTEND"
npx --no-install openapi-typescript "${API_URL%/}/openapi.json" -o "$TMP"

{
  cat <<'HEADER'
/**
 * GENERATED FILE. Do not edit by hand.
 *
 * TypeScript types for the API (Song, Line, AttemptResult and so on), produced by
 * scripts/gen-types.sh from the backend's OpenAPI output.
 *
 * Owner: A. Spec: docs/contracts/api.md.
 */
HEADER
  cat "$TMP"
} > "$OUT"

echo "Wrote $OUT from ${API_URL%/}/openapi.json"
