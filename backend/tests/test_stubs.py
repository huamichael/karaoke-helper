"""Every function in backend-interfaces.md section 3 exists with its contract signature.

The expected signatures are read from the contract file itself, so editing a
signature on one side only fails here. A stub still raising NotImplementedError
is expected until its owner replaces it.

Owner: B.
"""

import importlib
import inspect
import re
from pathlib import Path

import pytest

from app.audio import BadAudio

CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "contracts" / "backend-interfaces.md"

# backend-interfaces.md section 1
MODULE_OF = {
    "load_audio": "app.audio",
    "transcribe": "app.scoring.transcribe",
    "match": "app.scoring.matcher",
    "score_sounds_base": "app.scoring.matcher",
    "grade": "app.scoring.grader",
    "align": "app.scoring.ctc",
    "score_sounds": "app.scoring.ctc",
    "score_rhythm": "app.scoring.rhythm",
    "to_syllables": "app.mandarin",
    "segment_words": "app.mandarin",
    "sandhi_tones": "app.mandarin",
    "score_tones": "app.scoring.tone",
}


def contract_signatures() -> dict[str, str]:
    text = CONTRACT.read_text(encoding="utf-8")
    section = text.split("## 3. Functions", 1)[1].split("## 4.", 1)[0]
    found = re.findall(r"^(def (\w+)\(.*)$", section, flags=re.MULTILINE)
    return {name: line.strip() for line, name in found}


def render(fn) -> str:
    params = []
    for p in inspect.signature(fn).parameters.values():
        default = "" if p.default is inspect.Parameter.empty else f" = {p.default!r}"
        params.append(f"{p.name}: {p.annotation}{default}")
    return f"def {fn.__name__}({', '.join(params)}) -> {inspect.signature(fn).return_annotation}"


def load(name: str):
    module = importlib.import_module(MODULE_OF[name])
    fn = getattr(module, name)
    assert fn.__module__ == MODULE_OF[name], f"{name} is re-exported, not defined in {MODULE_OF[name]}"
    return fn


def test_contract_lists_every_function_we_map():
    assert sorted(contract_signatures()) == sorted(MODULE_OF)


@pytest.mark.parametrize("name", sorted(MODULE_OF))
def test_signature_matches_contract(name):
    assert render(load(name)) == contract_signatures()[name]


@pytest.mark.parametrize("name", sorted(MODULE_OF))
def test_stub_raises_not_implemented(name):
    fn = load(name)
    if not _is_stub(fn):
        pytest.skip(f"{name} is implemented")
    with pytest.raises(NotImplementedError):
        fn(*[None] * len(inspect.signature(fn).parameters))


def _is_stub(fn) -> bool:
    body = inspect.getsource(fn).split(":\n", 1)[1].strip()
    return body == "raise NotImplementedError"


def test_bad_audio_is_an_exception():
    assert issubclass(BadAudio, Exception)
