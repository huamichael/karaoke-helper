# Karaoke_Helper

A karaoke app that grades Mandarin pronunciation. The user hears a line of a song, sings it back, sees each word graded, and can click any word to practise saying it.

## Status

Skeleton only. Every source file holds a header describing its purpose; the code is not written yet. Until the kickoff deliverables exist, `docker compose up` starts both containers, but each prints what is missing and waits: the backend for its dependencies and routes, the frontend to be scaffolded.

## Where to look

- [docs/README.md](docs/README.md): index of all documentation.
- [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md): the project as a whole, including the repo layout in section 10.
- [docs/contracts/](docs/contracts/): the agreements between parts.
- [docs/tasks/](docs/tasks/): one task spec per developer.
- [AGENTS.md](AGENTS.md): rules for AI coding agents.

## Running with Docker

You need Docker with Compose (Docker Desktop on macOS and Windows), git, Chrome and an editor. The containers provide Python 3.12, uv, Node 22 and every package.

```bash
docker compose up            # backend on http://localhost:8000, frontend on http://localhost:5173
```

- The repo is mounted into the containers, so edits on your machine reload live. Dependencies added to `backend/pyproject.toml` or `frontend/package.json` are installed on the next start.
- The backend starts with the mock grader. Run `GRADER=real docker compose up` to grade for real. Layer switches work the same way, for example `ENABLE_CTC=1`.
- Model weights download on first use into a Docker volume (about 3 GB) and are kept between runs. The first real grading request needs internet.
- Raise Docker Desktop's memory limit to 8 GB or more before running the real grader.
- The microphone is used by Chrome on your machine, not by the containers.

Useful commands:

| Task | Command |
|---|---|
| Run the backend tests | `docker compose run --rm backend uv run pytest` |
| Run a pipeline script | `docker compose run --rm backend uv run python -m pipeline.build_song ...` |
| Scaffold the frontend, once | `docker compose run --rm frontend npm create vite@latest . -- --template react-ts` |
| Regenerate frontend types | `docker compose run --rm frontend npx openapi-typescript http://backend:8000/openapi.json -o src/api/types.ts` |
| Start again from clean installs | `docker compose down -v` (also deletes the downloaded models) |

Limits of the Docker setup:

- On a Mac the containers run in a Linux VM with no access to the GPU, so Whisper and the CTC model run on the CPU only, slower than natively. `mlx-whisper` does not run in a container at all.
- Your editor does not see the packages installed in the containers. For autocomplete, also install natively, or open the repo in a VS Code Dev Container.
- If file changes do not trigger a reload (most likely with a repo stored on the Windows side of WSL2), set `WATCHFILES_FORCE_POLLING=true` for the backend and enable polling in Vite's `server.watch`.

## Running natively

Needs Python 3.12, [uv](https://docs.astral.sh/uv/) and Node 22 on your machine. The demo machine runs this way (see `docs/PROJECT_PLAN.md`, section 6). Each task spec has a "Running" section with the commands for its part. In short:

```bash
# backend, on http://localhost:8000
cd backend && uv sync && GRADER=mock uv run uvicorn app.main:app --reload --port 8000

# frontend, on http://localhost:5173
cd frontend && npm install && npm run dev
```
