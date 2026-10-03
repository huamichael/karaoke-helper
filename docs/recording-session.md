# Recording session

**Keeper:** D. **Used by:** everyone who records, and B, C and D, who test against the recordings.

We need real voices to check that grading works. One short session gives three parts of the backend what they need:

| Recordings | Used by | To check |
|---|---|---|
| Song lines, sung, spoken and with deliberate mistakes | C (checkpoint B), B | That the CTC layer and the Whisper base catch mistakes and pass correct singing |
| Single words, said correctly | D, B | That the tone grader recognises each tone, and how Whisper copes with a word said on its own |
| Single words, said with the wrong tone | D | That the tone grader catches wrong tones |

**A Mandarin speaker makes the recordings.** Every recording also has a prompt clip, so anyone can take part by copying it.

**If you speak Mandarin:**
- **Parts 1 and 2:** say or sing each item the way you naturally would. Don't copy the speech voice. Your natural pronunciation is what the grader should accept. You still need the sung prompts in Part 1 for the melody.
- **Part 3, and the mistake and missing-word lines in Part 1:** follow the instruction column. These mistakes are deliberate, and each must be exactly the one described, so the tests know which syllable is wrong.

## At a glance

- **Who:** a Mandarin speaker records everything once. If possible, a second speaker with a different voice (lower or higher) also records Part 2, so the tone grader is tested on more than one voice.
- **Time:** about 25 minutes per person, 45 short recordings.
- **Consent:** the recordings are committed to our public GitHub repository. Only take part if you are fine with your voice being public.

## 1. Before the session (one person, once)

1. Get the latest code: `git pull --rebase origin main`.
2. Put the three song tracks (`audio.mp3`) into their folders under `data/songs/` from the team share. The sung prompts are cut from them.
3. Make the prompt clips. This needs internet:
   ```bash
   docker compose run --rm backend uv run python tests/fixtures/prompts.py
   ```
   It writes them to `backend/tests/fixtures/prompts/`. Most are already in the repository; this adds the three sung clips, which git ignores because they are cut from copyrighted tracks.

## 2. Set up (each person)

1. **A quiet room.** No music, fans or other people talking.
2. **One microphone,** a headset or the laptop's own, about a hand's width (15–20 cm) from your mouth. Keep the same distance for every recording.
3. **Audacity**, free from audacityteam.org. Before recording, set:
   - **Project rate:** 16000 Hz. In Audacity 3, open **Audio Setup → Audio Settings** and set **Project Sample Rate** to 16000.
   - **Channels:** 1 (Mono), in the same window under **Recording**.

   A phone's voice recorder also works. Save the files with the right names, and the checker in step 5 converts them.
4. **Pick your speaker name:** your first name in lowercase ASCII letters, no spaces or numbers, for example `rayan`. It goes at the end of every file name.
5. **Open the prompts folder** to play clips from. On Windows with WSL it is `\\wsl.localhost\Ubuntu\home\<user>\MHACKS\backend\tests\fixtures\prompts`. On a Mac it is the same path inside your clone.

## 3. Recording one item

1. Play the item's prompt once or twice.
2. Press record, wait half a second, then say or sing the item **once**.
3. Wait half a second, then stop.
4. Listen back. If you stumbled, coughed, or got it wrong in a way the item didn't ask for, delete it and record again. Deliberate mistakes are the point of some items; accidental ones are not.
5. **Export** with **File → Export Audio**: WAV, Signed 16-bit PCM, Mono, 16000 Hz. Use the exact file name from the checklist, with your name in place of `<you>`.
6. Save into `backend/tests/fixtures/audio/` for song lines, or `backend/tests/fixtures/tone/` for single words.

One recording per file. Don't put several takes in one file.

## 4. Checklist

File names have three parts separated by **two** underscores: `<item>__<variant>__<you>.wav`. Copy them exactly. The checker in step 5 rejects names it doesn't know.

