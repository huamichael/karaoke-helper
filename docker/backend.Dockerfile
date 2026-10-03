# Backend dev image: Python 3.12 and uv. No source is copied in.
#
# The repo is mounted at /workspace by compose.yaml, and the entrypoint runs
# `uv sync` on every start, so dependencies added to backend/pyproject.toml are
# installed without rebuilding this image.
#
# Owner: B. Docs: README.md, "Running with Docker".

FROM python:3.12-slim-bookworm

# uv, copied from its official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/cache/uv \
    UV_LINK_MODE=copy \
    HF_HOME=/cache/huggingface \
    TORCH_HOME=/cache/torch \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

# compose.yaml runs the container as the host user, so the venv and cache
# volumes must be writable by any user.
RUN mkdir -p /opt/venv /cache && chmod 1777 /opt/venv /cache

COPY backend-entrypoint.sh /usr/local/bin/backend-entrypoint
RUN chmod +x /usr/local/bin/backend-entrypoint

EXPOSE 8000
ENTRYPOINT ["backend-entrypoint"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
