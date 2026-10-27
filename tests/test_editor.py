"""Редактор целиком в headless-режиме: события pygame подаются вручную."""
import os
import wave

import pygame
import pytest

import autosave as AS
import chart as chartmod
import config as C
import editor as E
import jsonio
import settings
import songs


@pytest.fixture
def song_env(data_root, tmp_path, monkeypatch):
    sd = tmp_path / "songs"
    sd.mkdir()
    with wave.open(str(sd / "t.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\0\0" * 8000 * 30)
    monkeypatch.setattr(songs, "SONG_DIR", str(sd))
    songs.forget_cached()
    return data_root


def mkeditor(env, tmp_path, notes=()):
    ch = songs.new_chart("t.wav", "Тест")
    for t, lane, d in notes:
        ch.notes.append(chartmod.Note(t, lane, d))
    ch.sort()
    ed = E.Editor(pygame.time.Clock(), ch, autosave_dir=str(tmp_path / "as"))
    ed.autosaver.threaded = False
    return ed


def lane_xy(ed, lane, tm):
    return (E.C.FIELD_X + lane * (C.LANE_W + C.LANE_GAP) + C.LANE_W // 2, int(ed.time_to_y(tm)))


def click(ed, pos, button=1):
    ed._event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button), pos)


def release(ed, pos):
    ed._event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1), pos)


def move(ed, pos):
    ed._event(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(1, 0, 0)), pos)


def key(ed, k, mods=0, uni=""):
    pygame.key.set_mods(mods)
    try:
        return ed._event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=mods, unicode=uni), (0, 0))
    finally:
        pygame.key.set_mods(0)


def test_add_undo_redo_and_dirty(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path)
    ed.grid.snap_on = False
    assert ed.save_state() == "saved" or ed.save_state() == "dirty"
    ed.add_note(1234, 1)
    assert [n.key() for n in ed.chart.notes] == [(1234, 1, 0)]
    assert ed.dirty
    ed._undo()
    assert not ed.chart.notes
    ed._redo()
    assert len(ed.chart.notes) == 1
    ed.add_note(1234, 1)                       # точный дубликат отклоняется
    assert len(ed.chart.notes) == 1
    ed.add_note(1240, 1)                       # близко, но не дубликат — раньше запрещалось (40 мс)
    assert len(ed.chart.notes) == 2


def test_save_clears_dirty_and_writes_file(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path)
    ed.add_note(500, 0)
    assert ed._save()
    assert ed.save_state() in ("saving", "saved")
    assert not ed.dirty
    assert os.path.isfile(ed.chart.path)
    ed._undo()
    assert ed.dirty                           # undo после сохранения снова делает чарт изменённым
    ed._redo()
    assert not ed.dirty


def test_snap_off_places_exact_time_and_snap_on_nearest(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path)
    g = ed.grid
    g.mode, g.ms_step, g.snap_on = "ms", 50, True
    ed.cursor = 1037.0
    key(ed, pygame.K_d)
    assert ed.chart.notes[0].t == 1050
    ed._toggle_snap()
    assert not g.snap_on
    ed.cursor = 2037.0
    key(ed, pygame.K_f)
    assert [n.t for n in ed.chart.notes] == [1050, 2037]


def test_bpm_change_does_not_move_notes(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path, notes=[(1000, 0, 0), (1337, 1, 0)])
    before = [n.key() for n in ed.chart.notes]
    ed._grid_row_action("bpm", 1)
    ed._grid_row_action("div", 1)
    ed._grid_row_action("offset", 1)
    assert [n.key() for n in ed.chart.notes] == before
    assert ed.grid.bpm == 121.0
    ed._undo()
    ed._undo()
    ed._undo()
    assert ed.grid.bpm == 120.0 and ed.grid.offset == 0
    assert [n.key() for n in ed.chart.notes] == before


def test_snap_toggle_is_not_an_edit(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path)
    ed.add_note(100, 0)
    ed._save()
    ed._toggle_snap()
    ed._grid_row_action("lines", 1)
    assert not ed.dirty


def test_select_drag_move_is_one_undo_step(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path, notes=[(1000, 0, 0), (1500, 0, 0)])
    ed.grid.snap_on = False
    ed.cursor = 800.0
    a = lane_xy(ed, 0, 1000)
    click(ed, a)
    assert len(ed.sel) == 1
    for i in range(1, 6):
        move(ed, (lane_xy(ed, 2, 1000)[0], a[1] - i * 10))
    release(ed, (lane_xy(ed, 2, 1000)[0], a[1] - 50))
    moved = [n for n in ed.chart.notes if n.lane == 2]
    assert len(moved) == 1 and moved[0].t > 1000
    ed._undo()
    assert sorted(n.key() for n in ed.chart.notes) == [(1000, 0, 0), (1500, 0, 0)]


def test_drag_onto_existing_note_is_refused(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path, notes=[(1000, 0, 0), (1000, 1, 0)])
    ed.grid.snap_on = False
    ed.cursor = 800.0
    a = lane_xy(ed, 0, 1000)
    click(ed, a)
    move(ed, lane_xy(ed, 1, 1000))
    release(ed, lane_xy(ed, 1, 1000))
    assert sorted(n.key() for n in ed.chart.notes) == [(1000, 0, 0), (1000, 1, 0)]


