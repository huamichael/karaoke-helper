# Karaoke_Helper: Project Plan

**Status:** final spec, revision 5, 3 October 2026. Nothing is built yet.

This file describes the project as a whole. The agreements between parts and the per-developer task specs live beside it; [README.md](README.md) is the index.

What changed in revision 5:

- The documentation moved into `docs/`, split into this plan, four contracts and four task specs.
- A new section 4 names every design agreement, who it binds and where it is specified.
- The backend is split into three independent tasks with exact function boundaries ([contracts/backend-interfaces.md](contracts/backend-interfaces.md)).
- One syllable structure is now used by both song processing and user-input processing ([contracts/data-model.md](contracts/data-model.md)).
- The API contract, scoring rules and user interface moved out of this file into their own documents. The decisions in them are unchanged.

## 1. What we are building

Karaoke_Helper turns Mandarin songs into pronunciation exercises.

1. The user picks a song and a mode: **spoken accuracy** or **singing accuracy**.
2. The app plays one line of the song and shows it in Hanzi and Pinyin.
3. The user sings the line back unaccompanied while the app records. This is the same in both modes.
4. The backend grades the recording. The app shows each word of the line as a coloured chip, with a few overall scores.
5. The user can click any word to open **Word practice**: they hear the word spoken normally, say it themselves without melody, and get a grade for how they said it.
6. They retry the line or move to the next one.

A polished version of this loop on two songs beats a half-working system for arbitrary songs.

### The two modes

The user performs the same way in both. The modes differ in how deeply the recording is graded.

- **Spoken-accuracy mode** asks whether the right words came out. It uses the Whisper base layer. This is the MVP.
- **Singing-accuracy mode** adds the CTC layer on top of Whisper. It grades each sound more finely and scores the user's rhythm against the original singer.

### What each one judges

| | Spoken-accuracy mode | Singing-accuracy mode | Word practice |
|---|---|---|---|
| Unit | One line | One line | One word |
| The user | Sings the line after hearing it | Sings the line after hearing it | Says the word normally |
| Grading layers | Whisper base | Whisper base + CTC | Whisper base; CTC boundaries for tone |
| Initials and finals | Yes: match, near-match or mismatch | Yes, on a continuous scale | Yes |
| Rhythm | No | Yes, from stage 3 | No |
| Lexical tone | No | No | Yes, from stage 3 |
| Melody | No | Stretch goal | No |

Lexical tone is part of a word's pronunciation: mā, má, mǎ and mà are four different words. When a word is sung, the melody replaces its tone. So tone is graded only in Word practice, where the word is spoken.

### Build stages

Each stage must be stable before the next is integrated.

| Stage | What it adds | Where the user sees it |
|---|---|---|
| 1. Whisper base (the MVP) | Whisper transcribes the recording. We convert the transcript to pinyin and match it against the lyric. One grade per word. | Spoken-accuracy mode and Word practice |
| 2. CTC layer | A second model aligns the expected lyric to the recording. It gives finer scores per sound and the start and end of every syllable. | Singing-accuracy mode |
| 3. Rhythm and tone | Both are built on the CTC layer's syllable boundaries, in parallel. | Rhythm in singing-accuracy mode; tone in Word practice |
| Stretch | Melody score, singing along with the backing track | Singing-accuracy mode |

Until stage 2, both modes produce the same grades.

## 2. Constraints and decisions

| Topic | Decision |
|---|---|
| Build window | About 24 hours |
| Team | One frontend developer, three backend/ML developers, each working with AI coding agents |
| Machines | One Windows laptop (WSL2, no NVIDIA GPU) and three Macs |
| Demo | Runs locally on one Mac, in desktop Chrome. No hosting. |
| Speech-to-text | Open-source Whisper running locally, not the OpenAI hosted API |
| Grading | Whisper as the base layer; CTC alignment as the in-depth layer on top |
| Modes | Chosen by the user before starting a song: spoken accuracy (Whisper base) or singing accuracy (Whisper + CTC, plus rhythm) |
| Recording flow | Listen to the line, then sing it back unaccompanied, in both modes |
| Must be in the demo (stage 1) | A grade per word for a sung line in spoken-accuracy mode; click any word to open Word practice; Word practice graded on initials and finals |
| Next, in order | CTC layer for singing-accuracy mode (stage 2); rhythm and tone (stage 3) |
| Stretch | Melody score, singing along with the backing track |

