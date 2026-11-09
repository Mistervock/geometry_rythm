"""Эффекты изображения (Geometry Rhythm 7.0, пункт 6): размытие, свечение, хроматика, волна, цветовые фильтры.

Всё делается средствами pygame без шейдеров и GPU: smoothscale для размытия и уменьшения, BLEND_RGB_ADD и
BLEND_RGB_MULT для сложения и окраски, pygame.transform.grayscale для чёрно-белого. Эффекты на весь экран
(событие «fx») применяются к готовому кадру перед постобработкой. Эффект «ОБЪЕКТ» меняет картинку или ролик
перед показом. Пульс «В ТАКТ» берёт сетку чарта: сила эффекта падает сразу после удара и растёт к следующему.

Качество задаёт настройка fx_quality: 0 — выключено, 1 — низкое (геометрические эффекты на половине разрешения),
2 — высокое. Если средний проход эффектов дольше BUDGET_MS, игра переходит на низкое качество до конца сессии.
Эффект, который упал на этом устройстве, отключается и больше не вызывается, остальные продолжают работать.
"""
#-- Импорт
import collections
import math
import time

import pygame

import settings

#-- Определения
KINDS = ("blur", "glow", "chroma", "wave", "warm", "cool", "mono")
LOOKS = ("",) + KINDS
NAMES = {"blur": "РАЗМЫТИЕ", "glow": "СВЕЧЕНИЕ", "chroma": "ХРОМАТИКА", "wave": "ВОЛНА",
         "warm": "ТЁПЛЫЙ", "cool": "ХОЛОДНЫЙ", "mono": "ЧЁРНО-БЕЛЫЙ", "": "НЕТ"}
GEOMETRIC = ("blur", "glow", "chroma", "wave")
TINTS = {"warm": (255, 205, 150), "cool": (150, 205, 255)}
QUALITY = ("off", "low", "high")
QUALITY_NAMES = {"off": "ВЫКЛ", "low": "НИЗКОЕ", "high": "ВЫСОКОЕ"}
BUDGET_MS = 6.0
SAMPLES = 60


#-- Сила и огибающая

def clamp01(v):
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def envelope(ev, elapsed):
    """Нарастание за attack мс, удержание и спад за такое же время до конца. Вне события — 0."""
    dur = ev["dur"]
    if elapsed < 0 or elapsed >= dur:
        return 0.0
    att = ev.get("attack", 0)
    if att <= 0:
        return 1.0
    return min(clamp01(elapsed / att), clamp01((dur - elapsed) / att))


def beat_factor(now, bpm, offset):
    """Множитель пульса: 1 на ударе, минимум 0.5 в середине такта. Без сетки — 1."""
    if not bpm or bpm <= 0:
        return 1.0
    beat_ms = 60000.0 / bpm
    phase = ((now - offset) % beat_ms) / beat_ms
    return 0.5 + 0.5 * (1.0 - phase) ** 2


def level(ev, now, grid=None):
    """Сила эффекта события «fx» в момент now (мс песни), 0..1."""
    lvl = ev["amount"] / 100.0 * envelope(ev, now - ev["t"])
    if ev.get("beat") and grid:
        lvl *= beat_factor(now, grid.get("bpm"), grid.get("offset", 0.0))
    return clamp01(lvl)


def active_levels(events_list, now, grid=None):
    """Список (вид, сила) для всех событий «fx», которые сейчас звучат. Одинаковые виды не складываются:
    берётся большая сила."""
    best = collections.OrderedDict()
    for ev in events_list:
        if ev.get("type") != "fx":
            continue
        lvl = level(ev, now, grid)
        if lvl > 0 and lvl > best.get(ev["kind"], 0.0):
            best[ev["kind"]] = lvl
    return list(best.items())


#-- Пиксельные эффекты (работают на поверхности на месте)

