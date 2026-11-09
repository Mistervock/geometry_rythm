"""Игра с эффектами и анимированной картинкой: кадры целиком, с подменой часов (без реального времени)."""
import wave

import pygame
import pytest

import anim as AN
import audio
import chart as chartmod
import events as EV
import fx as FX
import game as G
import practice as PR
import session as SE
import settings
import songs
import stretch


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
    pic = pygame.Surface((40, 20))
    pic.fill((200, 30, 30))
    pygame.image.save(pic, str(tmp_path / "red.png"))
    monkeypatch.setattr(songs, "SONG_DIR", str(sd))
    monkeypatch.setattr(EV, "IMAGE_DIR", str(tmp_path))
    monkeypatch.setattr(PR, "PATH", str(tmp_path / "practice.json"))
    monkeypatch.setattr(stretch, "DIR", str(tmp_path / "speed"))
    EV._src.clear()
    EV._scaled.clear()
    songs.forget_cached()
    return tmp_path


def _anim():
    a = AN.new_animation("Рывок", [])
    a["id"] = "a1"
    a["dur"] = 1000
    a["keys"] = [AN.make_key(0, "linear", x=0, alpha=100), AN.make_key(1000, "linear", x=100, alpha=100)]
    return a


def _chart(events, animations):
    ch = songs.new_chart("t.wav", "T")
    ch.notes = [chartmod.Note(1000 + i * 400, i % 4, 0) for i in range(6)]
    ch.sort()
    ch.animations.extend(animations)
    ch.events.extend(events)
    return ch


def _game(ch):
    s = SE.prepare(ch, None, None)
    g = G.Game(pygame.time.Clock(), s)
    ft = FakeTime()
    g.song = audio.SongClock(s.speed, time_fn=ft, latency_fn=lambda: 0)
    g.song.start(g.start_time)
    return g, ft


def _run(g, ft, chart_ms, frame=16):
    end = ft.t + chart_ms / 1000.0 / g.speed
    while ft.t < end and not g.finished:
        ft.t += frame / 1000.0
        g._update(frame / 1000.0)
        g._draw((0, 0))


def _set_quality(monkeypatch, value):
    real_get = settings.get
    monkeypatch.setattr(settings, "get",
                        lambda key, *a, **k: value if key == "fx_quality" else real_get(key, *a, **k))


def test_game_draws_animated_picture_and_fx_layers(song_env, monkeypatch):
    _set_quality(monkeypatch, 2)
    ev_img = EV.normalize({"type": "image", "t": 300, "file": "red.png", "dur": 1500, "w": 200,
                           "anim_id": "a1", "anim": "fade", "fade": 100})
    ev_fx = EV.normalize({"type": "fx", "t": 500, "kind": "glow", "amount": 80, "attack": 100, "dur": 1500,
                          "beat": True})
    ch = _chart([ev_img, ev_fx], [_anim()])
    frames = []
    real = FX.frame

    def spy(surface, layers, now, bud=None):
        frames.append(list(layers))
        return real(surface, layers, now, bud)

    monkeypatch.setattr(FX, "frame", spy)
    g, ft = _game(ch)
    assert "a1" in g.anims
    _run(g, ft, G.COUNTDOWN_MS + 1500)
    active = [layers for layers in frames if layers]
    assert active, "ни один кадр не получил слой эффекта"
    assert all(kind == "glow" for layers in active for kind, _ in layers)


def test_game_runs_to_the_end_with_effects_switched_off(song_env, monkeypatch):
    _set_quality(monkeypatch, 0)
    ev_fx = EV.normalize({"type": "fx", "t": 300, "kind": "wave", "amount": 90, "attack": 0, "dur": 2000})
    ev_img = EV.normalize({"type": "image", "t": 300, "file": "red.png", "dur": 2000, "w": 200,
                           "anim_id": "a1", "anim": "fade", "fade": 100})
    ch = _chart([ev_fx, ev_img], [_anim()])
    g, ft = _game(ch)
    total = G.COUNTDOWN_MS + 2500
    _run(g, ft, total)
    assert g.finished or ft.t >= 100.0 + total / 1000.0 / g.speed
    assert FX.budget().mode() == "off"
