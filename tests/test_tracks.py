"""Дорожки событий и групповые правки: модуль tracks, проверка файла и поведение экрана событий."""
import pygame
import pytest

import chart as chartmod
import dialogs
import events as EV
import tracks
import validation as V


#-- Помощники

def _chart(events=(), folders=()):
    ch = chartmod.Chart("t.ogg")
    ch.events.extend(events)
    ch.folders.extend(folders)
    return ch


def _screen(ch, cursor=5000):
    import events_screen as ES
    return ES, ES.EventsScreen(pygame.time.Clock(), ch, cursor, 60000)


def _ev(kind, t, **kw):
    ev = EV.make(kind, t)
    ev.update(kw)
    return ev


def _mark_in(scr, ev):
    if not scr._marked():
        scr._clear_marks()
        scr._select_row(("event", ev))
        scr._mark(ev, True)
    else:
        scr._extend(("event", ev), toggle=True)


def _fields_of(kind):
    return [(k, lbl, lo, hi, st) for k, lbl, lo, hi, st, _ in EV.FIELDS[kind]]


#-- Дорожки: проверка файла

def test_old_folder_gets_default_kind_and_visibility_without_warning():
    rep = V.Report("t")
    _, folders = V._check_events_and_folders([], [{"name": "A", "locked": False}], rep, 60000, None)
    assert folders == [{"name": "A", "locked": False, "kind": "custom", "visible": True}]
    assert not rep.has_code("folder.kind")


def test_track_kind_and_visibility_are_kept():
    rep = V.Report("t")
    _, folders = V._check_events_and_folders(
        [], [{"name": "A", "locked": True, "kind": "decor", "visible": False}], rep, 60000, None)
    assert folders == [{"name": "A", "locked": True, "kind": "decor", "visible": False}]


def test_unknown_track_kind_is_fixed_and_reported():
    rep = V.Report("t")
    _, folders = V._check_events_and_folders([], [{"name": "B", "kind": "weird"}], rep, 60000, None)
    assert folders[0]["kind"] == tracks.DEFAULT_KIND
    assert rep.has_code("folder.kind") and rep.ok


def test_track_fields_survive_chart_round_trip():
    ch = _chart(folders=[{"name": "A", "locked": False, "kind": "effects", "visible": False}])
    clean, rep = V.check_chart(ch.to_dict())
    assert clean is not None
    assert clean["folders"] == [{"name": "A", "locked": False, "kind": "effects", "visible": False}]


#-- Модуль tracks: значения и поля

def test_next_kind_cycles_through_all_kinds():
    seen = [tracks.DEFAULT_KIND]
    for _ in range(len(tracks.KINDS)):
        seen.append(tracks.next_kind(seen[-1]))
    assert seen[0] == seen[-1] and set(seen) == set(tracks.KINDS)


def test_hidden_names_lists_only_hidden_tracks():
    folders = [tracks.new_folder("A"), {"name": "B", "visible": False, "locked": False, "kind": "custom"}]
    assert tracks.hidden_names(folders) == {"B"}


def test_common_value_is_mixed_when_values_differ():
    a, b = _ev("glitch", 0, dur=800), _ev("glitch", 100, dur=800)
    assert tracks.common_value([a, b], "dur") == 800
    b["dur"] = 900
    assert tracks.common_value([a, b], "dur") is tracks.MIXED


def test_common_fields_intersects_ranges_for_mixed_media():
    fields = tracks.common_fields({"image", "video"}, _fields_of)
    keys = [f[0] for f in fields]
    assert "dur" in keys and "w" in keys and "dx" in keys
    assert "h" not in keys
    dur = next(f for f in fields if f[0] == "dur")
    assert dur[2] == 200 and dur[3] == 20000


def test_common_fields_for_one_kind_returns_its_numeric_fields():
    keys = [f[0] for f in tracks.common_fields({"glitch"}, _fields_of)]
    assert keys == ["dur", "strength"]


def test_common_fields_is_empty_for_unrelated_kinds_without_shared_keys():
    assert tracks.common_fields({"card", "heal"}, _fields_of) == []


#-- Групповые правки

