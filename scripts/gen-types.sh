#!/usr/bin/env bash
# Regenerate the frontend's API types.
#
# Reads the running backend's /openapi.json and writes frontend/src/api/types.ts
# with openapi-typescript. Run it whenever backend/app/schemas.py changes.
#
# Owner: A. Spec: docs/tasks/frontend.md.
