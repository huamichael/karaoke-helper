# Agent guide

This repository builds Karaoke_Helper, a Mandarin pronunciation-scoring karaoke app. Four developers work in parallel, each owning a separate part.

## Where the specs are

All specifications live in `docs/`. Start at `docs/README.md`.

- `docs/PROJECT_PLAN.md`: the project as a whole.
- `docs/contracts/`: the agreements between parts. These are binding.
- `docs/tasks/`: one task spec per developer.

Ask the developer which task they own, then read that task file. It lists the contracts to read and the files you may edit.

| Task | File |
|---|---|
| A: Frontend | `docs/tasks/frontend.md` |
| B: API and Whisper base | `docs/tasks/backend-api-whisper.md` |
| C: CTC layer and rhythm | `docs/tasks/backend-ctc-rhythm.md` |
| D: Songs and tone | `docs/tasks/backend-songs-tone.md` |

## Rules

1. **Stay in your owner's files.** Each task file has a "What you own" list. Do not edit files outside it. The full ownership map is in `docs/contracts/backend-interfaces.md` section 1.
2. **Contracts are binding.** Match the types and function signatures in `docs/contracts/` exactly. Do not change a contract on your own. If one looks wrong or incomplete, stop and tell the developer.
3. **One syllable structure.** Use the `Syllable` record from `docs/contracts/data-model.md`. Only `to_syllables()` in `backend/app/mandarin.py` creates syllables from text. Do not call pypinyin anywhere else.
4. **One entry per expected syllable.** Any per-syllable list you return has exactly one entry for each expected syllable, in order.
5. **Scoring rules live in one place.** Thresholds and formulas come from `docs/contracts/scoring.md`. Do not invent or duplicate them.
6. **No scoring logic in the frontend.**
7. **Keep documents current.** When behaviour changes, update the matching document in the same commit.
8. **Stay cross-platform.** The team uses Windows (WSL2) and macOS with no NVIDIA GPU. Do not add dependencies that need conda, CUDA, a system ffmpeg, or a cloud service.
