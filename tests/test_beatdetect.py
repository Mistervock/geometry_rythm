"""Авто-определение BPM и сдвига первой доли на синтетических трэках с известным ритмом."""
import numpy as np
import pytest

import beatdetect


def _track(bpm, off, dur=30.0, sr=22050, seed=3):
    rng = np.random.default_rng(seed)
    y = rng.standard_normal(int(sr * dur)) * 0.02
    tt = np.arange(int(0.02 * sr)) / sr
    burst = np.sin(2 * np.pi * 150 * tt) * np.exp(-tt * 200) * 0.8
    t = off
    while t < dur - 0.1:
        s = int(t * sr)
        y[s:s + len(burst)] += burst
        t += 60.0 / bpm
    return y, sr


@pytest.mark.parametrize("bpm,off", [(128, 0.23), (100, 0.05), (140, 0.40), (90, 0.0), (174, 0.11), (120, 0.30)])
def test_tempo_is_accurate(bpm, off):
    y, sr = _track(bpm, off)
    r = beatdetect.analyze(y, sr)
    assert r is not None
    assert abs(r["bpm"] - bpm) < 0.5, r


@pytest.mark.parametrize("bpm,off", [(128, 0.23), (100, 0.05), (140, 0.40), (174, 0.11)])
def test_offset_is_within_15_ms_modulo_beat(bpm, off):
    y, sr = _track(bpm, off)
    r = beatdetect.analyze(y, sr)
    beat = 60000.0 / bpm
    err = (r["offset_ms"] - off * 1000 + beat / 2) % beat - beat / 2
    assert abs(err) < 15.0, (r, err)


def test_too_short_or_silent_returns_none():
    sr = 22050
    assert beatdetect.analyze(np.zeros(sr * 3), sr) is None
    assert beatdetect.analyze(np.zeros(sr * 20), sr) is None


def test_confidence_is_in_range_and_high_for_clear_beat():
    y, sr = _track(120, 0.3)
    r = beatdetect.analyze(y, sr)
    assert 0.0 <= r["confidence"] <= 1.0
    assert r["confidence"] > 0.5
