"""Тест чарта от точки редактора (F5): копия играется от курсора, ничего не пишется, исходный чарт не меняется."""
import copy
import wave

import pygame
import pytest

import audio
import chart as chartmod
import editor as E
import game as G
import keymap
import library
import practice as PR
import runs
import session as SE
import songs
from i18n import t


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


def _chart():
    ch = songs.new_chart("t.wav", "T")
    ch.notes = [chartmod.Note(1000 + i * 400, i % 4, 0) for i in range(6)]
    ch.sort()
    return ch


def _forbid(*a, **k):
    raise AssertionError("тест не должен писать на диск или трогать прогресс")


OUTCOME = {"action": "test", "test_complete": True, "grade": "A", "acc": 91.5, "score": 1234,
           "max_combo": 7, "end_ms": 3000}


@pytest.fixture
def fake_game(monkeypatch):
    """Игра не открывается: run() отдаёт заранее заданный итог, сводка записывается."""
    shown = []
    monkeypatch.setattr(G.Game, "run", lambda self: dict(OUTCOME))
    monkeypatch.setattr("dialogs.info_lines", lambda clock, title, lines, **k: shown.append((title, lines)))
    return shown


@pytest.fixture
def prep_log(monkeypatch):
    calls = []

    def fake_prep(clock, chart, practice=None, ghost=None, notes=(), mods=(), test=False):
        calls.append({"practice": practice, "test": test, "mods": list(mods)})
        return SE.prepare(chart, practice, ghost, notes, mods, test)
    monkeypatch.setattr(SE, "prep_screen", fake_prep)
    return calls


def _drive(g, ft, limit_s, frame=0.05):
    while not g.finished and ft.t < limit_s:
        ft.t += frame
        g._update(frame)
        g._draw((0, 0))


#-- Клавиша и редактор

def test_f5_is_bound_to_test_from_cursor():
    assert keymap.label("test_here") == "F5"
    assert pygame.K_F5 in keymap.codes("test_here")


def test_f5_plays_a_copy_from_the_cursor_and_keeps_the_chart(song_env, tmp_path, prep_log, fake_game):
    ch = _chart()
    ed = E.Editor(pygame.time.Clock(), ch, autosave_dir=str(tmp_path / "as"))
    ed.autosaver.threaded = False
    ed.cursor = 2000.0
    before = ch.to_dict()
    ed._key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F5, mod=0, unicode="", scancode=0))
    assert prep_log[0]["test"] is True
    assert prep_log[0]["practice"].a == 2000
    assert ch.to_dict() == before, "исходный чарт изменился после теста"
    assert ed.cursor == OUTCOME["end_ms"]
    assert fake_game[0][0] == t("ТЕСТ ОКОНЧЕН")


def test_f5_too_close_to_the_end_does_not_start_a_test(song_env, tmp_path, prep_log, fake_game):
    ed = E.Editor(pygame.time.Clock(), _chart(), autosave_dir=str(tmp_path / "as"))
    ed.autosaver.threaded = False
    ed.cursor = float(ed.duration - 100)
    ed._key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F5, mod=0, unicode="", scancode=0))
    assert prep_log == []


#-- Запуск

def test_play_test_runs_a_copy_in_test_mode_with_no_persistence(song_env, prep_log, fake_game, monkeypatch):
    monkeypatch.setattr(library, "get", _forbid)
    ch = _chart()
    out = runs.play_test(pygame.time.Clock(), copy.deepcopy(ch), 2000, 1.0)
    cfg = prep_log[0]["practice"]
    assert prep_log[0]["test"] is True
    assert cfg.a == 2000 and cfg.loop is False and cfg.hp_loss is False
    assert out["action"] == "test" and out["test_complete"] is True


def test_real_game_in_test_mode_plays_to_the_end_and_reports_test(song_env, monkeypatch):
    monkeypatch.setattr(library, "get", _forbid)
    s = SE.prepare(_chart(), PR.PracticeConfig(a=1000, b=0, loop=False), test=True)
    g = G.Game(pygame.time.Clock(), s)
    ft = FakeTime()
    g.song = audio.SongClock(s.speed, time_fn=ft, latency_fn=lambda: 0)
    g.song.start(g.start_time)
    _drive(g, ft, 100.0 + 25.0)
    assert g.finished
    out = g.result()
    assert out["action"] == "test" and out["test_complete"] is True


def test_notes_before_the_point_are_not_scored(song_env):
    s = SE.prepare(_chart(), PR.PracticeConfig(a=2000, b=0, loop=False), test=True)
    g = G.Game(pygame.time.Clock(), s)
    assert g.total == 3


def test_pause_menu_in_test_mode_offers_only_resume_restart_and_editor(song_env):
    s = SE.prepare(_chart(), PR.PracticeConfig(a=1000, b=0, loop=False), test=True)
    g = G.Game(pygame.time.Clock(), s)
    assert [a for a, _ in g.pause_btns] == ["resume", "restart", "menu"]
    g._go_menu()
    out = g.result()
    assert out["action"] == "test" and out["test_complete"] is False


def test_interrupted_test_returns_without_summary(song_env, prep_log, fake_game, monkeypatch):
    monkeypatch.setattr(G.Game, "run", lambda self: dict(OUTCOME, test_complete=False))
    out = runs.play_test(pygame.time.Clock(), _chart(), 1000, 1.0)
    assert out["test_complete"] is False
    assert fake_game == []
