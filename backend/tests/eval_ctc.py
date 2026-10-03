"""Checkpoint B script. Run by hand; pytest does not collect it.

Compares the Whisper base and the CTC layer on the fixture recordings: errors
caught and correct syllables wrongly flagged, per layer. Also writes the audio
cut at each span, for listening.

Owner: C. Spec: docs/tasks/backend-ctc-rhythm.md.

Sanity checklist once the model and fixtures are available:

1. Run ``uv run python tests/eval_ctc.py`` from ``backend/``. Confirm it reports
   the Whisper-base and CTC results side by side, and reports caught deliberate
   errors and correct syllables wrongly flagged for each layer.
2. Listen to the exported span clips. Check that each clip contains the named
   syllable, with no neighboring syllable taking most of the clip.
3. Run ``uv run python -m pipeline.align_track --song <id>`` for a demo song.
   Confirm reported mean confidences are plausible and spot-check the saved
   syllable times against the original track. Use ``--vocals`` when available.
4. Time one five-second clip on the demo Mac and record model, device, and
   elapsed time. The project target is about one second for the CTC pass.

These checks need real fixture recordings and a locally available CTC model;
they are intentionally separate from deterministic pytest coverage.
"""
