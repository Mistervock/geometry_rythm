
#-- Импорт
import os
import warnings

import pygame

import config as C
import settings
import style as S

os.environ["SDL_RENDER_SCALE_QUALITY"] = "1"


#-- Режимы

MODES = (
    ("масштаб на весь экран", pygame.SCALED | pygame.FULLSCREEN),
)


#-- Окно

def _reset():
    pygame.display.quit()
    pygame.display.init()


VSYNC = False


def _windowed():
    global VSYNC
    _reset()
    VSYNC = False
    S.SCANLINES = True
    return pygame.display.set_mode((C.WIDTH, C.HEIGHT))


def _try(flags):
    global VSYNC
    last = None
    for vsync in (1, 0):
        _reset()
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                surf = pygame.display.set_mode((C.WIDTH, C.HEIGHT), flags, vsync=vsync)
            VSYNC = bool(vsync) and not caught
            return surf
        except (pygame.error, TypeError) as e:
            last = e
    raise last


SHOW_FPS = False
_f3_was_down = False
_clock = None


def _poll_f3():
    """F3 переключает счётчик FPS. Опрос клавиш, а не событий: каждый экран читает очередь по-своему."""
    global SHOW_FPS, _f3_was_down
    try:
        down = bool(pygame.key.get_pressed()[pygame.K_F3])
    except (pygame.error, IndexError):
        return
    if down and not _f3_was_down:
        SHOW_FPS = not SHOW_FPS
    _f3_was_down = down


def tick(clock):
    global _clock
    _clock = clock
    _poll_f3()
    if VSYNC:
        return clock.tick()
    return clock.tick(C.FPS)


def flip():
    """Показ кадра. Все экраны выводят кадр через эту функцию, поэтому счётчик FPS виден везде."""
    if SHOW_FPS and _clock is not None:
        import style as S
        scr = pygame.display.get_surface()
        txt = f"FPS {_clock.get_fps():5.1f}"
        fnt = S.font(14, True)
        w, h = fnt.size(txt)
        box = pygame.Surface((w + 12, h + 6), pygame.SRCALPHA)
        box.fill((0, 0, 0, 170))
        scr.blit(box, (8, C.HEIGHT - h - 14))
        scr.blit(fnt.render(txt, True, C.GOLD), (14, C.HEIGHT - h - 11))
    pygame.display.flip()


def apply():
    os.environ["SDL_RENDER_SCALE_QUALITY"] = "1"
    if not settings.get("fullscreen"):
        return _windowed()
    for name, flags in MODES:
        try:
            surf = _try(flags)
            S.SCANLINES = False
            print(f"[display] {name}: ok, vsync={VSYNC}")
            return surf
        except pygame.error as e:
            print(f"[display] {name}: {e}")
    settings.set("fullscreen", 0)
    return _windowed()


def toggle():
    settings.set("fullscreen", 0 if settings.get("fullscreen") else 1)
    return apply()