### Part 1: song lines (12 recordings), saved in `audio/`

For the mistake and missing-word items, play the sung prompt for the melody and the spoken prompt to hear the change, then sing the changed line.

| Done | File name | Prompt to play | What to do |
|---|---|---|---|
| ☐ | `audio/yueliang__correct__<you>.wav` | `prompts/lines/yueliang__sung.wav` | Listen to the original, then sing the line back on your own, as written. |
| ☐ | `audio/yueliang__spoken__<you>.wav` | `prompts/lines/yueliang__spoken.mp3` | Say the line normally, without any melody. |
| ☐ | `audio/yueliang__error-1-iang-ian__<you>.wav` | `prompts/lines/yueliang__error-1-iang-ian.mp3` | Sing it, but say 亮 liàng as liàn: drop the final "ng". |
| ☐ | `audio/yueliang__missing-4__<you>.wav` | `prompts/lines/yueliang__missing-4.mp3` | Sing it, but leave out 我 (wǒ), the fifth character. |
| ☐ | `audio/yijianmei__correct__<you>.wav` | `prompts/lines/yijianmei__sung.wav` | Listen to the original, then sing the line back on your own, as written. |
| ☐ | `audio/yijianmei__spoken__<you>.wav` | `prompts/lines/yijianmei__spoken.mp3` | Say the line normally, without any melody. |
| ☐ | `audio/yijianmei__error-2-ing-in__<you>.wav` | `prompts/lines/yijianmei__error-2-ing-in.mp3` | Sing it, but say 冰 bīng as bīn: drop the final "g". |
| ☐ | `audio/yijianmei__missing-4__<you>.wav` | `prompts/lines/yijianmei__missing-4.mp3` | Sing it, but leave out 不 (bù), the fifth character. |
| ☐ | `audio/jasmine__correct__<you>.wav` | `prompts/lines/jasmine__sung.wav` | Listen to the original, then sing the line back on your own, as written. |
| ☐ | `audio/jasmine__spoken__<you>.wav` | `prompts/lines/jasmine__spoken.mp3` | Say the line normally, without any melody. |
| ☐ | `audio/jasmine__error-4-l-n__<you>.wav` | `prompts/lines/jasmine__error-4-l-n.mp3` | Sing it, but say 麗 lì as nì: start with "n" instead of "l". |
| ☐ | `audio/jasmine__missing-1__<you>.wav` | `prompts/lines/jasmine__missing-1.mp3` | Sing it, but leave out 一 (yī), the second character. |

### Part 2: single words, said correctly (21 recordings), saved in `tone/`

Copy the prompt's pitch as closely as you can; the pitch movement is what is being tested. The four tones:

| Tone | Pitch movement |
|---|---|
| 1 | high and level, like holding one note |
| 2 | rising, as when asking "What?" |
| 3 | dipping low, then coming back up |
| 4 | falling sharply, like a firm "No!" |