## 3. Choosing the scoring approach

### Whisper, MFA or CTC alignment

Our original plan was to use Whisper alone to extract the syllables and tones the user sang. We also considered the Montreal Forced Aligner (MFA) and a CTC alignment model.

| | Whisper, then compare pinyin | MFA forced alignment | CTC forced alignment + likelihood scoring |
|---|---|---|---|
| What it outputs | A Hanzi transcript | Phone and word boundaries for the lyric you give it | Per-frame sound probabilities, from which boundaries and scores are derived |
| Catches a mispronounced syllable | Sometimes. Its language model often "corrects" the learner to the right character. | No. It forces the expected phones onto whatever was sung. | Yes. It compares the expected syllable against commonly confused variants on the same audio. |
| Per-syllable timing | Rough word-level timestamps only | Good on speech (tens of ms) | 20–40 ms resolution |
| Tone | Not measured. It picks a character and never looks at pitch. | Not measured. Tones are dictionary labels it assumes. | Not measured |
| Sung audio | Degrades; invents text on silence and held notes | Degrades; speech-trained models can fail on long notes | Also speech-trained and untested by us |
| Setup | One Python package | Conda and Kaldi; built as a batch command-line tool | `pip install torch torchaudio` |

**Whisper**

- Pros: easy to integrate, robust to noise and accents, and it tells us whether the user sang the right words at all.
- Cons: it outputs characters, so tones and individual sounds are never measured. It is built to recover the intended word from sloppy speech, which for us means false passes. When it does get a syllable wrong, the error is noisy: one wrong syllable can change a whole word.

**MFA**

- Pros: it uses the known lyric, gives accurate boundaries on speech, has pretrained Mandarin models with a pinyin dictionary, and runs on CPU.
- Cons: alignment is not assessment. It returns boundaries, but no "what was actually said" and no score. It needs a conda/Kaldi install on four laptops and is slow to call once per recording.

**CTC alignment**

- Pros: a neural model gives, for every 20 ms of audio, a probability for each possible sound. From one pass we get the start and end of each syllable, a direct comparison such as "expected zh, heard z", and missing syllables.
- Cons: it is a second model to integrate and tune, and it is unproven on our recordings, sung audio above all.

### What we chose

- **Whisper is the base layer.** It grades every recording and is all the MVP needs.
- **CTC alignment is the in-depth layer.** It sits on top of Whisper. When it is on, it supplies the per-sound scores and the syllable boundaries. Whisper still decides whether anything was sung and supplies the "what we heard" transcript.
- **Candidate CTC models** are torchaudio's `MMS_FA` and a Mandarin-specific model such as `kehanlu/mandarin-wav2vec2-aishell1`. Which works better on our recordings is the first thing the CTC owner tests.
- **Tone is measured from pitch,** inside the syllable boundaries CTC provides. Neither Whisper nor the CTC model measures it.

### Where each layer applies

The team's decision is that spoken-accuracy mode uses the Whisper base and singing-accuracy mode uses Whisper plus CTC. The spec follows that as the default, with two additions:

- **Word practice also uses the CTC layer's boundaries.** Grading tone in a word of two or more syllables requires knowing where each syllable starts and ends.
- **The CTC layer is switched on per context by configuration, after a test.** The model is trained on speech and is least proven on singing, which is where we most want it. Checkpoint B (section 7) tests it on our own recordings before it reaches users.

If the test goes badly, we step down in this order:

1. **Scores and boundaries both hold up.** Singing-accuracy mode gets finer scores and rhythm. Word practice gets tone.
2. **Only the boundaries hold up.** Singing-accuracy mode keeps Whisper-base scores and adds rhythm. Word practice gets tone.
3. **Neither holds up.** The mode choice is hidden and we demo spoken-accuracy mode. Tone is limited to single-syllable words.

### Considered and dropped

- **A second lyric file made by running Whisper on the song.** The idea was to grade singing against how Whisper hears the original. A transcript records words, not pronunciation, and Whisper's errors on the original recording do not match its errors on a learner, so users would be penalised for the reference's mistakes.
- **Melody scoring as a committed stage.** It needs the singer's voice isolated from the track and a separate scorer. It stays a stretch goal.
- **MFA.** See the comparison above.

