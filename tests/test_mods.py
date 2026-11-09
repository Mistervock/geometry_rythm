"""Моды: проверка манифеста, изоляция ошибок, палитра, перевод, песни/чарты/картинки из модов."""
import json
import os
import wave

import pytest

import chart as chartmod
import config as C
import i18n
import modsys
import songs
import events as EV


@pytest.fixture
def mods_env(tmp_path, monkeypatch):
    md = tmp_path / "mods"
    md.mkdir()
    monkeypatch.setattr(modsys, "MODS_DIR", str(md))
    monkeypatch.setattr(modsys, "LOG_PATH", str(tmp_path / "mods.log"))
    monkeypatch.setattr(modsys, "LOADED", [])
    saved_en = dict(i18n.EN)
    saved = {k: getattr(C, k) for k in modsys.PALETTE_KEYS}
    yield md
    i18n.EN.clear()
    i18n.EN.update(saved_en)
    for k, v in saved.items():
        setattr(C, k, v)


def _mod(md, folder, manifest):
    d = md / folder
    d.mkdir(exist_ok=True)
    (d / "mod.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return d


def _base(ident="my_mod", **extra):
    m = {"format": modsys.FORMAT, "api": modsys.API, "id": ident, "name": "Мод"}
    m.update(extra)
    return m


def _wav(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\0\0" * 800)


def test_valid_mod_applies_palette_and_translation(mods_env):
    _mod(mods_env, "a", _base(palette={"CYAN": [1, 2, 3], "LANE_COLORS": [[1, 1, 1]] * 4},
                              translations={"en": {"ИГРАТЬ": "PLAY NOW"}}))
    mods = modsys.load()
    assert mods[0].active and not mods[0].errors
    assert C.CYAN == (1, 2, 3)
    assert C.LANE_COLORS[0] == (1, 1, 1)
    assert i18n.EN["ИГРАТЬ"] == "PLAY NOW"


def test_broken_json_is_isolated_and_reported(mods_env):
    d = mods_env / "bad"
    d.mkdir()
    (d / "mod.json").write_text("{ не json", encoding="utf-8")
    _mod(mods_env, "good", _base("good_mod", palette={"GOLD": [9, 9, 9]}))
    mods = modsys.load()
    byid = {m.id: m for m in mods}
    assert byid["bad"].errors and not byid["bad"].active
    assert byid["good_mod"].active
    assert C.GOLD == (9, 9, 9)
    assert "[ОШИБКА]" in "\n".join(modsys.report_lines())


@pytest.mark.parametrize("manifest,needle", [
    ({"format": "other", "api": 1, "id": "x1"}, "формат"),
    ({"format": modsys.FORMAT, "api": 2, "id": "x1"}, "api"),
    (_base("NO WAY"), "id"),
    (_base(palette={"CYAN": [256, 0, 0]}), "цвет"),
    (_base(palette={"CYAN": [1, 2]}), "цвет"),
    (_base(palette={"CYAN": [True, 0, 0]}), "цвет"),
    (_base(songs="../outside"), "выходит"),
    (_base(songs="/abs/path"), "выходит"),
    (_base(enabled="yes"), "enabled"),
    (_base(translations={"en": {"a": 5}}), "строки"),
])
def test_invalid_manifests_are_rejected(mods_env, manifest, needle):
    _mod(mods_env, "m", manifest)
    mod = modsys.load()[0]
    assert mod.errors, manifest
    assert any(needle in e for e in mod.errors), mod.errors
    assert not mod.active


def test_unknown_fields_and_languages_are_only_warnings(mods_env):
    _mod(mods_env, "w", _base(surprise=1, translations={"ru": {"a": "b"}}))
    mod = modsys.load()[0]
    assert mod.active and len(mod.warnings) == 2


def test_duplicate_id_second_mod_rejected(mods_env):
    _mod(mods_env, "one", _base("same_id"))
    _mod(mods_env, "two", _base("same_id"))
    mods = modsys.load()
    assert mods[0].active
    assert not mods[1].active and any("уже занят" in e for e in mods[1].errors)


def test_disabled_mod_is_not_applied(mods_env):
    _mod(mods_env, "off", _base("off_mod", enabled=False, palette={"RED": [7, 7, 7]}))
    before = C.RED
    mod = modsys.load()[0]
    assert not mod.active and mod.enabled is False
    assert C.RED == before


def test_mod_songs_and_images_are_found_game_first(mods_env, tmp_path, monkeypatch):
    game_songs = tmp_path / "game_songs"
    game_songs.mkdir()
    monkeypatch.setattr(songs, "SONG_DIR", str(game_songs))
    _wav(game_songs / "shared.wav")
    d = _mod(mods_env, "s", _base(songs="songs", images="images"))
    _wav(d / "songs" / "shared.wav")
    _wav(d / "songs" / "extra.wav")
    (d / "images").mkdir()
    (d / "images" / "pic.png").write_bytes(b"x")
    modsys.load()
    names = songs.list_songs()
    assert names.count("shared.wav") == 1 and "extra.wav" in names
    assert songs.song_path("shared.wav").startswith(str(game_songs))
    assert songs.song_path("extra.wav").startswith(str(d))
    assert EV.image_path("pic.png").startswith(str(d))
    assert EV.image_path("missing.png") is None


def test_mod_chart_is_read_only_and_saves_as_copy(mods_env, tmp_path, data_root, monkeypatch):
    d = _mod(mods_env, "c", _base(charts="charts"))
    (d / "charts").mkdir()
    ch = songs.new_chart("mod_song.wav", "Чарт мода")
    ch.notes.append(chartmod.Note(1000, 1))
    ch.id = "mod-chart-1"
    mod_file = d / "charts" / "mod_chart.json"
    ch.save_as(str(mod_file)) if hasattr(ch, "save_as") else mod_file.write_text(
        json.dumps(ch.to_dict(), ensure_ascii=False), encoding="utf-8")
    original = mod_file.read_bytes()
    modsys.load()
    loaded = [c for c in songs.all_charts() if getattr(c, "from_mod", None)]
    assert loaded, "чарт мода не найден"
    mc = loaded[0]
    mc.notes.append(chartmod.Note(5000, 2))
    saved_path = songs.save_chart(mc)
    assert os.path.dirname(saved_path) == os.path.abspath(songs.CHART_DIR) or \
        os.path.dirname(saved_path) == songs.CHART_DIR
    assert mod_file.read_bytes() == original
    saved = json.loads(open(saved_path, encoding="utf-8").read())
    assert saved["id"] and saved["id"] != "mod-chart-1"
    assert len(saved["notes"]) == len(mc.notes)
    songs.delete_chart(mc)
    assert mod_file.exists()
