"""The table of commonly confused Mandarin sounds (zh/z, n/l, an/ang and so on).

The matcher uses it to score near-misses, and the CTC layer uses it to build the
variants it compares. This is the single source for these pairs.

Owner: B. Spec: docs/contracts/scoring.md.
"""

INITIAL_PAIRS: tuple[tuple[str, str], ...] = (
    ("zh", "z"), ("ch", "c"), ("sh", "s"), ("j", "zh"), ("q", "ch"), ("x", "sh"), ("n", "l"),
)
FINAL_PAIRS: tuple[tuple[str, str], ...] = (
    ("an", "ang"), ("en", "eng"), ("in", "ing"), ("ian", "iang"), ("uan", "uang"), ("uen", "ueng"),
)


def _partners(sound: str, pairs: tuple[tuple[str, str], ...]) -> list[str]:
    return [b if a == sound else a for a, b in pairs if sound in (a, b)]


def initial_partners(initial: str) -> list[str]:
    """The initials commonly confused with this one, in table order. [] when there are none."""
    return _partners(initial, INITIAL_PAIRS)


def final_partners(final: str) -> list[str]:
    """The finals commonly confused with this one, in table order. [] when there are none."""
    return _partners(final, FINAL_PAIRS)
