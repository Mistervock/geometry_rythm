"""Игра с кинематографикой и пакетами: камера в кадре, переход с пропуском Enter, пакеты и лимит активных."""
import wave

import pygame
import pytest

import audio
import chart as chartmod
import events as EV
import game as G
import packs as PK
import practice as PR
import session as SE
import songs


class FakeTime:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


@pytest.fixture
def song_env(data_root, tmp_path, monkeypatch):
    sd = tmp_path / "songs"
    sd.mkdir()
    with wave.open(str(sd / "t.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\0\0\0\0" * 44100 * 20)
    monkeypatch.setattr(songs, "SONG_DIR", str(sd))
    songs.forget_cached()
    return tmp_path


def _chart(events):
    ch = songs.new_chart("t.wav", "T")
    ch.notes = [chartmod.Note(19000, 0, 0)]
    ch.events.extend(events)
    return ch


def _game(ch):
    s = SE.prepare(ch, None, None)
    g = G.Game(pygame.time.Clock(), s)
    ft = FakeTime()
    g.song = audio.SongClock(s.speed, time_fn=ft, latency_fn=lambda: 0)
    g.song.start(g.start_time)
    return g, ft


ORIGIN = 100.0


def _run_to(g, ft, chart_ms, frame=0.016):
    """Идёт по времени карты до chart_ms (отрицательные значения — отсчёт перед песней), рисуя каждый кадр."""
    end = ORIGIN + (G.COUNTDOWN_MS + chart_ms) / 1000.0
    while ft.t < end and not g.finished:
        ft.t += frame
        g._update(frame)
        g._draw((0, 0))


def test_level_opens_from_closed_during_the_countdown(song_env):
    g, ft = _game(_chart([]))
    _run_to(g, ft, -G.COUNTDOWN_MS + 100)
    shown = g.cine.overlay_at(g.now, g.cine_skipped)
    assert shown is not None and shown[0] > 0.5, "уровень не появляется из закрытого экрана"
    _run_to(g, ft, -G.COUNTDOWN_MS + 1100)
    assert g.cine.overlay_at(g.now, g.cine_skipped) is None


def test_practice_start_does_not_play_the_appearance(song_env):
    s = SE.prepare(_chart([]), PR.PracticeConfig(a=2000, b=0, loop=False))
    g = G.Game(pygame.time.Clock(), s)
    assert g.cine.overlay_at(g.start_time) is None


def test_music_follows_the_closed_screen(song_env, monkeypatch):
    levels = []
    monkeypatch.setattr(audio, "set_duck", lambda level: levels.append(level))
    g, ft = _game(_chart([]))
    _run_to(g, ft, -G.COUNTDOWN_MS + 200)
    assert levels and min(levels) < 0.5, "музыка не приглушена пока экран закрыт"
    _run_to(g, ft, -G.COUNTDOWN_MS + 1200)
    assert levels[-1] == pytest.approx(1.0)


def test_level_end_closes_the_screen_before_the_result(song_env):
    g, ft = _game(_chart([]))
    _run_to(g, ft, 20300)
    assert g.finish_at is not None and not g.finished, "итог показан до закрытия экрана"
    shown = g.cine.overlay_at(g.now, g.cine_skipped)
    assert shown is not None, "экран не начал закрываться перед итогом"
    _run_to(g, ft, 21400)
    assert g.finished


def test_camera_zooms_the_frame_during_its_move(song_env):
    ev = EV.normalize({"type": "camera", "t": 300, "dur": 600, "zoom": 200, "x": 0, "y": 0, "ease": "linear"})
    g, ft = _game(_chart([ev]))
    _run_to(g, ft, 600)
    zoom = g.cine.camera_at(g.now)[0]
    assert 140 < zoom < 160


def test_enter_skips_an_open_transition_without_touching_the_score(song_env):
    close = EV.normalize({"type": "transition", "t": 200, "dur": 200, "mode": "out", "kind": "fade"})
    opn = EV.normalize({"type": "transition", "t": 800, "dur": 800, "mode": "in", "kind": "fade",
                        "ease": "linear", "skip": True})
    g, ft = _game(_chart([close, opn]))
    _run_to(g, ft, 1200)
    assert g.cine.overlay_at(g.now, g.cine_skipped) is not None
    score = g.score
    g._skip_transition()
    assert g.cine_skipped, "переход не отмечен как пропущенный"
    assert g.cine.overlay_at(g.now, g.cine_skipped) is None
    assert g.skip_toast > 0 and g.score == score


def test_a_closing_transition_cannot_be_skipped(song_env):
    close = EV.normalize({"type": "transition", "t": 200, "dur": 800, "mode": "out", "kind": "iris"})
    g, ft = _game(_chart([close]))
    _run_to(g, ft, 500)
    g._skip_transition()
    assert g.cine_skipped == set()


def test_pack_event_is_drawn_and_cached(song_env):
    PK.reload()
    ev = EV.normalize({"type": "pack", "t": 300, "dur": 800, "pack": "burst", "lane": 0})
    g, ft = _game(_chart([ev]))
    _run_to(g, ft, 500)
    assert g.pack_events, "пакет не попал в список событий игры"
    assert g.pack_cache, "пакет не отрисован"


def test_no_more_than_the_active_limit_is_drawn_at_once(song_env):
    PK.reload()
    events = [EV.normalize({"type": "pack", "t": 300, "dur": 900, "pack": "burst", "lane": 0, "x": i * 10})
              for i in range(PK.MAX_ACTIVE + 4)]
    g, ft = _game(_chart(events))
    _run_to(g, ft, 500)
    assert 0 < len(g.pack_cache) <= PK.MAX_ACTIVE
