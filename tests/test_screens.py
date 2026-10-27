"""Экраны в headless-режиме: события подаются по номеру кадра, проверяем, что ничего не падает и результат верный."""
import wave

import pygame
import pytest

import chart as chartmod
import config as C
import ghost as GH
import history_screen
import library
import practice as PR
import results
import session as SE
import songs


def K(key, uni=""):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=uni)


def feed(monkeypatch, script):
    """script: {номер вызова event.get: [события]}. Вне скрипта возвращает пустой список."""
    state = {"n": 0}

    def fake_get(*a, **k):
        state["n"] += 1
        if state["n"] > 5000:
            raise RuntimeError("экран завис")
        return list(script.get(state["n"], []))
    monkeypatch.setattr(pygame.event, "get", fake_get)


@pytest.fixture
def env(data_root, tmp_path, monkeypatch):
    sd = tmp_path / "songs"
    sd.mkdir()
    with wave.open(str(sd / "t.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\0\0\0\0" * 44100 * 20)
    monkeypatch.setattr(songs, "SONG_DIR", str(sd))
    monkeypatch.setattr(PR, "PATH", str(tmp_path / "practice.json"))
    monkeypatch.setattr(library, "PATH", str(tmp_path / "library.json"))
    library.reset_for_tests()
    import progress
    monkeypatch.setattr(progress, "PATH", str(tmp_path / "progress.json"))
    import ghost
    monkeypatch.setattr(ghost, "DIR", str(tmp_path / "ghosts"))
    songs.forget_cached()
    return tmp_path


def mkchart(n=40):
    ch = songs.new_chart("t.wav", "T")
    ch.notes = [chartmod.Note(1000 + i * 250, i % 4, 400 if i % 6 == 0 else 0) for i in range(n)]
    ch.sort()
    ch.difficulty = 4
    songs.save_chart(ch)
    return ch


def fake_outcome(ch, practice=False):
    import engine as EN
    notes = ch.copy_notes()
    e = EN.Engine(notes, practice=practice, section=(1000, 6000) if practice else None)
    ev = []
    for n in notes:
        if not (e.sect_a is None or e.sect_a <= n.t <= e.sect_b):
            continue
        ev.append((n.t + (n.idx % 5) * 12 - 20, 1, n.lane))
        if n.dur:
            ev.append((n.end + 10, 0, n.lane))
    for tm, down, lane in sorted(ev):
        e.update(tm)
        (e.press if down else e.release)(lane, tm)
    e.update(e.end_time + 10)
    st = e.summary()
    out = {"score": st["score"], "acc": st["acc"], "grade": st["grade"], "counts": st["counts"],
           "max_combo": st["max_combo"], "failed": st["failed"], "total": st["total"], "song": "t", "chart": ch.name,
           "action": "results", "stats": st, "practice": practice, "notes_hash": ch.notes_hash()}
    if practice:
        out.update(section=(1000, 6000), speed=0.75, attempts=[{"acc": st["acc"], "score": st["score"], "grade": st["grade"]}])
    else:
        out["judgments"] = [j.to_list() for j in e.judgments]
        out["timeline"] = list(e.timeline)
    return out


def test_results_both_tabs_and_exit(env, monkeypatch):
    ch = mkchart()
    out = fake_outcome(ch)
    out["pb_compare"] = {"score": 10, "acc": 0.5, "max_combo": 1, "misses": 0, "better": True}
    out["pb_timeline"] = [(1000, 100, 1), (5000, 3000, 20)]
    out["unlocked"] = ["Тест"]
    out["rank"] = {"grade": "S", "best": "S", "new": True, "prev": None, "song": "S"}
    # записи в таблицу рекордов не будет (ввод имени): ESC → пропуск; затем TAB, потом M
    feed(monkeypatch, {200: [K(pygame.K_ESCAPE)], 210: [K(pygame.K_TAB)], 220: [K(pygame.K_TAB)],
                       225: [K(pygame.K_TAB)], 240: [K(pygame.K_m)]})
    monkeypatch.setattr(results.records, "qualifies", lambda s: True)
    assert results.results_screen(pygame.time.Clock(), out) == "menu"


def test_results_practice_setup_choice(env, monkeypatch):
    ch = mkchart()
    out = fake_outcome(ch, practice=True)
    feed(monkeypatch, {200: [K(pygame.K_s)]})
    assert results.results_screen(pygame.time.Clock(), out) == "setup"


def test_practice_setup_screen_returns_config(env, monkeypatch):
    ch = mkchart()
    feed(monkeypatch, {3: [K(pygame.K_b), K(pygame.K_LEFT)], 4: [K(pygame.K_a), K(pygame.K_RIGHT)],
                       5: [K(pygame.K_1)], 6: [K(pygame.K_l)], 7: [K(pygame.K_h)], 8: [K(pygame.K_RETURN)]})
    cfg = PR.setup_screen(pygame.time.Clock(), ch, 20000)
    assert cfg is not None and cfg.speed == 0.5 and cfg.loop is False and cfg.hp_loss is True
    assert cfg.a == 250 and cfg.b == 19750 and cfg.b - cfg.a >= PR.MIN_LEN
    saved = PR.load_saved(ch, 20000)
    assert (saved.a, saved.b, saved.speed) == (cfg.a, cfg.b, 0.5)


def test_practice_setup_cancel(env, monkeypatch):
    ch = mkchart()
    feed(monkeypatch, {3: [K(pygame.K_ESCAPE)]})
    assert PR.setup_screen(pygame.time.Clock(), ch, 20000) is None


def test_practice_config_validation():
    cfg = PR.PracticeConfig.from_dict({"a": 99999999, "b": -5, "speed": 0.123, "loop": "x"}, 10000)
    assert 0 <= cfg.a < cfg.b <= 10000 and cfg.b - cfg.a >= PR.MIN_LEN and cfg.speed == 1.0
    assert PR.PracticeConfig.from_dict("junk", 5000).length >= PR.MIN_LEN
    assert PR.PracticeConfig.from_dict({"a": float("nan"), "b": float("inf")}, 8000).b <= 8000


def test_prep_screen_ok_and_error(env, monkeypatch):
    ch = mkchart()
    feed(monkeypatch, {})
    s = SE.prep_screen(pygame.time.Clock(), ch, None, None, ["предупреждение"])
    assert s is not None and s.warnings and s.timings
    bad = songs.new_chart("t.wav", "empty")
    feed(monkeypatch, {50: [K(pygame.K_ESCAPE)]})
    assert SE.prep_screen(pygame.time.Clock(), bad) is None


def test_history_records_launch_vs_finish_and_resolve(env, monkeypatch):
    ch = mkchart()
    lib = library.get()
    e1 = lib.start_run(ch)
    e2 = lib.start_run(ch, "practice")
    lib.finish_run(e2, {"score": 123, "acc": 90.5, "grade": "A", "failed": False})
    hist = lib.history()
    assert [h["result"] is None for h in hist] == [False, True]      # новые сверху; незавершённый — без результата
    found = lib.resolve(hist[1])
    assert found and found[0] == "t.wav" and found[1].name == ch.name
    feed(monkeypatch, {5: [K(pygame.K_DOWN)], 6: [K(pygame.K_DELETE)], 8: [K(pygame.K_ESCAPE)]})
    assert history_screen.run(pygame.time.Clock()) is None
    assert len(library.get().history()) == 1
    library.reset_for_tests(str(env / "library.json"))                 # перечитать с диска
    assert len(library.get().history()) == 1


def test_history_open_song(env, monkeypatch):
    ch = mkchart()
    library.get().start_run(ch)
    feed(monkeypatch, {5: [K(pygame.K_RETURN)]})
    res = history_screen.run(pygame.time.Clock())
    assert res[0] == "t.wav" and res[2] == "play"


def test_achievements_screen_both_tabs(env, monkeypatch):
    import achievements_screen
    feed(monkeypatch, {5: [K(pygame.K_TAB)], 8: [K(pygame.K_DOWN)], 10: [K(pygame.K_TAB)], 12: [K(pygame.K_ESCAPE)]})
    achievements_screen.run(pygame.time.Clock())


def test_songs_screen_favorite_and_play(env, monkeypatch):
    import songs_screen
    mkchart()
    # открыть песню (Enter), отметить чарт (B), закрыть и выбрать ИГРАТЬ через Enter
    feed(monkeypatch, {5: [K(pygame.K_RETURN)], 12: [K(pygame.K_b)], 14: [K(pygame.K_RETURN)]})
    res = songs_screen.songs_screen(pygame.time.Clock())
    assert res[0] == "play" and res[2] == "play"
    assert library.get().is_favorite_chart(res[1])
    feed(monkeypatch, {5: [K(pygame.K_b)], 8: [K(pygame.K_l)], 12: [K(pygame.K_ESCAPE)], 14: [K(pygame.K_ESCAPE)]})
    assert songs_screen.songs_screen(pygame.time.Clock()) is None
    assert library.get().is_favorite_song("t.wav")


def test_songs_screen_practice_key(env, monkeypatch):
    import songs_screen
    mkchart()
    feed(monkeypatch, {5: [K(pygame.K_RETURN)], 12: [K(pygame.K_p)]})
    res = songs_screen.songs_screen(pygame.time.Clock())
    assert res[2] == "practice"


def test_settings_and_menu_render(env, monkeypatch):
    import menu
    import settings_screen
    feed(monkeypatch, {200: [K(pygame.K_ESCAPE)]})
    assert menu.main_menu(pygame.time.Clock()) == "quit"
    feed(monkeypatch, {10: [K(pygame.K_ESCAPE)]})
    settings_screen.settings_screen(pygame.time.Clock())
