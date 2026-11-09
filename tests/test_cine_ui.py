"""Экран событий и браузер пакетов: поля камеры, перехода и пакета, кнопки, предпросмотр, список пакетов."""
import json

import pygame
import pytest

import anim as AN
import config as C
import cine as CN
import events as EV
import events_screen as ES
import pack_browser as PB
import packs as PK
import screen_setting as SS
import songs
from i18n import t


@pytest.fixture(autouse=True)
def _restore_library():
    yield
    PK.reload()


@pytest.fixture
def lib(tmp_path):
    builtin = tmp_path / "builtin"
    user = tmp_path / "user"
    builtin.mkdir()
    user.mkdir()
    return builtin, user


def _pack_json(pid="spark_test"):
    return {"format": PK.FORMAT, "api": PK.API, "id": pid, "name": "Тест", "dur": 600,
            "params": [{"id": "size", "name": "Размер", "min": 10, "max": 100, "step": 5, "default": 50}],
            "layers": [{"kind": "ring", "start": 0, "end": 1, "radius": [0, "$size"], "width": 4,
                        "alpha": [255, 0]}]}


def _screen(events=()):
    ch = songs.new_chart("t.wav", "T")
    ch.events.extend(events)
    return ES.EventsScreen(pygame.time.Clock(), ch, 1000, 20000)


def _key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0))


#-- Кнопки добавления

def test_add_row_holds_twelve_types_without_overlap(data_root):
    scr = _screen()
    names = [n for n, _ in ES.SECTIONS[0][2]]
    assert len(names) == 12 and {"camera", "transition", "pack"} <= set(names)
    rects = [scr.btns[n].rect for n in names]
    for a, b in zip(rects, rects[1:]):
        assert a.right <= b.left, "кнопки ряда ДОБАВИТЬ перекрываются"
    assert rects[-1].right <= SS.U(C.WIDTH - 16)


def test_add_buttons_create_the_new_events(data_root):
    scr = _screen()
    scr._action("camera")
    assert scr.cur["type"] == "camera" and scr.cur["ease"] == AN.DEFAULT_EASE
    scr._action("transition")
    assert scr.cur["type"] == "transition" and scr.cur["mode"] == "out" and scr.cur["skip"] is True
    scr._action("pack")
    assert scr.cur["type"] == "pack" and scr.cur["pack"] == sorted(PK.known_ids())[0]


#-- Поля камеры и перехода

def test_camera_fields_and_values(data_root):
    scr = _screen([EV.make("camera", 1000)])
    keys = [r[0] for r in scr._fields()]
    assert {"t", "dur", "zoom", "x", "y", "ease"} <= set(keys)
    ease_before = scr.cur["ease"]
    scr._adjust("ease", None, None, None, 1)
    assert scr.cur["ease"] == AN.EASES[(AN.EASES.index(ease_before) + 1) % len(AN.EASES)]
    row = next(r for r in scr._fields() if r[0] == "zoom")
    scr._adjust(row[0], row[2], row[3], row[4], 1)
    assert scr.cur["zoom"] == 105
    assert scr._value_text("ease") == t(AN.EASE_NAMES[scr.cur["ease"]])


def test_transition_fields_cycle_kind_mode_and_skip(data_root):
    scr = _screen([EV.make("transition", 1000)])
    keys = [r[0] for r in scr._fields()]
    assert {"dur", "colour", "kind", "mode", "ease", "skip"} <= set(keys)
    scr._adjust("mode", None, None, None, 1)
    assert scr.cur["mode"] == "in"
    scr._adjust("kind", None, None, None, 1)
    assert scr.cur["kind"] == "iris"
    assert scr._value_text("kind") == t(CN.KIND_NAMES["iris"])
    scr._adjust("skip", None, None, None, 1)
    assert scr.cur["skip"] is False and scr._value_text("skip") == t("НЕТ")


def test_colour_of_transition_is_shown_by_name(data_root):
    scr = _screen([EV.make("transition", 1000)])
    scr.cur["colour"] = 2
    assert scr._value_text("colour") == t(CN.COLOUR_NAMES[2])


#-- Поля пакета

def test_pack_field_cycles_the_library_and_resets_parameters(data_root, lib):
    builtin, user = lib
    (user / "spark_test.json").write_text(json.dumps(_pack_json()), encoding="utf-8")
    PK.reload(builtin=builtin, user=user)
    scr = _screen()
    scr._action("pack")
    assert scr.cur["pack"] == "spark_test"
    keys = [r[0] for r in scr._fields()]
    assert "pack" in keys and "p:size" in keys
    assert scr._value_text("p:size") == "50"
    scr._adjust("p:size", 10, 100, 5, 1)
    assert scr.cur["params"]["size"] == 55.0 and scr._value_text("p:size") == "55"
    scr._adjust("pack", None, None, None, 1)
    assert scr.cur["pack"] == "" and scr.cur["params"] == {}


def test_typed_parameter_value_is_clamped_and_rounded(data_root, lib):
    builtin, user = lib
    (user / "spark_test.json").write_text(json.dumps(_pack_json()), encoding="utf-8")
    PK.reload(builtin=builtin, user=user)
    scr = _screen()
    scr._action("pack")
    scr._set_value("p:size", 33.7, 10, 100)
    assert scr.cur["params"]["size"] == 33.7 and scr._value_text("p:size") == "33.7"
    scr._set_value("p:size", 999, 10, 100)
    assert scr.cur["params"]["size"] == 100


def test_pack_hint_depends_on_the_event_type():
    assert ES._hint_text({"type": "pack"}, "x") == ES.HINTS["pack.x"]
    assert ES._hint_text({"type": "camera"}, "x") == ES.HINTS["camera.x"]
    assert ES._hint_text({"type": "fx"}, "x") == ES.HINTS["x"]


def test_previews_of_the_three_new_types_draw(data_root, lib):
    builtin, user = lib
    (user / "spark_test.json").write_text(json.dumps(_pack_json()), encoding="utf-8")
    PK.reload(builtin=builtin, user=user)
    scr = _screen()
    surface = pygame.display.get_surface()
    samples = [EV.make("camera", 0), EV.make("transition", 0), dict(EV.make("pack", 0), pack="spark_test")]
    for ev in samples:
        scr._draw_cine_sample(surface, ev, 200)


#-- Список пакетов

def _select_then(*keys):
    for k in keys:
        _key(k)


def test_browser_enter_returns_the_current_pack(data_root):
    PK.reload()
    _key(pygame.K_RETURN)
    assert PB.run(pygame.time.Clock(), "sparks") == "sparks"


def test_browser_down_then_enter_moves_selection(data_root):
    PK.reload()
    ids = sorted(PK.known_ids(), key=lambda pid: (PK.get(pid).get("name", pid), pid))
    start = ids.index("burst")
    _select_then(pygame.K_DOWN, pygame.K_RETURN)
    assert PB.run(pygame.time.Clock(), "burst") == ids[(start + 1) % len(ids)]


def test_browser_escape_cancels(data_root):
    PK.reload()
    _key(pygame.K_ESCAPE)
    assert PB.run(pygame.time.Clock(), "burst") is None


def test_browser_lists_broken_files_with_their_reasons(data_root, lib):
    builtin, user = lib
    (user / "bad.json").write_text("{не json", encoding="utf-8")
    PK.reload(builtin=builtin, user=user)
    lines = PB._issue_lines()
    assert lines and any("bad.json" in line for line in lines)
    _key(pygame.K_ESCAPE)
    assert PB.run(pygame.time.Clock(), "") is None