| Done | File name | Prompt to play | What to do |
|---|---|---|---|
| ☐ | `tone/xin1__correct__<you>.wav` | `prompts/tone/xin1__correct.mp3` | Say 心 (xin1) on its own, normally. Its tone is high and level. |
| ☐ | `tone/xiang1__correct__<you>.wav` | `prompts/tone/xiang1__correct.mp3` | Say 香 (xiang1) on its own, normally. Its tone is high and level. |
| ☐ | `tone/zhen1__correct__<you>.wav` | `prompts/tone/zhen1__correct.mp3` | Say 真 (zhen1) on its own, normally. Its tone is high and level. |
| ☐ | `tone/jiang1__correct__<you>.wav` | `prompts/tone/jiang1__correct.mp3` | Say 將 (jiang1) on its own, normally. Its tone is high and level. |
| ☐ | `tone/kua1__correct__<you>.wav` | `prompts/tone/kua1__correct.mp3` | Say 誇 (kua1) on its own, normally. Its tone is high and level. |
| ☐ | `tone/ma1__correct__<you>.wav` | `prompts/tone/ma1__correct.mp3` | Say 妈 (ma1) on its own, normally. Its tone is high and level. |
| ☐ | `tone/qing2__correct__<you>.wav` | `prompts/tone/qing2__correct.mp3` | Say 情 (qing2) on its own, normally. Its tone is rising. |
| ☐ | `tone/bai2__correct__<you>.wav` | `prompts/tone/bai2__correct.mp3` | Say 白 (bai2) on its own, normally. Its tone is rising. |
| ☐ | `tone/lai2__correct__<you>.wav` | `prompts/tone/lai2__correct.mp3` | Say 來 (lai2) on its own, normally. Its tone is rising. |
| ☐ | `tone/ren2__correct__<you>.wav` | `prompts/tone/ren2__correct.mp3` | Say 人 (ren2) on its own, normally. Its tone is rising. |
| ☐ | `tone/ma2__correct__<you>.wav` | `prompts/tone/ma2__correct.mp3` | Say 麻 (ma2) on its own, normally. Its tone is rising. |
| ☐ | `tone/wo3__correct__<you>.wav` | `prompts/tone/wo3__correct.mp3` | Say 我 (wo3) on its own, normally. Its tone is dipping low, then rising. |
| ☐ | `tone/ni3__correct__<you>.wav` | `prompts/tone/ni3__correct.mp3` | Say 你 (ni3) on its own, normally. Its tone is dipping low, then rising. |
| ☐ | `tone/you3__correct__<you>.wav` | `prompts/tone/you3__correct.mp3` | Say 有 (you3) on its own, normally. Its tone is dipping low, then rising. |
| ☐ | `tone/wen3__correct__<you>.wav` | `prompts/tone/wen3__correct.mp3` | Say 吻 (wen3) on its own, normally. Its tone is dipping low, then rising. |
| ☐ | `tone/ma3__correct__<you>.wav` | `prompts/tone/ma3__correct.mp3` | Say 马 (ma3) on its own, normally. Its tone is dipping low, then rising. |
| ☐ | `tone/ai4__correct__<you>.wav` | `prompts/tone/ai4__correct.mp3` | Say 愛 (ai4) on its own, normally. Its tone is falling sharply. |
| ☐ | `tone/wen4__correct__<you>.wav` | `prompts/tone/wen4__correct.mp3` | Say 問 (wen4) on its own, normally. Its tone is falling sharply. |
| ☐ | `tone/qu4__correct__<you>.wav` | `prompts/tone/qu4__correct.mp3` | Say 去 (qu4) on its own, normally. Its tone is falling sharply. |
| ☐ | `tone/rang4__correct__<you>.wav` | `prompts/tone/rang4__correct.mp3` | Say 讓 (rang4) on its own, normally. Its tone is falling sharply. |
| ☐ | `tone/ma4__correct__<you>.wav` | `prompts/tone/ma4__correct.mp3` | Say 骂 (ma4) on its own, normally. Its tone is falling sharply. |

### Part 3: single words, said with the wrong tone (12 recordings), saved in `tone/`

These prompts are the same voice with its pitch reshaped, so they can sound slightly robotic. Copy the pitch movement, not the robotic quality.

