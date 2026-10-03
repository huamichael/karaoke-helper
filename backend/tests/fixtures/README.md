# Test fixtures

Shared recordings and expected lines that every backend task tests against.

- `lines/<name>.json`: one `Line` object, the expected syllables.
- `audio/<name>__<variant>.wav`: a 16 kHz mono recording of that line.

Naming rules and variants: `docs/contracts/backend-interfaces.md`, section 6. Keeper: D.

## Lines

| Name | Song, line | Text | Why it is here |
|---|---|---|---|
| `yueliang` | 月亮代表我的心, line 3 | 月亮代表我的心 | Traditional characters; the neutral 的; two-character words |
| `yijianmei` | 一剪梅, line 5 | 冷冷冰雪不能掩没 | Simplified; a reading fixed in lyrics.yaml (没 = mò); 不 before a second tone |
| `jasmine` | 茉莉花, line 0 | 好一朵美麗的茉莉花 | 一 sandhi; a three-character word; the third tones 好 and 美 |

They are copied from each song's `song.json`. If a song's lyrics.yaml changes, copy the line again.

## Recording

Record each line in each variant, as WAV, 16 kHz, mono:

| Variant | What to do |
|---|---|
| `correct` | Sing the line as written |
| `spoken` | Say the line normally, without melody |
| `error-<expected>-<produced>` | Sing it with one deliberate error, for example `error-zh-z` |
| `missing-<index>` | Sing it leaving out the syllable at that index (from 0) |

For example `yueliang__correct.wav`, `yijianmei__error-n-l.wav`. Any recorder works; Audacity can
convert to the right format (Export Audio: WAV, 16000 Hz, mono).
