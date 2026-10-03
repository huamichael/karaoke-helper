# Design: user interface

**Keeper:** A. **Used by:** A, and anyone preparing the demo.

**Status:** draft v0.4, 3 October 2026. Follows [PROJECT_PLAN.md](../PROJECT_PLAN.md) revision 5.

This document holds the frontend's visual design and interaction details. It does not restate behaviour or data. When it disagrees with these files, they win:

- [tasks/frontend.md](../tasks/frontend.md): screens, line-screen states, rules, deliverables, implementation notes.
- [contracts/api.md](../contracts/api.md): every request and every field.

Screenshots of the clickable prototype are in [screens/](screens/).

## 1. What this adds to the frontend task

| Topic | tasks/frontend.md | This document |
|---|---|---|
| Look | Not specified | Per-song colour themes, glass surfaces, Hanzi and Pinyin type, motion (section 3) |
| Word chips | "Each word as a coloured chip" | The lyric's own words are the chips: a status bar under each word, no second row of words (section 5.3) |
| Line-screen framing | Header, line, buttons | Two display modes: immersive (default) and expanded, switched with one button or `F` (section 5.3.1) |
| Header controls | Title, line count, mode badge | Pinyin and Translation switches tucked into one **Aa** menu (section 5.3.2) |
| Moving between lines | Retry, Next line, progress | Also swipe with a trackpad, mouse wheel or touch, one line per gesture (section 5.3.3) |
| Word practice | A panel over the line screen | A centred card the word grows into; the user practises until the word is graded `good`, or leaves when confident (section 5.4) |

## 2. Goals

1. Make the **listen → sing → see each word → practise a word** loop feel effortless and fun on a laptop. While singing, the lyrics fill the screen and controls appear only when needed.
2. Make the per-word feedback (Hanzi + Pinyin + status colour) the visual signature of the product, the thing judges remember.
3. Look polished enough to compete in **Best Design (Figma × MHacks)**.
4. Be explainable to judges who don't speak Chinese in under 10 seconds.

Non-goals, as in the frontend task: mobile layout, accounts, saved history.

## 3. Visual direction

**One-line pitch:** a Beautiful-Lyrics / Apple-Music-style immersive lyric view, with NetEase Cloud Music touches (vinyl record, glass cards), plus our own per-word grading layer.

