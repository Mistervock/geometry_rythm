"""Игровой цикл целиком: сессия → Game → результат, с подменой часов (без реального времени)."""
import wave

import pygame
import pytest

import audio
import chart as chartmod
import config as C
import game as G
import ghost as GH
import practice as PR
import session as SE
import songs


class FakeTime:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


@pytest.fixture
def env(data_root, tmp_path, monkeypatch):
    sd = tmp_path / "songs"
    sd.mkdir()
    with wave.open(str(sd / "t.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\0\0\0\0" * 44100 * 20)
    monkeypatch.setattr(songs, "SONG_DIR", str(sd))
    monkeypatch.setattr(PR, "PATH", str(tmp_path / "practice.json"))
    import stretch
    monkeypatch.setattr(stretch, "DIR", str(tmp_path / "speed"))
    songs.forget_cached()
    return tmp_path


def mkchart(specs):
    ch = songs.new_chart("t.wav", "T")
    ch.notes = [chartmod.Note(*s) for s in specs]
    ch.sort()
    return ch


def make_game(ch, practice=None, ghost=None):
    s = SE.prepare(ch, practice, ghost)
    g = G.Game(pygame.time.Clock(), s)
    ft = FakeTime()
    g.song = audio.SongClock(s.speed, time_fn=ft, latency_fn=lambda: 0)
    g.song.start(g.start_time)
    return g, ft


def step(g, ft, chart_ms, frame=16):
    """Продвигает игру на chart_ms мс чарта кадрами по frame мс реального времени."""
    end = ft.t + chart_ms / 1000.0 / g.speed
    while ft.t < end and not g.finished:
        ft.t += frame / 1000.0
        g._update(frame / 1000.0)
        g._draw((0, 0))


def tap(g, lane, hold_ms=0):
    g.engine.press(lane, g.song.now())


def test_full_run_perfect(env):
    ch = mkchart([(1000, 0, 0), (1500, 1, 800), (3000, 2, 0), (3500, 3, 0)])
    g, ft = make_game(ch)
    # дойти до первой ноты: старт -3000 → нота в +1000
    step(g, ft, 4000 - 4)
    tap(g, 0)
    step(g, ft, 500)
    tap(g, 1)
    step(g, ft, 800)
    g.engine.release(1, g.song.now())
    step(g, ft, 700)
    tap(g, 2)
    step(g, ft, 500)
    tap(g, 3)
    step(g, ft, 3000)
    assert g.finished
    out = g.result()
    assert out["failed"] is False and not out["practice"]
    st = out["stats"]
    assert st["total"] == 4 and st["holds_ok"] == 1 and st["counts"]["miss"] == 0
    assert out["judgments"] and out["timeline"]
    assert out["notes_hash"] == ch.notes_hash()


def test_miss_all_fails_in_normal_mode(env):
    ch = mkchart([(1000 + i * 300, i % 4, 0) for i in range(10)])
    g, ft = make_game(ch)
    step(g, ft, 10000)
    assert g.finished and g.result()["failed"] and g.result()["grade"] == "F"


def test_practice_loop_resets_everything(env):
    ch = mkchart([(2000, 0, 0), (2500, 1, 600), (3500, 2, 0), (8000, 3, 0)])
    cfg = PR.PracticeConfig(1500, 4000, 0.5, True, False).fit(20000)
    g, ft = make_game(ch, cfg)
    assert g.engine.total == 3 and g.song.speed == 0.5
    step(g, ft, 5000)                    # без нажатий: все ноты участка пропущены → повтор
    assert len(g.attempts) >= 1
    assert g.engine.attempt >= 3 and g.engine.counts["miss"] <= 2
    a0 = g.attempts[0]
    assert a0["counts"]["miss"] == 3 and not a0["failed"]
    assert g.engine.score == 0 and not g.engine.holds and len(g.s.events) == 0
    assert sum(1 for n in g.notes if n.state == "skip") == 1
    # повтор не дублирует ноты и события
    assert sum(len(q) for q in g.engine.pending) <= 3


def test_practice_no_loop_finishes_and_flags(env):
    ch = mkchart([(2000, 0, 0), (2500, 1, 0)])
    cfg = PR.PracticeConfig(1000, 3000, 0.75, False, False).fit(20000)
    g, ft = make_game(ch, cfg)
    step(g, ft, 6000)
    assert g.finished
    out = g.result()
    assert out["practice"] and out["section"] == (1000, 3000) and out["speed"] == 0.75
    assert "judgments" not in out and "timeline" not in out


def test_speed_keeps_notes_in_sync(env):
    ch = mkchart([(4000, 0, 0)])
    cfg = PR.PracticeConfig(3000, 6000, 0.5, False, False).fit(20000)
    g, ft = make_game(ch, cfg)
    # начало часов = a - preroll = 1000 мс чарта; на скорости 0.5 до ноты 3000 мс чарта = 6 с реальных
    step(g, ft, 3000 - 16)
    tap(g, 0)
    assert g.engine.counts["perfect"] + g.engine.counts["great"] + g.engine.counts["good"] == 1
    assert abs(g.engine.judgments[0].offset) <= C.WIN_GOOD


def test_ghost_view_and_draw_states(env):
    ch = mkchart([(1000 + i * 400, i % 4, 500 if i % 3 == 0 else 0) for i in range(12)])
    ghost_data = {"format": GH.FORMAT, "version": 1, "chart_id": "", "chart_key": "", "notes_hash": ch.notes_hash(),
                  "total": 12, "score": 5000, "acc": 90.0, "grade": "A", "max_combo": 10, "counts": {},
                  "saved_at": "", "timeline": [[1000, 300, 1], [1400, 600, 2]], "marks": [[1000, 0, "p"], [1400, 1, "p"]]}
    assert GH.validate(ghost_data)[0]
    g, ft = make_game(ch, None, GH.Ghost(ghost_data))
    step(g, ft, 4500)
    assert g.gview is not None and g.gview.score == 600
    g.engine.press(1, g.song.now())
    g.paused = True
    g._draw((300, 300))


def test_prep_errors_and_warnings(env, monkeypatch):
    ch = mkchart([])
    with pytest.raises(SE.PrepError):
        SE.prepare(ch)
    ch = mkchart([(1000, 0, 0)])
    ch.song = "nope.wav"
    with pytest.raises(SE.PrepError):
        SE.prepare(ch)
    ch = mkchart([(1000, 0, 0)])
    ch.events = [{"type": "image", "t": 500, "file": "missing.png", "dur": 500, "w": 200, "x": 0, "y": 0,
                  "fade": 0, "fadeout": 0}]
    s = SE.prepare(ch)
    assert s.events == [] and any("missing.png" in w for w in s.warnings)
    assert s.timings and s.index is not None and s.total_ms >= 0
