# Karaoke_Helper

A karaoke app that grades Mandarin pronunciation. The user hears a line of a song, sings it back, sees each word graded, and can click any word to practise saying it.

## Status

Skeleton only. Every source file holds a header describing its purpose; the code is not written yet.

## Where to look

- [docs/README.md](docs/README.md): index of all documentation.
- [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md): the project as a whole, including the repo layout in section 10.
- [docs/contracts/](docs/contracts/): the agreements between parts.
- [docs/tasks/](docs/tasks/): one task spec per developer.
- [AGENTS.md](AGENTS.md): rules for AI coding agents.

## Running

Each task spec has a "Running" section with the commands for its part. In short, once the kickoff deliverables exist:

```bash
# backend, on http://localhost:8000
cd backend && uv sync && GRADER=mock uv run uvicorn app.main:app --reload --port 8000

# frontend, on http://localhost:5173
cd frontend && npm install && npm run dev
```
