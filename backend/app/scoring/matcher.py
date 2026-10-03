"""Whisper base, step 2: line up what was heard against what was expected.

Provides match (sequence-aligns the heard syllables to the expected ones and
returns one observed syllable, or None, per expected syllable) and
score_sounds_base (the 100 / 60 / 20 component scores for initials and finals).

Owner: B. Spec: docs/contracts/scoring.md.
"""

from __future__ import annotations

from app.schemas import Part, SoundScore, Syllable
from app.scoring.confusions import final_partners, initial_partners

GAP = 1.5
# Component distance -> component score: exact, confused pair, other mismatch.
COMPONENT_SCORE = {0: 100, 1: 60, 2: 20}


def match(expected: list[Syllable], heard: list[Syllable]) -> list[Syllable | None]:
    n, m = len(expected), len(heard)
    cost = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0] = i * GAP
    for j in range(1, m + 1):
        cost[0][j] = j * GAP
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost[i][j] = min(
                cost[i - 1][j - 1] + _pair_cost(expected[i - 1], heard[j - 1]),
                cost[i - 1][j] + GAP,
                cost[i][j - 1] + GAP,
            )

    observed: list[Syllable | None] = [None] * n
    i, j = n, m
    while i > 0 and j > 0:
        if cost[i][j] == cost[i - 1][j - 1] + _pair_cost(expected[i - 1], heard[j - 1]):
            observed[i - 1] = _observed(expected[i - 1], heard[j - 1])
            i, j = i - 1, j - 1
        elif cost[i][j] == cost[i - 1][j] + GAP:
            i -= 1
        else:
            j -= 1
    return observed


def score_sounds_base(expected: list[Syllable], observed: list[Syllable | None]) -> list[SoundScore | None]:
    if len(expected) != len(observed):
        raise ValueError(f"expected has {len(expected)} syllables but observed has {len(observed)}")
    scores: list[SoundScore | None] = []
    for e, o in zip(expected, observed):
        if o is None:
            scores.append(None)
            continue
        initial = None
        if e.initial or o.initial:
            initial = Part(expected=e.initial, heard=o.initial,
                           score=COMPONENT_SCORE[_distance(e.initial, o.initial, initial_partners)])
        final = Part(expected=e.final, heard=o.final, score=COMPONENT_SCORE[_distance(e.final, o.final, final_partners)])
        scores.append(SoundScore(initial=initial, final=final))
    return scores


def _distance(expected: str, heard: str, partners) -> int:
    if expected == heard:
        return 0
    return 1 if heard in partners(expected) else 2


def _pair_cost(e: Syllable, h: Syllable) -> float:
    if e.hanzi == h.hanzi:
        return 0.0
    worst = max(_distance(e.initial, h.initial, initial_partners), _distance(e.final, h.final, final_partners))
    return float(worst)


def _observed(e: Syllable, h: Syllable) -> Syllable:
    reading = e if e.hanzi == h.hanzi else h
    return Syllable(
        hanzi=h.hanzi, pinyin=reading.pinyin, pinyin_numeric=reading.pinyin_numeric,
        initial=reading.initial, final=reading.final, tone=None, start_ms=None, end_ms=None,
    )
