# Design: user interface

**Keeper:** A. **Used by:** A, and anyone preparing the demo.

**Status:** draft v0.11, 3 October 2026. Follows [PROJECT_PLAN.md](../PROJECT_PLAN.md) revision 5.

This document holds the frontend's visual design and interaction details. It does not restate behaviour or data. When it disagrees with these files, they win:

- [tasks/frontend.md](../tasks/frontend.md): screens, line-screen states, rules, deliverables, implementation notes.
- [contracts/api.md](../contracts/api.md): every request and every field.

Screenshots of the clickable prototype are in [screens/](screens/).

## 1. What this adds to the frontend task

| Topic | tasks/frontend.md | This document |
|---|---|---|
| Look | Not specified | Per-song colour themes, glass surfaces, Hanzi and Pinyin type, motion (section 3) |
| Song screen | "A list of songs" | One full-screen photograph per song with a huge hairline title, and a huge stylized record whose label is the song's album cover. Spinning the record changes songs, three in view at a time, looping; the picture dissolves through static between them (section 5.1) |
| Word chips | "Each word as a coloured chip" | The lyric's own words are the chips: a status bar under each word, no second row of words (section 5.3) |
| Line-screen controls | Header, line, buttons | One look. The dock shows only the current step's actions; one **Aa** pill opens every control and option (section 5.3.1) |
| Moving between lines | Retry, Next line, progress | Also swipe with a trackpad, mouse wheel or touch, one line per gesture (section 5.3.3) |
| Starting a song | A Start button | No window: the song screen's photo blurs into the line screen's background and the lyrics rise in. The mode choice and the microphone prompt are inline (sections 5.1, 5.2) |
| Word practice | A panel over the line screen | In place: the word moves to the exact centre of the screen, the lyrics step back, and the dock carries the practice actions until the word is graded `good` (section 5.4) |
| Coach | Not specified | The feedback message is the coach speaking; later, the same spot opens a conversation (section 5.5) |

## 2. Goals

1. Make the **listen → sing → see each word → practise a word** loop feel effortless and fun on a laptop. While singing, the lyrics fill the screen and controls appear only when needed.
2. Make the per-word feedback (Hanzi + Pinyin + status colour) the visual signature of the product, the thing judges remember.
3. Look polished enough to compete in **Best Design (Figma × MHacks)**.
4. Be explainable to judges who don't speak Chinese in under 10 seconds.

Non-goals, as in the frontend task: mobile layout, accounts, saved history.

## 3. Visual direction

**One-line pitch:** a Beautiful-Lyrics / Apple-Music-style immersive lyric view, with NetEase Cloud Music touches (vinyl record, glass surfaces), plus our own per-word grading layer.

