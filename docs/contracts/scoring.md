# Contract: scoring rules

**Keeper:** B. **Used by:** B, C, D.

These rules decide every number and colour the user sees. All of them run in the backend. The numbers are starting values that we tune on our own recordings.

## Who computes what

| Value | Computed by | Where |
|---|---|---|
| Component scores on the Whisper base (initial, final) | B | `scoring/matcher.py` |
| Component scores with the CTC layer on | C | `scoring/ctc.py` |
| Rhythm score, per syllable and per line | C | `scoring/rhythm.py` |
| Tone score | D | `scoring/tone.py` |
| Syllable score, status, word roll-up, overall scores, feedback | B | `scoring/grader.py`, `scoring/feedback.py` |

Every score is an integer from 0 to 100.

## Per syllable

- Each syllable has an initial (the opening consonant) and a final (the rest). Each gets a component score.
- On the Whisper base, a component is 100 for an exact match, 60 for a commonly confused pair, 20 for any other mismatch, and 0 if the syllable is missing.
- With the CTC layer on, a component is a continuous value from 0 to 100. When a confused variant wins over the expected sound, the score should land at 60 or below, so the two layers stay comparable.
- Commonly confused pairs: zh/z, ch/c, sh/s, j/zh, q/ch, x/sh, n/l, an/ang, en/eng, in/ing, ian/iang, uan/uang, uen/ueng. The table lives in `scoring/confusions.py` and both layers import it.
- Syllable score = 0.43 × initial + 0.57 × final. If the syllable has no initial, the score is the final alone.
- If the syllable has no initial but one was heard (果 guǒ for 我 wǒ), the initial is scored as an other mismatch (20) against an empty expected initial, and the weights above apply.
- Status: `good` at 85 or above, `ok` from 70 to 84, `wrong` below 70, and `missing`. These bands apply to the sound score. A syllable that would be `good` on sound, but whose heard tone differs from the expected tone, takes the status of its tone score instead, and is never `good`: a tone score still at 85 or above becomes `ok`. A wrong tone is capped at 60, so in practice the status is `wrong`. The syllable's own score stays the sound score. An unmeasured tone (`heard` null) does not change the status.
- Rhythm never changes a syllable's status, in either mode, so word colour is pronunciation only (and tone in Word practice). Rhythm is reported in `scores.rhythm`, which counts toward the singing-mode overall score, and in each syllable's `timing.offset_ms` and `timing.score`. A per-word early/late marker is implemented but disabled; see api.md, "Rhythm marker (disabled)".

On the Whisper base, those thresholds work out as follows:

| Initial | Final | Syllable score | Status |
|---|---|---|---|
| Exact (100) | Exact (100) | 100 | good |
| Confused pair (60) | Exact (100) | 83 | ok |
| Exact (100) | Confused pair (60) | 77 | ok |
| Other mismatch (20) | Exact (100) | 66 | wrong |
| Added where none expected (20) | Exact (100) | 66 | wrong |
| Confused pair (60) | Confused pair (60) | 60 | wrong |

## Per word

- Word score = mean of its syllable scores.
- Word status = the worst status among its syllables, so one wrong syllable marks the whole word.

## Per attempt

- Pronunciation = mean syllable score over the syllables that were not missing.
- Completeness = percentage of expected syllables that were not missing.
- A `null` component drops out of an overall score and the remaining weights are rescaled.

| Context | Overall | Before stage 3 |
|---|---|---|
| Line, spoken-accuracy mode | 0.71 × pronunciation + 0.29 × completeness | Same |
| Line, singing-accuracy mode | 0.60 × pronunciation + 0.25 × completeness + 0.15 × rhythm | 0.71 × pronunciation + 0.29 × completeness |
| Word practice | 0.40 × pronunciation + 0.10 × completeness + 0.50 × tone | 0.80 × pronunciation + 0.20 × completeness |

The singing-accuracy weights are the ones from our research notes. The spoken-accuracy weights are the same ones without rhythm. In Word practice tone carries half the overall score: with 0.30, a word said with the wrong tone (tone score 52–60) still scored 86–88 on our recordings; with 0.50 it scores 76–80. Completeness is low because a single word is almost always either fully heard or not heard at all. Lowering completeness for a line would reward skipping syllables, because missing syllables drop out of pronunciation.

## How each layer works

### Whisper base (stage 1, owner B)

Transcribe the recording with Whisper, convert the transcript to syllables, and line them up against the expected syllables, treating confused pairs as near-matches. For a line the expected syllables are the whole line. In Word practice they are the one word.

