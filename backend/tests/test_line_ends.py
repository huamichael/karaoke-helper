"""Tests for pipeline/line_ends.py: correcting line times and rewriting lyrics.yaml.

Owner: D.
"""

import numpy as np
import yaml

from pipeline.line_ends import ONSET_LEAD_MS, START_LEAD_MS, corrected_times, quietest_ms, rewrite_times, voice_onset_ms

RATE = 16_000


def voice(*sung: tuple[int, int], total_ms: int = 7000) -> np.ndarray:
    """A voice track that is loud in each (start_ms, end_ms) and quiet elsewhere."""
    x = np.full(total_ms * RATE // 1000, 0.001, np.float32)
    for a, b in sung:
        x[a * RATE // 1000: b * RATE // 1000] = 0.5
    return x


def line(index, *starts):
    return {"index": index, "syllables": [{"start_ms": s} for s in starts]}


ENTRIES = [
    {"text": "", "start_ms": 0, "end_ms": 1000},             # intro
    {"text": "我想和你一起", "start_ms": 1000, "end_ms": 3000},
    {"text": "你好", "start_ms": 3000, "end_ms": 5000},
    {"text": "", "start_ms": 5000},                           # outro, no end
]


def test_line_moves_to_just_before_its_singing_and_neighbours_follow():
    # The singer starts line 0 at 900 ms (before its 1000 ms timestamp) and line 1 at 2850 ms.
    times = corrected_times(ENTRIES, [line(0, 900, 1500), line(1, 2850, 3500)])
    assert times[1][0] == 900 - START_LEAD_MS
    assert times[0] == (0, 900 - START_LEAD_MS)              # the intro ends where line 0 now starts
    assert times[2][0] == 2850 - START_LEAD_MS
    assert times[1][1] == 2850 - START_LEAD_MS               # line 0 no longer plays into line 1
    assert times[3] == (5000, None)


def test_a_line_whose_singing_starts_late_enough_is_left_alone():
    times = corrected_times(ENTRIES, [line(0, 1200, 1500), line(1, 3300, 3500)])
    assert times == [(e["start_ms"], e.get("end_ms")) for e in ENTRIES]


def test_never_moves_a_line_over_the_previous_lines_last_syllable():
    # Line 1's singing is aligned at 2900 ms, but line 0's last syllable is at 2950 ms:
    # moving line 1 earlier would cut that syllable off line 0, so line 1 stays at 3000 ms.
    times = corrected_times(ENTRIES, [line(0, 1000, 2950), line(1, 2900, 3500)])
    assert times[2][0] == 3000 and times[1][1] == 3000


def test_unaligned_line_keeps_its_times():
    times = corrected_times(ENTRIES, [line(0, None, None), line(1, 2850)])
    assert times[1][0] == 1000 and times[2][0] == 2850 - START_LEAD_MS


def test_fade_trim_applies_only_before_an_instrumental_break():
    times = corrected_times(ENTRIES, [line(0, 1200), line(1, 3200)], trims={0: 2000, 1: 4200})
    assert times[1][1] == 3000      # line 0 runs straight into line 1: not trimmed
    assert times[2][1] == 4200      # line 1 is followed by the outro: trimmed


LYRICS = """version: '1.0'
metadata:
  title: Test
# reading fixes stay put
readings:
  长留: chang2 liu2
lines:
- text: ''
  start_ms: 0
  end_ms: 1000
- text: 我想和你一起
  start_ms: 1000
  end_ms: 3000
- text: 你好
  start_ms: 3000
  end_ms: 5000
- text: ''
  start_ms: 5000
plain: |-
  我想和你一起
  start_ms: 1
"""


def test_rewrite_changes_only_the_times():
    new = rewrite_times(LYRICS, [(0, 850), (850, 2700), (2700, 5000), (5000, None)])
    parsed = yaml.safe_load(new)
    assert [(e["start_ms"], e.get("end_ms")) for e in parsed["lines"]] == [(0, 850), (850, 2700), (2700, 5000), (5000, None)]
    assert parsed["readings"] == {"长留": "chang2 liu2"} and "# reading fixes stay put" in new
    assert parsed["plain"].endswith("start_ms: 1")          # text after the lines block is untouched
    assert new.count("\n") == LYRICS.count("\n")


def test_rewrite_with_no_changes_is_identical():
    times = [(e["start_ms"], e.get("end_ms")) for e in yaml.safe_load(LYRICS)["lines"]]
    assert rewrite_times(LYRICS, times) == LYRICS


# --- with the singer's voice track -------------------------------------------------------


def test_boundary_moves_to_the_breath_when_the_singer_starts_early():
    # Line 0 is sung 1000-2600 ms, line 1 from 2700 ms, but the timestamp says 3000 ms and
    # the aligner missed line 1's first syllable (its first aligned one is at 3300 ms).
    vocals = voice((1000, 2600), (2700, 4800))
    times = corrected_times(ENTRIES, [line(0, 1100, 2000), line(1, None, 3300)], vocals=vocals)
    assert 2600 <= times[2][0] <= 2700        # in the breath, before the singer comes back in
    assert times[1][1] == times[2][0]         # line 0 ends exactly there


def test_boundary_moves_later_when_the_previous_line_is_still_being_sung():
    vocals = voice((1000, 3200), (3400, 4800))
    times = corrected_times(ENTRIES, [line(0, 1100, 2800), line(1, 3450)], vocals=vocals)
    assert 3200 <= times[2][0] <= 3400


def test_line_after_a_break_starts_just_before_the_voice():
    vocals = voice((800, 2900), (3100, 4800))
    times = corrected_times(ENTRIES, [line(0, 1000, 2000), line(1, 3200)], vocals=vocals)
    assert 800 - ONSET_LEAD_MS - 60 <= times[1][0] <= 800 - ONSET_LEAD_MS  # within the smoothing
    assert times[0][1] == times[1][0]


def test_quietest_and_onset_helpers():
    vocals = voice((0, 1000), (1500, 3000))
    assert 1000 <= quietest_ms(vocals, 500, 2000) <= 1500
    assert 1460 <= voice_onset_ms(vocals, 1100, 2000, 3000) <= 1500  # within the 3-frame smoothing
    assert voice_onset_ms(np.zeros(RATE * 3, np.float32), 0, 2000, 3000) is None