def test_shift_values_clamps_and_skips_locked():
    free = _ev("glitch", 0, dur=4990)
    locked = _ev("glitch", 0, dur=1000, locked=True)
    changed = tracks.shift_values([free, locked], "dur", 100, 5000, 50)
    assert changed == 1 and free["dur"] == 5000 and locked["dur"] == 1000


def test_set_values_writes_one_value_to_unlocked_only():
    a, b = _ev("glitch", 0, dur=200), _ev("glitch", 0, dur=300, locked=True)
    assert tracks.set_values([a, b], "dur", 400, 100, 5000) == 1
    assert a["dur"] == 400 and b["dur"] == 300


def test_toggle_flag_turns_all_on_then_off():
    a, b = _ev("bg", 0, orig=True), _ev("bg", 0, orig=False)
    assert tracks.toggle_flag([a, b], "orig") == 2
    assert a["orig"] is True and b["orig"] is True
    tracks.toggle_flag([a, b], "orig")
    assert a["orig"] is False and b["orig"] is False


def test_move_to_keeps_intervals_and_clamps_to_duration():
    a, b = _ev("flash", 1000), _ev("flash", 3000)
    tracks.move_to([a, b], 50000, 52000)
    assert a["t"] == 50000 and b["t"] == 52000


def test_duplicate_keeps_intervals_and_copies_are_unlocked():
    a = _ev("flash", 1000, locked=True)
    b = _ev("flash", 1600)
    copies = tracks.duplicate_at([a, b], 20000, 60000)
    assert [c["t"] for c in copies] == [20000, 20600]
    assert all(c["locked"] is False for c in copies)
    assert copies[0] is not a


def test_remove_events_keeps_locked_and_list_identity():
    a, b = _ev("flash", 0), _ev("flash", 10, locked=True)
    keep = _ev("glitch", 20)
    events = [a, b, keep]
    alias = events
    removed, skipped = tracks.remove_events(events, [a, b])
    assert (removed, skipped) == (1, 1)
    assert events is alias and events == [b, keep]


def test_assign_folder_skips_locked():
    a, b = _ev("flash", 0), _ev("flash", 10, locked=True)
    assert tracks.assign_folder([a, b], "A") == 1
    assert a["folder"] == "A" and b["folder"] == ""


#-- Экран событий: дорожки

def test_hidden_track_hides_events_but_keeps_them_in_chart():
    evs = [_ev("flash", 1000, folder="A"), _ev("glitch", 2000, folder="A"), _ev("flash", 3000)]
    ch = _chart(evs, [tracks.new_folder("A")])
    ES, scr = _screen(ch)
    assert sum(1 for kind, _ in scr._view() if kind == "event") == 3
    scr.sel_folder = "A"
    scr._toggle_visible()
    assert ch.folders[0]["visible"] is False
    rows = scr._view()
    assert [kind for kind, _ in rows].count("event") == 1
    assert len(ch.events) == 3


def test_showing_track_again_restores_its_events():
    ch = _chart([_ev("flash", 1000, folder="A")], [tracks.new_folder("A")])
    ES, scr = _screen(ch)
    scr.sel_folder = "A"
    scr._toggle_visible()
    scr._toggle_visible()
    assert ch.folders[0]["visible"] is True
    assert sum(1 for kind, _ in scr._view() if kind == "event") == 1


def test_cycle_kind_changes_folder_type():
    ch = _chart(folders=[tracks.new_folder("A")])
    ES, scr = _screen(ch)
    scr.sel_folder = "A"
    scr._cycle_kind()
    assert ch.folders[0]["kind"] == "effects"


#-- Экран событий: выбор и групповые правки

def test_shift_click_marks_events_and_fields_show_dash_for_mixed_values():
    a = _ev("glitch", 1000, dur=800)
    b = _ev("glitch", 2000, dur=1200)
    ch = _chart([a, b])
    ES, scr = _screen(ch)
    _mark_in(scr, a)
    _mark_in(scr, b)
    assert len(scr._batch_targets()) == 2
    assert scr._value_text("dur") == "—"
    assert scr._value_text("strength") == str(a["strength"])


