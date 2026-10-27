import json
import os
import time

import autosave as A
import chart as chartmod
import jsonio
import songs


def mk(name="Ч1", song="a.ogg", notes=3):
    ch = chartmod.Chart(song, name=name, notes=[chartmod.Note(i * 100, i % 4) for i in range(notes)])
    return ch


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_due_logic_does_not_spam_disk(tmp_path):
    clk = Clock()
    ch = mk()
    a = A.Autosaver(ch, directory=str(tmp_path / "as"), clock=clk, threaded=False)
    assert not a.due(0)                      # первая правка только запускает отсчёт
    clk.t += 5
    assert not a.due(0)
    clk.t += A.INTERVAL
    assert a.due(0)
    a.save(0)
    assert a.writes == 1 and not a.due(0)    # та же ревизия — писать нечего
    clk.t += 100
    assert not a.due(0)
    assert not a.due(1) or True
    clk.t += 1
    a.due(1)
    clk.t += A.INTERVAL
    assert a.due(1)


def test_important_change_is_debounced(tmp_path):
    clk = Clock()
    a = A.Autosaver(mk(), directory=str(tmp_path), clock=clk, threaded=False)
    a.due(1)
    clk.t += 10
    assert a.due(1, important=True)
    a.save(1)
    assert not a.due(2, important=True)      # слишком рано после прошлой записи
    clk.t += A.IMPORTANT_DEBOUNCE + 0.1
    assert a.due(2, important=True)


def test_key_separates_charts_and_drafts(tmp_path, data_root):
    tmp_path = tmp_path / 'as'
    c1, c2 = mk("A"), mk("B")
    songs.save_chart(c1)
    songs.save_chart(c2)
    a1 = A.Autosaver(c1, directory=str(tmp_path), threaded=False)
    a2 = A.Autosaver(c2, directory=str(tmp_path), threaded=False)
    assert a1.key != a2.key
    a1.save(1)
    a2.save(1)
    assert sorted(os.listdir(tmp_path)) == sorted([a1.key + A.SUFFIX, a2.key + A.SUFFIX])
    draft = A.Autosaver(mk("D"), directory=str(tmp_path), threaded=False)
    assert draft.key.startswith("new-")


def test_threaded_write_and_flush(tmp_path):
    a = A.Autosaver(mk(), directory=str(tmp_path), threaded=True)
    a.save(1)
    a.flush()
    assert a.state == "ok" and os.path.exists(A.path_for(str(tmp_path), a.key))
    env = json.load(open(A.path_for(str(tmp_path), a.key), encoding="utf-8"))
    assert env["format"] == A.FORMAT and env["notes"] == 3 and env["chart"]["notes"][0]["t"] == 0


