# Test fixtures

Shared recordings and expected lines that every backend task tests against.

- `lines/<name>.json`: one `Line` object, the expected syllables.
- `audio/<name>__<variant>__<speaker>.wav`: a 16 kHz mono recording of that line.
- `tone/<reading>__<variant>__<speaker>.wav`: a single word, for checking tone.

Naming rules: `docs/contracts/backend-interfaces.md`, section 6. Keeper: D.

**To record:** follow [docs/recording-session.md](../../../docs/recording-session.md). It has the checklist, a prompt clip for every item, and how to check your files.

| File | Purpose |
|---|---|
| `session.py` | The list of every recording. The prompt maker, the checker and the guide follow it. |
| `prompts.py` | Makes `prompts/`: a clip to copy for every recording. |
| `check_recordings.py` | Checks names, format and loudness, converts other formats with `--convert`, and lists what each speaker still needs. |

## Lines

| Name | Song, line | Text | Why it is here |
|---|---|---|---|
| `yueliang` | 月亮代表我的心, line 3 | 月亮代表我的心 | Traditional characters; the neutral 的; two-character words |
| `yijianmei` | 一剪梅, line 5 | 冷冷冰雪不能掩没 | Simplified; a reading fixed in lyrics.yaml (没 = mò); 不 before a second tone |
| `jasmine` | 茉莉花, line 0 | 好一朵美麗的茉莉花 | 一 sandhi; a three-character word; the third tones 好 and 美 |

They are copied from each song's `song.json`. If a song's lyrics.yaml changes, copy the line again.