def test_batch_time_shift_moves_every_selected_event():
    a, b = _ev("flash", 1000), _ev("glitch", 3000)
    ch = _chart([a, b])
    ES, scr = _screen(ch)
    _mark_in(scr, a)
    _mark_in(scr, b)
    scr._adjust("t", 0, 60000, 10, 1)
    assert a["t"] == 1010 and b["t"] == 3010


def test_batch_typed_value_applies_to_all_selected(monkeypatch):
    a, b = _ev("glitch", 1000, dur=800), _ev("glitch", 2000, dur=1200)
    ch = _chart([a, b])
    ES, scr = _screen(ch)
    _mark_in(scr, a)
    _mark_in(scr, b)
    keys = [r[0] for r in scr._fields()]
    scr._start_edit(keys.index("dur"))
    scr.edit_buf = "400"
    scr._finish_edit(True)
    assert a["dur"] == 400 and b["dur"] == 400


def test_locked_event_is_left_alone_by_batch_edit():
    a = _ev("glitch", 1000, dur=800)
    b = _ev("glitch", 2000, dur=800, locked=True)
    ch = _chart([a, b])
    ES, scr = _screen(ch)
    _mark_in(scr, a)
    _mark_in(scr, b)
    scr._adjust("dur", 100, 5000, 100, 1)
    assert a["dur"] == 900 and b["dur"] == 800


def test_batch_delete_removes_unlocked_after_confirm(monkeypatch):
    monkeypatch.setattr(dialogs, "confirm", lambda clock, message: True)
    a, b = _ev("flash", 1000), _ev("flash", 2000)
    keep = _ev("glitch", 3000, locked=True)
    ch = _chart([a, b, keep])
    ES, scr = _screen(ch)
    _mark_in(scr, a)
    _mark_in(scr, b)
    _mark_in(scr, keep)
    scr._delete()
    assert ch.events == [keep]


def test_batch_delete_cancelled_keeps_everything(monkeypatch):
    monkeypatch.setattr(dialogs, "confirm", lambda clock, message: False)
    a, b = _ev("flash", 1000), _ev("flash", 2000)
    ch = _chart([a, b])
    ES, scr = _screen(ch)
    _mark_in(scr, a)
    _mark_in(scr, b)
    scr._delete()
    assert len(ch.events) == 2


def test_batch_duplicate_places_copies_at_cursor():
    a, b = _ev("flash", 1000), _ev("flash", 1500)
    ch = _chart([a, b])
    ES, scr = _screen(ch, cursor=20000)
    _mark_in(scr, a)
    _mark_in(scr, b)
    scr._duplicate()
    times = sorted(e["t"] for e in ch.events)
    assert times == [1000, 1500, 20000, 20500]


def test_ctrl_a_marks_only_visible_events():
    a, b = _ev("flash", 1000), _ev("flash", 2000, folder="H")
    ch = _chart([a, b], [tracks.new_folder("H")])
    ch.folders[0]["visible"] = False
    ES, scr = _screen(ch)
    scr._mark_all()
    assert scr._marked() == [a]


def test_escape_clears_selection_before_leaving(monkeypatch):
    a, b = _ev("flash", 1000), _ev("flash", 2000)
    ch = _chart([a, b])
    ES, scr = _screen(ch)
    _mark_in(scr, a)
    _mark_in(scr, b)
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=0)
    assert scr._key(ev) is None
    assert scr._marked() == []
    assert scr._key(ev) == "back"


def test_plain_click_clears_marks_and_selects_one(monkeypatch):
    a, b = _ev("flash", 1000), _ev("flash", 2000)
    ch = _chart([a, b])
    ES, scr = _screen(ch)
    _mark_in(scr, a)
    _mark_in(scr, b)
    scr._clear_marks()
    scr._select_row(("event", a))
    assert scr._marked() == [] and scr.cur is a


def test_marks_drop_events_removed_from_chart():
    a, b = _ev("flash", 1000), _ev("flash", 2000)
    ch = _chart([a, b])
    ES, scr = _screen(ch)
    _mark_in(scr, a)
    _mark_in(scr, b)
    ch.events.remove(a)
    assert scr._marked() == [b]
