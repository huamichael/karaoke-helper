"""Feedback messages.

Picks the feedback code for a syllable (MISSING, INITIAL_ZH_Z, TONE_3_2,
RHYTHM_EARLY and so on), which records which problem the grader found, and writes
the message the learner reads.

The message is a hint on how to say the target syllable: its starting sound, what
is distinctive about its ending, and, in Word practice, its tone. It never says
what the learner said or why it was wrong: the grader's idea of what it heard can
be mistaken, and a confident wrong diagnosis misleads more than it helps.

Owner: B; C and D add the rows for their own codes. Spec: docs/contracts/scoring.md.
"""

from app.mandarin import spell
from app.schemas import Feedback, Part, SoundScore, Syllable, ToneGrade
from app.scoring.confusions import final_partners, initial_partners

MESSAGES: dict[str, str] = {
    "MISSING": "Say this syllable clearly, on its own.",
    # Rhythm codes. Wording is the scoring.md example; C can replace it.
    "RHYTHM_EARLY": "You came in early here. Wait a little longer before this syllable.",
    "RHYTHM_LATE": "You came in late here. Start this syllable a little sooner.",
}

_PALATAL = "tongue tip down behind your bottom teeth and the middle of your tongue raised"
_CURLED = "tongue tip curled up and back toward the roof of your mouth"
_FLAT = "tongue flat, with the tip just behind your top teeth"

# How to make each starting consonant. A syllable with no consonant (wǒ, yī, ài) has no tip here.
INITIAL_TIPS: dict[str, str] = {
    "b": 'Start with "b": lips together, then open them without a puff of air.',
    "p": 'Start with "p": lips together, then open them with a strong puff of air.',
    "m": 'Start with "m": lips together, humming through your nose.',
    "f": 'Start with "f": top teeth resting on your lower lip, blowing gently.',
    "d": 'Start with "d": tongue tip tapping behind your top teeth, without a puff of air.',
    "t": 'Start with "t": tongue tip tapping behind your top teeth, with a strong puff of air.',
    "n": 'Start with "n": tongue tip behind your top teeth, with the air going through your nose.',
    "l": 'Start with "l": tongue tip behind your top teeth, with the air flowing around its sides.',
    "g": 'Start with "g": back of your tongue raised, released without a puff of air.',
    "k": 'Start with "k": back of your tongue raised, released with a strong puff of air.',
    "h": 'Start with "h": breathe out from the back of your throat, a little rougher than English "h".',
    "j": f'Start with "j": {_PALATAL}, without a puff of air.',
    "q": f'Start with "q": {_PALATAL}, with a strong puff of air.',
    "x": f'Start with "x": {_PALATAL}, letting the air hiss out.',
    "zh": f'Start with "zh": {_CURLED}, without a puff of air.',
    "ch": f'Start with "ch": {_CURLED}, with a strong puff of air.',
    "sh": f'Start with "sh": {_CURLED}, letting the air hiss out.',
    "r": f'Start with "r": {_CURLED}, as for "sh", with your voice on.',
    "z": f'Start with "z": {_FLAT}, like "ds" in "kids".',
    "c": f'Start with "c": {_FLAT}, like "ts" in "cats".',
    "s": f'Start with "s": {_FLAT}, letting the air hiss out.',
}

ENDING_TIPS = {
    "n": 'End with your tongue tip touching just behind your top teeth, for "-n".',
    "ng": 'End at the back of your mouth, as in "song", for "-ng".',
}

# How the tone sounds, for Word practice. In a sung line the melody replaces the tone.
TONE_TIPS = {
    1: "Keep your pitch high and level, as if holding one note.",
    2: 'Let your pitch rise, as when asking "What?"',
    3: "Drop your pitch low; at the end of a word, let it come back up a little.",
    4: 'Let your pitch fall sharply, like a firm "No!"',
    5: "Say it lightly and quickly.",
}

GENERAL_TIP = "Listen to it again and copy it, sound by sound."


def _ending_tips(initial: str, final: str) -> list[str]:
    """What is distinctive about a syllable's vowel and ending, as hints."""
    tips = []
    if final == "i" and initial in ("z", "c", "s", "zh", "ch", "sh", "r"):
        tips.append(f'The "i" after "{initial}" is a buzz, not "ee": keep your tongue where the "{initial}" put it.')
    elif "v" in final:
        letter = "ü" if initial in ("n", "l") else "u"
        tips.append(f'The "{letter}" here is "ee" said with rounded lips.')
    elif final == "e":
        tips.append('The "e" is a relaxed "uh", not "eh".')
    ending = "ng" if final.endswith("ng") else "n" if final.endswith("n") else ""
    if ending:
        tips.append(ENDING_TIPS[ending])
    return tips


def hint(initial: str, final: str, tone: int | None = None, shown: str | None = None) -> str:
    """How to say a syllable: its start, its ending and, if given, its tone. Nothing about an attempt.

    tone is the tone to speak (after sandhi) in Word practice, or None for a sung line.
    shown is how to write the syllable when no tone is given (its lyric pinyin).
    """
    target = spell(initial, final, tone) if tone else (shown or spell(initial, final))
    tips = ([INITIAL_TIPS[initial]] if initial in INITIAL_TIPS else []) + _ending_tips(initial, final)
    if tone in TONE_TIPS:
        tips.append(TONE_TIPS[tone])
    return f'How to say "{target}": ' + " ".join(tips or [GENERAL_TIP])


def initial_code(part: Part) -> str:
    if part.heard is not None and part.heard in initial_partners(part.expected):
        return f"INITIAL_{part.expected.upper()}_{part.heard.upper()}"
    return "INITIAL_OTHER"


def final_code(part: Part) -> str:
    if part.heard is not None and part.heard in final_partners(part.expected):
        return f"FINAL_{part.expected.upper()}_{part.heard.upper()}"
    return "FINAL_OTHER"


def pick(sound: SoundScore | None, tone: ToneGrade | None, rhythm_code: str | None = None,
         *, syllable: Syllable | None = None) -> Feedback | None:
    """The one feedback for a syllable, or None when nothing is wrong.

    The code says which problem was found, in this order: missing, initial or final,
    tone, rhythm. The message is the same hint on how to say the syllable whichever
    problem it was; only rhythm keeps its own message. syllable is the expected one.
    """
    if sound is None:
        code = "MISSING"
    else:
        parts = [("initial", sound.initial), ("final", sound.final)]
        flawed = [(kind, p) for kind, p in parts if p is not None and (p.score or 0) < 100]
        if flawed:
            kind, part = min(flawed, key=lambda kp: kp[1].score or 0)
            code = initial_code(part) if kind == "initial" else final_code(part)
        elif tone is not None and tone.heard is not None and tone.heard != tone.expected:
            code = f"TONE_{tone.expected}_{tone.heard}"
        elif rhythm_code is not None:
            return Feedback(code=rhythm_code, message=MESSAGES[rhythm_code])
        else:
            return None
    if syllable is not None:
        initial, final, shown = syllable.initial, syllable.final, syllable.pinyin
    elif sound is not None:
        initial, final, shown = (sound.initial.expected if sound.initial else ""), sound.final.expected, None
    else:
        return Feedback(code=code, message=MESSAGES["MISSING"])
    spoken_tone = tone.expected if tone is not None else None
    return Feedback(code=code, message=hint(initial, final, spoken_tone, shown))
