"""Совместимость со старыми данными: поставляемый чарт, настройки, рекорды, победы, ранги, достижения."""
import json
import os
import shutil

import achievements
import chart as chartmod
import jsonio
import records
import settings
import songs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_shipped_chart_loads_without_loss_and_roundtrips(tmp_path):
    src = os.path.join(ROOT, "data", "charts", "default_game.json")
    raw = json.load(open(src, encoding="utf-8"))
    ch, rep = chartmod.Chart.load_checked(src)
    assert ch is not None and rep.ok
    assert not rep.lossy and rep.dropped_notes == 0 and rep.dropped_events == 0
    assert [(n["t"], n["lane"], n.get("d", 0)) for n in raw["notes"]] == [n.key()[:2] + (n.dur,) for n in ch.notes] \
        or sorted((n["t"], n["lane"], n.get("d", 0)) for n in raw["notes"]) == sorted(n.key() for n in ch.notes)
    assert len(ch.events) == len(raw["events"]) and ch.charter == "Mistervock" and ch.difficulty == 3
    # сохранение в новом формате и повторная загрузка дают то же содержимое
    out = tmp_path / "c.json"
    ch.path = str(out)
    jsonio.write_atomic(str(out), ch.to_dict())
    ch2, rep2 = chartmod.Chart.load_checked(str(out))
    assert ch2.notes_hash() == ch.notes_hash() and ch2.events == ch.events and rep2.ok
    assert json.load(open(out))["version"] == chartmod.FORMAT_VERSION


def test_old_chart_versions_open(tmp_path):
    for version in (1, 2, 3):
        p = tmp_path / f"v{version}.json"
        p.write_text(json.dumps({"version": version, "song": "a.ogg", "name": "old",
                                 "notes": [{"t": 100, "lane": 0}, {"t": 300, "lane": 2, "d": 500}]}))
        ch, rep = chartmod.Chart.load_checked(str(p))
        assert ch is not None and len(ch.notes) == 2 and ch.notes[1].dur == 500


def test_unknown_top_level_fields_are_preserved(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"version": 4, "song": "a.ogg", "name": "x", "notes": [{"t": 1, "lane": 0}],
                             "my_mod_field": {"a": 1}}))
    ch, _ = chartmod.Chart.load_checked(str(p))
    assert ch.to_dict()["my_mod_field"] == {"a": 1}


def test_shipped_settings_accepted(tmp_path, monkeypatch):
    shipped = os.path.join(ROOT, "data", "settings.json")
    copy = tmp_path / "settings.json"
    shutil.copy(shipped, copy)
    monkeypatch.setattr(settings, "PATH", str(copy))
    monkeypatch.setattr(settings, "_data", None)
    assert settings.get("scroll_ms") == 900 and settings.get("lane_keys") == ["d", "f", "j", "k"]
    assert settings.get("ghost") in (0, 1) and settings.get("autosave") in (0, 1)
    settings.set("preview", 0)
    assert json.load(open(copy))["scroll_ms"] == 900            # неизвестные/старые поля сохранены при записи
    monkeypatch.setattr(settings, "_data", None)


def test_old_records_wins_ranks_and_unlocked_files(data_root):
    d = str(data_root)
    json.dump([{"name": "A", "score": 5, "acc": 50.0, "grade": "B", "date": "2025-01-01", "song": "s", "chart": "c"}],
              open(records.PATH, "w"))
    assert records.load()[0]["score"] == 5
    json.dump(["a__1.json"], open(songs.WINS_PATH, "w"))
    assert songs._won_set() == {"a__1.json"}
    json.dump({"a__1.json": {"grade": "A", "acc": 90.0, "score": 100}}, open(songs.RANKS_PATH, "w"))
    assert songs._ranks()["a__1.json"]["grade"] == "A"
    json.dump(["Old Achievement.vcld"], open(achievements.UNLOCKED_PATH, "w"))
    assert achievements.is_unlocked("Old Achievement.vcld")
    assert achievements.unlock("gr:first_clear") is True
    assert achievements.is_unlocked("Old Achievement.vcld")        # прежний прогресс на месте
