"""Призраки: экспорт, импорт, выбор игрока и прозрачность (Geometry Rhythm 7.0)."""
import json
import os
import shutil

import pygame
import pytest

import chart as chartmod
import ghost as GH
import modifiers as MD
import settings


#-- Помощники

def _chart(notes=None, cid="abcdef12"):
    data = {"version": 6, "song": "a.ogg", "name": "Тест", "difficulty": 2,
            "notes": notes or [{"t": 1000, "lane": 0}, {"t": 2000, "lane": 1}, {"t": 3000, "lane": 3}]}
    ch = chartmod.Chart.from_dict(data)
    ch.id = cid
    ch.path = "/nowhere/x.chart.json"
    return ch


def _outcome(mods=(), score=4321, acc=97.5):
    return {
        "stats": {"total": 3, "judged": 3},
        "judgments": [(0, 0, 0, "perfect", 0, 1000.0), (1, 1, 0, "great", 0, 2000.0), (2, 3, 0, "good", 0, 3000.0)],
        "score": score, "acc": acc, "grade": "A", "max_combo": 3,
        "counts": {"perfect": 1, "great": 1, "good": 1, "miss": 0},
        "timeline": [(1000.0, 300, 1), (2000.0, 3000, 2), (3000.0, score, 3)],
        "mods": list(mods), "practice": False, "failed": False,
    }


def _save_own(ch, mods=()):
    assert GH.maybe_save(ch, _outcome(mods)) == "saved"


#-- Свой призрак

def test_own_ghost_is_saved_and_loads_back(data_root):
    ch = _chart()
    _save_own(ch)
    g, status = GH.load(ch)
    assert status == GH.OK and g.score == 4321


def test_export_copies_own_ghost_into_export_folder(data_root, tmp_path):
    ch = _chart()
    _save_own(ch)
    out = tmp_path / "exp"
    path = GH.export_own(ch, out_dir=str(out))
    assert path and os.path.basename(path) == "abcdef12.ghost.json"
    with open(path, encoding="utf-8") as f:
        exported = json.load(f)
    assert exported["chart_name"] == "Тест" and exported["score"] == 4321


def test_export_without_own_ghost_returns_none(data_root, tmp_path):
    assert GH.export_own(_chart(), out_dir=str(tmp_path)) is None


#-- Импорт

def _import_copy(src, name="friend.ghost.json"):
    os.makedirs(GH.IMPORT_DIR, exist_ok=True)
    dest = os.path.join(GH.IMPORT_DIR, name)
    shutil.copyfile(src, dest)
    return name


def test_imported_ghost_is_listed_and_can_be_chosen(data_root, tmp_path):
    ch = _chart()
    _save_own(ch)
    exported = GH.export_own(ch, out_dir=str(tmp_path))
    name = _import_copy(exported)
    found = GH.inspect_imports(ch)
    assert [(n, s) for n, s, _ in found] == [(name, GH.OK)]
    assert GH.save_choice(ch, GH.IMPORT_PREFIX + name)
    g, status = GH.for_play(ch)
    assert status == GH.OK and g is not None and g.score == 4321


def test_imported_ghost_for_other_notes_is_not_used(data_root, tmp_path):
    ch = _chart()
    _save_own(ch)
    name = _import_copy(GH.export_own(ch, out_dir=str(tmp_path)))
    other = _chart(notes=[{"t": 500, "lane": 2}], cid="other001")
    assert [s for _, s, _ in GH.inspect_imports(other)] == [GH.STALE]
    GH.save_choice(other, GH.IMPORT_PREFIX + name)
    assert GH.for_play(other) == (None, GH.STALE)


def test_imported_ghost_with_other_modifiers_is_not_used(data_root, tmp_path):
    ch = _chart()
    _save_own(ch, mods=[{"id": "mirror", "value": True}])
    name = _import_copy(GH.export_own(ch, mods=[{"id": "mirror", "value": True}], out_dir=str(tmp_path)))
    assert [s for _, s, _ in GH.inspect_imports(ch)] == [GH.OTHER_MODS]
    assert [s for _, s, _ in GH.inspect_imports(ch, [{"id": "mirror", "value": True}])] == [GH.OK]


def test_corrupt_import_is_reported_and_left_in_place(data_root):
    ch = _chart()
    os.makedirs(GH.IMPORT_DIR, exist_ok=True)
    bad = os.path.join(GH.IMPORT_DIR, "broken.ghost.json")
    with open(bad, "w", encoding="utf-8") as f:
        f.write("{ не json")
    assert [s for _, s, _ in GH.inspect_imports(ch)] == [GH.CORRUPT]
    assert os.path.exists(bad)


def test_import_names_ignore_other_files_and_path_tricks(data_root):
    os.makedirs(GH.IMPORT_DIR, exist_ok=True)
    for name in ("ok.ghost.json", "notes.txt", "x.json"):
        with open(os.path.join(GH.IMPORT_DIR, name), "w", encoding="utf-8") as f:
            f.write("{}")
    assert GH.import_names() == ["ok.ghost.json"]
    ch = _chart()
    GH.save_choice(ch, GH.IMPORT_PREFIX + "../secret.ghost.json")
    assert GH.for_play(ch) == (None, GH.NONE)


#-- Выбор игрока

def test_default_choice_is_own_ghost(data_root):
    ch = _chart()
    assert GH.choice_of(ch) == GH.CHOICE_OWN
    _save_own(ch)
    g, status = GH.for_play(ch)
    assert status == GH.OK and g is not None


def test_choice_none_hides_ghost_even_when_own_exists(data_root):
    ch = _chart()
    _save_own(ch)
    GH.save_choice(ch, GH.CHOICE_NONE)
    assert GH.for_play(ch) == (None, GH.NONE)


def test_choice_is_stored_per_chart(data_root):
    a, b = _chart(cid="aaaaaaa1"), _chart(cid="bbbbbbb2")
    GH.save_choice(a, GH.CHOICE_NONE)
    assert GH.choice_of(a) == GH.CHOICE_NONE
    assert GH.choice_of(b) == GH.CHOICE_OWN


def test_ghost_ui_marks_unverified_and_unfit_rows(data_root, tmp_path):
    import ghost_ui
    ch = _chart()
    _save_own(ch)
    name = _import_copy(GH.export_own(ch, out_dir=str(tmp_path)), "good.ghost.json")
    bad_src = os.path.join(GH.IMPORT_DIR, name)
    other = _chart(notes=[{"t": 500, "lane": 2}], cid="other002")
    rows = ghost_ui._entries(ch, [])
    imported = [r for r in rows if r["value"] == GH.IMPORT_PREFIX + name]
    assert len(imported) == 1 and imported[0]["ok"] and imported[0]["tag"]
    unfit = [r for r in ghost_ui._entries(other, []) if r["value"] == GH.IMPORT_PREFIX + name]
    assert len(unfit) == 1 and unfit[0]["ok"] is False
    assert os.path.exists(bad_src)


#-- Прозрачность

def test_ghost_alpha_is_limited_to_20_100():
    old = settings.get("ghost_alpha")
    try:
        settings.set("ghost_alpha", 5)
        assert settings.get("ghost_alpha") == 20
        settings.set("ghost_alpha", 400)
        assert settings.get("ghost_alpha") == 100
        settings.set("ghost_alpha", 60)
        assert settings.get("ghost_alpha") == 60
    finally:
        settings.set("ghost_alpha", old)


def test_ghost_alpha_default_keeps_old_look():
    assert settings.DEFAULTS["ghost_alpha"] == 100
