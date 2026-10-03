"""Feedback messages.

Maps feedback codes (MISSING, INITIAL_ZH_Z, TONE_3_2, RHYTHM_EARLY and so on) to
the text the learner reads, and picks the one message shown for each syllable.

Owner: B; C and D add the rows for their own codes. Spec: docs/contracts/scoring.md.
"""

from app.schemas import Feedback, Part, SoundScore, ToneGrade
from app.scoring.confusions import final_partners, initial_partners

MESSAGES: dict[str, str] = {
    "MISSING": "We didn't hear this syllable.",
    "INITIAL_N_L": ('Sounded closer to "l". For "n", keep the tongue tip behind your top teeth '
                    "and let the air go through your nose."),
}


def initial_code(part: Part) -> str:
    if part.heard is not None and part.heard in initial_partners(part.expected):
        return f"INITIAL_{part.expected.upper()}_{part.heard.upper()}"
    return "INITIAL_OTHER"


def final_code(part: Part) -> str:
    if part.heard is not None and part.heard in final_partners(part.expected):
        return f"FINAL_{part.expected.upper()}_{part.heard.upper()}"
    return "FINAL_OTHER"


def _sound_message(code: str, kind: str, part: Part) -> str:
    if code in MESSAGES:
        return MESSAGES[code]
    if kind == "initial" and not part.expected:
        return f'Start straight on the vowel, without a "{part.heard}" sound.'
    if kind == "initial" and not part.heard:
        return f'Start the syllable with "{part.expected}".'
    return f'Sounded closer to "{part.heard}". Aim for "{part.expected}".'


def pick(sound: SoundScore | None, tone: ToneGrade | None) -> Feedback | None:
    """The one message for a syllable. Order: missing, initial or final, tone. None when nothing is wrong."""
    if sound is None:
        return Feedback(code="MISSING", message=MESSAGES["MISSING"])
    parts = [("initial", sound.initial), ("final", sound.final)]
    flawed = [(kind, p) for kind, p in parts if p is not None and (p.score or 0) < 100]
    if flawed:
        kind, part = min(flawed, key=lambda kp: kp[1].score or 0)
        code = initial_code(part) if kind == "initial" else final_code(part)
        return Feedback(code=code, message=_sound_message(code, kind, part))
    if tone is not None and tone.heard is not None and tone.heard != tone.expected:
        code = f"TONE_{tone.expected}_{tone.heard}"
        return Feedback(code=code, message=MESSAGES.get(code, f"Tone {tone.heard} heard; aim for tone {tone.expected}."))
    return None
