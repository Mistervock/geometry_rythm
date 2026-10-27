import json
import os

import pytest

import chart as chartmod
import jsonio
import songs
import validation as V


def sample(**kw):
    d = {"version": 4, "song": "a.ogg", "name": "T", "difficulty": 2,
         "notes": [{"t": 100, "lane": 0}, {"t": 500, "lane": 1, "d": 300}]}
    d.update(kw)
    return d


#-- jsonio

def test_read_valid_and_missing(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    assert jsonio.read(str(p)).data == {"x": 1}
    assert jsonio.read(str(tmp_path / "none.json")).kind == jsonio.MISSING


@pytest.mark.parametrize("text", ["{bad", "", "   ", "[1,", "NaN", '{"a": Infinity}'])
def test_corrupt_json_does_not_raise_and_is_quarantined(tmp_path, text):
    p = tmp_path / "bad.json"
    p.write_text(text, encoding="utf-8")
    assert jsonio.load(str(p), {"d": 1}) == {"d": 1}
    assert not p.exists()                                   # перенесён в карантин, а не затёрт
    kept = [n for n in os.listdir(tmp_path) if ".corrupt-" in n]
    assert len(kept) == 1
    assert (tmp_path / kept[0]).read_text(encoding="utf-8") == text


def test_wrong_root_type_quarantined(tmp_path):
    p = tmp_path / "l.json"
    p.write_text("[1, 2]", encoding="utf-8")
    assert jsonio.load(str(p), {}, expect=dict) == {}
    assert any(".corrupt-" in n for n in os.listdir(tmp_path))


def test_write_atomic_keeps_old_file_on_failure(tmp_path, monkeypatch):
    p = tmp_path / "keep.json"
    jsonio.write_atomic(str(p), {"v": 1})

    def boom(src, dst):
        raise PermissionError("locked")
    monkeypatch.setattr(os, "replace", boom)
    monkeypatch.setattr("time.sleep", lambda s: None)
    with pytest.raises(jsonio.SaveError):
        jsonio.write_atomic(str(p), {"v": 2})
    monkeypatch.undo()
    assert json.loads(p.read_text(encoding="utf-8")) == {"v": 1}
    assert not [n for n in os.listdir(tmp_path) if n.endswith(".tmp")]


def test_write_rejects_nan(tmp_path):
    with pytest.raises(jsonio.SaveError):
        jsonio.write_atomic(str(tmp_path / "n.json"), {"x": float("nan")})
    assert not (tmp_path / "n.json").exists()


def test_backup_rotation(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("1", encoding="utf-8")
    for i in range(8):
        jsonio.backup_file(str(p), str(tmp_path / "bk"), keep=3, tag=f"-{i}")
    assert len(os.listdir(tmp_path / "bk")) == 3


def test_unwritable_directory_reports_error(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    ok, err = jsonio.try_write(str(blocker / "sub" / "x.json"), {})
    assert not ok and err


#-- validation

def test_valid_chart_loads_clean():
    c, rep = V.check_chart(sample(version=5, id="abcdef123456"))
    assert rep.ok and rep.clean and c["notes"] == [(100, 0, 0), (500, 1, 300)]


def test_old_version_migrates_with_info():
    c, rep = V.check_chart(sample(version=2))
    assert c["version"] == V.CHART_VERSION and rep.has_code("chart.migrated") and rep.ok


def test_newer_version_is_critical():
    c, rep = V.check_chart(sample(version=99))
    assert c is None and rep.has_code("chart.version_new")


@pytest.mark.parametrize("data,code", [
    ([], "chart.not_object"),
    ({"version": 5}, "chart.no_song"),
    ({"version": 5, "song": "a.ogg"}, "chart.no_notes"),
    ({"version": 5, "song": "a.ogg", "notes": {}}, "chart.notes_type"),
    ({"version": "x", "song": "a.ogg", "notes": []}, "chart.version_bad"),
])
def test_critical_errors(data, code):
    c, rep = V.check_chart(data)
    assert c is None and rep.has_code(code) and not rep.ok


def test_bad_notes_are_skipped_and_reported_with_index():
    notes = [{"t": 100, "lane": 0}, {"t": "x", "lane": 1}, {"t": -5, "lane": 1}, {"t": 5, "lane": 9},
             {"t": float("inf"), "lane": 0}, {"t": True, "lane": 0}, {"lane": 2}, 7, {"t": 10, "lane": 3.5}]
    c, rep = V.check_chart(sample(notes=notes))
    assert c["notes"] == [(100, 0, 0)]
    assert rep.lossy and rep.dropped_notes == 8
    assert any(i.where == "notes[1]" for i in rep.warnings)
    assert rep.ok


def test_fixes_are_in_memory_and_listed():
    notes = [{"t": 300.4, "lane": 1, "d": -5}, {"t": 100, "lane": 0}]
    c, rep = V.check_chart(sample(notes=notes, difficulty=99, name="x" * 50))
    assert c["notes"] == [(100, 0, 0), (300, 1, 0)]
    assert c["difficulty"] == 5 and len(c["name"]) == V.NAME_MAX
    for code in ("chart.notes_sorted", "note.dur_negative", "note.rounded", "chart.field_range", "chart.field_trim"):
        assert rep.has_code(code), code


def test_hold_limits():
    c, rep = V.check_chart(sample(notes=[{"t": 0, "lane": 0, "d": 10**9}]))
    assert c["notes"][0][2] == V.MAX_HOLD and rep.has_code("note.dur_big")


def test_duplicates_and_overlaps_warn_but_load():
    notes = [{"t": 100, "lane": 0}, {"t": 100, "lane": 0}, {"t": 1000, "lane": 1, "d": 500}, {"t": 1200, "lane": 1}]
    c, rep = V.check_chart(sample(notes=notes))
    assert len(c["notes"]) == 4 and rep.has_code("note.duplicate") and rep.has_code("note.in_hold")


def test_notes_after_end_warn():
    c, rep = V.check_chart(sample(), duration_ms=300)
    assert rep.has_code("note.after_end")


def test_unknown_event_and_missing_resource():
    ev = [{"type": "nope", "t": 1}, {"type": "image", "t": 10, "file": "zz.png"}, "str",
          {"type": "flash", "t": 5, "attack": "x", "dur": 10 ** 6}]
    c, rep = V.check_chart(sample(events=ev), image_exists=lambda n: False)
    assert [e["type"] for e in c["events"]] == ["flash", "image"]
    assert rep.has_code("event.resource_missing") and rep.has_code("event.unknown_type")
    flash = c["events"][0]
    assert flash["dur"] == 3000 and flash["attack"] == 40


def test_infinite_event_value_does_not_crash():
    c, rep = V.check_chart(sample(events=[{"type": "glitch", "t": 1e999, "dur": 1e999}]))
    assert c is not None and c["events"][0]["t"] <= 3600000


def test_extra_keys_preserved_roundtrip(data_root):
    d = sample(version=5, mod_data={"a": 1})
    ch = chartmod.Chart.from_dict(d)
    assert ch.to_dict()["mod_data"] == {"a": 1}


def test_grid_validation():
    c, rep = V.check_chart(sample(grid={"bpm": 9999, "div": 3, "offset": "x", "snap": 0}))
    assert c["grid"]["bpm"] == 400.0 and c["grid"]["snap"] is False and c["grid"]["div"] == 3
    assert rep.has_code("grid.range") and rep.has_code("grid.type")


def test_settings_validation_clamps_and_keeps_defaults():
    defaults = {"a": 5, "b": 1}
    out, rep = V.check_settings({"a": 9999, "b": "x", "zzz": 1}, defaults, {"a": (0, 10, 1), "b": (0, 3, 1)})
    assert out == {"a": 10, "b": 1} and rep.has_code("settings.range") and rep.has_code("settings.type")


def test_records_validation():
    raw = [{"name": "a", "score": 5}, {"name": "b", "score": "x"}, 3, {"name": "c", "score": 10, "acc": float("nan")}]
    out, rep = V.check_records(raw)
    assert [e["name"] for e in out] == ["c", "a"] and out[0]["acc"] == 0.0 and rep.has_code("records.entry")


#-- chart + songs

def test_chart_roundtrip_v5(data_root):
    ch = chartmod.Chart.from_dict(sample())
    ch.song = "a.ogg"
    path = songs.save_chart(ch)
    again, rep = songs.load_chart_file(path)
    assert again.id == ch.id and again.id and again.key == os.path.basename(path)
    assert [n.key() for n in again.notes] == [n.key() for n in ch.notes]
    assert json.load(open(path, encoding="utf-8"))["version"] == 5


def test_save_keeps_backup_of_previous_version(data_root):
    ch = chartmod.Chart.from_dict(sample())
    path = songs.save_chart(ch)
    ch.notes.append(chartmod.Note(900, 2))
    songs.save_chart(ch)
    stem = os.path.splitext(os.path.basename(path))[0]
    backups = os.listdir(os.path.join(songs.BACKUP_DIR, stem))
    assert len(backups) == 1
    old = json.load(open(os.path.join(songs.BACKUP_DIR, stem, backups[0]), encoding="utf-8"))
    assert len(old["notes"]) == 2


def test_corrupt_chart_file_is_listed_as_error_not_crash(data_root):
    p = os.path.join(songs.CHART_DIR, "broken.json")
    open(p, "w", encoding="utf-8").write("{oops")
    ch, rep = songs.load_chart_file(p)
    assert ch is None and rep.has_code("json.syntax")
    assert songs.charts_for("a.ogg") == []
    assert os.path.exists(p)                                   # исходный файл не тронут и не удалён


def test_chart_cache_invalidates_on_change(data_root):
    ch = chartmod.Chart.from_dict(sample())
    path = songs.save_chart(ch)
    assert len(songs.charts_for("a.ogg")[0].notes) == 2
    ch.notes.append(chartmod.Note(900, 2))
    songs.save_chart(ch)
    assert len(songs.charts_for("a.ogg")[0].notes) == 3


def test_import_failures_have_reasons(data_root, tmp_path):
    os.makedirs(songs.EXPORT_DIR, exist_ok=True)
    open(os.path.join(songs.EXPORT_DIR, "bad.json"), "w").write("{")
    with pytest.raises(songs.ImportFailure) as e:
        songs.import_chart("bad.json")
    assert e.value.reason == "bad_file"


def test_ranks_roundtrip_and_corrupt_ranks_file(data_root):
    ch = chartmod.Chart.from_dict(sample())
    songs.save_chart(ch)
    assert songs.record_rank(ch, "A", 90.0, 1000)[0]
    assert songs.chart_best(ch)["grade"] == "A"
    open(songs.RANKS_PATH, "w").write("{broken")
    songs._json_cache.clear()
    assert songs.chart_best(ch) is None                        # не падаем
    assert any(".corrupt-" in n for n in os.listdir(os.path.dirname(songs.RANKS_PATH)))
