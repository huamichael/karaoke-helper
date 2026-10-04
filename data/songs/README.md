# Song bundles

One folder per song: `<song_id>/lyrics.yaml` (written by hand), `audio.mp3`, and the generated `song.json` and `words/` with a spoken clip per word.

Built by `backend/pipeline/build_song.py`, then `align_track.py`. Format: `docs/contracts/data-model.md`, section 5. Keeper: D.

The tracks (`audio.mp3`) are copyrighted and ignored by git. Get them from the team share and place each one in its song folder.

Task C generated provisional syllable timings for `yue-liang-dai-biao-wo-de-xin` and `yi-jian-mei` on 3 October 2026. Unusable spans remain null. These full-mix alignments need listening review before rhythm is enabled; see `docs/tasks/backend-ctc-rhythm.md` for measured coverage and remaining checkpoints.
