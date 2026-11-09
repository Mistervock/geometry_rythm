"""Запуск чарта от выбора до результатов: практика/обычная игра, подготовка, итоги, запись прогресса.

Здесь собрано всё, что происходит ВОКРУГ игры, чтобы game.py занимался только игрой, а main.py — только меню:
  * экран выбора участка (практика), подготовка (session), игра (game), экран результатов;
  * запись рекордов/рангов/побед/достижений ТОЛЬКО для обычных проходов; практика их не трогает;
  * сохранение призрака (ghost), история запусков (library), счётчики и встроенные достижения (progress).
"""
import ghost as GH
import library
import modifiers as MD
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

    if ghost_old is not None and not outcome["failed"]:
        outcome["pb_compare"] = scoring.compare(outcome["stats"], ghost_old.data)
        outcome["pb_timeline"] = ghost_old.timeline
    if not outcome["failed"]:
        songs.mark_win(chart)
        fresh_best, prev = songs.record_rank(chart, outcome["grade"], outcome["acc"], outcome["score"],
                                             outcome.get("mods", []))
        best = songs.chart_best(chart, None, outcome.get("mods", []))
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


def play_test(clock, chart, at_ms, speed=1.0):
    """Проверка чарта от выбранной точки редактора (F5).

    chart — копия чарта: игра не должна менять исходный. Тестовый режим (session.test) отключает всё,
    что пишется на диск: историю, рекорды, призрак, достижения и счётчики. Экран результатов не открывается,
    после завершения показывается короткая сводка. Возвращает итог игры с action == "test"
    или None, если подготовка отменена.
    """
    import session
    from game import Game

    cfg = PR.PracticeConfig(a=at_ms, b=0, speed=speed, loop=False, hp_loss=False)
    mods = MD.effective(chart, "play")
    sess = session.prep_screen(clock, chart, cfg, None, [], mods, test=True)
    if sess is None:
        return None
    outcome = Game(clock, sess).run()
    if outcome.get("test_complete"):
        _test_summary(clock, outcome)
    return outcome


def _test_summary(clock, outcome):
    import dialogs
    lines = [f"{t('Оценка')}: {outcome['grade']}    {t('Точность')}: {outcome['acc']:.1f}%",
             f"{t('Счёт')}: {outcome['score']}    {t('Макс. комбо')}: {outcome['max_combo']}",
             t("Ничего не записано: рекорды, история и призрак не изменены.")]
    dialogs.info_lines(clock, t("ТЕСТ ОКОНЧЕН"), lines, footer="ESC")


def _notify_into(lst, kind, **data):
    try:
        import progress
        lst.extend(progress.notify(kind, **data))
    except Exception as e:
        print(f"[progress] {kind}: {e}")


def load_ghost(chart, mods=()):
    """(Ghost | None, предупреждения для экрана подготовки). Призрак — выбор игрока: свой, импортированный или нет."""
    if not settings.get("ghost"):
        return None, []
    g, status = GH.for_play(chart, mods)
    if GH.choice_of(chart).startswith(GH.IMPORT_PREFIX):
        if status != GH.OK:
            return None, [t("Импортированный призрак не подходит к этому чарту: игра без призрака")]
        return g, []
    notes = {GH.STALE: t("Призрак устарел: чарт изменён после рекорда — пройдите чарт заново"),
             GH.CORRUPT: t("Файл призрака повреждён и убран в карантин"),
             GH.NEWER: t("Призрак создан более новой версией игры"),
             GH.OTHER_MODS: t("Призрак записан с другими модификаторами и не показан")}
    return g, ([notes[status]] if status in notes else [])


def load_own(chart, mods=()):
    """Свой лучший проход для сравнения в результатах: не зависит от призрака, выбранного для показа."""
    if not settings.get("ghost"):
        return None
    return GH.load(chart, None, mods)[0]


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
        mods = MD.effective(chart, "practice" if cfg else "play")
        ghost_obj, warns = load_ghost(chart, mods)
        sess = session.prep_screen(clock, chart, cfg, ghost_obj, warns, mods)
        if sess is None:
            return
        entry = library.get().start_run(chart, "practice" if cfg else "play")
        outcome = Game(clock, sess).run()
        if outcome["action"] == "menu":
            return
        outcome = finish_run(chart, outcome, entry, load_own(chart, mods))
        choice = results.results_screen(clock, outcome)
        if choice == "menu":
            return
        if choice == "setup" and cfg is not None:
            new = PR.setup_screen(clock, chart, sess.duration, cfg, sess.energy, sess.energy_fps)
            if new is not None:
                cfg = new
        intro.to_game(clock, False, bg)
