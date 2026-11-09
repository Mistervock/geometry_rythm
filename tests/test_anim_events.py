"""Анимации и эффекты в чарте: проверка файла, события, отрисовка с анимацией и история правок."""
import pygame
import pytest

import anim as AN
import chart as chartmod
import config as C
import events as EV
import history as H
import validation as V


#-- Помощники

@pytest.fixture
def img_dir(tmp_path, monkeypatch):
    s = pygame.Surface((40, 20))
    s.fill((200, 30, 30))
    pygame.image.save(s, str(tmp_path / "red.png"))
    monkeypatch.setattr(EV, "IMAGE_DIR", str(tmp_path))
    EV._src.clear()
    EV._scaled.clear()
    return tmp_path


def _data(**kw):
    base = {"version": V.CHART_VERSION, "song": "a.ogg", "name": "Т", "difficulty": 1,
            "notes": [{"t": 1000, "lane": 0}]}
    base.update(kw)
    return base


def _key(t, **kw):
    k = {"t": t, "ease": "linear", "x": 0, "y": 0, "scale": 100, "rot": 0, "alpha": 100, "tint": [255, 255, 255]}
    k.update(kw)
    return k


def _anim(aid="a1", **kw):
    a = {"id": aid, "name": "Рывок", "dur": 1000, "loop": False, "keys": [_key(0), _key(1000, x=100)]}
    a.update(kw)
    return a


def _img(**kw):
    ev = {"type": "image", "t": 0, "file": "red.png", "dur": 1000, "w": 200, "x": 10, "y": 0, "fade": 100,
          "anim": "fade", "full": False, "dx": 0, "dy": 0, "look_amt": 60}
    ev.update(kw)
    return ev


def _fx(**kw):
    ev = {"type": "fx", "t": 0, "kind": "wave", "amount": 50, "attack": 0, "dur": 500, "beat": False}
    ev.update(kw)
    return ev


#-- Формат чарта

def test_chart_format_is_version_eight():
    assert V.CHART_VERSION == 8


def test_version_six_chart_loads_and_gets_empty_animations():
    clean, rep = V.check_chart(_data(version=6))
    assert clean["version"] == 8 and clean["animations"] == []
    assert rep.has_code("chart.migrated") and rep.ok


def test_newer_version_is_refused_by_this_build():
    clean, rep = V.check_chart(_data(version=9))
    assert clean is None and rep.has_code("chart.version_new")


def test_bad_animation_entries_are_dropped_with_warning():
    clean, rep = V.check_chart(_data(animations=[_anim(), "мусор"]))
    assert [a["id"] for a in clean["animations"]] == ["a1"]
    assert rep.has_code("anim.item_type")


def test_event_keeps_link_to_existing_animation():
    clean, rep = V.check_chart(_data(animations=[_anim()], events=[_img(anim_id="a1")]))
    assert clean["events"][0]["anim_id"] == "a1"


def test_event_with_missing_animation_loses_the_link_with_warning():
    clean, rep = V.check_chart(_data(animations=[_anim()], events=[_img(anim_id="zz")]))
    assert clean["events"][0]["anim_id"] == ""
    assert rep.has_code("event.anim_missing")


def test_unknown_fx_kind_is_fixed_to_blur():
    clean, rep = V.check_chart(_data(events=[_fx(kind="bogus")]))
    assert clean["events"][0]["kind"] == "blur"
    assert rep.has_code("event.enum") and rep.ok


def test_unknown_look_is_cleared_with_warning():
    clean, rep = V.check_chart(_data(events=[_img(look="bogus")]))
    assert clean["events"][0]["look"] == ""
    assert rep.has_code("event.enum")


def test_animations_and_fx_survive_a_round_trip():
    ch = chartmod.Chart.from_dict(_data(animations=[_anim()], events=[_img(anim_id="a1"), _fx(beat=True)]))
    again = chartmod.Chart.from_dict(ch.to_dict())
    assert again.animations == ch.animations
    kinds = [(e["type"], e.get("kind")) for e in again.events]
    assert ("fx", "wave") in kinds
    fx_ev = next(e for e in again.events if e["type"] == "fx")
    assert fx_ev["beat"] is True


def test_chart_without_animations_writes_no_animations_key():
    ch = chartmod.Chart.from_dict(_data())
    assert "animations" not in ch.to_dict()


#-- Значения событий

def test_fx_defaults_and_normalization():
    ev = EV.normalize({"type": "fx"})
    assert ev["kind"] == "blur" and ev["beat"] is False
    assert ev["amount"] == 60 and ev["attack"] == 300 and ev["dur"] == 2000


def test_fx_keeps_valid_fields():
    ev = EV.normalize(_fx(kind="mono", beat=True))
    assert ev["kind"] == "mono" and ev["beat"] is True


def test_image_look_and_anim_id_are_normalized():
    ev = EV.normalize(_img(look="mono", anim_id="x" * 40))
    assert ev["look"] == "mono" and len(ev["anim_id"]) == 16
    assert EV.normalize(_img(look="bogus"))["look"] == ""


