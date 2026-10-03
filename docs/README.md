# Karaoke_Helper documentation

Start here. This folder is the single source of truth for the project. Every document has one topic, and no topic is specified in two places.

## Map

| File | What it holds | Read it when |
|---|---|---|
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | The project as a whole: product, decisions, design agreements, architecture, tech stack, roadmap, risks | Once, before anything else |
| [contracts/api.md](contracts/api.md) | The HTTP contract between frontend and backend | You send or serve a request |
| [contracts/data-model.md](contracts/data-model.md) | The syllable record and the song bundle that every part shares | You produce or consume syllables or `song.json` |
| [contracts/backend-interfaces.md](contracts/backend-interfaces.md) | Module ownership, the functions between the three backend tasks, layer switches, integration schedule | You work on the backend |
| [contracts/scoring.md](contracts/scoring.md) | Formulas, thresholds, how each layer scores, feedback codes | You compute or explain a score |
| [tasks/frontend.md](tasks/frontend.md) | Task A: the user interface | You are A |
| [design/ui.md](design/ui.md) | The frontend's visual design and interaction details, with prototype screenshots. The clickable prototype is in `frontend/prototype/` | You are A, or you prepare the demo |
| [tasks/backend-api-whisper.md](tasks/backend-api-whisper.md) | Task B: the API and the Whisper base | You are B |
| [tasks/backend-ctc-rhythm.md](tasks/backend-ctc-rhythm.md) | Task C: the CTC layer and rhythm | You are C |
| [tasks/backend-songs-tone.md](tasks/backend-songs-tone.md) | Task D: the song pipeline and tone | You are D |
| [recording-session.md](recording-session.md) | How to record the test recordings: checklist, prompts, file names | You record test audio |

## Reading order

Everyone reads sections 1, 2 and 4 of the plan. After that, open your task file. It lists exactly which contracts you need and in what order.

## Which document wins

- **A data shape or a function signature:** the contract wins over a task file and over the plan.
- **A score, threshold or formula:** `contracts/scoring.md`.
- **Scope, order and timing:** `PROJECT_PLAN.md`.
- **How the frontend looks and moves:** `design/ui.md`. It yields to `tasks/frontend.md` and the contracts on behaviour and data.
- **Once code exists:** `backend/app/schemas.py` is the contracts in executable form. If the code and a contract disagree, that is a bug. Fix whichever is wrong and make them agree in the same commit.

## Changing a contract

1. Say what you want to change in the team chat, and name the owners it affects.
2. Edit the contract file first.
3. Change the code in the same commit.

Adding a field needs no approval. Renaming or removing something needs a yes from everyone who uses it.

## Working with AI agents

- Point the agent at your task file. It names everything else the agent must read.
- Tell the agent which files you own. The list is under "What you own" in your task file, and the full map is in `contracts/backend-interfaces.md` section 1.
- An agent must not edit another owner's files or anything in `docs/contracts/`. If it thinks a contract is wrong, it stops and tells you.
- When behaviour changes, the agent updates the matching document in the same commit.
- [AGENTS.md](../AGENTS.md) at the repo root states these rules for agents directly.
