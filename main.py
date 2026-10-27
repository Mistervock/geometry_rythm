
#-- Импорт
import os
import sys

CORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core")
sys.path.insert(0, CORE_DIR)

import pygame

import config as C


def play_chart(clock, chart, first, mode="play"):
    import runs
    runs.play_chart(clock, chart, first, mode)


def main():
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
    except pygame.error:
        pass
    pygame.init()
    import display
    screen = display.apply()
    pygame.display.set_caption(C.TITLE)
    clock = pygame.time.Clock()

    import cache
    cache.warm()

    import intro
    import menu
    import settings_screen
    import songs
    import songs_screen

    songs.migrate_legacy()

    snap = intro.play_credits(clock)
    if snap is None:
        snap = screen.copy()
    intro.to_menu(clock, snap, menu.background_surface())

    import startup
    startup.run(clock)

    first_game = True
    while True:
        action = menu.main_menu(clock)
        if action == "quit":
            break
        if action == "records":
            menu.records_screen(clock)
        elif action == "achievements":
            import achievements_screen
            achievements_screen.run(clock)
        elif action == "settings":
            settings_screen.settings_screen(clock)
        elif action == "history":
            import history_screen
            pick = history_screen.run(clock)
            if pick is not None:
                play_chart(clock, pick[1], first_game, pick[2] if len(pick) > 2 else "play")
                first_game = False
        elif action == "songs":
            pick = songs_screen.songs_screen(clock)
            if pick is not None:
                play_chart(clock, pick[1], first_game, pick[2] if len(pick) > 2 else "play")
                first_game = False

    pygame.quit()


def _guarded():
    """Запуск с журналом падений: в собранном exe без консоли ошибка иначе пропала бы бесследно."""
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:                      # сборка без консоли: print() не должен падать
            setattr(sys, name, open(os.devnull, "w"))
    try:
        main()
    except SystemExit:
        raise
    except BaseException:                                   # noqa: BLE001 — записываем и пробрасываем дальше
        import time
        import traceback
        try:
            with open(C.root("crash.log"), "a", encoding="utf-8") as f:
                f.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} Geometry Rhythm {C.VERSION} ===\n")
                f.write(traceback.format_exc())
        except OSError:
            pass
        raise


if __name__ == "__main__":
    _guarded()
