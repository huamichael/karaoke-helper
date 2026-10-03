"""Pipeline step 1: build a song bundle.

Command-line tool. Turns synced lyrics (LRC) and a track into
data/songs/<song_id>/song.json: lines, syllables, words, and a spoken clip for
each word. Leaves syllable times empty for align_track to fill.

Owner: D. Spec: docs/contracts/data-model.md, section 5; docs/tasks/backend-songs-tone.md.
"""
