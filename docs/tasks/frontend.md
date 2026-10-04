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
- Selecting a song shows the mode choice before anything starts. While choosing, the explanation replaces the song's description above the Sing pill:
  - **Practice mode.** "Sing or say a line at a time and every word is graded. Click a word to practice it on its own." Opens the line screen.
  - **Karaoke mode.** "Sing along to the instrumental, with the lyrics filling in time. Nothing is graded." Opens the karaoke screen.
- Choosing a mode starts at line 1.

Singing accuracy was retired on 4 October 2026 (PROJECT_PLAN.md, "The two modes"); Karaoke mode took its place.

### 2. Line screen (Practice mode)

- Header: song title, "line 3 of 12", and the badge "Practice mode".
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

Opens over the line screen when the user clicks a word chip.

- The word in Hanzi and Pinyin, with its English meaning.
- A Play button for the spoken reference.
- A Record button.
- The result: each syllable coloured by its status, the scores, then one feedback message: that of the first syllable that still needs work. Showing every syllable's message at once ran under the dock in a word of two or three syllables and hid the scores.
- Closing the panel returns to the line.

### 4. Karaoke screen (Karaoke mode)

Sing along with the song; nothing is recorded or graded. `screens/KaraokeScreen.tsx`, design in docs/design/ui.md §5.6.

- Plays `song.instrumental_url` from the start. When it is `null` or cannot be played, plays `audio_url` instead and says so; with no track at all, the lyric runs on a silent clock.
- The lyric list follows the song: the line being sung is centred and fills character by character with the line screen's karaoke fill (`logic/timing.ts`), and the next line takes over by the song screen subtitle's rule (`logic/subtitle.ts`).
- During an intro or a break, the waiting line shows "Instrumental · next line in 12 s", then a count-in of dots, and the dock offers "Skip to the singing" (`logic/karaoke.ts`).
- Dock: play and pause (the vinyl, spinning while it plays), Start again, Skip to the singing. Keys: Space, ↑ ↓ change line (the song jumps to a few seconds before it), → skip, R start again, P pinyin.
- Header: song title, "line 3 of 12", the badge "Karaoke", and the Pinyin and Translation switches.

### States of the line screen

`idle` → `listening` → `ready` → `recording` → `grading` → `result`

- If the backend returns `status: "no_speech"`, show "We didn't hear anything" and return to `ready`. Clear the previous score, word grades and feedback so a failed retry cannot look like the earlier attempt. Keep the line's attempt history in memory, including `no_speech`, but display grades only when its newest attempt has `status: "ok"`. Word practice clears its last result and returns to `ready`, keeping the dots from earlier graded attempts.
- If the request fails, show a retry button and keep the recording so it can be sent again.
- When a displayed result has `engine: "mock"`, label it "Demo scores — your audio is not being graded." in both line and word practice results.

## Rules

- Chip colour comes from `status`: good is green, ok is yellow, wrong is red, missing is grey. Never compute it from a score.
- Show every score that is not `null`, and hide the ones that are. Rhythm and Tone then appear by themselves when the backend starts sending them.
- Send `mode: "spoken"` with every `target=line` attempt: Practice mode is the API's spoken-accuracy grading.
- Any word chip is clickable, not only the one in `next_step`.

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

`VITE_SHOW_MODE_CHOICE` and `VITE_SINGING_READY` are no longer read: Sing always offers Practice mode and Karaoke mode.

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
- Grading a song sung along with the instrumental. Karaoke mode only plays it.
