"""Разрешение игры и масштаб раскладки.

Вся раскладка написана в расчётных координатах REF_W × REF_H (1280 × 720).
U(v) переводит расчётное число в пиксели выбранного режима. Для 1280 × 720
U(v) == v, поэтому старый вид не меняется.

Чтобы добавить режим, допишите строку в MODES. Размеры и позиции, которые
хранятся в чарте (ноты, события), остаются расчётными и от режима не зависят.
Для рисования используйте только U / UR / UP, а не голые числа.
"""
import json
import os

import pygame

REF_W, REF_H = 1280, 720
MODES = (
    ("1280x720", 1280, 720),
    ("1920x1080", 1920, 1080),
)
DEFAULT = "1280x720"

SCALE = 1.0
_name = DEFAULT


def names():
    return [m[0] for m in MODES]


def size(name):
    for mode, w, h in MODES:
        if mode == name:
            return w, h
    return size(DEFAULT)


def current():
    return _name


def read_saved(path):
    """Имя режима из settings.json; при ошибке или неизвестном имени — DEFAULT."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            name = json.load(f).get("resolution")
    except (OSError, ValueError, AttributeError):
        return DEFAULT
    return name if name in names() else DEFAULT


def apply_name(name):
    """Меняет масштаб раскладки без обращения к config (нужно при импорте config)."""
    global SCALE, _name
    if name not in names():
        name = DEFAULT
    w, h = size(name)
    _name = name
    SCALE = w / REF_W
    return w, h


def set_mode(name):
    """Переключает режим во время работы: размеры игры и производные константы."""
    import config as C
    w, h = apply_name(name)
    C.WIDTH, C.HEIGHT = w, h
    C.refresh_derived()
    return w, h


def U(v):
    """Расчётное число → пиксели текущего режима."""
    return int(round(v * SCALE))


def UR(x, y, w, h):
    return pygame.Rect(U(x), U(y), U(w), U(h))


def UP(x, y):
    return (U(x), U(y))