## 4. Design agreements

Four people build four parts at the same time. These agreements are what let the parts fit together. Each one is written down in exactly one file and has one keeper who approves changes.

| Agreement | Binds | Specified in | Keeper |
|---|---|---|---|
| The HTTP API: requests and graded results | Frontend (A) and backend (B) | [contracts/api.md](contracts/api.md) | B |
| The syllable record | Every backend part | [contracts/data-model.md](contracts/data-model.md) | B |
| The song bundle, `song.json` | Pipeline (D, C), backend (B) and frontend (A) | [contracts/data-model.md](contracts/data-model.md), section 5 | D |
| The functions between backend modules | B, C and D | [contracts/backend-interfaces.md](contracts/backend-interfaces.md) | B |
| Scoring rules: formulas, thresholds, who computes what | B, C and D | [contracts/scoring.md](contracts/scoring.md) | B |
| Shared test recordings | B, C and D | [contracts/backend-interfaces.md](contracts/backend-interfaces.md), section 6 | D |

Three principles run through all of them:

- **One syllable structure everywhere.** Processing a song and processing a user's recording both produce the same record: Hanzi, pinyin, initial, final, tone, start and end time. Because the two sides have the same shape, every score is a field-by-field comparison.
- **One entry per expected syllable.** Every layer returns a list with exactly one entry for each expected syllable, in order. Layers are merged by index and nothing is ever re-aligned.
- **Stubs and switches.** At kickoff, B commits the shared types and a stub for every function. Each owner replaces their own stubs. Each layer sits behind a switch that is off by default, and a layer that fails never breaks the Whisper base.

The three backend tasks:

| Task | Provides | Depends on |
|---|---|---|
| B: API and Whisper base | The API, shared types, audio loading, transcription, matching, the grader that combines every layer | `to_syllables` from D |
| C: CTC layer and rhythm | Syllable spans, finer sound scores, the rhythm score, syllable times in `song.json` | Shared types from B; song bundles from D |
| D: Songs and tone | Text-to-syllables, the song pipeline and bundles, the tone score | Shared types from B; syllable spans from C for longer words |

Each task can be developed and tested alone, because every function in the interface takes plain audio and syllable lists as arguments.

## 5. Architecture

```text
┌───────────────── Browser: React + TypeScript ─────────────────┐
│ Song screen: pick song + mode (spoken or singing accuracy)    │
│ Line screen: play line [start_ms,end_ms] → record             │
│   → graded word chips → click a word → Word practice          │
└───────┬──────────────────────────────────▲────────────────────┘
        │ GET /songs, /songs/{id}          │ AttemptResult (JSON)
        │ POST /attempts (audio + ids)     │
┌───────▼──────────────────────────────────┴────────────────────┐
│ FastAPI                                                 [B]   │
│  audio ingest: decode → 16 kHz mono → trim silence      [B]   │
│  base layer: Whisper → syllables → match to the lyric   [B]   │
│  CTC layer: align the lyric → spans, finer scores       [C]   │
│  rhythm: user's syllable times vs the original's        [C]   │
│  tone: pitch contour inside each syllable               [D]   │
│  grader: merge layers → scores, feedback → result       [B]   │
│  song store: data/songs/<id>/song.json + audio          [B]   │
└───────▲───────────────────────────────────────────────────────┘
        │ writes song bundles once, ahead of time
┌───────┴───────────────────────────────────────────────────────┐
│ Pipeline CLI                                                  │
│  build_song: lyrics → syllables, words, word clips      [D]   │
│  align_track: original audio → syllable times           [C]   │
│  → song.json (served to the frontend)                         │
└───────────────────────────────────────────────────────────────┘
```

The letters in brackets are the owners from section 7.

- **Frontend.** A song screen and a line screen. It contains no scoring logic. Specified in [tasks/frontend.md](tasks/frontend.md).
- **Backend.** One endpoint receives a recording and returns a graded result. Configuration decides which layers run in which context, so the frontend never changes when a layer is switched on.
- **Song pipeline.** Command-line scripts run ahead of time. Nothing expensive happens during a user session.

Which layers run where, once each stage passes its checkpoint:

