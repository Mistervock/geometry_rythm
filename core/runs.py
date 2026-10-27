"""Запуск чарта от выбора до результатов: практика/обычная игра, подготовка, итоги, запись прогресса.

Здесь собрано всё, что происходит ВОКРУГ игры, чтобы game.py занимался только игрой, а main.py — только меню:
  * экран выбора участка (практика), подготовка (session), игра (game), экран результатов;
  * запись рекордов/рангов/побед/достижений ТОЛЬКО для обычных проходов; практика их не трогает;
  * сохранение призрака (ghost), история запусков (library), счётчики и встроенные достижения (progress).
"""
import ghost as GH
import library
import practice as PR
import scoring
import settings
import songs
from i18n import t


def finish_run(chart, outcome, entry_id=None, ghost_old=None):
    """Записывает итоги. Возвращает outcome, дополненный полями для экрана результатов."""
    lib = library.get()
    if entry_id:
        lib.finish_run(entry_id, outcome)
    unlocked = []
    if outcome.get("practice"):
        _notify_into(unlocked, "practice_finished", chart=chart, outcome=outcome)
        outcome["unlocked"] = unlocked
        return outcome

    # сравнение с личным рекордом: до сохранения нового призрака
    if ghost_old is not None and not outcome["failed"]:
        outcome["pb_compare"] = scoring.compare(outcome["stats"], ghost_old.data)
        outcome["pb_timeline"] = ghost_old.timeline
    if not outcome["failed"]:
        songs.mark_win(chart)
        fresh_best, prev = songs.record_rank(chart, outcome["grade"], outcome["acc"], outcome["score"])
        best = songs.chart_best(chart)
        outcome["rank"] = {"grade": outcome["grade"], "best": best["grade"] if best else outcome["grade"],
                           "new": fresh_best, "prev": prev, "song": songs.song_rank(chart.song)}
        if chart.achievement:
            import achievements
            ach = achievements.find(chart.achievement)
            if ach is not None:
                outcome["achievement"] = {"name": ach["name"], "new": achievements.unlock(chart.achievement)}
        outcome["ghost_saved"] = GH.maybe_save(chart, outcome)
    _notify_into(unlocked, "run_finished", chart=chart, outcome=outcome)
    outcome["unlocked"] = unlocked
    return outcome


def _notify_into(lst, kind, **data):
    try:
        import progress
        lst.extend(progress.notify(kind, **data))
    except Exception as e:                      # noqa: BLE001 — достижения не должны ронять игру
        print(f"[progress] {kind}: {e}")


def load_ghost(chart):
    """(Ghost | None, предупреждения для экрана подготовки)."""
    if not settings.get("ghost"):
        return None, []
    g, status = GH.load(chart)
    notes = {GH.STALE: t("Призрак устарел: чарт изменён после рекорда — пройдите чарт заново"),
             GH.CORRUPT: t("Файл призрака повреждён и убран в карантин"),
             GH.NEWER: t("Призрак создан более новой версией игры")}
    return g, ([notes[status]] if status in notes else [])


def play_chart(clock, chart, first, mode="play"):
    """mode: 'play' | 'practice'."""
    import intro
    import menu
    import results
    import session
    from game import Game

    bg = menu.background_surface()
    cfg = None
    if mode == "practice":
        info = songs.info(chart.song)
        cfg = PR.setup_screen(clock, chart, int(info.get("duration_ms") or 0), None,
                              info.get("energy"), float(info.get("energy_fps") or 21.5))
        if cfg is None:
            return
    intro.to_game(clock, first, bg)
    while True:
        ghost_obj, warns = load_ghost(chart)
        sess = session.prep_screen(clock, chart, cfg, ghost_obj, warns)
        if sess is None:
            return
        entry = library.get().start_run(chart, "practice" if cfg else "play")
        outcome = Game(clock, sess).run()
        if outcome["action"] == "menu":
            return
        outcome = finish_run(chart, outcome, entry, ghost_obj)
        choice = results.results_screen(clock, outcome)
        if choice == "menu":
            return
        if choice == "setup" and cfg is not None:
            new = PR.setup_screen(clock, chart, sess.duration, cfg, sess.energy, sess.energy_fps)
            if new is not None:
                cfg = new
        intro.to_game(clock, False, bg)