- If Whisper returns the same character as the lyric, it counts as a match whatever reading that character has.
- A different character with the same sound also counts as a match. Whisper often returns one for a word spoken on its own.
- We do not give Whisper the expected text as a hint. That would bias it toward a pass.
- We do not read tone from Whisper's output. The character it picks mostly reflects which word is likely as text, not the pitch the user produced.

### CTC layer (stage 2, owner C)

Run the CTC model once on the recording and align the expected pinyin (without tones) to it. This gives each syllable's start and end. Then compare each expected syllable against its confused variants on the same audio.

- The best-scoring variant is `heard`, and how clearly the expected one wins sets the component score.
- A near-empty span means the syllable is missing.
- When this layer is on, its component scores replace the Whisper base's. Whisper still decides `no_speech` and supplies the transcript.

### Rhythm (stage 3, singing-accuracy mode, owner C)

Compare when the user starts each syllable with when the original singer does.

- The original singer's syllable times come from `song.json`, filled by `align_track`.
- The user sings unaccompanied, so tempo and starting point are removed first: fit a straight line from the original times to the user's times and score what is left over.
- Each syllable scores 100 × e^(−error / 400 ms), the formula from our research notes. The rhythm score is the mean.
- Lines with fewer than three aligned syllables get no rhythm score.
- A syllable whose rhythm score is below 85 is early when `offset_ms` is negative and late when it is positive. That is what `RHYTHM_EARLY` and `RHYTHM_LATE` report. Sound and tone messages still come first.

### Tone (stage 3, Word practice, owner D)

Extract the pitch contour inside each syllable's span and express it in semitones relative to the median pitch of the recording. Compare it with the four standard tone shapes: high level, rising, dipping, falling.

- Each shape may stretch to between 0.5 and 2 times its size to fit the speaker's pitch range. The closest stretched shape is `heard`.
- Score = 100 × e^(−distance / 6 semitones), where distance is the RMS gap to the expected shape. If another shape fits better, the score is capped at 60.
- The shapes on the five-level scale are 55, 35, 214 (21 when the third tone is not the last syllable of the word) and 51. One level is 2.5 semitones.
- Expected tones follow tone sandhi, applied in this order:
  - 一: second tone before a fourth or neutral tone, fourth before any other tone, first tone at the end of a word or after 第.
  - 不: second tone before a fourth tone, otherwise fourth.
  - 一 or 不 between two copies of the same character (想一想, 好不好) is neutral.
  - In a run of third tones, all but the last are said as second tones.
- The neutral tone is not scored. A syllable with under 50 ms of voiced pitch gets `heard` and `score` of `None`.
- These numbers come from synthetic voices and must be tuned on real recordings. They are constants at the top of `app/scoring/tone.py`.
- A single-syllable word uses the whole voiced part of the recording, so it does not depend on the CTC layer. A word of two or more syllables needs the CTC layer's spans.
- In a word of two or more syllables, a syllable's pitch is read from the start of its span to the start of the next syllable's span. CTC spans mark only where a syllable is recognised, often under half of it. The last syllable, and one followed by a syllable without a span, is read to the last voiced frame, for at most 400 ms.
- A single syllable is compared by shape only. In a longer word, three quarters of each syllable's own mean pitch is removed from it and from the shapes, so shape counts most and height relative to the recording's median still counts a little. This lets a low, flat third tone inside a word (雨 in 雨天) be told apart from a level first tone.
- On synthetic speech these two rules raised correctly recognised syllables in two-syllable words from 22% to 59%. In whole spoken lines the figure rose from 39% to 74%, and to 66% on voices not used to choose the numbers. On our own spoken line takes the tone checker is still near chance, so tone is not scored on lines.

## Feedback

Each syllable carries at most one feedback message. When a syllable has several problems, the grader picks one in this order: missing, initial or final, tone, rhythm.

| Code pattern | Example | Supplied by |
|---|---|---|
| `MISSING` | "We didn't hear this syllable." | B |
| `INITIAL_<expected>_<heard>` | `INITIAL_ZH_Z` | B |
| `FINAL_<expected>_<heard>` | `FINAL_AN_ANG` | B |
| `INITIAL_OTHER`, `FINAL_OTHER` | Generic message for pairs not in the table | B |
| `TONE_<expected>_<heard>` | `TONE_3_2` | D |
| `RHYTHM_EARLY`, `RHYTHM_LATE` | "You came in early here." | C |

Messages live in `scoring/feedback.py`. C and D add the rows for their own codes.
