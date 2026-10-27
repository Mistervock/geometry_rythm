"""Единая временная шкала звука: все скорости играют из одного декодирования и точно совпадают с чартом."""
import os
import wave

import numpy as np
import pygame
import pytest

import stretch


@pytest.fixture
def click_song(tmp_path, monkeypatch):
    monkeypatch.setattr(stretch, "DIR", str(tmp_path / "speed"))
    sr, dur = 22050, 6
    x = np.zeros(sr * dur, dtype=np.int16)
    for k in range(int(dur / 0.5)):
        s = int(k * 0.5 * sr)
        x[s:s + 40] = 20000
    p = tmp_path / "song.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(x.tobytes())
    return str(p)


def _clicks(path):
    with wave.open(path) as w:
        ch, rate = w.getnchannels(), w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, ch)[:, 0]
    idx = np.where(np.abs(a) > 10000)[0]
    out, last = [], -10 ** 9
    for i in idx:
        if i - last > rate * 0.2:
            out.append(i / rate * 1000.0)
        last = i
    return out


def test_clicks_stay_at_chart_time_for_every_speed(click_song):
    base = _clicks(stretch.ensure(click_song, 1.0))
    assert len(base) >= 10
    for speed in (0.5, 0.75, 1.25):
        got = [c * speed for c in _clicks(stretch.ensure(click_song, speed))]
        assert len(got) == len(base)
        assert max(abs(a - b) for a, b in zip(got, base)) < 2.0, speed


def test_normal_speed_is_cached_pcm_not_original(click_song):
    p = stretch.playable(click_song, 1.0)
    assert p != click_song and p.endswith(".wav") and os.path.isfile(p)


def test_duration_scales_exactly_with_speed(click_song):
    def dur(p):
        with wave.open(p) as w:
            return w.getnframes() / w.getframerate()
    d1 = dur(stretch.ensure(click_song, 1.0))
    assert abs(dur(stretch.ensure(click_song, 0.5)) - d1 / 0.5) < 0.01
    assert abs(dur(stretch.ensure(click_song, 0.75)) - d1 / 0.75) < 0.01


def test_cache_follows_replaced_song(click_song):
    a = stretch.ensure(click_song, 0.5)
    st = os.stat(click_song)
    os.utime(click_song, (st.st_atime, st.st_mtime + 100))
    b = stretch.ensure(click_song, 0.5)
    assert a != b


def test_playable_falls_back_to_song_at_normal_speed_only(click_song, monkeypatch):
    monkeypatch.setattr(stretch, "AVAILABLE", False)
    assert stretch.playable(click_song, 1.0) == click_song
    assert stretch.playable(click_song, 0.5) is None


def test_prune_removes_oldest_over_limit(click_song):
    for sp in (0.5, 0.75, 1.0):
        p = stretch.ensure(click_song, sp)
        os.utime(p, (1000 + int(sp * 100), 1000 + int(sp * 100)))
    stretch.prune(max_bytes=1)
    assert os.listdir(stretch.DIR) == []


def test_wav_seek_is_sample_exact_not_whole_seconds(click_song, monkeypatch):
    """Регрессия: mixer.music.play(start=) для WAV отбрасывал дробные секунды (7.3 с → 7.0 с)."""
    import audio
    path = stretch.ensure(click_song, 0.5)
    freq, _, ch = pygame.mixer.get_init()
    audio._pcm.update(path=None, raw=None)
    assert audio._load_pcm(path)
    total = len(audio._pcm["raw"])
    seen = []
    real_sound = pygame.mixer.Sound

    def spy(*a, **kw):
        if "buffer" in kw:
            seen.append(len(kw["buffer"]))
        return real_sound(*a, **kw)
    monkeypatch.setattr(pygame.mixer, "Sound", spy)
    for start_ms in (0.0, 1300.0, 7345.0):
        seen.clear()
        audio.play_song(path, start_ms)
        frames_skipped = int(round(start_ms / 1000.0 * freq))
        if seen:
            assert seen[0] == total - frames_skipped * 2 * ch, start_ms
    audio.stop_song()


def test_play_and_stop_cycle_leaves_no_busy_channel(click_song):
    import audio
    path = stretch.ensure(click_song, 0.75)
    audio.preload_song(path)
    assert audio._music_path == path
    audio.play_song(path, 500.0)
    audio.pause_song()
    audio.resume_song()
    audio.stop_song()
    assert not pygame.mixer.Channel(audio.SONG_CHANNEL).get_busy()


def test_foreign_wav_format_falls_back_to_stream(tmp_path):
    import audio
    p = tmp_path / "odd.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\0\0" * 8000)
    assert audio._load_pcm(str(p)) is False
