"""Редактор анимаций и строки экрана событий: клавиатура, мышь, перетаскивание ключа, диалоги и отрисовка."""
import pygame
import pytest

import anim as AN
import anim_editor as AE
import chart as chartmod
import dialogs
import events as EV
import screen_setting as SS
from i18n import t


#-- Помощники

def _anim(aid="a1", name="Рывок", **kw):
    a = AN.new_animation(name, [])
    a["id"] = aid
    a.update(kw)
    return a


def _editor(anims=None, events=None, anim_id=""):
    ch = chartmod.Chart("t.ogg")
    ch.animations.extend(anims or [])
    ch.events.extend(events or [])
    return AE.AnimEditor(pygame.time.Clock(), ch, anim_id), ch


def _kd(key, mods=0, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mods, unicode=unicode, scancode=0)


def _click(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(SS.U(x), SS.U(y)), button=1)


def _move(x, y):
    return pygame.event.Event(pygame.MOUSEMOTION, pos=(SS.U(x), SS.U(y)), rel=(0, 0), buttons=(1, 0, 0))


def _release():
    return pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(0, 0), button=1)


def _field(ed, name):
    return next(i for i, (_, n, _) in enumerate(AE.ROWS) if n == name)


def _mid():
    return (AE.TL_Y0 + AE.TL_Y1) // 2


#-- Клавиатура и ключи

def test_draw_runs_with_and_without_animations():
    ed, ch = _editor()
    ed._draw((0, 0))
    ed, ch = _editor([_anim()])
    ed._draw((0, 0))
    ed.playing = True
    ed._draw((0, 0))


def test_k_adds_key_at_playhead_and_selects_it():
    ed, ch = _editor([_anim()])
    ed.head = 500
    ed._on_key(_kd(pygame.K_k, unicode="k"))
    keys = ch.animations[0]["keys"]
    assert [k["t"] for k in keys] == [0, 500, 1000]
    assert ed.sel_key == 1


def test_first_key_cannot_be_moved():
    ed, ch = _editor([_anim()])
    ed.sel_key = 0
    ed._set("t", 300)
    assert ch.animations[0]["keys"][0]["t"] == 0
    assert ed.status == t("Первый ключ всегда стоит в начале анимации")


def test_moving_a_key_resorts_and_keeps_it_selected():
    ed, ch = _editor([_anim()])
    ed.head = 500
    ed._add_key()
    ed._set("t", 800)
    keys = ch.animations[0]["keys"]
    assert [k["t"] for k in keys] == [0, 800, 1000]
    assert keys[ed.sel_key]["t"] == 800


def test_key_cannot_land_on_an_occupied_time():
    ed, ch = _editor([_anim()])
    ed.head = 500
    ed._add_key()
    ed._set("t", 1000)
    assert [k["t"] for k in ch.animations[0]["keys"]] == [0, 500, 1000]
    assert ed.status == t("В этой точке времени уже есть ключ")


def test_arrow_keys_adjust_the_selected_field_and_clamp():
    ed, ch = _editor([_anim()])
    ed.field = _field(ed, "x")
    ed._on_key(_kd(pygame.K_RIGHT))
    assert ch.animations[0]["keys"][0]["x"] == 10
    ed._set("x", 99999)
    assert ch.animations[0]["keys"][0]["x"] == AN.LIMITS["x"][1]


def test_easing_cycles_through_all_kinds():
    ed, ch = _editor([_anim()])
    ed.sel_key = 1
    ed.field = _field(ed, "ease")
    ed._on_key(_kd(pygame.K_RIGHT))
    assert ch.animations[0]["keys"][1]["ease"] == AN.EASES[(AN.EASES.index(AN.DEFAULT_EASE) + 1) % len(AN.EASES)]


def test_tint_channels_stay_in_bytes():
    ed, ch = _editor([_anim()])
    ed.field = _field(ed, "r")
    ed._set("r", 999)
    assert ch.animations[0]["keys"][0]["tint"][0] == 255


def test_duration_change_keeps_the_end_frame():
    ed, ch = _editor([_anim()])
    ed.field = _field(ed, "dur")
    ed._on_key(_kd(pygame.K_LEFT))
    anim = ch.animations[0]
    assert anim["dur"] == 900
    assert anim["keys"][-1]["t"] == 900