| Context | Stage 1 | From stage 2 | From stage 3 |
|---|---|---|---|
| Line, spoken-accuracy mode | Whisper base | Whisper base | Whisper base |
| Line, singing-accuracy mode | Whisper base | Whisper + CTC scores | + rhythm |
| Word practice | Whisper base | Whisper base | + tone, using CTC boundaries |

The switches that implement this table are in [contracts/backend-interfaces.md](contracts/backend-interfaces.md), section 4.

## 6. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Vite + React + TypeScript + Tailwind | Client-only app. If the frontend developer is faster in Next.js, use it; the contract is identical. |
| Browser audio | `MediaRecorder` (webm/opus); Web Audio for a level meter | Echo cancellation, noise suppression and auto gain turned off. |
| API | Python 3.12, FastAPI, Uvicorn, Pydantic v2, `uv` for environments | |
| Audio decoding | PyAV, through `faster_whisper.decode_audio` | Avoids installing ffmpeg on four machines. |
| Speech-to-text | `faster-whisper`, plus `mlx-whisper` on macOS | Runs on Windows and macOS. The Mac default is `mlx-whisper` (`large-v3-turbo`, 0.63 s on a 1.4 s line). Docker and Windows use `faster-whisper` (~5 s on the same line). `WHISPER_ENGINE` overrides it. |
| CTC alignment | `torch` + `torchaudio` (`MMS_FA`, `forced_align`) | Pin versions: `forced_align` was scheduled for removal and then kept. The `ctc-forced-aligner` package is the fallback. |
| Mandarin text | `pypinyin`, `jieba` | Plus a per-song overrides file for readings. |
| Pitch | `praat-parselmouth` | For tone. |
| Spoken reference clips | `edge-tts`, generated ahead of time | Needs internet when generating. The browser's `speechSynthesis` covers a missing clip. |
| Synced lyrics | LRCLIB, converted by the pipeline | |
| Storage | JSON and audio files on disk | No database, no accounts. Recordings are saved to disk so we can tune thresholds. |

Everything installs with `pip` or `npm` on both Windows (WSL2) and macOS. Nothing requires conda, a GPU, or a cloud service at demo time.

**Two ways to run, both kept working:**

- **Docker, for development.** `docker compose up` gives everyone the same Python, uv, Node and packages with nothing else installed. Models download into a Docker volume on first use. On a Mac it runs on the CPU only.
- **Native, for the demo.** The demo Mac runs natively, for speed and so the `mlx-whisper` fallback is available. Set it up and test it during the hours 19–22 rehearsal, with the models already downloaded. Docker is the fallback if the native setup breaks.

On Linux, `backend/pyproject.toml` takes PyTorch from the CPU-only index, so neither WSL2 nor Docker downloads CUDA libraries.

## 7. Roadmap

### Owners

| Role | Owns | Task spec | Person |
|---|---|---|---|
| A: Frontend | The whole UI: song screen with the mode choice, line screen, word chips, Word practice | [tasks/frontend.md](tasks/frontend.md) | To be assigned |
| B: API and Whisper base | FastAPI, shared types, mock grader, audio, Whisper, matching, the grader, feedback | [tasks/backend-api-whisper.md](tasks/backend-api-whisper.md) | To be assigned |
| C: CTC layer and rhythm | CTC alignment, finer sound scores, aligning the original track, rhythm | [tasks/backend-ctc-rhythm.md](tasks/backend-ctc-rhythm.md) | To be assigned |
| D: Songs and tone | Text-to-syllables, the song pipeline, the demo songs, tone | [tasks/backend-songs-tone.md](tasks/backend-songs-tone.md) | To be assigned |

A is the bottleneck role, so B helps with frontend integration after hour 6. Role C needs someone comfortable working with PyTorch tensors.

### Timeline

Hours are counted from the start of the build. Each task spec breaks its column into deliverables with a "done when" check.

