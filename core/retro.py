"""Ретро-детали картинки: виньетка как у ЭЛТ, дизайн-растр на дорожках, уголки-рамки.

Всё вычисляется один раз и кэшируется по размеру экрана. Без numpy виньетка просто не рисуется,
остальное работает на чистом pygame."""
#-- Импорт
import pygame

import config as C
import screen_setting as SS

VIGNETTE_STRENGTH = 0.22

_vignette = None
_vignette_size = None
_vignette_failed = False
_dither = {}


def vignette():
    """Поверхность-множитель для BLEND_MULT: белый центр, потемнение к краям. None — если numpy недоступен."""
    global _vignette, _vignette_size, _vignette_failed
    size = (C.WIDTH, C.HEIGHT)
    if _vignette is not None and _vignette_size == size:
        return _vignette
    if _vignette_failed:
        return None
    try:
        import numpy as np
        import pygame.surfarray as sa
    except ImportError:
        _vignette_failed = True
        return None
    w, h = size
    x = np.linspace(-1.0, 1.0, w)[:, None]
    y = np.linspace(-1.0, 1.0, h)[None, :]
    d = np.clip((x * x * 0.8 + y * y) / 1.6, 0.0, 1.0)
    d = d * d * (3 - 2 * d)
    bright = (1.0 - VIGNETTE_STRENGTH * d) * 255.0
    val = bright.astype(np.uint8)
    arr = np.repeat(val[:, :, None], 3, axis=2)
    _vignette = sa.make_surface(arr).convert()
    _vignette_size = size
    return _vignette


def dither(width, height, col=(255, 255, 255), alpha=14, step=None):
    """Шахматный растр: полупрозрачные пиксельные «клетки». Нужен для дорожек, чтобы фон не был плоским."""
    step = step or SS.U(3)
    key = (width, height, col, alpha, step)
    surf = _dither.get(key)
    if surf is None:
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        for row, y in enumerate(range(0, height, step)):
            for x in range((row % 2) * step, width, step * 2):
                surf.fill((*col, alpha), (x, y, step, step))
        _dither[key] = surf
    return surf


def brackets(surface, rect, col, length=None, width=None):
    """Уголки-рамка по углам прямоугольника: строгая «VHS-OSD» рамка вместо сплошной обводки."""
    length = length or SS.U(10)
    width = width or max(1, SS.U(2))
    left, top = rect.left, rect.top
    right, bottom = rect.right - 1, rect.bottom - 1
    for px, py, dx, dy in ((left, top, 1, 1), (right, top, -1, 1),
                           (left, bottom, 1, -1), (right, bottom, -1, -1)):
        pygame.draw.line(surface, col, (px, py), (px + dx * length, py), width)
        pygame.draw.line(surface, col, (px, py), (px, py + dy * length), width)
