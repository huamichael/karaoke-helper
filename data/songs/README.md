# Song bundles

One folder per song: `<song_id>/lyrics.yaml` (written by hand), `audio.mp3`, and the generated `song.json`, `words/` with a spoken clip per word, and `instrumental.mp3`, the track without its singer for Karaoke mode.

Built by `backend/pipeline/build_song.py`, then `align_track.py`. Format: `docs/contracts/data-model.md`, section 5. Keeper: D.

The tracks (`audio.mp3`) and instrumentals (`instrumental.mp3`) are copyrighted and ignored by git. Get them from the team share and place each one in its song folder, or make the instrumentals yourself: `uv run --group vocals python -m pipeline.instrumental --all` (docs/tasks/backend-songs-tone.md, "Instrumentals").

Task C generated provisional syllable timings for `yue-liang-dai-biao-wo-de-xin` and `yi-jian-mei` on 3 October 2026. Unusable spans remain null. These full-mix alignments need listening review before rhythm is enabled; see `docs/tasks/backend-ctc-rhythm.md` for measured coverage and remaining checkpoints.
