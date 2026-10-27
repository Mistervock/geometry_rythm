import json
import os
import shutil
import wave

import pygame
import pytest

import achievements
import autosave as AS
import chart as chartmod
import dialogs
import ghost as GH
import jsonio
import library
import progress
import runs
import songs
import startup
from test_screens import fake_outcome, mkchart


@pytest.fixture
def env(data_root, tmp_path, monkeypatch):
    sd = tmp_path / "songs"
    sd.mkdir()
    with wave.open(str(sd / "t.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\0\0\0\0" * 44100 * 5)
    monkeypatch.setattr(songs, "SONG_DIR", str(sd))
    monkeypatch.setattr(library, "PATH", str(tmp_path / "library.json"))
    library.reset_for_tests()
    monkeypatch.setattr(progress, "PATH", str(tmp_path / "progress.json"))
    monkeypatch.setattr(GH, "DIR", str(tmp_path / "ghosts"))
    songs.forget_cached()
    return tmp_path


def test_first_run_saves_ghost_rank_and_win(env):
    ch = mkchart()
    out = runs.finish_run(ch, fake_outcome(ch))
    assert out["ghost_saved"] == "saved" and out["rank"]["new"]
    assert songs.is_won(ch)
    g, status = GH.load(ch)
    assert status == GH.OK and g.score == out["score"]
    # второй проход хуже — призрак остаётся прежним, сравнение с рекордом показывает «хуже»
    worse = fake_outcome(ch)
    worse["score"] -= 100
    worse["stats"]["score"] -= 100
    out2 = runs.finish_run(ch, worse, ghost_old=g)
    assert out2["ghost_saved"] == "kept" and out2["pb_compare"]["better"] is False
    # точно такой же результат: ничья оставляет старый
    same = fake_outcome(ch)
    assert runs.finish_run(ch, same, ghost_old=g)["ghost_saved"] == "kept"
    better = fake_outcome(ch)
    better["score"] += 500
    better["stats"]["score"] += 500
    assert runs.finish_run(ch, better, ghost_old=g)["ghost_saved"] == "saved"
    assert GH.load(ch)[0].score == better["score"]


def test_ghost_stale_corrupt_and_newer(env):
    ch = mkchart()
    runs.finish_run(ch, fake_outcome(ch))
    path = GH.path_for(ch.id or ch.key)
    assert os.path.exists(path) or any(os.path.exists(GH.path_for(k)) for k in GH.keys_for(ch))
    ch.notes.append(chartmod.Note(99000, 0, 0))                # чарт изменился → призрак устарел
    assert GH.load(ch)[1] == GH.STALE
    ch.notes.pop()
    p = next(GH.path_for(k) for k in GH.keys_for(ch) if os.path.exists(GH.path_for(k)))
    with open(p, "w") as f:
        f.write("{broken")
    g, status = GH.load(ch)
    assert g is None and status == GH.CORRUPT
    assert not os.path.exists(p) and any(".corrupt-" in n for n in os.listdir(os.path.dirname(p)))
    data = GH.build(ch, fake_outcome(ch))
    data["version"] = 99
    jsonio.write_atomic(p, data)
    assert GH.load(ch)[1] == GH.NEWER


def test_ghost_validation_rejects_garbage():
    assert not GH.validate({"format": "x"})[0]
    base = {"format": GH.FORMAT, "version": 1, "chart_id": "", "chart_key": "", "notes_hash": "", "score": 1,
            "acc": 50.0, "grade": "B", "max_combo": 1, "timeline": [[1, 1, 1]], "marks": [[1, 0, "p"]]}
    assert GH.validate(base)[0]
    for bad in ({"timeline": [[2, 1, 1], [1, 1, 1]]}, {"marks": [[1, 9, "p"]]}, {"score": float("nan")},
                {"grade": "Z"}, {"timeline": [[1, 1]]}):
        assert not GH.validate(dict(base, **bad))[0]


def test_ghost_not_saved_for_failed_partial_or_practice(env):
    ch = mkchart()
    out = fake_outcome(ch)
    out["failed"] = True
    assert GH.maybe_save(ch, out) == "skipped"
    part = fake_outcome(ch)
    part["stats"]["judged"] = part["stats"]["total"] - 1
    assert GH.maybe_save(ch, part) == "skipped"
    pr = fake_outcome(ch, practice=True)
    assert GH.maybe_save(ch, pr) == "skipped"


def test_practice_does_not_touch_records_ranks_wins_or_achievements(env):
    ch = mkchart()
    out = runs.finish_run(ch, fake_outcome(ch, practice=True))
    assert "rank" not in out and "ghost_saved" not in out and not songs.is_won(ch)
    assert songs.chart_best(ch) is None
    assert GH.load(ch)[1] == GH.NONE
    st = progress.load()
    assert st["finishes"] == 0 and st["fc_runs"] == 0 and st["best_streak"] == 0


def test_builtin_achievements_honest_and_not_repeated(env, tmp_path):
    ch = mkchart()
    # старый прогресс сохраняется
    achievements.unlock("old_one.vcld")
    out = runs.finish_run(ch, fake_outcome(ch))
    st = progress.load()
    assert st["finishes"] == 1 and st["best_streak"] == 1
    names1 = out["unlocked"]
    assert progress.is_unlocked("first_clear") and "old_one.vcld" in achievements.unlocked_names()
    assert names1                                           # что-то получено при первом финише
    out2 = runs.finish_run(ch, fake_outcome(ch))
    assert not [n for n in out2["unlocked"] if n in names1]  # повторно не выдаётся
    # проигрыш сбрасывает серию, но не отнимает полученное
    failed = fake_outcome(ch)
    failed["failed"] = True
    runs.finish_run(ch, failed)
    assert progress.load()["streak"] == 0 and progress.is_unlocked("first_clear")


def test_short_charts_do_not_give_no_miss(env):
    ch = mkchart(n=12)
    runs.finish_run(ch, fake_outcome(ch))
    st = progress.load()
    assert st["no_miss_runs"] == 0 and st["fc_runs"] == 0 and st["finishes"] == 1


def test_practice_achievements_need_real_section(env):
    ch = mkchart()
    out = fake_outcome(ch, practice=True)
    out["section"] = (0, 2000)                              # слишком короткий участок
    runs.finish_run(ch, out)
    assert progress.load()["practice_runs"] == 0
    out = fake_outcome(ch, practice=True)
    out["section"] = (0, 9000)
    out["stats"]["judged"] = 30
    runs.finish_run(ch, out)
    assert progress.load()["practice_runs"] == 1 and progress.is_unlocked("practice_1")


def test_editor_achievement_counters(env):
    ch = mkchart()
    ch.id = "abc123"
    progress.notify("chart_saved", chart=ch, snapped_notes=25, new=True)
    progress.notify("chart_saved", chart=ch, snapped_notes=25, new=True)   # тот же чарт — не «второй новый»
    st = progress.load()
    assert st["charts_created"] == 1 and st["grid_saves"] == 2
    assert progress.is_unlocked("create_1") and progress.is_unlocked("editor_grid")
    tiny = songs.new_chart("t.wav", "tiny")
    tiny.notes = [chartmod.Note(100, 0)]
    before = progress.load()["charts_saved"]
    progress.notify("chart_saved", chart=tiny, new=True)
    assert progress.load()["charts_saved"] == before


def test_progress_corrupt_file_is_quarantined(env):
    with open(progress.PATH, "w") as f:
        f.write("not json")
    assert progress.load()["finishes"] == 0
    assert any(".corrupt-" in n for n in os.listdir(os.path.dirname(progress.PATH)))


def test_library_favorites_survive_rename_and_history_limits(env, tmp_path):
    lib = library.get()
    sid = library.song_id("t.wav")
    assert lib.toggle_favorite_song("t.wav") is True
    shutil.copy(songs.song_path("t.wav"), songs.song_path("renamed.wav"))
    os.remove(songs.song_path("t.wav"))
    library._fp_cache.clear()
    assert library.song_id("renamed.wav") == sid and lib.is_favorite_song("renamed.wav")
    assert lib.toggle_favorite_song("renamed.wav") is False and not lib.is_favorite_song("renamed.wav")
    ch = songs.new_chart("renamed.wav", "x")
    for _ in range(library.HISTORY_LIMIT + 30):
        lib.start_run(ch)
    assert len(lib.history()) == library.HISTORY_LIMIT


def test_library_no_duplicates_and_corrupt_file(env):
    raw = {"favorites": {"songs": ["a", "a", "b", 5, None], "charts": "x"},
           "history": [{"id": "1", "song": "s"}, {"id": "1", "song": "dup"}, "junk", {"noid": 1}]}
    d = library.sanitize(raw)
    assert d["favorites"]["songs"] == ["a", "b"] and d["favorites"]["charts"] == []
    assert len(d["history"]) == 1
    with open(library.PATH, "w") as f:
        f.write("{oops")
    library.reset_for_tests(library.PATH)
    assert library.get().history() == []
    assert any(".corrupt-" in n for n in os.listdir(os.path.dirname(library.PATH)))


def test_library_chart_favorite_by_id(env):
    ch = mkchart()
    ch.ensure_id()
    lib = library.get()
    lib.toggle_favorite_chart(ch)
    ch.path = os.path.join(os.path.dirname(ch.path), "renamed.json")
    assert lib.is_favorite_chart(ch)                           # id пережил переименование файла


def test_startup_recovery_actions(env, tmp_path, monkeypatch):
    ch = mkchart()
    d = str(tmp_path / "as")
    a = AS.Autosaver(ch, directory=d, threaded=False)
    ch.notes.append(chartmod.Note(7000, 1, 0))
    a.save(1, "emergency")
    recs = AS.scan(d, songs.CHART_DIR)
    assert recs and recs[0].status == AS.NEWER
    monkeypatch.setattr(AS, "default_dir", lambda: d)
    calls = []
    monkeypatch.setattr(startup, "_open_editor", lambda clock, chart, rec=None: calls.append((chart, rec)))
    # восстановить
    monkeypatch.setattr(startup, "ask", lambda clock, rec: "restore")
    assert startup.handle(None, recs[0]) == "restored"
    assert len(calls[0][0].notes) == len(ch.notes) and calls[0][1] is recs[0]
    # открыть обычный: исходник без новой ноты, автосохранение остаётся, но больше не напоминает
    monkeypatch.setattr(startup, "ask", lambda clock, rec: "normal")
    assert startup.handle(None, recs[0]) == "normal"
    assert len(calls[1][0].notes) == len(ch.notes) - 1
    assert AS.scan(d, songs.CHART_DIR)[0].ignored
    # удалить с подтверждением
    monkeypatch.setattr(startup, "ask", lambda clock, rec: "delete")
    monkeypatch.setattr(dialogs, "confirm", lambda *a, **k: False)
    assert startup.handle(None, recs[0]) == "later" and AS.scan(d, songs.CHART_DIR)
    monkeypatch.setattr(dialogs, "confirm", lambda *a, **k: True)
    assert startup.handle(None, recs[0]) == "deleted" and not AS.scan(d, songs.CHART_DIR)


def test_startup_missing_song_keeps_autosave(env, tmp_path, monkeypatch):
    ch = mkchart()
    d = str(tmp_path / "as")
    a = AS.Autosaver(ch, directory=d, threaded=False)
    ch.notes.append(chartmod.Note(7000, 1, 0))
    a.save(1, "emergency")
    rec = AS.scan(d, songs.CHART_DIR)[0]
    os.remove(songs.song_path("t.wav"))
    monkeypatch.setattr(startup, "ask", lambda clock, rec: "restore")
    shown = []
    monkeypatch.setattr(dialogs, "info_lines", lambda clock, title, lines, **k: shown.append(lines))
    assert startup.handle(None, rec) == "later"
    assert shown and AS.scan(d, songs.CHART_DIR)