def test_l_toggles_loop_and_enter_types_a_number(monkeypatch):
    ed, ch = _editor([_anim()])
    ed._on_key(_kd(pygame.K_l, unicode="l"))
    assert ch.animations[0]["loop"] is True
    monkeypatch.setattr(dialogs, "ask_text", lambda clock, title, initial="", maxlen=24: "250")
    ed.field = _field(ed, "x")
    ed._on_key(_kd(pygame.K_RETURN))
    assert ch.animations[0]["keys"][0]["x"] == 250


def test_numeric_dialog_rejects_text(monkeypatch):
    ed, ch = _editor([_anim()])
    monkeypatch.setattr(dialogs, "ask_text", lambda clock, title, initial="", maxlen=24: "много")
    ed.field = _field(ed, "x")
    ed._edit(ed.field)
    assert ch.animations[0]["keys"][0]["x"] == 0
    assert ed.status == t("Нужно число")


def test_delete_key_refuses_first_and_removes_others():
    ed, ch = _editor([_anim()])
    ed.head = 500
    ed._add_key()
    ed.sel_key = 0
    ed._del_key()
    assert len(ch.animations[0]["keys"]) == 3
    ed.sel_key = 1
    ed._del_key()
    assert [k["t"] for k in ch.animations[0]["keys"]] == [0, 1000]


def test_escape_leaves_the_editor():
    ed, _ = _editor([_anim()])
    assert ed._on_key(_kd(pygame.K_ESCAPE)) == "back"


def test_step_keys_moves_playhead_to_neighbour_key():
    ed, ch = _editor([_anim()])
    ed.head = 500
    ed._add_key()
    ed.sel_key = 0
    ed._on_key(_kd(pygame.K_RIGHTBRACKET, unicode="]"))
    assert ed.sel_key == 1 and ed.head == 500


#-- Проигрывание

def test_loop_playback_wraps_to_start():
    ed, ch = _editor([_anim(loop=True)])
    ed.playing = True
    ed.head = 950
    ed._advance(100)
    assert ed.head == pytest.approx(50)


def test_playback_without_loop_stops_at_the_end():
    ed, ch = _editor([_anim()])
    ed.playing = True
    ed.head = 950
    ed._advance(100)
    assert ed.head == 1000 and ed.playing is False


def test_space_starts_again_from_zero_after_the_end():
    ed, ch = _editor([_anim()])
    ed.head = 1000
    ed._on_key(_kd(pygame.K_SPACE, unicode=" "))
    assert ed.playing is True and ed.head == 0


#-- Мышь

def test_clicking_the_timeline_moves_the_playhead():
    ed, ch = _editor([_anim()])
    x = ed._t_to_x(250, 1000)
    ed._event(_click(x, _mid()))
    assert ed.head == pytest.approx(250, abs=2)


def test_dragging_a_key_moves_it_in_time():
    ed, ch = _editor([_anim()])
    ed.head = 500
    ed._add_key()
    x = ed._t_to_x(500, 1000)
    ed._event(_click(x, _mid()))
    assert ed.drag is not None
    ed._event(_move(ed._t_to_x(700, 1000), _mid()))
    assert [k["t"] for k in ch.animations[0]["keys"]] == [0, 700, 1000]
    ed._event(_release())
    assert ed.drag is None


def test_clicking_a_list_row_selects_that_animation():
    ed, ch = _editor([_anim("a1"), _anim("a2", "Второй")])
    ed._event(_click(AE.LIST_X + 10, AE.LIST_Y + AE.LIST_ROW + 4))
    assert ed.sel == 1


def test_back_button_returns_back():
    ed, _ = _editor([_anim()])
    btn = ed.buttons["back"][0]
    assert ed._event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=btn.rect.center, button=1)) == "back"


#-- Список анимаций

def test_new_and_duplicate_keep_ids_unique():
    ed, ch = _editor()
    ed._new()
    ed._new()
    ed._dup()
    ids = [a["id"] for a in ch.animations]
    assert len(ids) == 3 and len(set(ids)) == 3


