# Task A: Frontend

**Owner:** to be assigned. **Works alongside:** B (API). B helps you with integration after hour 6.

## Goal

You build the whole user interface: the song screen, the line screen with recording and results, and the Word practice panel. You contain no scoring logic. Everything you show comes from the backend in a fixed format, and you can build against the mock grader from the first hour.

## Read first

1. [PROJECT_PLAN.md](../PROJECT_PLAN.md), sections 1 and 2.
2. [contracts/api.md](../contracts/api.md): every request you send and every field you render.
3. [design/ui.md](../design/ui.md): how the screens look and move. It adds design on top of this file and never overrides it.

You do not need the other contract files.

## What you own

```text
frontend/                  # everything in it
scripts/gen-types.sh       # regenerates TypeScript types from the backend
```

## What you use from others

| Thing | Owner | Until it exists |
|---|---|---|
| The API with the mock grader | B | Due at hour 1.5. Before that, use the example result in api.md as a local JSON file. |
| TypeScript types | generated from B's `/openapi.json` | Hand-copy the types from api.md until the backend runs |
| The real grader | B | Checkpoint A at hour 6. No frontend change is needed when it arrives. |

## Screens

### 1. Song screen

- A list of songs from `GET /api/v1/songs`.
- Selecting a song shows the mode choice before anything starts. Suggested wording:
  - **Spoken accuracy.** "Did the right words come out? Checks the sounds of each word."
  - **Singing accuracy.** "A closer look at every sound, plus your rhythm against the original."
- A Start button begins at line 1.

### 2. Line screen

The same screen serves both modes, and the user sings in both.

- Header: song title, "line 3 of 12", and a badge showing the mode.
- The line in Hanzi with Pinyin for each character, and the translation underneath.
- A Listen button plays the line from the original track.
- A Record button with a live level meter. Recording ends when the user presses it again or after a time limit.
- After grading, the same screen shows:
  - each word as a coloured chip;
  - a row of scores;
  - the "what we heard" transcript;
  - one feedback message;
  - Retry and Next line buttons.

### 3. Word practice panel

Opens over the line screen when the user clicks a word chip. It is identical in both modes.

- The word in Hanzi and Pinyin, with its English meaning.
- A Play button for the spoken reference.
- A Record button.
- The result: each syllable's initial, final and, when present, tone, each with a status colour and a feedback message.
- Closing the panel returns to the line.

### What differs between the modes

| Element | Spoken-accuracy mode | Singing-accuracy mode |
|---|---|---|
| Word chips | Grade from the Whisper base | Finer grade from Whisper + CTC |
| Score row | Pronunciation, Completeness, Overall | Pronunciation, Completeness, Rhythm (when present), Overall |
| Feedback message | Names the sound when Whisper heard a different syllable | Names the sound more often |
| Clicking a word | Opens Word practice | Opens Word practice |

You do not implement these differences. You send the mode, and the backend's response differs.

### States of the line screen

`idle` → `listening` → `ready` → `recording` → `grading` → `result`

- If the backend returns `status: "no_speech"`, show "We didn't hear anything" and return to `ready`.
- If the request fails, show a retry button and keep the recording so it can be sent again.

## Rules

- Chip colour comes from `status`: good is green, ok is yellow, wrong is red, missing is grey. Never compute it from a score.
- Show every score that is not `null`, and hide the ones that are. Rhythm and Tone then appear by themselves when the backend starts sending them.
- Send `mode` with every `target=line` attempt.
- Any word chip is clickable, not only the one in `next_step`.
- Until the CTC layer lands, both modes return the same grades. Put the mode choice behind a flag, `VITE_SHOW_MODE_CHOICE`, and default to spoken accuracy when it is off.

## Deliverables

### Kickoff, hours 0–1.5

1. A Vite + React + TypeScript + Tailwind project in `frontend/`.
2. An API client module with the types from api.md.

**Done when:** the app starts and renders the song list from a local JSON file.

### Block 1, hours 1.5–6

1. Song screen with the mode choice.
2. Line screen: play the line, show Hanzi and Pinyin, record, send, render word chips.
3. Word practice panel, reusing the record and result components.

**Done when (checkpoint A):** against the mock grader, a user can pick a song, record a line, see chips in all four colours, click a word, record it, and see its result. Then the same against the real grader.

### Block 2, hours 6–13

1. Score row and feedback message.
2. The "what we heard" transcript.
3. Line navigation: Retry, Next line, and progress through the song.
4. The `no_speech` and request-failure states.

**Done when:** a full song can be played through line by line with no dead ends.

### Block 3, hours 13–19

1. Rhythm in the score row and tone in Word practice, which should appear with no code change if the null rule is followed. Verify it.
2. Optional: mark syllables as early or late using `timing.offset_ms`.
3. Loading states, layout polish, and the demo run-through.

## Implementation notes

### Playing a line

- Use one `<audio>` element for the track. Set `currentTime = start_ms / 1000`, play, and pause when `currentTime` passes `end_ms / 1000`.
- Poll with `requestAnimationFrame` or a short timer. The `timeupdate` event fires too rarely to stop accurately.

### Recording

- Request the microphone with processing turned off:
  ```ts
  navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 }
  })
  ```
  Browser processing is designed for calls and can damage the consonants we grade.
- Record with `MediaRecorder` using `audio/webm;codecs=opus`. Collect the chunks into one Blob when recording stops.
- Stop automatically after twice the line's duration plus two seconds, and never beyond 30 seconds.
- The microphone only works on `localhost` or HTTPS.
- Drive the level meter from an `AnalyserNode` on the same stream.

### Sending an attempt

```ts
const form = new FormData();
form.append("audio", blob, "attempt.webm");
form.append("song_id", song.id);
form.append("line_index", String(line.index));
form.append("target", "line");          // or "word"
form.append("mode", mode);              // "spoken" | "singing"; omit when target is "word"
// form.append("word_index", String(i)) // only when target is "word"
await fetch(`${API_URL}/api/v1/attempts`, { method: "POST", body: form });
```

Grading takes a few seconds. Show the `grading` state, and time out after 20 seconds.

### Spoken reference in Word practice

Play `word.audio_url` when it is set. When it is `null`, fall back to the browser:

```ts
const u = new SpeechSynthesisUtterance(word.text);
u.lang = "zh-CN";
speechSynthesis.speak(u);
```

### Types

- Generate them: `npx openapi-typescript http://localhost:8000/openapi.json -o src/api/types.ts`. Put that in `scripts/gen-types.sh`.
- Do not edit the generated file. If a type looks wrong, the contract or the backend is wrong; raise it with B.

### Configuration

| Variable | Meaning | Default |
|---|---|---|
| `VITE_API_URL` | Backend address | `http://localhost:8000` |
| `VITE_SHOW_MODE_CHOICE` | Show the mode choice on the song screen | off |

### Running

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

## Out of scope

- Any scoring, thresholds or feedback wording.
- Accounts and saved history.
- Mobile browsers. The demo runs in desktop Chrome.
- Singing along with a backing track.