| Borrow from | What we take | What we avoid |
|---|---|---|
| [beautiful-lyrics](https://github.com/surfbryce/beautiful-lyrics) | Dynamic background blended from the song's colours; big centred lyrics; word-by-word karaoke fill; cinema feel | Spotify chrome (sidebars, library) |
| NetEase Cloud Music (网易云) | Spinning vinyl as the "now playing" object; soft glass surfaces | Red theme, dense layouts |
| Duolingo | One clear action per moment; encouraging tone | Gamification clutter (streaks, gems) |
| Award-winning sites on Awwwards (By-Kin, Iventions, Uncommon Studio) | Editorial type with extreme size contrast; one thing in the spotlight at a time instead of a grid | Spectacle that slows the page |

### 3.1 Colour

- **Per-song theme.** Each song has five colours: `c0` (base), `c1`–`c3` (background blobs) and `accent` (primary buttons, record button, highlights). Themes live in the frontend (`src/theme/songThemes.ts`, keyed by song id). They are design assets, not part of the API contract.
- **The theme always belongs to a song.** The song screen shows the selected song's theme; switching songs crossfades every colour on the page over about a second. Register the five colours with CSS `@property` so they animate.
- **Background:** the song's photograph. Sharp and slowly pushing in on the song screen; blurred (46px), saturated and darkened on the line screen, so the song's colours stay with the user. Fallback without a photo: blurred blobs in `c1`–`c3` over `c0`.
- **Film grain** over everything: an SVG noise texture, jittered at 8 frames a second, blended with `overlay` at about 10% (7% on the line screen). It rises towards 45% while the dial is between two songs.
- **Scrim:** 35–45% black over the background, so white text always passes contrast.
- **Text:** white at 100% (active line), 55% (upcoming), 30% (past).
- **Status colours**, the same everywhere in the app. The shape cue keeps them readable without colour:

| `status` | Colour | Shape cue on bars and dots |
|---|---|---|
| `good` | `#4ADE80` green | solid |
| `ok` | `#FACC15` yellow | half-filled |
| `wrong` | `#F87171` red | hollow |
| `missing` | `#94A3B8` grey | dashed outline |

Starting themes:

| Theme | c0 | c1 | c2 | c3 | accent |
|---|---|---|---|---|---|
| 茉莉花 | `#0f231a` | `#2f6b4f` | `#d9e4c4` | `#5f9c7a` | `#f4f1d6` |
| 一剪梅 | `#1d1222` | `#7a2f4f` | `#e7b8c6` | `#4a3a6b` | `#f8d3de` |
| 月亮代表我的心 | `#161230` | `#3b2f78` | `#f2cf7a` | `#6b4fa0` | `#f7dd99` |

Glass surfaces: dark 34% fill, 24px blur, 1px border in white 14%. Easing for UI motion: `cubic-bezier(.2,.8,.2,1)`.

### 3.2 Typography

- **Hanzi:** Noto Serif SC. 200 (hairline) for the song screen's titles; 700 for lyric lines, the dial and the practised word. Active line 60px (52px under 760px tall), other lines 30px, the practised word up to 150px.
- **Pinyin:** Instrument Sans 500, about 40% of the Hanzi size, **above** each character (ruby style), centred per syllable.
- **UI text:** Instrument Sans 13–16px. The size contrast between the Hanzi and the UI text is the design; keep the UI text small and quiet.
- **Self-host both fonts** with the `@fontsource` packages. Venue Wi-Fi is a risk (plan section 8).

### 3.3 Motion

Two springs, sampled into CSS `linear()` easings so CSS and JavaScript share them:

- **Line spring** (slight overshoot, about 500ms): moving between lines.
- **Soft spring** (almost no overshoot, about 300ms, like motion-primitives' toolbars): the dock and the options pill changing size. Their new contents fade in 30–40ms apart once the size has settled.

Moments:

- **Spinning the record (song screen):** the record follows the wheel, trackpad or drag continuously, 45° per song, and settles on a song with a spring when the gesture ends. It also turns slowly while a preview plays. On the way, the two photos crossfade and blur, the grain thickens into static (and, with sound on, radio static rises), and the title, copy and theme switch when the dial passes halfway. The new title's characters arrive one by one, out of a blur.
- **Starting a song:** the title's characters drift up and blur out, the dial turns away to the right, the photo blurs and darkens into the line screen's background, and the lyric lines rise in one after another, followed by the dock.
- **Karaoke fill during Listen:** each character fills left to right, in time with the singer. Each character starts filling 80 ms before its syllable's aligned `start_ms` (from `song.json`) and is full 400 ms after, or when the next syllable starts if that is sooner, so the colour keeps pace with the voice and a held note stays full rather than filling slowly across it. A syllable the aligner missed is spaced evenly between its timed neighbours. Constants: `FILL_LEAD_MS`, `FILL_MAX_MS`. A song with no aligned syllable splits the line's time evenly. Logic: `syllableStarts` and `fillFractions` in `frontend/src/logic/timing.ts`.
- **Changing line:** the list moves so the active line sits 40% from the top. The active line's growth and the list's movement animate together, so no other line jumps: measure before and after, then animate the difference with transforms (FLIP).
- **Swipe:** on touch, the list follows the finger. Past the first or last line, it stretches a little and springs back.
- **Result reveal:** each word's status bar grows in, left to right, 60ms apart; scores count up.
- **Word practice:** the word grows from its place in the lyric to the middle of the screen (View Transitions, `pword`); the lyrics fade to 12%, blur a little and shrink to 98%. Closing reverses it, and the word lands back in its slot.
- **Practice success:** the word turns green and one soft ring expands from it.
- **Buttons:** scale to 97% while pressed.
- **Header:** fades in on pointer movement and out after 2.5s of stillness, unless the controls are open, a word is being practised or the coach is open. The cursor hides with it.
- Respect `prefers-reduced-motion`: no drift, stagger, count-up, spin, morph or ring; changes happen without movement.

### 3.4 References (GitHub and Awwwards)

Checked on 2026-10-03. We copy behaviour and look, not code, except where the license allows it.

| Used for | Source | What we take | Can we use the code? |
|---|---|---|---|
| Look | [surfbryce/beautiful-lyrics](https://github.com/surfbryce/beautiful-lyrics) (~2.4k★) | Colour-matched background, word-synced lyrics, cinema view. **Main visual reference.** | No license: look only |
| Look | [amll-dev/applemusic-like-lyrics](https://github.com/amll-dev/applemusic-like-lyrics) (~2.2k★) | Apple Music style lyrics with a fluid background | AGPL-3.0: look only |
| Song screen | Awwwards Sites of the Day, late Sep–Oct 2026: [Tengile Malamala](https://tengilemalamala.com), [White Desert](https://white-desert.com), [Warm & Fuzzy](https://warmnfuzzy.tv) | Full-bleed photography with huge display type laid over it; a thin serif split across two staggered lines; visible film grain; almost no chrome | Look only |
| Song record | Awwwards inspiration: [Throwbacks Music circular menu](https://www.awwwards.com/inspiration/circular-menu-navigation-this-is-spotify), [KUROKAWA WONDERLAND clock-like navigation](https://www.awwwards.com/inspiration/clock-like-navigation) | Browsing a small music collection by turning a wheel | Look only |
| Album covers | Found with the iTunes Search API: 鳳飛飛《鳳飛飛 金賞輯 3》(1971) for 茉莉花, 費玉清《清韻悠揚 精選（一）》(1983) for 一剪梅, 鄧麗君《島國之情歌 第四集 香港之戀》(1977) for 月亮代表我的心 | The cover of the recording we sing along to, as the record's label | Copyrighted. Fine to show in the demo; keep them out of this public repo (section 9, question 7) |
| Song photos | Unsplash: [Irina Iriser](https://unsplash.com/photos/vB4_CtsfaZ0) (茉莉花), [yamasa-n](https://unsplash.com/photos/SPEUTg0phCg) (一剪梅), [Laura Cleffmann](https://unsplash.com/photos/gRT7o73xua0) (月亮代表我的心) | One photograph per song | Unsplash License: free to use; credit shown on the song screen |
| Options pill, dock | [ibelick/motion-primitives](https://github.com/ibelick/motion-primitives) (~6.5k★) | `toolbar-expandable` and `toolbar-dynamic`: spring with bounce 0.1 over 0.2–0.25s, measured width, contents fading in | MIT: **use the patterns** |
| React animation | [motiondivision/motion](https://github.com/motiondivision/motion) (~34k★) | `layout` and `layoutId` for the word-to-centre move and the dock's size changes in the React build | MIT: **use it** |
| Word practice | [Thiagohgl/ai-pronunciation-trainer](https://github.com/Thiagohgl/ai-pronunciation-trainer) (~0.5k★) | Words coloured by correctness; clicking one shows the expected and heard sounds | AGPL-3.0: look only |
| Coach drawer | [emilkowalski/vaul](https://github.com/emilkowalski/vaul) (~8.6k★) | How a drawer should move and dismiss | MIT |
| Swipe | [amll-dev/applemusic-like-lyrics](https://github.com/amll-dev/applemusic-like-lyrics), `scroll.ts` | A wheel gesture ends after 150ms without events; wheel steps animate with a spring | AGPL-3.0: look only |
| Swipe | [xiel/wheel-gestures](https://github.com/xiel/wheel-gestures) (<0.1k★) | Tells a new trackpad swipe apart from the momentum of the previous one | MIT: **use it** |

## 4. Layout

Target viewport **1440×900**; must work at **1280×720** (projector). Below 1024px wide, show a "built for laptops" notice. The window goes full screen only when the user presses `F`.

### 4.1 Song screen

```
┌──────────────────────────────────────────────────────────────────────┐
│ ◉ Karaoke Helper                    (full-screen photo)  (Sound on)  │
│ Learn Mandarin by singing the songs you love.        ╭───────────────│
│ 1 Listen  2 Sing it back  3 See every word …      ╭──╯  03 月亮代表… │
│                                                  │  ring text ╭──────│
│   茉 莉              ← hairline serif, sized to  │           │ album │
│        花               stop 72px short of the  │ ── 01 茉莉花 │ cover │
│        mò lì huā   Jasmine Flower     record     │    鳳飛飛  │ label │
│        A Jiangsu folk song, as 鳳飛飛 sang it …  │           ╰──────│
│        [ Sing 茉莉花 ]                            ╰──╮  02 一剪梅     │
│                                                     ╰───────────────│
│                好一朵美丽的茉莉花   ← subtitle: live fill + bars       │
│          Photo: Irina Iriser, Unsplash   Cover: 鳳飛飛《…》, 1971      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Line screen, controls closed (the default)

```
┌──────────────────────────────────────────────────────────────────────┐
│  (header fades in on pointer movement:  ← Songs  茉莉花 2/7     (Aa)) │
│                     (past lines, faded)                            ╷ │
│              hǎo   yì duǒ  ╭měi lì╮✓  de                         ┃ │ ← line rail
│              好    一朵    │美丽 │   的         ← active line       │ │
│              ▬▬    ▬▬▬▬    ╰▭▭▭▭─╯   ▬▬         ← status bars       ╵ │
│             What a beautiful jasmine flower                          │
│             Overall 96   Pronunciation 95   Completeness 100         │
│             We heard 好一朵买丽的茉莉花                                │
│        ╭───────────────────────────────────────────────────╮        │
│        │ (教) Say 美丽 (měi lì) on its own, then retry.  [Ask why] │ ← coach
│        ╰───────────────────────────────────────────────────╯        │
│                    ╭────────────────────────────╮                    │
│                    │ (◉)   ↻   [  Next line  ]  │   ← dock           │
│                    ╰────────────────────────────╯                    │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.3 Line screen, controls open

```
│  ← Songs  茉莉花  2 / 7  [Spoken accuracy]   ( • Pinyin  • Translation ✕) │
│                                          ( Next result: Auto Good … )   │ ← only with ?demo
│                          (same lyrics)                                   │
│   Space record  L listen  R retry  Enter next  ↑↓ change line  E hide    │
│        ╭──────────────────────────────────────────────────────╮         │
│        │ (◉) Listen   [● Record]   [↻ Retry]   [ Next line ]   │         │
│        ╰──────────────────────────────────────────────────────╯         │
```

- **Lyric column:** centred, max width 760px. It moves left only to make room for the coach drawer.
- **Header:** no bar. Back, title, line count and mode badge on the left; the options pill on the right; a soft gradient behind them.
- **Dock:** glass pill, bottom centre, 26px above the edge. Closed, it holds only what the current step needs; open, it holds every control with labels.
- **Line rail:** one short tick per line on the right edge. The active line's tick is longer and brighter.

## 5. Screens

### 5.1 Song screen: tune the dial

- **The photograph is the page.** Each song has one photograph, full screen, slowly pushing in, under a soft left-to-right and bottom shade and the film grain. The theme colours come from the same song.
- **The title is the bold element.** Noto Serif SC at weight 200, about 19% of the screen height, split over two staggered lines (茉莉 / 花, 月亮代表 / 我的心). It is measured after rendering and its characters (not the indent) shrink until every line ends at least 72px before the record. Under it, aligned with the second line: pinyin and English, one sentence about the song, and **Sing 茉莉花** on its own.
- **Sing opens into the mode choice.** When `VITE_SHOW_MODE_CHOICE` is on, pressing Sing (or Enter) springs the same pill open into **Spoken accuracy**, **Singing accuracy** and ✕. While it is open, the song's description above the pill gives way to a line explaining whichever option the pointer or focus is on; both share one slot, so the pill does not move, and the description sits clear of the background. Choosing one starts the song. Esc, ✕ or a click elsewhere closes it again. When the flag is off, Sing starts the song in spoken accuracy.
- **The record.** On the right, a stylized record about 1.1 screen-heights across, its centre just inside the right edge. Graphic rather than realistic: fine grooves, two track gaps, and a sheen in the song's own colours that stays still while the grooves turn.
- **Collage where the record meets the photo.** The record is a torn-paper cut-out pasted onto the photograph: a torn edge (SVG turbulence masks), a fringe of off-white paper with a paper shadow, and three scraps overlapping the rim, all cut from the song's own photo and each a different shape: a wide torn piece held by a strip of translucent tape, a narrow torn strip, and a round cut that echoes the record. Each shows an enlarged detail of the photo (a flower, part of the moon). The photo seems to run onto the record. Its label is the album cover of the recording we use, with a ring of small text around it (artist, album, year, title). The covers crossfade as it turns.
- **The songs ride the groove band,** between an accent needle on the rim and the label: number, title (sized to fit the band) and artist, plus "Playing a preview" on the selected one. Each name is tilted to the record's angle at its position, as if printed on it, and turns with it. At most three are in view: the selected one at the needle (level, 0°), one above at 45° and one below at −45°, measured from the record's centre. They loop: after the last song comes the first. Spin it with the wheel or trackpad, by dragging, with ↑ ↓ ← →, or by clicking a song. One wheel notch or one short swipe moves one song; a long swipe can move several. A song that isn't ready still tunes in, and its button reads "Coming soon".
- **Between songs** the picture dissolves through static (section 3.3). With sound on, a faint vinyl crackle plays on the song screen and radio static rises between songs; both are generated with Web Audio and need no files. Browsers only allow sound after a click or a key press.
- **The subtitle.** At the bottom centre, like a film subtitle, one line of the song's lyric fills and grades itself on a loop, with "Sing a line back and every word gets a colour." under it.
- **Preview.** Once the dial settles, about 12 seconds of the song from `audio_url`, faded in and out. See section 9, question 3 for where the clip comes from.
- **The tonearm** is rendered with three.js, built like a real S-shaped arm: gimbal base, anti-skate dial, cue lever, S-tube, headshell with cartridge and finger lift, knurled counterweight, arm rest. A top-down orthographic camera keeps it aligned with the flat record; brushed and polished metal, a key and a fill light, a cast shadow and contact shadows give it depth. Its accent parts take the song's accent colour, and it lights up under the pointer.
- **It behaves like a real turntable.** Arm on the record = playing; arm on its rest = stopped.
  - Play (click the arm, the cover or `Space`): the platter spins up, the arm lifts on the cue lever, swings to the record's lead-in just above the selected song, and sets down; then the preview and the crackle start. While it plays, the stylus creeps slowly inward.
  - Stop: the arm lifts, swings back and sets down on its rest; then the platter slows to a stop.
  - The cover works like a video player's play button. Stopped, it is dimmed and shows ▶. Playing, it shows nothing until the pointer is on it; then it dims and shows ⏸. The sign always shows the action a click will take. Pointing at the sign brightens it; it never grows. On a toggle the sign morphs: the two pause bars fold into the two halves of the triangle in about 240 ms, as on YouTube.
  - Changing songs while it plays lifts the arm on the cue lever; it sets down again when the record settles.
  - On first load the record starts like a real one: the arm moves from its rest onto the record.
- **Sound** on and off is the cap on the tonearm's pivot, with a speaker icon (or `M`). Clicking anywhere else on the arm plays or stops the record.
- **Credits** for the photo and the cover sit small in the bottom-left corner.
- **Starting the song** opens no window (section 3.3).

### 5.2 Microphone setup (first Record only)

No window. The first time the user presses Record, the dock turns into the prompt: "Recording needs your microphone", **Allow microphone**, "Use a simulated mic" and ✕. Once allowed, it shows a live level meter with "Say 你好 (nǐ hǎo) to test it" (a green check when sound is detected) and **Start recording**. Nothing is sent. Microphone settings follow the frontend task's implementation notes.

### 5.3 Line screen

The states and their rules are in the frontend task. This is what each state looks like:

| State | What the user sees | Dock, closed |
|---|---|---|
| `idle` | Active line highlighted; its previous result, if any, under it | Vinyl, labelled "Listen" |
| `listening` | The line plays; karaoke fill sweeps the line; vinyl spins | Spinning vinyl, labelled "Playing"; press it to stop |
| `ready` | Line at rest | Vinyl (listen again) · **Record** |
| `recording` | Ring pulses with the input level; a thin bar shows time used out of the limit | Vinyl (disabled) · **Stop** with the elapsed time |
| `grading` | The line breathes; "Listening back…" | Vinyl (disabled) · "Listening back…" |
| `result` | Status bars grow in, scores count up, what we heard, the coach's message | Vinyl · ↻ · **Next line** |
| request failed | Message under the line; the recording is kept | Vinyl · **Send again** |

- When `next_step.type` is `retry_line`, Retry is the primary action in `result` instead of Next line.
- On the last line, Next line reads "Back to songs".
- `no_speech`: "We didn't hear anything. Move closer to the mic and sing again." under the line, then `ready`. Clear the previous score row, transcript, feedback and word grades. Revisiting the line must not restore an older grade after this retry.

**After grading:**

- **The words are the chips.** Each word gets a bar under it in its `status` colour and shape, and the pinyin of a word that is not `good` takes the same colour. There is no second row of words.
- If `next_step.type` is `practice_word`, that word gets an accent ring that pulses once.
- Under the line: the translation, the score row (every score that is not `null`: Overall, Pronunciation, Completeness, then Rhythm, Tone and Melody when the backend sends them), "We heard" with `heard.hanzi` and its pinyin, and the coach bubble (section 5.5).
- Results with `engine: "mock"` show "Demo scores — your audio is not being graded." above the score row, also in Word practice.

#### 5.3.1 Controls: closed and open

One look in both. Opening the controls never changes the window size; `F` alone does that.

| | Closed (default) | Open |
|---|---|---|
| Dock | The current step's actions only | Every control with a label: Listen (the vinyl), Record, Retry, Next line. Unavailable ones are dimmed; the primary one is filled |
| Header | Fades out after 2.5s of stillness | Stays |
| Options pill | "Aa" | Grows leftwards into Pinyin and Translation switches; "Aa" turns into ✕ |
| Keyboard hints | Hidden | A row of hints above the dock |
| Rehearsal (with `?demo`) | Hidden | A small pill under the options pill: "Next result: Auto / Good / With a mistake / No speech / Request fails" |

- **Switching:** the Aa pill, `E`, or a double-click anywhere that isn't a button, a word or the coach. Esc closes the controls.
- **Full screen:** `F`, anywhere in the app, toggles the browser's full screen. Nothing else changes the window.
- **First line of a session:** a short hint, "Swipe or press ↑ ↓ to change line. Double-click anywhere for every control."

#### 5.3.2 Changing line

Four ways: swipe, `↑/↓`, click a line, click a tick on the line rail.

- **One gesture moves one line.** A trackpad swipe and its momentum count as one gesture; detect momentum with `wheel-gestures`. One mouse-wheel notch is one gesture.
- **Touch:** the list follows the finger. Releasing after more than 48px, or with a quick flick, moves one line; otherwise the list springs back.
- **The new line becomes active in `idle`,** showing its previous result if it has one. Changing line closes the coach.
- **First and last line:** swiping past them stretches the list a little, then it springs back.
- **Locked while `recording` or `grading`, and while a word is being practised.** The active line nudges 8px and settles, and during recording a hint reads "Stop recording to change line."
- **While `listening`:** a swipe stops playback and moves.

#### 5.3.3 Other interactions

- **Click a word** → practise it (section 5.4). Every graded word is clickable. Words graded `wrong`, `ok` or `missing` lift on hover and show "Practise"; `good` words open it too but show no label.
- **Practised mark:** when practice ends after a `good` attempt, a small ✓ sits on the word's corner. The word keeps its colour from the sung attempt, because colour comes only from that attempt's `status`. Singing the line again clears the mark.
- **Hover a word** (P2): a tooltip per syllable with the expected and heard initial and final.
- **Early or late** (optional, block 3): when `syllables[].timing.offset_ms` is set, the hover tooltip says "came in 120 ms early" and a small notch on the word's bar sits left (early) or right (late) of centre.
- **Keyboard:** `Space` record or stop, `L` listen, `R` retry, `Enter` next line, `↑/↓` change line, `P` pinyin, `E` controls, `F` full screen, `Esc` close whatever is open.
- **The active line sits at the vertical centre of the screen;** what is under it (translation, scores, the coach) flows below.

### 5.4 Word practice, in place

The frontend task's Word practice panel, without a panel. It sends `target=word` with the word's `word_index`.

- **Opening:** the clicked word grows from its slot in the lyric to the exact centre of the screen (pinyin above, Hanzi up to 150px). The lyrics fade to 12%, blur slightly and shrink to 98%; the line rail hides. The header's back button reads "Line 2". The layout is three rows (`1fr auto 1fr`) with the word in the middle one, so the word stays centred whatever appears under it.
- **The result is marked on the word itself.** In the pinyin above each character, the initial and the final take their own status colour and underline (dotted for `ok`, wavy for `wrong`, dashed for `missing`; `good` stays plain), and a small caption under the character says what was heard ("heard ai", "not heard"). Tone joins from stage 3.
- **Under the word:** its English meaning with one dot per graded attempt beside it, then the hint "Listen, then say the word on its own", or "Nailed it.", or the coach bubble with the syllables' feedback messages and "Ask why".
- **The dock carries the practice actions:** Listen (the spoken reference: `audio_url`, or `speechSynthesis` in `zh-CN` when it is `null`), **Record** / **Record again**, and a quiet "I'm confident" that ends practice at any time.
- **Success:** when the returned word's `status` is `good`, the Hanzi turns green, a ring expands, "Nailed it." appears, and the dock offers **Sing the line again** (primary) and Keep practising. Sing the line again ends practice and puts the line in `ready`.
- **Ending practice:** I'm confident, the back button, Esc, or a click on the faded lyrics (not while recording or grading). The word flies back into its slot.
- `no_speech`: "We didn't hear anything. Say the word a little louder." Clear the previous word grade, captions, feedback and scores, return to `ready`, and keep the earlier attempt dots. A failed request shows Send again, which resends the same recording.
- Attempts and the practised mark live in memory for the session only.

### 5.5 Coach

The plan's MVP has rule-based feedback and no LLM. This design gives the feedback a place that a conversational coach can grow into later, without moving anything.

- **MVP:** the message under the line (`next_step.message`) and the practice feedback appear as a coach bubble: a small avatar (教) and the message, on a glass surface.
- **Later:** the bubble gets an **Ask why** button. It opens a drawer on the right (384px, glass); the lyrics, the practised word and the dock move left to make room. The drawer holds the conversation, a few suggested questions, a text box and a microphone button for voice.
- **What the coach starts from:** the attempt's own data: which sound was heard instead of which (`syllables[].initial` and `.final`), the feedback message, and the song's other syllables with the same sound.
- **Behind a flag** (`VITE_SHOW_COACH`, off by default) until a coach endpoint exists. Section 9, question 4 proposes one.
- The prototype shows the drawer with scripted replies built from the attempt, and says so in the drawer.

## 6. Components and logic

The file split in `frontend/src/` is a starting point (plan section 10). This design adds or changes:

| Component | Key inputs | Notes |
|---|---|---|
| `DynamicBackground` | theme, `playing` | Drifting, or static with reduced motion |
| `PhotoBackdrop`, `Grain` | the songs' photos, dial position | Crossfades and blurs the photos; sharp on the song screen, blurred on the line screen |
| `SongRecord` | `SongSummary[]`, covers, position | Unbounded position with a settling spring, shown modulo the song count; wheel, drag, keys, click; at most three names in view |
| `SingButton` | mode-choice flag | One pill that opens into the two modes |
| `Tonearm` | playing, record geometry, accent colour | three.js (or @react-three/fiber) canvas over the record; swing with lift; hit-testing by raycast |
| `Ambience`, `PreviewPlayer` | sound on, dial position, a clip URL | Crackle and static generated with Web Audio; the preview with fades |
| `TopBar` | title, line N of M, mode, controls open | Fades when idle |
| `OptionsPill` | `showPinyin`, `showTranslation`, open, demo flag | Also the switch for the dock |
| `Dock` | actions for the state, open, input level | Renders `actionsFor(state, open)` or the practice actions; animates its width |
| `LineRail` | line count, active index | |
| `LyricLine` + `WordChips` | `Line`, `isActive`, fill, result | The words of the line are the chips |
| `WordPractice` | `Word`, its syllables, attempts | Replaces `WordPracticePanel`: no panel, the word in the middle |
| `CoachBubble`, `CoachDrawer` | message, attempt | The drawer stays behind its flag |
| `Vinyl` | theme, `spinning` | Also the Listen button in the dock |

Logic that is easy to get wrong goes in small pure modules with unit tests:

- `actions.ts`: `actionsFor(state, nextStep, open)` returns the dock's actions and which one is primary.
- `practiceMachine.ts`: the Word practice states and the attempt list; `success` only when the returned word's `status` is `good`.
- `lineSwipe.ts`: turns wheel and touch input into "up one line" or "down one line", built on `wheel-gestures`. Tested with recorded event sequences: one trackpad swipe with a long momentum tail gives exactly one step.

In React, Motion's `layoutId` gives the word-to-centre move and `layout` gives the dock's width change, so neither needs hand-written FLIP code.

## 7. Rules this design adds

The frontend task's rules all apply. In addition:

1. Word practice's success comes only from the returned word's `status` being `good`.
2. Practice attempts and practised marks are kept in memory for the session only.
3. Line changes are refused while recording, grading or practising a word.
4. The window goes full screen only when the user presses `F`.

### Where each element gets its data

| UI element | Field (contracts/api.md) |
|---|---|
| Song screen | `GET /api/v1/songs` → `SongSummary`; themes and sleeve characters from the frontend's theme file |
| Lyric line, pinyin, translation | `Song.lines[]`: `text`, `syllables[].pinyin`, `translation` |
| Karaoke fill timing | `syllables[].start_ms` when set (each character fills from 80 ms before its syllable to 400 ms after, gaps spaced evenly); otherwise the line's `start_ms`–`end_ms` split evenly |
| "N / M", line rail | `line.index`, `SongSummary.line_count` |
| Status bars | `AttemptResult.words[]`: `status`, `syllable_indices` |
| Suggested word, primary action | `AttemptResult.next_step` |
| Score row | `AttemptResult.scores` (non-`null` only) |
| We heard | `AttemptResult.heard` |
| Coach bubble | `next_step.message`; in practice, `syllables[].feedback.message` |
| Word practice word | `line.words[]`: `text`, `gloss`, `audio_url` |
| Word practice rows | `syllables[]`: `initial`, `final`, `tone` |
| Early or late notch | `syllables[].timing.offset_ms` |

## 8. Design priorities

Every item ships if time allows. The tiers set the build order: finish a tier before starting the next. The frontend task's checkpoints come first; if stage 1 isn't stable at hour 6, P1 waits. Estimates are rough, for one developer working with a coding agent.

| Tier | Hours (plan section 7) | Item | Est. |
|---|---|---|---|
| **P0 Foundation**, built into the components | 0–6 | Theme tokens (song themes, status colours, glass, easing, springs) | 0.5 h |
| | | Self-hosted fonts | 0.25 h |
| | | Hanzi + Pinyin ruby layout and type scale | 1 h |
| | | Status bars with colour and shape cues | 0.5 h |
| | | Static theme gradient and scrim | 0.25 h |
| | | Line screen layout at 1440×900 and 1280×720: header, dock, rail; narrow-screen notice | 0.75 h |
| | | Options pill and the open state of the dock | 0.75 h |
| | | Word practice in place: layout, dock actions | 0.75 h |
| | | Coach bubble | 0.25 h |
| **P1 Signature moments** | 6–13 | Song screen: photos, hairline title, dial, dissolve through static, entering a song | 2.5 h |
| | | Status bars grow in; scores count up | 1 h |
| | | Karaoke fill during Listen | 1.5 h |
| | | Line change with a spring and no jumping lines | 1 h |
| | | Swipe between lines: wheel-gestures, touch, stretch at the ends, lock | 1.5 h |
| | | Word grows into the middle and back (`layoutId`) | 1 h |
| | | Practice loop: attempt dots, success moment, practised mark | 1 h |
| | | Dock and pill springs, header fade, cursor hide | 0.75 h |
| **P2 Atmosphere** | 13–19 | Dynamic drifting background | 1.5 h |
| | | Song previews with fades | 1 h |
| | | Vinyl spins while audio plays | 0.5 h |
| | | Record-button ring driven by the input level | 0.5 h |
| | | Word hover tooltip | 1 h |
| | | Line rail | 0.5 h |
| | | `prefers-reduced-motion` | 0.5 h |
| **P3 Finish** | before the hour-19 freeze | Keyboard shortcuts and hints | 1 h |
| | | Loading and grading states | 0.5 h |
| | | Microphone prompt in the dock | 0.5 h |
| | | Crackle and static ambience | 0.5 h |
| | | Tonearm (three.js) and real turntable behaviour | 2.5 h |
| | | Collage edge: torn paper, scraps, tape | 1 h |
| | | Optional: early or late notches from `timing.offset_ms` | 1 h |
| **Beyond the MVP** | after the freeze, or after the event | Coach drawer and conversation | not estimated |

Total is about 24 hours of design work on top of the functional work. P1 alone is 9.75 hours in a 7-hour window, so it needs B's help after checkpoint A, as the plan already provides. If the hour-19 freeze arrives first, whatever tier is complete is what we demo.

## 9. Open questions

1. **Rehearsal switch in the mock grader (B).** The mock cycles statuses by syllable and line, so a retried line never turns green and the demo script below cannot be rehearsed against it. Proposal: an optional form field `mock_result` (`good`, `mistake`, `no_speech`, `fail`) that only `GRADER=mock` reads. Adding a field needs no approval.
2. **Initial and final rows have no status.** Word practice colours each initial and final row, but `Part` has only `expected`, `heard` and `score`. Without a `status`, the frontend would turn a score into a colour, which the rules forbid. Proposal: B adds `status` to `Part`. The prototype's fake grader already sends it.
3. **Where the song preview comes from (B and D).** `SongSummary` has no audio. Options: add `preview_url` and `preview_start_ms` to `SongSummary` (D picks a chorus when building the bundle), or fetch the full `Song` on each switch and start at line 1. Adding fields needs no approval.
4. **A coach endpoint, after the MVP.** Proposal: `POST /api/v1/coach` with `attempt_id` and the conversation so far, returning a reply and, optionally, an `audio_url` of the reply spoken. A spoken coach would also fit the ElevenLabs sponsor track.
5. **Which message goes under the line?** The frontend task lists "one feedback message", and the `Feedback` component header names both "the feedback message" and "the suggested next step". This design shows `next_step.message` under the line and the syllables' `feedback.message` in Word practice. B to confirm.
6. **Best Design (Figma × MHacks):** does the track require a Figma file? If so, who makes it and when?
7. **Photos and covers for each song.** Each song needs a photograph that can be used freely (Unsplash License or our own) and the album cover of the recording we use. Covers are copyrighted: fine on the demo screen, but they should not be committed to this public repo. Proposal: D adds `cover_url` (and the album, artist and year) to the song bundle and keeps the image out of git, like the track itself. Who picks the photos?
8. **Dropped from earlier drafts:** a phonetic respelling row ("how" for hǎo), culture notes, an end-of-song results screen, and the mode-choice window. The first three need new fields or summary rules; revisit only after the hour-19 freeze.

## 10. Demo script (90 seconds)

1. Song screen: turn the dial from 茉莉花 to 一剪梅 and back (the jasmine dissolves through static into plum blossom and back), then **Sing 茉莉花**: the title drifts away and the photo becomes the background.
2. Line 1: press the vinyl to **Listen** (karaoke fill), **Record**, sing it well → green bars grow in, scores count up.
3. Swipe up on the trackpad → line 2 springs into place. Sing it with one deliberate mistake → one word turns red; the coach names the word to practise; that word has an accent ring.
4. Click that word → it grows into the middle of the screen as the lyrics step back → **Listen** → say the word → initial and final results (and tone from stage 3). Say it again until it turns green: "Nailed it."
5. **Sing the line again** → the word flies back into the line; sing it → it turns green.
6. Tap **Aa** → every control and option appears, to show the judges.
7. If checkpoint B passed: back to songs, choose **Singing accuracy**, sing a line → Rhythm appears in the score row.

## 11. Prototype

A single-file clickable prototype lives in [frontend/prototype/](../../frontend/prototype/). It is a design reference, not the app: the app is written during the event, against the mock grader.

To run it, serve that folder (`cd frontend/prototype && python3 -m http.server 5180`) and open `http://localhost:5180/?demo`. `?demo` shows the Rehearsal switch. The album covers in `assets/covers/` are copyrighted, so `.gitignore` keeps them out of the repo; without them the record labels on the song screen are blank. Ask A for them.

It shows everything in this document with a fake in-browser grader, including the song screen, both control states, swiping, Word practice in place from first mistake to success, and the coach drawer with scripted replies. The song preview is shown, not heard: the prototype has no audio files. With Rehearsal on Auto, the first attempt at lines 2, 4 and 6 comes back with a mistake and every other attempt is good, so the demo script plays out without touching the controls.

Checked in headless Chrome at 1440×900 and 1280×720. Not yet checked by hand: a real trackpad's momentum, a real mouse wheel, touch, and speech playback, which needs a Chinese voice on the Mac.

| Screen | File |
|---|---|
| Song screen | Not committed: it shows album covers, which are copyrighted. See the prototype. |
| Microphone prompt in the dock | [screens/mic-prompt.jpg](screens/mic-prompt.jpg) |
| Line screen, controls closed | [screens/immersive-result.jpg](screens/immersive-result.jpg) |
| Line screen, controls open | [screens/controls-open.jpg](screens/controls-open.jpg) |
| A word to practise | [screens/mistake.jpg](screens/mistake.jpg) |
| Word practice, after a wrong attempt | [screens/practice-wrong.jpg](screens/practice-wrong.jpg) |
| Word practice with the coach drawer | [screens/coach.jpg](screens/coach.jpg) |
| Word practice, success | [screens/practice-success.jpg](screens/practice-success.jpg) |