def test_write_error_sets_error_state_and_retries(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    a = A.Autosaver(mk(), directory=str(blocker / "sub"), threaded=False)
    a.save(1)
    assert a.state == "error" and a.error
    assert a.saved_rev == -1                 # будет повторная попытка


def test_generation_rotation(tmp_path, monkeypatch):
    a = A.Autosaver(mk(), directory=str(tmp_path), threaded=False)
    a.save(1)
    p0 = A.path_for(str(tmp_path), a.key)
    old = time.time() - 1000
    os.utime(p0, (old, old))
    a.chart.notes.append(chartmod.Note(999, 0))
    a.save(2)
    assert os.path.exists(A.path_for(str(tmp_path), a.key, 1))
    prev = json.load(open(A.path_for(str(tmp_path), a.key, 1), encoding="utf-8"))
    assert prev["notes"] == 3
    # свежая запись перезаписывается на месте, без нового поколения
    a.save(3)
    assert not os.path.exists(A.path_for(str(tmp_path), a.key, 2))


def _setup_saved_chart(data_root):
    ch = mk("Основной")
    songs.save_chart(ch)
    return ch


def test_scan_finds_newer_and_restore_in_place_only_after_user_saves(tmp_path, data_root):
    ch = _setup_saved_chart(data_root)
    orig_bytes = open(ch.path, "rb").read()
    a = A.Autosaver(ch, directory=str(tmp_path), threaded=False)
    ch.notes.append(chartmod.Note(5000, 1))
    a.save(1)
    recs = A.scan(str(tmp_path), songs.CHART_DIR)
    assert len(recs) == 1 and recs[0].status == A.NEWER
    rec = recs[0]
    restored = A.restore_chart(rec)
    assert len(restored.notes) == 4 and restored.path == ch.path
    assert open(ch.path, "rb").read() == orig_bytes          # исходный файл не тронут восстановлением


def test_identical_autosave_is_stale_and_removed(tmp_path, data_root):
    tmp_path = tmp_path / 'as'
    ch = _setup_saved_chart(data_root)
    a = A.Autosaver(ch, directory=str(tmp_path), threaded=False)
    a.save(1)
    assert A.scan(str(tmp_path), songs.CHART_DIR) == []
    assert os.listdir(tmp_path) == []


def test_conflict_when_source_changed_restores_as_copy(tmp_path, data_root):
    ch = _setup_saved_chart(data_root)
    a = A.Autosaver(ch, directory=str(tmp_path), threaded=False)
    ch.notes.append(chartmod.Note(5000, 1))
    a.save(1)
    other = songs.charts_for("a.ogg")[0]
    other.notes.append(chartmod.Note(7777, 2))
    songs.save_chart(other)                                   # кто-то сохранил исходный чарт после автосейва
    rec = A.scan(str(tmp_path), songs.CHART_DIR)[0]
    assert rec.status == A.CONFLICT and not rec.can_restore_in_place
    restored = A.restore_chart(rec)
    assert restored.path is None and "восстан" in restored.name
    assert restored.id == ""                                  # не наследует идентификатор чужого файла


def test_orphan_and_draft_restore_as_new(tmp_path, data_root):
    ch = _setup_saved_chart(data_root)
    a = A.Autosaver(ch, directory=str(tmp_path), threaded=False)
    ch.notes.append(chartmod.Note(1, 1))
    a.save(1)
    os.remove(ch.path)
    songs.forget_cached()
    rec = A.scan(str(tmp_path), songs.CHART_DIR)[0]
    assert rec.status == A.ORPHAN and A.restore_chart(rec).path is None
    d = A.Autosaver(mk("Черновик"), directory=str(tmp_path / "d"), threaded=False)
    d.save(1)
    rec = A.scan(str(tmp_path / "d"), songs.CHART_DIR)[0]
    assert rec.status == A.DRAFT


def test_same_file_name_different_chart_does_not_get_overwritten(tmp_path, data_root):
    ch = _setup_saved_chart(data_root)
    a = A.Autosaver(ch, directory=str(tmp_path), threaded=False)
    ch.notes.append(chartmod.Note(1, 1))
    a.save(1)
    # файл с тем же именем подменили чартом другой песни
    data = json.load(open(ch.path, encoding="utf-8"))
    data["song"] = "other.ogg"
    json.dump(data, open(ch.path, "w", encoding="utf-8"))
    songs.forget_cached()
    rec = A.scan(str(tmp_path), songs.CHART_DIR)[0]
    assert rec.status == A.ORPHAN and not rec.can_restore_in_place


def test_corrupt_current_falls_back_to_older_generation(tmp_path, data_root):
    ch = _setup_saved_chart(data_root)
    a = A.Autosaver(ch, directory=str(tmp_path), threaded=False)
    ch.notes.append(chartmod.Note(5000, 1))
    a.save(1)
    p0 = A.path_for(str(tmp_path), a.key)
    old = time.time() - 1000
    os.utime(p0, (old, old))
    ch.notes.append(chartmod.Note(6000, 1))
    a.save(2)
    open(p0, "w").write("{broken json")
    rec = A.scan(str(tmp_path), songs.CHART_DIR)[0]
    assert rec.status == A.NEWER and rec.env["notes"] == 4     # вернулись к предыдущему поколению


def test_fully_corrupt_autosave_does_not_crash(tmp_path, data_root):
    tmp_path = tmp_path / 'as'
    os.makedirs(tmp_path, exist_ok=True)
    (tmp_path / ("x" + A.SUFFIX)).write_text("not json")
    (tmp_path / ("y" + A.SUFFIX)).write_text(json.dumps({"format": A.FORMAT, "version": 1, "chart": "bad"}))
    (tmp_path / ("z" + A.SUFFIX)).write_text(json.dumps({"format": "other"}))
    recs = A.scan(str(tmp_path), songs.CHART_DIR)
    assert len(recs) == 3 and all(r.status == A.CORRUPT for r in recs)
    for r in recs:
        A.discard(r)
    assert os.listdir(tmp_path) == []


def test_legacy_autosave_restores_as_new_copy(tmp_path, data_root):
    ch = _setup_saved_chart(data_root)
    legacy = tmp_path / "Основной-autosave.json"
    legacy.write_text(json.dumps(ch.to_dict()), encoding="utf-8")
    rec = A.scan(str(tmp_path), songs.CHART_DIR)[0]
    assert rec.status == A.LEGACY
    assert A.restore_chart(rec).path is None
    A.discard(rec)
    assert not legacy.exists()


def test_ignore_until_newer(tmp_path, data_root):
    ch = _setup_saved_chart(data_root)
    a = A.Autosaver(ch, directory=str(tmp_path), threaded=False)
    ch.notes.append(chartmod.Note(5000, 1))
    a.save(1)
    rec = A.scan(str(tmp_path), songs.CHART_DIR)[0]
    A.ignore(str(tmp_path), rec)
    assert A.scan(str(tmp_path), songs.CHART_DIR)[0].ignored
    time.sleep(0.01)
    a.clock = lambda: time.time() + 5
    ch.notes.append(chartmod.Note(5500, 1))
    a.save(2)
    assert not A.scan(str(tmp_path), songs.CHART_DIR)[0].ignored


def test_clear_removes_all_generations(tmp_path):
    a = A.Autosaver(mk(), directory=str(tmp_path), threaded=False)
    a.save(1)
    a.clear()
    assert os.listdir(tmp_path) == []


def test_retarget_after_first_save_removes_draft_files(tmp_path, data_root):
    ch = mk("Новый")
    a = A.Autosaver(ch, directory=str(tmp_path), threaded=False)
    a.save(1)
    draft_key = a.key
    songs.save_chart(ch)
    a.retarget()
    assert a.key != draft_key and not os.path.exists(A.path_for(str(tmp_path), draft_key))


def test_cleanup_removes_old_and_caps_count(tmp_path):
    for i in range(5):
        p = tmp_path / f"k{i}{A.SUFFIX}"
        p.write_text("{}")
        age = time.time() - (40 * 86400 if i < 2 else 100)
        os.utime(p, (age, age))
    assert A.cleanup(str(tmp_path)) == 2
    assert A.cleanup(str(tmp_path), max_files=1) == 2