| Done | File name | Prompt to play | What to do |
|---|---|---|---|
| ☐ | `tone/xin1__said-tone2__<you>.wav` | `prompts/tone/xin1__said-tone2.wav` | Say 心 with the wrong tone: make it rising, like the prompt. |
| ☐ | `tone/xin1__said-tone3__<you>.wav` | `prompts/tone/xin1__said-tone3.wav` | Say 心 with the wrong tone: make it dipping low, then rising, like the prompt. |
| ☐ | `tone/xin1__said-tone4__<you>.wav` | `prompts/tone/xin1__said-tone4.wav` | Say 心 with the wrong tone: make it falling sharply, like the prompt. |
| ☐ | `tone/qing2__said-tone1__<you>.wav` | `prompts/tone/qing2__said-tone1.wav` | Say 情 with the wrong tone: make it high and level, like the prompt. |
| ☐ | `tone/qing2__said-tone3__<you>.wav` | `prompts/tone/qing2__said-tone3.wav` | Say 情 with the wrong tone: make it dipping low, then rising, like the prompt. |
| ☐ | `tone/qing2__said-tone4__<you>.wav` | `prompts/tone/qing2__said-tone4.wav` | Say 情 with the wrong tone: make it falling sharply, like the prompt. |
| ☐ | `tone/wo3__said-tone1__<you>.wav` | `prompts/tone/wo3__said-tone1.wav` | Say 我 with the wrong tone: make it high and level, like the prompt. |
| ☐ | `tone/wo3__said-tone2__<you>.wav` | `prompts/tone/wo3__said-tone2.wav` | Say 我 with the wrong tone: make it rising, like the prompt. |
| ☐ | `tone/wo3__said-tone4__<you>.wav` | `prompts/tone/wo3__said-tone4.wav` | Say 我 with the wrong tone: make it falling sharply, like the prompt. |
| ☐ | `tone/ai4__said-tone1__<you>.wav` | `prompts/tone/ai4__said-tone1.wav` | Say 愛 with the wrong tone: make it high and level, like the prompt. |
| ☐ | `tone/ai4__said-tone2__<you>.wav` | `prompts/tone/ai4__said-tone2.wav` | Say 愛 with the wrong tone: make it rising, like the prompt. |
| ☐ | `tone/ai4__said-tone3__<you>.wav` | `prompts/tone/ai4__said-tone3.wav` | Say 愛 with the wrong tone: make it dipping low, then rising, like the prompt. |

## 5. Check your files

```bash
docker compose run --rm backend uv run python tests/fixtures/check_recordings.py
```

For each speaker it prints how many recordings are done and lists any still missing. It also lists every file that needs fixing:

| Message | Fix |
|---|---|
| name must be `<item>__<variant>__<yourname>` | Rename the file. Check for two underscores between parts. |
| not in the session list | A typo in the item or variant. Compare with the checklist. |
| not 16 kHz mono WAV | Run the command again with `--convert`. It converts the file and removes the original. |
| almost silent | Record again, closer to the microphone. |
| too loud and distorted | Record again, further from the microphone or with a lower input level. |
| only … s long | The recording was cut short. Record again. |

The session is complete when every speaker shows `left 0` and nothing needs fixing.

## While a Mandarin speaker is here

Three checks only a Mandarin speaker can do, about 10 minutes in total:

1. **Readings and word splits.** Run `docker compose run --rm backend uv run python -m pipeline.build_song --all --no-clips`. It prints every line with its pinyin and how it is split into words (`/`). Note any wrong reading or odd split.
2. **Two corrected words.** Play `data/songs/yi-jian-mei/words/yan3-mo4.mp3` and `chang2-liu2.mp3`. The speech voice should say yǎn mò and cháng liú, not yǎn méi or zhǎng liú.
3. **Translations and word meanings.** Skim the `translations` and `glosses` blocks in the three `data/songs/*/lyrics.yaml` files.

Fixes go in the song's `lyrics.yaml`: `readings` for pronunciations, `words` for word splits. Then rebuild with the same command, without `--no-clips` if a clip changed.

## 6. Share the recordings

```bash
git pull --rebase origin main
git add backend/tests/fixtures/audio backend/tests/fixtures/tone
git commit -m "Recording session: <you>"
git push origin main
```

Then tell the team, so C can run checkpoint B and D can tune the tone grader.

## Changing the session

The list of recordings lives in `backend/tests/fixtures/session.py`. The prompt maker, the checker and this checklist all follow it. If you add or change an item there, make its prompt again with `prompts.py`, and update the tables above.