def test_fx_is_a_known_event_type_with_name_and_colour():
    assert "fx" in EV.TYPES and "fx" in EV.TYPE_NAMES and "fx" in EV.TYPE_COLORS and "fx" in EV.DESCRIPTIONS


#-- Положение картинки с анимацией

def test_pose_uses_animation_keys_and_adds_event_offset():
    ev = EV.normalize(_img(x=10, anim_id="a1"))
    alpha, ox, oy, scale, rot, tint = EV.media_pose(ev, 500, {"a1": _anim()})
    assert alpha == 1.0 and ox == pytest.approx(60) and oy == 0
    assert scale == 100 and rot == 0 and tint == (255, 255, 255)


def test_pose_without_animation_uses_presets():
    ev = EV.normalize(_img(x=10, anim="drift", dx=40))
    pose = EV.media_pose(ev, 500, {})
    assert pose[:3] == EV.image_state(ev, 500)
    assert pose[3:] == (100, 0, EV.TINT_NONE)


def test_unknown_animation_id_falls_back_to_presets():
    ev = EV.normalize(_img(anim_id="nope"))
    assert EV.media_pose(ev, 500, {"a1": _anim()})[:3] == EV.image_state(ev, 500)


def test_pose_is_invisible_after_the_event_ends():
    ev = EV.normalize(_img(anim_id="a1"))
    assert EV.media_pose(ev, 1000, {"a1": _anim()})[0] == 0.0


def test_full_screen_picture_ignores_event_offsets():
    ev = EV.normalize(_img(x=300, full=True, anim_id="a1"))
    assert EV.media_pose(ev, 500, {"a1": _anim()})[1] == pytest.approx(50)


def test_pose_takes_scale_rotation_alpha_and_tint_from_keys():
    anim = _anim(keys=[_key(0, scale=50, rot=90, alpha=40, tint=[255, 0, 0]),
                       _key(1000, scale=50, rot=90, alpha=40, tint=[255, 0, 0])])
    ev = EV.normalize(_img(anim_id="a1"))
    alpha, ox, oy, scale, rot, tint = EV.media_pose(ev, 300, {"a1": anim})
    assert alpha == pytest.approx(0.4) and scale == 50 and rot == 90 and tint == (255, 0, 0)


def test_draw_media_applies_tint_from_animation(img_dir):
    ev = EV.normalize(_img(w=80, x=0, anim_id="a1"))
    anim = _anim(keys=[_key(0, tint=[255, 0, 0]), _key(1000, tint=[255, 0, 0])])
    surf = pygame.Surface((C.WIDTH, C.HEIGHT))
    surf.fill((0, 0, 0))
    EV.draw_media(surf, ev, 300, {"a1": anim})
    r, g, b, *_ = surf.get_at((C.WIDTH // 2, C.HEIGHT // 2))
    assert r > 0 and g == 0 and b == 0


def test_draw_media_rotates_the_picture(img_dir):
    ev = EV.normalize(_img(w=80, x=0, y=0, anim_id="a1"))
    anim = _anim(keys=[_key(0, rot=90), _key(1000, rot=90)])
    surf = pygame.Surface((C.WIDTH, C.HEIGHT))
    surf.fill((0, 0, 0))
    EV.draw_media(surf, ev, 300, {"a1": anim})
    below = surf.get_at((C.WIDTH // 2, C.HEIGHT // 2 + 30))
    assert sum(below[:3]) > 0


def test_draw_images_passes_animations_through(img_dir):
    ev = EV.normalize(_img(w=80, x=0, anim_id="a1"))
    anim = _anim(keys=[_key(0, alpha=0), _key(1000, alpha=0)])
    surf = pygame.Surface((C.WIDTH, C.HEIGHT))
    surf.fill((0, 0, 0))
    EV.draw_images(surf, [(ev, 300)], {"a1": anim})
    assert sum(surf.get_at((C.WIDTH // 2, C.HEIGHT // 2))[:3]) == 0


#-- История правок

def test_setevents_snapshot_covers_animations():
    ch = chartmod.Chart("t.ogg", animations=[_anim()])
    before = H.SetEvents.snapshot(ch)
    ch.animations.append(_anim("a2"))
    after = H.SetEvents.snapshot(ch)
    cmd = H.SetEvents(before, after)
    assert cmd.effective()
    cmd.undo(ch)
    assert [a["id"] for a in ch.animations] == ["a1"]
    cmd.do(ch)
    assert [a["id"] for a in ch.animations] == ["a1", "a2"]


def test_old_two_item_snapshot_leaves_animations_alone():
    ch = chartmod.Chart("t.ogg", animations=[_anim()])
    before = ([], [])
    after = ([EV.normalize(_fx())], [])
    cmd = H.SetEvents(before, after)
    cmd.do(ch)
    assert len(ch.events) == 1 and [a["id"] for a in ch.animations] == ["a1"]
    cmd.undo(ch)
    assert ch.events == []
