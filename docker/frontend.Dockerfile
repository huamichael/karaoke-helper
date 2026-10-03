# Frontend dev image: Node 22. No source is copied in.
#
# The repo is mounted at /workspace by compose.yaml, and the entrypoint installs
# packages from frontend/package.json on every start, then runs the Vite dev
# server.
#
# Owner: B (repo tooling); the frontend itself belongs to A. Docs: README.md, "Running with Docker".

FROM node:22-bookworm-slim

COPY frontend-entrypoint.sh /usr/local/bin/frontend-entrypoint
RUN chmod +x /usr/local/bin/frontend-entrypoint

EXPOSE 5173
ENTRYPOINT ["frontend-entrypoint"]
