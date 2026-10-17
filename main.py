
#-- Импорт
import os
import sys

CORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core")
sys.path.insert(0, CORE_DIR)

import pygame

import config as C


def play_chart(clock, chart, first):
    import intro
    import menu
    import results
    from game import Game

    bg = menu.background_surface()
    intro.to_game(clock, first, bg)
    while True:
        outcome = Game(clock, chart).run()
        if outcome["action"] == "menu":
            return
        choice = results.results_screen(clock, outcome)
        if choice == "menu":
            return
        intro.to_game(clock, False, bg)


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

    first_game = True
    while True:
        action = menu.main_menu(clock)
        if action == "quit":
            break
        if action == "records":
            menu.records_screen(clock)
        elif action == "settings":
            settings_screen.settings_screen(clock)
        elif action == "songs":
            pick = songs_screen.songs_screen(clock)
            if pick is not None:
                play_chart(clock, pick[1], first_game)
                first_game = False

    pygame.quit()


if __name__ == "__main__":
    main()