def test_rename_uses_dialog(monkeypatch):
    ed, ch = _editor([_anim()])
    monkeypatch.setattr(dialogs, "ask_text", lambda clock, title, initial="", maxlen=24: "Новое имя")
    ed._rename()
    assert ch.animations[0]["name"] == "Новое имя"


def test_delete_clears_links_from_events(monkeypatch):
    anim = _anim()
    ev = EV.normalize({"type": "image", "t": 0, "file": "", "anim_id": "a1"})
    ed, ch = _editor([anim], [ev])
    monkeypatch.setattr(dialogs, "confirm", lambda clock, message: True)
    ed._delete()
    assert ch.animations == [] and ch.events[0]["anim_id"] == ""


def test_delete_can_be_cancelled(monkeypatch):
    ed, ch = _editor([_anim()])
    monkeypatch.setattr(dialogs, "confirm", lambda clock, message: False)
    ed._delete()
    assert len(ch.animations) == 1


def test_limits_are_reported_not_exceeded():
    ed, ch = _editor([_anim(str(i)) for i in range(AN.MAX_ANIMS)])
    ed._new()
    assert len(ch.animations) == AN.MAX_ANIMS
    assert ed.status == t("Анимаций уже максимум") + f": {AN.MAX_ANIMS}"


#-- Строки экрана событий

def _screen(ch):
    import events_screen as ES
    return ES, ES.EventsScreen(pygame.time.Clock(), ch, 0, 60000)


def test_image_row_cycles_through_chart_animations():
    ch = chartmod.Chart("t.ogg")
    ch.animations.extend([_anim("a1", "Один"), _anim("a2", "Два")])
    ES, scr = _screen(ch)
    scr._add("image")
    assert "anim_id" in [r[0] for r in scr._fields()] and "look" in [r[0] for r in scr._fields()]
    scr._adjust("anim_id", None, None, None, 1)
    assert scr.cur["anim_id"] == "a1"
    assert scr._value_text("anim_id") == "Один"
    scr._adjust("anim_id", None, None, None, 1)
    assert scr.cur["anim_id"] == "a2"
    scr._adjust("anim_id", None, None, None, 1)
    assert scr.cur["anim_id"] == ""


def test_look_row_cycles_through_object_effects():
    ch = chartmod.Chart("t.ogg")
    ES, scr = _screen(ch)
    scr._add("video")
    scr._adjust("look", None, None, None, 1)
    assert scr.cur["look"] == "blur"


def test_fx_event_has_kind_and_beat_rows():
    ch = chartmod.Chart("t.ogg")
    ES, scr = _screen(ch)
    scr._add("fx")
    keys = [r[0] for r in scr._fields()]
    assert keys[:4] == ["t", "amount", "attack", "dur"] and "kind" in keys and "beat" in keys
    scr._adjust("kind", None, None, None, 1)
    assert scr.cur["kind"] == "glow"
    scr._adjust("beat", None, None, None, 1)
    assert scr.cur["beat"] is True
    assert scr._value_text("beat") == t("ДА")


def test_every_button_row_fits_inside_the_screen():
    import config as C
    import events_screen as ES
    scr = ES.EventsScreen(pygame.time.Clock(), chartmod.Chart("t.ogg"), 0, 60000)
    for _, _, items in ES.SECTIONS:
        for name, _ in items:
            assert scr.btns[name].rect.right <= SS.U(C.WIDTH - 16), name
            assert scr.btns[name].rect.left >= SS.U(16), name


def test_events_screen_draws_fx_and_animation_rows(monkeypatch):
    ch = chartmod.Chart("t.ogg")
    ch.animations.append(_anim())
    ES, scr = _screen(ch)
    scr._add("fx")
    scr._draw((0, 0))
    scr._add("image")
    scr._draw((0, 0))


def test_animations_button_opens_editor(monkeypatch):
    ch = chartmod.Chart("t.ogg")
    opened = []
    import events_screen as ES
    monkeypatch.setattr(ES.anim_editor, "run", lambda clock, chart, aid="": opened.append(aid))
    ES, scr = _screen(ch)
    scr._add("image")
    scr._action("anims")
    assert opened == [""]
