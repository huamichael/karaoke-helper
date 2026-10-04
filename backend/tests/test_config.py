"""Tests for the layer switches in app/config.py.

Owner: B. Spec: docs/contracts/backend-interfaces.md, section 4.
"""

import pytest

from app import config


@pytest.fixture(autouse=True)
def experiments_off(monkeypatch):
    for name in config.EXPERIMENT_FLAGS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def flags_off(monkeypatch):
    for name in config.LAYER_FLAGS:
        monkeypatch.setenv(name, "0")


@pytest.mark.parametrize(("target", "mode", "n", "wanted"), [
    ("line", "spoken", 6, (False, False, False, False)),
    ("line", "singing", 6, (True, True, True, False)),
    ("word", None, 1, (False, False, False, True)),
    ("word", None, 2, (True, False, False, True)),
    ("word", None, 3, (True, False, False, True)),
])
def test_table_with_every_switch_on(monkeypatch, target, mode, n, wanted):
    for name in config.LAYER_FLAGS:
        monkeypatch.setenv(name, "1")
    layers = config.layers_for(target, mode, n)
    assert (layers.ctc_spans, layers.ctc_scores, layers.rhythm, layers.tone) == wanted


def test_all_off_even_in_singing_mode(flags_off):
    layers = config.layers_for("line", "singing", 6)
    assert (layers.ctc_spans, layers.ctc_scores, layers.rhythm, layers.tone) == (False, False, False, False)


def test_ctc_alone_does_not_turn_on_rhythm_or_tone(monkeypatch):
    monkeypatch.setenv("ENABLE_CTC", "1")
    monkeypatch.setenv("ENABLE_RHYTHM", "0")
    monkeypatch.setenv("ENABLE_TONE", "0")
    singing = config.layers_for("line", "singing", 6)
    assert (singing.ctc_spans, singing.ctc_scores, singing.rhythm, singing.tone) == (True, True, False, False)
    word = config.layers_for("word", None, 2)
    assert (word.ctc_spans, word.ctc_scores, word.rhythm, word.tone) == (True, False, False, False)


def test_spoken_never_gets_ctc_even_when_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_CTC", "1")
    layers = config.layers_for("line", "spoken", 6)
    assert (layers.ctc_spans, layers.ctc_scores) == (False, False)


@pytest.mark.parametrize("name", config.LAYER_FLAGS + config.EXPERIMENT_FLAGS)
def test_bad_flag_rejected(monkeypatch, name):
    monkeypatch.setenv(name, "yes")
    with pytest.raises(ValueError, match=name):
        config.validate_layer_flags()


@pytest.mark.parametrize(("target", "mode", "n"), [
    ("song", "spoken", 1), ("line", None, 1), ("word", None, 0),
])
def test_bad_layers_for_arguments(flags_off, target, mode, n):
    with pytest.raises(ValueError):
        config.layers_for(target, mode, n)