| Hours | A: Frontend | B: API + Whisper base | C: CTC + rhythm | D: Songs + tone |
|---|---|---|---|---|
| 0–1.5: kickoff | Project scaffold, API client | Shared types, stubs, mock grader, routes | Record fixtures; set up the model | `to_syllables` (due hour 2); hand-written demo lines |
| 1.5–6: stage 1 | Song screen, line screen, word chips, Word practice, against the mock | Audio, Whisper, matching, the grader; test Whisper on isolated words | Experiment: does alignment run, which model, are boundaries right, how fast | Pipeline; song 1 reviewed by hand; word clips |
| 6–13: stage 2 | Score row, feedback, navigation, error states | Layer switches, saved attempts, feedback catalogue; plug in the CTC layer; help A | `align`, `score_sounds`, original track aligned for song 1, the evaluation script | Tone on single-syllable words; song 2 |
| 13–19: stage 3, as far as checkpoint B allows | Rhythm and tone in the results; polish | Plug in rhythm and tone; tuning; bug fixes | Rhythm score; song 2 aligned | Tone on longer words; tone feedback |

### Fixed points

1. **Hours 0–1.5, everyone.** Agree the contracts, scaffold the repo, hand-write two lines of `song.json`, record the fixture recordings, get the mock grader serving.
2. **Hour 6, checkpoint A: stage 1 is stable.** On one song, in spoken-accuracy mode, a user can sing a line, see a grade per word, click a word, speak it and get a grade. C and D prepare later stages in parallel before this point, but nothing from stage 2 is integrated until it passes. If stage 1 is not stable at hour 6, C and D help fix it first.
3. **Hour 13, checkpoint B: test the CTC layer.** Use about 20 of our own recordings of sung lines, half correct and half with a deliberate error such as z for zh. Two questions:
   - Do its scores flag the wrong recordings and pass the right ones more reliably than the Whisper base?
   - Do its syllable boundaries sound right when we cut the audio at them?

   The answers pick one of the three outcomes in section 3. Repeat the boundary check on spoken words for Word practice.
4. **Hour 19.** Feature freeze. Whichever stage is stable at this point is what we demo.
5. **Hours 19–22.** Rehearse on the demo Mac with the real microphone in a noisy room. Record a backup video. Confirm all models are already downloaded.
6. **Hours 22–24.** Submission and pitch.

Stretch goals are attempted only once stage 3 is in and stable: melody score, then singing along with the backing track.

## 8. Risks

| Risk | What we do about it |
|---|---|
| The CTC model is trained on speech and is unproven on singing, which is where the plan uses it most. | C's experiment in the first block. Checkpoint B tests it on our own recordings. The step-down order in section 3 says what ships if it fails. Slow songs with one syllable per note. |
| The user sings in both modes, so the modes differ only in grading depth. If the CTC layer fails, they are identical. | The frontend hides the mode choice behind a flag, and we demo spoken-accuracy mode. |
| Spoken-accuracy mode is forgiving. Whisper tends to hear the intended word, so some mispronunciations pass. | Word practice catches more, because a single word gives Whisper no sentence to guess from. Singing-accuracy mode adds the finer check. Three-level chips, not precise numbers. |
| Rhythm needs the original track aligned to the lyric, and instruments make that alignment worse. | Songs with sparse accompaniment. Check the aligned times by ear. If they are poor, isolate the vocal with a stem-separation tool or correct the times by hand in `song.json`. |
| Whisper is less reliable on very short clips, such as one syllable spoken on its own. It can return nothing or invented text. We have not tested this yet. | B tests about 20 isolated words in the first block. Keep a margin of silence around the word when trimming. Treat an empty result as `no_speech`. If single syllables stay unreliable, practise the syllable inside a longer word or short phrase. |
| Whisper invents text when given silence. | Trim silence and use its voice-activity filter before transcribing; return `no_speech`. |
| Songs use readings that automatic pinyin gets wrong: 的 sung as "dì", 了 as "liǎo", characters with several readings such as 和. | A per-song overrides file, and a Mandarin reader reviews every demo song. |
| Four people and their AI agents edit one repo at once. | One owner per file. Contracts change before code does. Agents are told to stay inside their owner's files. |
| Venue Wi-Fi and noise. | Download roughly 3 GB of models before the event. Use a close microphone or headset. |
| Audio and lyrics rights. | If the repo is public, do not commit copyrighted recordings. Folk tunes such as 两只老虎 or 茉莉花 are safe compositions, though a given recording still has its own rights. Judges already know the melody of 两只老虎 (it is "Frère Jacques"). |

## 9. Still to settle

None of these changes the architecture.

