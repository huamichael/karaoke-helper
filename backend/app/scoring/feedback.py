"""Feedback messages.

Maps feedback codes (MISSING, INITIAL_ZH_Z, TONE_3_2, RHYTHM_EARLY and so on) to
the text the learner reads, and picks the one message shown for each syllable.

Owner: B; C and D add the rows for their own codes. Spec: docs/contracts/scoring.md.
"""

from app.schemas import Feedback, Part, SoundScore, ToneGrade
from app.scoring.confusions import final_partners, initial_partners

_CURL = "curl your tongue tip up and back toward the roof of your mouth"
_FLAT = "keep your tongue flat, with the tip just behind your top teeth"
_PALATAL = "keep your tongue tip down behind your bottom teeth, raise the middle of your tongue, and spread your lips"
_LIFT = "lift your tongue tip and curl it back, keeping the middle of your tongue low"
_FRONT = "end with your tongue tip touching just behind your top teeth"
_BACK = 'end at the back of your mouth, as in "song", with your tongue tip resting low'


def _tip(heard: str, expected: str, how: str) -> str:
    return f'Sounded closer to "{heard}". For "{expected}", {how}.'


MESSAGES: dict[str, str] = {
    "MISSING": "We didn't hear this syllable.",
    "INITIAL_N_L": ('Sounded closer to "l". For "n", keep the tongue tip behind your top teeth '
                    "and let the air go through your nose."),
    "INITIAL_L_N": _tip("n", "l", "touch your tongue tip behind your top teeth and let the air flow around its sides, "
                                  "not through your nose"),
    "INITIAL_ZH_Z": _tip("z", "zh", _CURL),
    "INITIAL_Z_ZH": _tip("zh", "z", _FLAT),
    "INITIAL_CH_C": _tip("c", "ch", f"{_CURL}, with a puff of air"),
    "INITIAL_C_CH": _tip("ch", "c", f"{_FLAT}, with a puff of air"),
    "INITIAL_SH_S": _tip("s", "sh", _CURL),
    "INITIAL_S_SH": _tip("sh", "s", _FLAT),
    "INITIAL_J_ZH": _tip("zh", "j", _PALATAL),
    "INITIAL_ZH_J": _tip("j", "zh", _LIFT),
    "INITIAL_Q_CH": _tip("ch", "q", f"{_PALATAL}, with a puff of air"),
    "INITIAL_CH_Q": _tip("q", "ch", f"{_LIFT}, with a puff of air"),
    "INITIAL_X_SH": _tip("sh", "x", _PALATAL),
    "INITIAL_SH_X": _tip("x", "sh", _LIFT),
    "FINAL_AN_ANG": _tip("ang", "an", _FRONT),
    "FINAL_ANG_AN": _tip("an", "ang", _BACK),
    "FINAL_EN_ENG": _tip("eng", "en", _FRONT),
    "FINAL_ENG_EN": _tip("en", "eng", _BACK),
    "FINAL_IN_ING": _tip("ing", "in", _FRONT),
    "FINAL_ING_IN": _tip("in", "ing", _BACK),
    "FINAL_IAN_IANG": _tip("iang", "ian", _FRONT),
    "FINAL_IANG_IAN": _tip("ian", "iang", _BACK),
    "FINAL_UAN_UANG": _tip("uang", "uan", _FRONT),
    "FINAL_UANG_UAN": _tip("uan", "uang", _BACK),
    "FINAL_UEN_UENG": _tip("ueng", "uen", _FRONT),
    "FINAL_UENG_UEN": _tip("uen", "ueng", _BACK),
    # Tone codes are TONE_<expected>_<heard>. Owner: D.
    "TONE_1_2": "Your pitch rose. Keep it high and level, as if holding one note.",
    "TONE_1_3": "Your pitch dipped. Keep it high and level, as if holding one note.",
    "TONE_1_4": "Your pitch fell. Keep it high and level, as if holding one note.",
    "TONE_2_1": 'Your pitch stayed level. Let it rise, as when asking "What?"',
    "TONE_2_3": 'Your pitch dipped first. Start in the middle and rise steadily, as when asking "What?"',
    "TONE_2_4": 'Your pitch fell. Let it rise instead, as when asking "What?"',
    "TONE_3_1": "Your pitch stayed high. Drop your voice low; at the end of a word, let it come back up a little.",
    "TONE_3_2": "Your pitch rose without going low. Drop your voice low first; at the end of a word, let it come back up.",
    "TONE_3_4": "Your pitch fell from high. Start low and stay low; at the end of a word, let it come back up a little.",
    "TONE_4_1": 'Your pitch stayed level. Start high and drop sharply, like a firm "No!"',
    "TONE_4_2": 'Your pitch rose. Start high and drop sharply, like a firm "No!"',
    "TONE_4_3": 'Your pitch dipped and rose. Start high and drop sharply, like a firm "No!"',
    # Rhythm codes. Wording is the scoring.md example; C can replace it.
    "RHYTHM_EARLY": "You came in early here. Wait a little longer before this syllable.",
    "RHYTHM_LATE": "You came in late here. Start this syllable a little sooner.",
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
    if part.heard == part.expected:
        return f'We could not hear the "{part.expected}" sound clearly. Try it again.'
    if code in MESSAGES:
        return MESSAGES[code]
    if kind == "initial" and not part.expected:
        return f'Start straight on the vowel, without a "{part.heard}" sound.'
    if kind == "initial" and not part.heard:
        return f'Start the syllable with "{part.expected}".'
    return f'Sounded closer to "{part.heard}". Aim for "{part.expected}".'


def pick(sound: SoundScore | None, tone: ToneGrade | None, rhythm_code: str | None = None) -> Feedback | None:
    """The one message for a syllable. Order: missing, initial or final, tone, rhythm. None when nothing is wrong.

    rhythm_code is RHYTHM_EARLY or RHYTHM_LATE when the grader has decided this syllable's
    rhythm score is below the good line. Sound and tone messages still win.
    """
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
    if rhythm_code is not None:
        return Feedback(code=rhythm_code, message=MESSAGES[rhythm_code])
    return None
