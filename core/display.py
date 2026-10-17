
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


def tick(clock):
    if VSYNC:
        return clock.tick()
    return clock.tick(C.FPS)


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
