"""Pipeline step 2: add the original singer's syllable times.

Command-line tool. Aligns each lyric line to the original track with the same
align() used on user recordings, and writes start_ms and end_ms into song.json.
The rhythm score needs these times.

Owner: C. Spec: docs/tasks/backend-ctc-rhythm.md.
"""