def _blur(s, lvl):
    w, h = s.get_size()
    k = 2 + int(round(lvl * 10))
    small = pygame.transform.smoothscale(s, (max(1, w // k), max(1, h // k)))
    back = pygame.transform.smoothscale(small, (w, h))
    back.set_alpha(int(255 * lvl))
    s.blit(back, (0, 0))


def _glow(s, lvl):
    w, h = s.get_size()
    small = pygame.transform.smoothscale(s, (max(1, w // 4), max(1, h // 4)))
    bloom = pygame.transform.smoothscale(small, (w, h))
    bloom.fill((int(160 * lvl),) * 3 + (255,), special_flags=pygame.BLEND_RGB_MULT)
    s.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


def _chroma(s, lvl):
    d = max(1, int(round(lvl * 8)))
    out = s.copy()
    out.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGB_MULT)
    for col, dx in (((255, 0, 0, 255), -d), ((0, 255, 0, 255), 0), ((0, 0, 255, 255), d)):
        layer = s.copy()
        layer.fill(col, special_flags=pygame.BLEND_RGB_MULT)
        out.blit(layer, (dx, 0), special_flags=pygame.BLEND_RGB_ADD)
    s.blit(out, (0, 0))


def _wave(s, lvl, now, low):
    w, h = s.get_size()
    amp = lvl * 14.0
    step = 8 if low else 4
    phase = now / 180.0
    src = s.copy()
    for y in range(0, h, step):
        dx = int(amp * math.sin(y * 0.045 + phase))
        s.blit(src, (dx, y), area=pygame.Rect(0, y, w, min(step, h - y)))


def _tint(s, lvl, col):
    layer = s.copy()
    layer.fill(col + (255,), special_flags=pygame.BLEND_RGB_MULT)
    layer.set_alpha(int(255 * lvl))
    s.blit(layer, (0, 0))


def _mono(s, lvl):
    layer = pygame.transform.grayscale(s)
    layer.set_alpha(int(255 * lvl))
    s.blit(layer, (0, 0))


def apply_kind(s, kind, lvl, now, low=False):
    """Применяет один вид эффекта к поверхности s с силой lvl (0..1). Неизвестный вид — ValueError."""
    if kind == "blur":
        _blur(s, lvl)
    elif kind == "glow":
        _glow(s, lvl)
    elif kind == "chroma":
        _chroma(s, lvl)
    elif kind == "wave":
        _wave(s, lvl, now, low)
    elif kind in TINTS:
        _tint(s, lvl, TINTS[kind])
    elif kind == "mono":
        _mono(s, lvl)
    else:
        raise ValueError(f"unknown fx kind {kind!r}")


def _run(surface, kind, lvl, now, low):
    if low and kind in GEOMETRIC:
        w, h = surface.get_size()
        small = pygame.transform.smoothscale(surface, (max(1, w // 2), max(1, h // 2)))
        apply_kind(small, kind, lvl, now, True)
        surface.blit(pygame.transform.smoothscale(small, (w, h)), (0, 0))
    else:
        apply_kind(surface, kind, lvl, now, False)


#-- Качество, бюджет и откат

class Budget:
    """Учёт времени эффектов и выбранного качества. Один экземпляр на сессию (см. budget())."""

    def __init__(self):
        self.auto_low = False
        self.broken = set()
        self.times = collections.deque(maxlen=SAMPLES)

    def setting(self):
        try:
            idx = int(settings.get("fx_quality"))
        except (TypeError, ValueError):
            idx = 2
        return QUALITY[min(2, max(0, idx))]

    def mode(self):
        mode = self.setting()
        if mode == "high" and self.auto_low:
            return "low"
        return mode

    def record(self, ms):
        self.times.append(ms)
        if self.auto_low or len(self.times) < SAMPLES:
            return
        if sum(self.times) / len(self.times) > BUDGET_MS:
            self.auto_low = True
            self.times.clear()


_budget = Budget()


def budget():
    return _budget


def available():
    """Есть ли нужные функции pygame. Если нет — эффекты выключаются без ошибок."""
    return hasattr(pygame.transform, "smoothscale") and hasattr(pygame.transform, "grayscale")


def frame(surface, layers, now, bud=None):
    """Применяет слои (вид, сила) к кадру. Ошибка одного вида отключает только его."""
    bud = bud or _budget
    if not layers or bud.mode() == "off" or not available():
        return
    start = time.perf_counter()
    low = bud.mode() == "low"
    for kind, lvl in layers:
        if kind in bud.broken or lvl <= 0:
            continue
        try:
            _run(surface, kind, lvl, now, low)
        except (pygame.error, ValueError, TypeError, MemoryError):
            bud.broken.add(kind)
    bud.record((time.perf_counter() - start) * 1000.0)


def look(surf, kind, amount, now, bud=None):
    """Эффект «ОБЪЕКТ»: возвращает обработанную копию картинки или исходную поверхность, если эффекта нет."""
    bud = bud or _budget
    if not kind or amount <= 0 or bud.mode() == "off" or kind in bud.broken or not available():
        return surf
    out = surf.copy()
    try:
        apply_kind(out, kind, clamp01(amount / 100.0), now, False)
    except (pygame.error, ValueError, TypeError, MemoryError):
        bud.broken.add(kind)
        return surf
    return out