1. **Who takes which role** in section 7?
2. **Does anyone read Mandarin well enough** to verify pinyin and record "correct" attempts for tuning? If not, we need another way to check the demo songs.
3. **Which two songs?** They should be slow, with one syllable per note and sparse accompaniment, and we need a recording we are allowed to use.
4. **Frontend framework.** Vite or Next.js is the frontend developer's call.
5. **Assumed defaults.** Two hand-prepared songs, rule-based feedback messages with no LLM, no user history. Object if any of these is wrong.

## 10. Repo layout

The letter after each path is its owner.

```text
MHACKS/
├── AGENTS.md                      # entry point for AI agents; points into docs/
├── CLAUDE.md                      # loads AGENTS.md in Claude Code
├── README.md                      # what this is and how to run it, with Docker or natively
├── .gitignore
├── compose.yaml                   # B  dev environment: backend and frontend containers
├── docker/                        # B  Dockerfiles and container entrypoints
├── docs/
│   ├── README.md                  # index of the documentation
│   ├── PROJECT_PLAN.md            # this file
│   ├── contracts/                 # api, data-model, backend-interfaces, scoring
│   ├── design/                    # A  ui.md: visual design and interaction details; screens/
│   └── tasks/                     # frontend, backend-api-whisper, backend-ctc-rhythm, backend-songs-tone
├── frontend/                      # A; the file split inside src/ is a starting point
│   ├── prototype/                 # A  clickable design prototype, not the app; see design/ui.md §11
│   └── src/
│       ├── api/                   # client.ts, types.ts (generated)
│       ├── audio/                 # player.ts, recorder.ts
│       ├── components/            # LyricLine, RecordButton, WordChips, ScoreRow, Feedback, WordPracticePanel
│       └── screens/               # SongScreen, LineScreen
├── backend/
│   ├── pyproject.toml             # B; C and D add their dependencies
│   ├── app/
│   │   ├── main.py                # B  routes
│   │   ├── schemas.py             # B  every shared type
│   │   ├── config.py              # B  layer switches
│   │   ├── audio.py               # B
│   │   ├── songs.py               # B
│   │   ├── mandarin.py            # D  text to syllables
│   │   └── scoring/
│   │       ├── grader.py          # B
│   │       ├── mock.py            # B
│   │       ├── transcribe.py      # B
│   │       ├── matcher.py         # B
│   │       ├── confusions.py      # B
│   │       ├── feedback.py        # B; C and D add rows
│   │       ├── ctc.py             # C
│   │       ├── rhythm.py          # C
│   │       ├── pitch.py           # D
│   │       └── tone.py            # D
│   ├── pipeline/
│   │   ├── build_song.py          # D
│   │   └── align_track.py         # C
│   └── tests/
│       ├── test_matcher.py, test_grader.py, test_api.py   # B
│       ├── test_ctc.py, test_rhythm.py, eval_ctc.py       # C
│       ├── test_mandarin.py, test_tone.py                 # D
│       └── fixtures/{lines,audio}/   # D keeps; everyone adds recordings
├── data/
│   ├── songs/<song_id>/           # D  song.json, overrides.json, audio, words/
│   └── attempts/                  # ignored by git: saved recordings for tuning
└── scripts/
    ├── dev.sh                     # start backend and frontend together
    └── gen-types.sh               # A  regenerate the frontend's API types
```

The skeleton exists: every file above has been created with a header that states its purpose, what it provides, its owner and its spec. The code inside is each owner's task.

## Sources

- [LRCLIB](https://github.com/tranxuanthang/lrclib)
- [pypinyin](https://github.com/mozillazg/python-pinyin)
- [TorchAudio maintenance-phase update (issue 3902)](https://github.com/pytorch/audio/issues/3902)
- [kehanlu/Mandarin-Wav2Vec2](https://github.com/kehanlu/Mandarin-Wav2Vec2/blob/main/README.md)
- [MFA Mandarin pinyin dictionary v2.0.0](https://mfa-models.readthedocs.io/en/latest/dictionary/Mandarin/Mandarin%20PINYIN%20dictionary%20v2_0_0.html)
- [Interspeech 2025 paper on Whisper and Chinese singing](https://www.isca-archive.org/interspeech_2025/liang25c_interspeech.pdf)
