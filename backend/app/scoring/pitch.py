"""Pitch tracking helper.

Extracts the pitch contour of a stretch of audio, in semitones relative to the
recording's median, with unvoiced frames dropped. Used by the tone scorer.

Owner: D. Spec: docs/tasks/backend-songs-tone.md.
"""

import numpy as np
import parselmouth

FRAME_MS = 10            # one pitch value every 10 ms
PITCH_FLOOR_HZ = 75      # covers low male voices
PITCH_CEILING_HZ = 500   # covers high female voices


def pitch_track(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    """The pitch of a recording, one value per 10 ms frame.

    Returns (times_ms, semitones). times_ms is each frame's centre, measured
    from the start of samples. semitones is relative to the median pitch of the
    recording's voiced frames, and NaN where a frame is unvoiced.
    Both arrays are empty when the recording is too short to analyse.
    """
    try:
        sound = parselmouth.Sound(np.asarray(samples, dtype=np.float64), sampling_frequency=sample_rate)
        pitch = sound.to_pitch(
            time_step=FRAME_MS / 1000, pitch_floor=PITCH_FLOOR_HZ, pitch_ceiling=PITCH_CEILING_HZ
        )
    except parselmouth.PraatError:
        return np.array([]), np.array([])

    hertz = pitch.selected_array["frequency"]
    times_ms = pitch.xs() * 1000
    semitones = np.full(hertz.shape, np.nan)
    voiced = hertz > 0
    if voiced.any():
        semitones[voiced] = 12 * np.log2(hertz[voiced] / np.median(hertz[voiced]))
    return times_ms, semitones