| Borrow from | What we take | What we avoid |
|---|---|---|
| [beautiful-lyrics](https://github.com/surfbryce/beautiful-lyrics) | Dynamic background blended from the song's colours; big centred lyrics; word-by-word karaoke fill; cinema feel; romanization toggle | Spotify chrome (sidebars, library) |
| NetEase Cloud Music (网易云) | Spinning vinyl as the "now playing" object; soft glass cards | Red theme, dense layouts |
| Duolingo | One clear action per moment; encouraging tone | Gamification clutter (streaks, gems) |

### 3.1 Colour

- **Per-song theme.** Each song has five colours: `c0` (base), `c1`–`c3` (background blobs) and `accent` (primary buttons, record button, highlights). Themes live in the frontend (`src/theme/songThemes.ts`, keyed by song id). They are design assets, not part of the API contract. The song screen uses a neutral home theme.
- **Background:** drifting, heavily blurred blobs in `c1`–`c3` over `c0`. Fallback: a static gradient of the same colours.
- **Scrim:** 35–45% black over the background, so white text always passes contrast.
- **Text:** white at 100% (active line), 55% (upcoming), 30% (past).
- **Status colours**, the same everywhere in the app. The shape cue keeps them readable without colour:

| `status` | Colour | Shape cue on bars and dots |
|---|---|---|
| `good` | `#4ADE80` green | solid |
| `ok` | `#FACC15` yellow | half-filled |
| `wrong` | `#F87171` red | hollow |
| `missing` | `#94A3B8` grey | dashed outline |

Starting values:

| Theme | c0 | c1 | c2 | c3 | accent |
|---|---|---|---|---|---|
| Home | `#15141f` | `#3b3f6b` | `#6b4a6a` | `#2f5a5a` | `#ece8ff` |
| 茉莉花 | `#0f231a` | `#2f6b4f` | `#d9e4c4` | `#5f9c7a` | `#f4f1d6` |

Glass surfaces: white 8% fill, 24px blur, 1px border in white 14%. Easing for UI motion: `cubic-bezier(.2,.8,.2,1)`.

### 3.2 Typography

- **Hanzi:** Noto Serif SC, 700 (lines) and 900 (song sleeves). Active line 60px (52px on screens under 760px tall), other lines 30px, Word practice card 96px.
- **Pinyin:** Instrument Sans 500, about 40% of the Hanzi size, **above** each character (ruby style), centred per syllable.
- **UI text:** Instrument Sans 14–16px.
- **Self-host both fonts** with the `@fontsource` packages. Venue Wi-Fi is a risk (plan section 8).

### 3.3 Motion

- **Karaoke fill during Listen:** while the original line plays, each character fills left to right. Use each syllable's `start_ms` and `end_ms` from `song.json` when the pipeline has aligned the track; until then they are `null`, so split the line's time evenly across its syllables.
- **Changing line:** the list moves so the active line sits 40% from the top, with a spring of about 500ms. The active line's growth and the list's movement animate together, so no other line jumps: measure the layout before and after the change, then animate the difference with transforms (the FLIP technique).
- **Swipe:** on touch, the list follows the finger. Wheel and trackpad steps use the same spring. Past the first or last line, the list stretches a little and springs back.
- **Recording:** a soft ring around the record button, driven by the live input level.
- **Result reveal:** each word's status bar grows in, left to right, 60ms apart; scores count up.
- **Vinyl:** rotates while any audio plays (the line or a word's reference) and pauses otherwise. In immersive mode it is also the Listen button.
- **Word practice:** the word grows from its place in the lyric into the card, with the View Transitions API (`document.startViewTransition`, Chrome 111+), while the lyrics behind it dim and blur. Closing plays it in reverse. Without the API: fade and scale up from 96%.
- **Practice success:** the word turns green and one soft ring expands from it.
- **Header in immersive mode:** fades in (200ms) on pointer movement and out after 2.5s of stillness.
- Respect `prefers-reduced-motion`: no background drift, stagger, count-up, vinyl spin, card morph or ring; line changes jump without a spring.

### 3.4 References (GitHub)

Checked on 2026-10-03. We copy behaviour and look, not code, except where the license allows it.

| Used for | Repo | Stars | What we take | Can we use the code? |
|---|---|---|---|---|
| Look | [surfbryce/beautiful-lyrics](https://github.com/surfbryce/beautiful-lyrics) | ~2.4k | Colour-matched background, word-synced karaoke lyrics, cinema view. **Main visual reference.** | No license: look only |
| Look | [amll-dev/applemusic-like-lyrics](https://github.com/amll-dev/applemusic-like-lyrics) | ~2.2k | Apple Music style lyric component with a fluid background | AGPL-3.0: look only |
| Look | [qier222/YesPlayMusic](https://github.com/qier222/YesPlayMusic) | ~33k | NetEase Cloud Music player with a clean lyric page | MIT, but Vue/Electron: layout reference |
| Word practice | [Thiagohgl/ai-pronunciation-trainer](https://github.com/Thiagohgl/ai-pronunciation-trainer) | ~0.5k | Words coloured by correctness; clicking one opens a modal with the expected and heard sounds and plays the reference | AGPL-3.0: look only |
| Word practice | [yomidevs/yomitan](https://github.com/yomidevs/yomitan) | ~2.9k | Pointing at a word brings up a card about that word, over the text | GPL-3.0: look only |
| Display modes | [readest/readest](https://github.com/readest/readest) | ~24.8k | The reader's header stays hidden; it appears when the pointer reaches it and stays while one of its menus is open | AGPL-3.0: look only |
| Swipe | [amll-dev/applemusic-like-lyrics](https://github.com/amll-dev/applemusic-like-lyrics), `packages/core/src/lyric-player/base/scroll.ts` | ~2.2k | A wheel gesture ends after 150ms without events; wheel steps animate with a spring, touch follows the finger | AGPL-3.0: look only |
| Swipe | [xiel/wheel-gestures](https://github.com/xiel/wheel-gestures) | <0.1k | Tells a new trackpad swipe apart from the momentum of the previous one | MIT: **use it** |

No open-source "learn a language by singing with pronunciation feedback" UI turned up, so the per-word grading view has no template to copy. That is also our novelty pitch.

## 4. Layout

Target viewport **1440×900**; must work at **1280×720** (projector). Below 1024px wide, show a "built for laptops" notice.

### 4.1 Immersive (the default)

```
┌──────────────────────────────────────────────────────────────────────┐
│  (header hidden; fades in when the pointer moves)                    │
│                                                                    ╷ │
│                     (past lines, faded)                            │ │
│                                                                    ┃ │ ← line rail
│              hǎo   yì duǒ  ╭měi lì╮✓  de                         │ │
│              好    一朵    │美丽 │   的         ← active line       │ │
│              ▬▬    ▬▬▬▬    ╰▭▭▭▭─╯   ▬▬         ← status bars       ╵ │
│             What a beautiful jasmine flower                          │
│             Overall 96   Pronunciation 95   Completeness 100         │
│             We heard 好一朵买丽的茉莉花                                │
│             Say 美丽 (měi lì) on its own, then retry the line.        │
│                                                                      │
│                    (upcoming lines, fading out)                      │
│                    ╭────────────────────────────╮                    │
│                    │ (◉)   ↻   [  Next line  ]  │   ← dock           │
│                    ╰────────────────────────────╯                    │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Expanded

```
┌──────────────────────────────────────────────────────────────────────┐
│ ← Songs   茉莉花  2 / 7   [Spoken accuracy]                   Aa   ⤢   │
├──────────────────────────────────────────────────────────────────────┤
│               (same lyric column as immersive)                       │
├──────────────────────────────────────────────────────────────────────┤
│ (◉) Line 2 of 7   [▶ Listen] [● Record] [↻ Retry] [Next line]   keys │
└──────────────────────────────────────────────────────────────────────┘
```

- **Lyric column:** centred, max width 760px, in both modes. It never shifts sideways.
- **Header:** 64px, glass. Always visible in expanded mode; fades in over the lyrics in immersive mode.
- **Bottom bar (expanded):** 88px, glass. All four actions are always there; the ones not available now are dimmed; the current primary action is the only filled button. Keyboard hints on the right, hidden below 1360px wide.
- **Dock (immersive):** glass pill, bottom centre, 26px above the edge. It holds only what the current state needs.
- **Line rail (immersive):** one short tick per line on the right edge. The active line's tick is longer and brighter.
- **Word practice card:** 500px wide, centred, over the dimmed and blurred lyrics. The same in both modes.

## 5. Screens

### 5.1 Song screen

- Hero line: "Learn Mandarin by singing the songs you love."
- One card per song, drawn as a **typographic record sleeve** (one large character, e.g. 茉) with the vinyl sliding out on hover. Title, artist, line count.
- Hovering a card tints the page background with that song's theme.
- Selecting a song opens a small card with the mode choice and Start. The wording is from the frontend task:
  - **Spoken accuracy.** "Did the right words come out? Checks the sounds of each word."
  - **Singing accuracy.** "A closer look at every sound, plus your rhythm against the original."
  - Subtitle: "Pick a mode. You sing the same way in both."
- When `VITE_SHOW_MODE_CHOICE` is off (the default), the card shows only the song and Start, and the mode is spoken accuracy.
- **Start** opens the line screen at line 1, in immersive mode.

### 5.2 Microphone setup (first Record only)

A single centred card the first time the user presses Record: "Allow microphone", then a live level meter and "Say 你好 (nǐ hǎo) to test it", with a green check when sound is detected. This is a local check; nothing is sent. Microphone settings follow the frontend task's implementation notes.

### 5.3 Line screen

The states and their rules are in the frontend task. This is what each state looks like:

| State | What the user sees | Dock (immersive) |
|---|---|---|
| `idle` | Active line highlighted; its previous result, if any, under it | Vinyl, labelled "Listen" |
| `listening` | The line plays; karaoke fill sweeps the line; vinyl spins | Spinning vinyl, labelled "Playing"; press it to stop |
| `ready` | Line at rest | Vinyl (listen again) · **Record** |
| `recording` | Ring pulses with the input level; a thin bar shows time used out of the limit | Vinyl (disabled) · **Stop** with the elapsed time |
| `grading` | The line breathes; "Listening back…" | Vinyl (disabled) · "Listening back…" |
| `result` | Status bars grow in, scores count up, what we heard, the message | Vinyl · ↻ · **Next line** |
| request failed | Message under the line; the recording is kept | Vinyl · **Send again** |

- The dock and the expanded bottom bar read the same list of actions for each state, so they cannot disagree. The dock shows only that list; the bottom bar shows all four actions and dims the rest.
- When `next_step.type` is `retry_line`, Retry is the primary action in `result` instead of Next line.
- On the last line, Next line reads "Back to songs".
- `no_speech`: "We didn't hear anything. Move closer to the mic and sing again." under the line, then `ready`.

**After grading,** in both display modes:

- **The words are the chips.** Each word gets a bar under it in its `status` colour and shape, and the pinyin of a word that is not `good` takes the same colour. There is no second row of words.
- If `next_step.type` is `practice_word`, that word gets an accent ring that pulses once.
- Under the line: the translation, the score row (every score that is not `null`: Overall, Pronunciation, Completeness, then Rhythm, Tone and Melody when the backend sends them), "We heard" with `heard.hanzi` and its pinyin, and the message (section 9, question 4).

#### 5.3.1 Display modes

| | Immersive (default) | Expanded |
|---|---|---|
| Purpose | Singing: nothing on screen but the song and the next thing to press | Seeing every control and shortcut; first-time users; explaining the app to judges |
| Header | Hidden. Any pointer movement fades it in; it fades out after 2.5s of stillness, unless the pointer is over it or the Aa menu is open. The cursor hides with it | Always visible |
| Controls | Dock with the current state's actions | Bottom bar with all four actions, line progress, vinyl and keyboard hints |
| Line rail | Shown | Hidden; the header shows "N / M" |
| Browser full screen | Requested on entry | Left on entry |

- **Switching:** the full-screen button at the right of the header (arrows pointing outwards in expanded mode, inwards in immersive mode), or `F`. The choice holds until the user leaves the song.
- **Start** enters immersive mode. Start is a click, so Chrome allows the full-screen request.
- **Esc in full screen** is taken by Chrome to leave full screen; the page sees the change and switches to expanded mode.
- **If the full-screen request is refused,** stay in immersive mode inside the window.
- **First time in immersive mode,** a short hint: "Swipe or press ↑ ↓ to change line. Press F to see every control."
- **Until the immersive tier is built (section 8),** the app opens in expanded mode.

#### 5.3.2 Header and the Aa menu

Header, left to right: ← Songs · song title · "2 / 7" · mode badge (when the mode choice is shown) · spacer · **Aa** · full-screen button.

**Aa** opens a small glass menu under the button:

- **Pinyin** switch, on by default. `P` toggles it directly.
- **Translation** switch, on by default.
- **Rehearsal**, only when the URL has `?demo`: "Next result: Auto / Good / With a mistake / No speech / Request fails". It needs a switch in the mock grader (section 9, question 1). Nothing about it is visible in a normal session.

The menu closes on Esc or a click outside it. While it is open, the header stays visible.

#### 5.3.3 Changing line

Four ways: swipe, `↑/↓`, click a line, click a tick on the line rail.

- **One gesture moves one line.** A trackpad swipe and its momentum count as one gesture; detect momentum with `wheel-gestures`. One mouse-wheel notch is one gesture.
- **Touch:** the list follows the finger. Releasing after more than 48px, or with a quick flick, moves one line; otherwise the list springs back.
- **The new line becomes active in `idle`,** showing its previous result if it has one.
- **First and last line:** swiping past them stretches the list a little, then it springs back.
- **Locked while `recording` or `grading`, and while Word practice is open.** The active line nudges 8px and settles, and during recording a hint reads "Stop recording to change line." A recording is never thrown away by a stray swipe.
- **While `listening`:** a swipe stops playback and moves.

#### 5.3.4 Other interactions

- **Click a word** → Word practice for that word (section 5.4). Every graded word is clickable. Words graded `wrong`, `ok` or `missing` lift on hover and show "Practise"; `good` words open it too but show no label.
- **Practised mark:** when Word practice closes after a `good` attempt, a small ✓ sits on the word's corner. The word keeps its colour from the sung attempt, because colour comes only from that attempt's `status`. Singing the line again clears the mark.
- **Hover a word** (P2): a tooltip per syllable with the expected and heard initial and final, and that syllable's feedback message.
- **Early or late** (optional, block 3): when `syllables[].timing.offset_ms` is set, the hover tooltip says "came in 120 ms early" and a small notch on the word's bar sits left (early) or right (late) of centre.
- **Keyboard:** `Space` record or stop, `L` listen, `R` retry, `Enter` next line, `↑/↓` change line, `P` pinyin, `F` display mode, `Esc` close the card or menu.

### 5.4 Word practice

The frontend task's Word practice panel, presented as a centred card. It opens when a graded word is clicked, is the same in both modes, and sends `target=word` with the word's `word_index`.

**Layout, top to bottom:**

1. ✕ to close, top right.
2. The word: pinyin above, Hanzi at 96px, English meaning (`gloss`) below.
3. **Listen** plays the spoken reference (`audio_url`, or `speechSynthesis` in `zh-CN` when it is `null`). **Record** is the filled button and reuses the line screen's record component.
4. The latest attempt: one column per syllable, with rows for initial, final and (from stage 3) tone. Each row shows a status dot, the expected sound and the heard one ("ei, heard ai"). Under the columns, the feedback message of each syllable that is not `good`.
5. **Attempts:** one dot per graded attempt, coloured by the word's status, newest on the right. `no_speech` and failed requests add no dot.
6. **I'm confident**, a text button at the bottom, closes the card at any time.

| State | What the user sees | Primary action |
|---|---|---|
| `ready` | The word, Listen and Record; the previous attempt's result, if any | Record |
| `playing` | The reference plays; Listen becomes Stop | Record |
| `recording` | Ring pulses with the input level; elapsed time | Stop |
| `grading` | "Listening back…" | — |
| `result` | Syllable rows and messages; a new dot | Record again |
| `success` | The word's status is `good`: the Hanzi turns green, a ring expands, "Nailed it." above the buttons | **Sing the line again** (secondary: Keep practising) |

- **Success comes only from the backend:** the `status` of the returned word. Never from a score.
- **Sing the line again** closes the card and puts the line in `ready`, so the next press records.
- **Closing:** ✕, I'm confident, Esc, or a click outside the card when it is not recording or grading. In browser full screen the first Esc leaves full screen (Chrome takes it) and the second closes the card.
- `no_speech`: "We didn't hear anything. Say the word a little louder." under the buttons. A failed request shows Send again, which resends the same recording.
- Attempts and the practised mark live in memory for the session only.

## 6. Components and logic

The file split in `frontend/src/` is a starting point (plan section 10). This design adds:

| Component | Key inputs | Notes |
|---|---|---|
| `DynamicBackground` | theme, `playing` | Drifting, or static with reduced motion |
| `SongCard` | `SongSummary`, theme | Sleeve, vinyl slides out on hover, tints the page |
| `TopBar` | title, line N of M, mode, display mode | Fades in and out in immersive mode |
| `DisplayMenu` (Aa) | `showPinyin`, `showTranslation`, demo flag | |
| `Dock`, `BottomBar` | actions for the state, input level | Both render `actionsFor(state)` |
| `LineRail` | line count, active index | |
| `LyricLine` + `WordChips` | `Line`, `isActive`, fill, result | The words of the line are the chips |
| `WordPracticePanel` | `Word`, its syllables, attempts | Rendered as the centred card |
| `Vinyl` | theme, `spinning` | Also the Listen button in the dock |

Logic that is easy to get wrong goes in small pure modules with unit tests:

- `actions.ts`: `actionsFor(state, nextStep)` returns the actions and which one is primary.
- `practiceMachine.ts`: the Word practice states and the attempt list; `success` only when the returned word's `status` is `good`.
- `lineSwipe.ts`: turns wheel and touch input into "up one line" or "down one line", built on `wheel-gestures`. Tested with recorded event sequences: one trackpad swipe with a long momentum tail gives exactly one step.

## 7. Rules this design adds

The frontend task's rules all apply. In addition:

1. Word practice's success state comes only from the returned word's `status` being `good`.
2. Practice attempts and practised marks are kept in memory for the session only.
3. Line changes are refused while recording or grading.

### Where each element gets its data

| UI element | Field (contracts/api.md) |
|---|---|
| Song cards | `GET /api/v1/songs` → `SongSummary` |
| Lyric line, pinyin, translation | `Song.lines[]`: `text`, `syllables[].pinyin`, `translation` |
| Karaoke fill timing | `syllables[].start_ms`, `end_ms` when set; otherwise the line's `start_ms`–`end_ms` split evenly |
| "N / M", line rail | `line.index`, `SongSummary.line_count` |
| Status bars | `AttemptResult.words[]`: `status`, `syllable_indices` |
| Suggested word, primary action | `AttemptResult.next_step` |
| Score row | `AttemptResult.scores` (non-`null` only) |
| We heard | `AttemptResult.heard` |
| Word practice word | `line.words[]`: `text`, `gloss`, `audio_url` |
| Word practice rows | `syllables[]`: `initial`, `final`, `tone`, `feedback` |
| Early or late notch | `syllables[].timing.offset_ms` |

## 8. Design priorities

Every item ships if time allows. The tiers set the build order: finish a tier before starting the next. The frontend task's checkpoints come first; if stage 1 isn't stable at hour 6, P1 waits. Estimates are rough, for one developer working with a coding agent.

| Tier | Hours (plan section 7) | Item | Est. |
|---|---|---|---|
| **P0 Foundation**, built into the components | 0–6 | Theme tokens (song themes, status colours, glass, easing) | 0.5 h |
| | | Self-hosted fonts | 0.25 h |
| | | Hanzi + Pinyin ruby layout and type scale | 1 h |
| | | Status bars with colour and shape cues | 0.5 h |
| | | Static theme gradient and scrim | 0.25 h |
| | | Expanded layout at 1440×900 and 1280×720, narrow-screen notice | 0.75 h |
| | | Header with the Aa menu and the full-screen button | 0.5 h |
| | | Word practice card layout | 0.5 h |
| **P1 Signature moments** | 6–13 | Status bars grow in; scores count up | 1 h |
| | | Karaoke fill during Listen | 1.5 h |
| | | Line change with a spring and no jumping lines (FLIP) | 1 h |
| | | Swipe between lines: wheel-gestures, touch, stretch at the ends, lock | 1.5 h |
| | | Immersive mode: dock, header fade, cursor hide, browser full screen | 1 h |
| | | Word grows into the practice card (View Transitions) | 1 h |
| | | Practice loop: attempt dots, success moment, practised mark | 1 h |
| | | Song cards as typographic record sleeves | 1.5 h |
| **P2 Atmosphere** | 13–19 | Dynamic drifting background; card hover tints the page | 2 h |
| | | Vinyl spins while audio plays | 0.5 h |
| | | Record-button ring driven by the input level | 0.5 h |
| | | Word hover tooltip | 1 h |
| | | Line rail | 0.5 h |
| | | `prefers-reduced-motion` | 0.5 h |
| **P3 Finish** | before the hour-19 freeze | Keyboard shortcuts | 1 h |
| | | Loading and grading states | 0.5 h |
| | | Mic setup card polish | 0.5 h |
| | | Optional: early or late notches from `timing.offset_ms` | 1 h |

Total is about 21 hours of design work on top of the functional work. P1 alone is 9.5 hours in a 7-hour window, so it needs B's help after checkpoint A, as the plan already provides. If the hour-19 freeze arrives first, whatever tier is complete is what we demo.

## 9. Open questions

1. **Rehearsal switch in the mock grader (B).** The mock cycles statuses by syllable and line, so a retried line never turns green and the demo script below cannot be rehearsed against it. Proposal: an optional form field `mock_result` (`good`, `mistake`, `no_speech`, `fail`) that only `GRADER=mock` reads. Adding a field needs no approval.
2. **Initial and final rows have no status.** Word practice colours each initial and final row, but `Part` has only `expected`, `heard` and `score`. Without a `status`, the frontend would turn a score into a colour, which the rules forbid. Proposal: B adds `status` to `Part`. The prototype's fake grader already sends it.
3. **Best Design (Figma × MHacks):** does the track require a Figma file? If so, who makes it and when?
4. **Which message goes under the line?** The frontend task lists "one feedback message", and the `Feedback` component header names both "the feedback message" and "the suggested next step". This design shows `next_step.message` under the line and each syllable's `feedback.message` in the hover tooltip and in Word practice. B to confirm, or name the field for the line's message.
5. **Full screen on Start:** Chrome shows a "Press Esc to exit full screen" banner, and the first Record shows the mic permission prompt. Check both on the demo Mac. If they get in the way, Start enters immersive mode without full screen and the presenter presses ⌃⌘F.
6. **Suggestion, not committed:** a "Your take" button in Word practice that plays back the user's last attempt next to the reference, as ai-pronunciation-trainer does. About 0.5 h, no contract change.
7. **Dropped from earlier drafts:** a phonetic respelling row ("how" for hǎo), culture notes and an end-of-song results screen. Each needs new fields or summary rules. Revisit only after the hour-19 freeze.

## 10. Demo script (90 seconds)

1. Song screen: hover both cards (background tints, vinyl slides out), pick 茉莉花, Start → the lyrics take over the screen.
2. Line 1: press the vinyl to **Listen** (karaoke fill, vinyl spins), **Record**, sing it well → green bars grow in, scores count up.
3. Swipe up on the trackpad → line 2 springs into place. Sing it with one deliberate mistake → one word turns red; the message names the word to practise; that word has an accent ring.
4. Click that word → it grows into the practice card → **Listen** → say the word → initial and final results (and tone from stage 3). Say it again until it turns green: "Nailed it."
5. **Sing the line again** → the word turns green.
6. Press `F` → expanded mode, to show the judges every control and the keyboard hints.
7. If checkpoint B passed: back to songs, choose **Singing accuracy**, sing a line → Rhythm appears in the score row.

## 11. Prototype

A single-file clickable prototype exists outside this repo; ask A for it. It is a design reference, not the app: the app is written during the event, against the mock grader.

It shows everything in this document with a fake in-browser grader: both display modes, the Aa menu, swiping between lines, Word practice from first mistake to success, and both modes' score rows (singing accuracy adds a made-up Rhythm score). With Rehearsal on Auto, the first attempt at lines 2, 4 and 6 comes back with a mistake and every other attempt is good, so the demo script plays out without touching the menu.

Checked in headless Chrome at 1440×900 and 1280×720. Not yet checked by hand: a real trackpad's momentum, a real mouse wheel, touch, browser full screen, and speech playback, which needs a Chinese voice on the Mac.

| Screen | File |
|---|---|
| Immersive, after a clean line | [screens/immersive-result.jpg](screens/immersive-result.jpg) |
| A word to practise | [screens/mistake.jpg](screens/mistake.jpg) |
| Word practice, after a wrong attempt | [screens/practice-wrong.jpg](screens/practice-wrong.jpg) |
| Word practice, success | [screens/practice-success.jpg](screens/practice-success.jpg) |
| Expanded mode with the Aa menu | [screens/expanded-menu.jpg](screens/expanded-menu.jpg) |
| Mode choice | [screens/mode-choice.jpg](screens/mode-choice.jpg) |
