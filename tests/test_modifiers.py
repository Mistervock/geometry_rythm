#-- Импорт
import pytest

import chart as chartmod
import ghost as GH
import modifiers as MD
import session as SESSION
import settings
import songs
import validation as V
from noteindex import NoteIndex


#-- Помощники

def base_chart(**kw):
    d = {"version": 6, "song": "a.ogg", "name": "T", "difficulty": 2,
         "notes": [{"t": 1000, "lane": 0}, {"t": 2000, "lane": 1, "d": 300}, {"t": 3000, "lane": 3}]}
    d.update(kw)
    return d


def mods(*items):
    return [{"id": i, "value": v} for i, v in items]


#-- Нормализация

def test_normalize_is_canonical_and_drops_bad_entries():
    warns = []
    raw = [{"id": "hidden", "value": True}, {"id": "bogus", "value": True},
           {"id": "speed", "value": 9}, {"id": "mirror", "value": "yes"}, "junk",
           {"id": "speed", "value": 1.25}, {"id": "speed", "value": 1.5}]
    out = MD.normalize(raw, warn=lambda code, **a: warns.append((code, a.get("id"))))
    assert out == [{"id": "speed", "value": 1.25}, {"id": "hidden", "value": True}]
    codes = [c for c, _ in warns]
    assert "modifiers.unknown" in codes and "modifiers.value" in codes
    assert "modifiers.item_type" in codes and "modifiers.duplicate" in codes


def test_normalize_disabled_flags_and_non_list():
    assert MD.normalize([{"id": "mirror", "value": False}]) == []
    assert MD.normalize("mirror") == []
    assert MD.normalize(None) == []


#-- Суффиксы ключей (рекорды и призраки)

def test_suffix_empty_without_modifiers_so_old_keys_stay():
    assert MD.suffix([]) == ""
    assert MD.suffix(None) == ""


def test_suffix_is_stable_and_distinct_per_set():
    a = MD.suffix(mods(("mirror", True), ("speed", 1.25), ("hidden", True)))
    b = MD.suffix(mods(("hidden", True), ("speed", 1.25), ("mirror", True)))
    assert a == b == "__mir-spd125-hid"
    assert MD.suffix(mods(("speed", 1.5))) != MD.suffix(mods(("speed", 0.75)))


#-- Влияние на игру

def test_scroll_scales_with_speed():
    assert MD.scroll_for(900, []) == 900
    assert MD.scroll_for(900, mods(("speed", 1.25))) == pytest.approx(720)
    assert MD.scroll_for(900, mods(("speed", 0.75))) == pytest.approx(1200)


def test_mirror_lane_flips_the_four_lanes():
    assert [MD.mirror_lane(i) for i in range(4)] == [3, 2, 1, 0]


def test_hidden_alpha_fades_in_last_third():
    scroll = 900.0
    assert MD.hidden_alpha(0, scroll) == 1.0
    assert MD.hidden_alpha(0.35 * scroll, scroll) == 1.0
    assert MD.hidden_alpha(0.70 * scroll, scroll) == 0.0
    assert MD.hidden_alpha(2000, scroll) == 0.0
    mid = MD.hidden_alpha(0.525 * scroll, scroll)
    assert 0.45 < mid < 0.55


#-- Формат v6 и миграция

def test_v5_chart_migrates_to_v6_without_modifiers():
    clean, rep = V.check_chart(base_chart(version=5))
    assert clean is not None and clean["modifiers"] == []
    assert rep.has_code("chart.migrated") and rep.ok


def test_v6_modifiers_round_trip_through_chart_file():
    data = base_chart(modifiers=[{"id": "mirror", "value": True}, {"id": "speed", "value": 1.25}])
    ch = chartmod.Chart.from_dict(data)
    assert ch.modifiers == [{"id": "mirror", "value": True}, {"id": "speed", "value": 1.25}]
    out = ch.to_dict()
    assert out["version"] == V.CHART_VERSION == 8
    assert out["modifiers"] == ch.modifiers


def test_unknown_modifier_in_chart_is_warned_not_fatal():
    clean, rep = V.check_chart(base_chart(modifiers=[{"id": "gravity", "value": True}]))
    assert clean is not None and clean["modifiers"] == []
    assert rep.has_code("modifiers.unknown") and rep.ok


def test_chart_without_modifiers_does_not_write_the_key():
    ch = chartmod.Chart.from_dict(base_chart())
    assert "modifiers" not in ch.to_dict()


#-- Выбор игрока

def test_effective_uses_author_default_then_player_choice(data_root):
    ch = chartmod.Chart.from_dict(base_chart(modifiers=[{"id": "hidden", "value": True}]))
    ch.id = "abcdef12"
    assert MD.effective(ch) == [{"id": "hidden", "value": True}]
    assert MD.save_choice(ch, mods(("mirror", True)))
    assert MD.effective(ch) == [{"id": "mirror", "value": True}]
    assert MD.effective(ch, "practice") == []


#-- Рекорды и призраки

def test_records_are_kept_per_modifier_set(data_root):
    ch = chartmod.Chart.from_dict(base_chart())
    ch.path = "/nowhere/x.chart.json"
    ch.id = "abcdef12"
    songs.record_rank(ch, "A", 90.0, 5000, [])
    assert songs.chart_best(ch) is not None
    assert songs.chart_best(ch, None, mods(("mirror", True))) is None
    songs.record_rank(ch, "S", 99.0, 9000, mods(("mirror", True)))
    best = songs.chart_best(ch, None, mods(("mirror", True)))
    assert best["grade"] == "S"
    assert songs.chart_best(ch)["grade"] == "A"


def test_ghost_keys_differ_per_modifier_set():
    ch = chartmod.Chart.from_dict(base_chart())
    ch.id = "abcdef12"
    plain = GH.keys_for(ch)
    mirrored = GH.keys_for(ch, mods(("mirror", True)))
    assert plain == ["abcdef12"]
    assert mirrored == ["abcdef12__mir"]


#-- Применение к сессии

def test_mirror_applies_to_notes_and_speed_to_scroll():
    ch = chartmod.Chart.from_dict(base_chart())
    prep = SESSION.Preparer(ch, None, None, (), mods(("mirror", True), ("speed", 1.25)))
    prep._build(prep.session)
    s = prep.session
    assert s.scroll == pytest.approx(settings.get("scroll_ms") / 1.25)
    assert [n.lane for n in s.notes] == [3, 2, 0]
    assert isinstance(s.index, NoteIndex)


def test_no_modifiers_leave_session_unchanged():
    ch = chartmod.Chart.from_dict(base_chart())
    prep = SESSION.Preparer(ch)
    prep._build(prep.session)
    assert [n.lane for n in prep.session.notes] == [0, 1, 3]
    assert prep.session.mods == []


def test_ghost_delete_removes_all_modifier_variants(tmp_path):
    ch = chartmod.Chart.from_dict(base_chart())
    ch.id = "abcdef12"
    for sfx in ("", "__mir", "__spd125-hid"):
        (tmp_path / f"abcdef12{sfx}.ghost.json").write_text("{}", encoding="utf-8")
    (tmp_path / "other.ghost.json").write_text("{}", encoding="utf-8")
    GH.delete(ch, str(tmp_path))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["other.ghost.json"]