def test_hold_resize_by_wheel_and_min_length(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path, notes=[(1000, 0, 0)])
    ed.grid.snap_on = False
    ed.cursor = 800.0
    pos = lane_xy(ed, 0, 1000)
    n = ed.chart.notes[0]
    ed._wheel_note(1, pos)
    assert n.dur == E.MIN_HOLD
    ed._wheel_note(-1, pos)
    assert n.dur == 0


def test_box_select_copy_paste_delete(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path, notes=[(1000, 0, 0), (1100, 1, 0), (5000, 2, 0)])
    ed.cursor = 800.0
    ed._set_selection(ed.chart.notes[:2])
    ed._copy()
    ed.cursor = 3000.0
    ed.grid.snap_on = False
    ed._paste()
    assert len(ed.chart.notes) == 5
    ed.delete_notes(ed._selected())
    assert len(ed.chart.notes) == 3
    ed._undo()
    ed._undo()
    assert len(ed.chart.notes) == 3


def test_quantize_moves_to_grid_and_undoes(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path, notes=[(1013, 0, 0), (1990, 1, 0)])
    g = ed.grid
    g.mode, g.ms_step = "ms", 50
    ed._quantize()
    assert [n.t for n in ed.chart.notes] == [1000, 2000]
    ed._undo()
    assert [n.t for n in ed.chart.notes] == [1013, 1990]


def test_autosave_runs_and_recovers(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path)
    ed.add_note(700, 3)
    ed._maybe_autosave()            # обычная правка: сразу не пишем (нет частых записей на диск)
    assert ed.autosaver.writes == 0
    ed.autosaver.dirty_since -= 100
    ed._maybe_autosave()
    assert ed.autosaver.writes == 1
    ed._maybe_autosave()
    assert ed.autosaver.writes == 1  # без новых правок повторной записи нет
    recs = AS.scan(str(tmp_path / "as"), songs.CHART_DIR)
    assert recs and recs[0].name == "Тест"
    ed2 = E.Editor(pygame.time.Clock(), AS.restore_chart(recs[0]), recovery=recs[0],
                   autosave_dir=str(tmp_path / "as"))
    assert [n.key() for n in ed2.chart.notes] == [(700, 3, 0)]
    assert ed2.dirty


def test_emergency_autosave_on_error(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path)
    ed.add_note(100, 0)
    ed._emergency_autosave()
    assert AS.scan(str(tmp_path / "as"), songs.CHART_DIR)


def test_draw_all_states_without_crash(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path, notes=[(i * 120, i % 4, 400 if i % 5 == 0 else 0) for i in range(80)])
    ed._set_selection(ed.chart.notes[:3])
    for state in ("normal", "menu", "help", "name"):
        ed.menu_open = state == "menu"
        ed.help_open = state == "help"
        ed.name_edit = state == "name"
        ed._draw((100, 100))
    for z in (E.ZOOM_MIN, 0.3, E.ZOOM_MAX):
        ed.zoom = z
        ed._draw((400, 300))
    ed.grid.mode, ed.grid.div, ed.grid.bpm = "beat", 16, 240
    ed._draw((400, 300))


def test_status_states(song_env, tmp_path):
    ed = mkeditor(song_env, tmp_path)
    ed.add_note(10, 0)
    assert ed.save_state() == "dirty"
    ed.save_error = "boom"
    assert ed.save_state() == "error"
    ed.save_error = ""
    ed.saving = 0.2
    assert ed.save_state() == "saving"


def test_save_error_is_reported_not_raised(song_env, tmp_path, monkeypatch):
    ed = mkeditor(song_env, tmp_path)
    ed.add_note(10, 0)

    def boom(ch, backup=True):
        raise jsonio.SaveError("нет места")
    monkeypatch.setattr(songs, "save_chart", boom)
    assert ed._save() is False
    assert ed.save_state() == "error" and ed.dirty


def test_check_report_and_help_lines(song_env, tmp_path, monkeypatch):
    ed = mkeditor(song_env, tmp_path, notes=[(100, 0, 0)])
    import dialogs
    seen = {}
    monkeypatch.setattr(dialogs, "info_lines", lambda clock, title, lines, **kw: seen.update(lines=lines))
    ed._check_report()
    assert seen["lines"]
    assert len(E.help_lines()) > 15


def test_speed_change_keeps_clock_and_audio_position_in_sync(song_env, tmp_path, monkeypatch):
    """Регрессия: после замедления и возврата на 1x звук и ноты расходились (звук стартовал не с той секунды)."""
    import audio
    ed = mkeditor(song_env, tmp_path)
    fake = [1000.0]
    ed.sclk._time = lambda: fake[0]
    monkeypatch.setattr(audio, "play_song", lambda path, at: calls.append((path, at)))
    calls = []
    real_get = E.settings.get
    monkeypatch.setattr(E.settings, "get", lambda k, *a: 0 if k == "latency_ms" else real_get(k, *a))
    ed.cursor = 10345.0
    ed.speed_i = E.SPEEDS.index(0.5)
    ed._start_audio(ed.cursor)
    assert calls[-1][1] == pytest.approx(20690.0)                 # реальные мс замедленной дорожки
    fake[0] += 1.0                                                 # прошла 1 реальная секунда
    assert ed._now() == pytest.approx(10345.0 + 500.0)            # в чарте — 0.5 с
    ed.playing = True
    ed._tick(0.016)
    cur = ed.cursor
    ed._set_speed(E.SPEEDS.index(1.0))
    assert calls[-1][1] == pytest.approx(cur)                      # на 1x звук стартует с позиции курсора
    fake[0] += 2.0
    assert ed._now() == pytest.approx(cur + 2000.0)
    ed.playing = False
