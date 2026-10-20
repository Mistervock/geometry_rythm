
#-- Импорт
import sys
import time

import pygame

import config as C
import style as S
from i18n import t

NOTE_SCALES = [round(1.0 + 0.05 * i, 2) for i in range(16)]
RING_RADII = list(range(18, 120, 2))

_notes = {}
_rings = {}
_texts = {}
_bands = {}
_warmed = False
_warm_keys = set()
TEXT_LIMIT = 400

COUNTDOWN_WORDS = ("3", "2", "1", "RYTHM!")
COUNTDOWN_SIZE = 96


def _scale_index(scale):
    i = int(round((scale - 1.0) / 0.05))
    return max(0, min(len(NOTE_SCALES) - 1, i))


def _build_note(lane, scale):
    r = C.LANE_W * 0.33 * scale
    size = int(r * 3) + 8
    layer = pygame.Surface((size, size), pygame.SRCALPHA)
    ox = oy = size // 2
    col = C.LANE_COLORS[lane]
    kind = C.LANE_SHAPES[lane]
    for i in range(3):
        pygame.draw.circle(layer, (*col, 18), (ox, oy), int(r * 1.5) - i * 4)
    pts = [(x + ox, y + oy) for x, y in S._shape_points(kind, 0, 0, r)]
    pygame.draw.polygon(layer, (*col, 170), pts)
    pygame.draw.polygon(layer, (*C.WHITE, 255), pts, 2)
    return layer


def _build_ring(color, radius):
    size = radius * 2 + 6
    layer = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(layer, (*color, 255), (radius + 3, radius + 3), radius, 3)
    return layer


def _bake_text(font_size, bold, text, color):
    return S.font(font_size, bold).render(text, True, color).convert_alpha()


def warm():
    global _warmed
    t0 = time.perf_counter()
    for store in (_notes, _rings, _texts, _bands):
        store.clear()
    for lane in range(4):
        _bands[lane] = pygame.Surface((C.LANE_W, C.HEIGHT))
        _bands[lane].fill(C.LANE_COLORS[lane])
        for si, scale in enumerate(NOTE_SCALES):
            _notes[(lane, si)] = _build_note(lane, scale).convert_alpha()
    colors = set(C.LANE_COLORS) | {C.GOLD, C.WHITE, C.RED_LIGHT}
    for col in colors:
        for r in RING_RADII:
            _rings[(col, r)] = _build_ring(col, r).convert_alpha()
    for grade, col in (("PERFECT", C.GOLD), ("GREAT", C.CYAN), ("GOOD", C.GREEN), ("MISS", C.RED_LIGHT)):
        _texts[(22, True, grade, col)] = _bake_text(22, True, grade, col)
    for name in COUNTDOWN_WORDS:
        col = C.GOLD if name == "RYTHM!" else C.CYAN
        _texts[(COUNTDOWN_SIZE, True, name, col)] = _bake_text(COUNTDOWN_SIZE, True, name, col)
        _texts[(COUNTDOWN_SIZE, True, name, C.CYAN)] = _bake_text(COUNTDOWN_SIZE, True, name, C.CYAN)
    _texts[(14, False, t("ESC — пауза"), (90, 90, 120))] = _bake_text(14, False, t("ESC — пауза"), (90, 90, 120))
    for size in range(22, 29):  # размеры комбо меняются от удара к удару
        S.font(size, True)
    _warm_keys.clear()
    _warm_keys.update(_texts)
    _warmed = True
    return (time.perf_counter() - t0) * 1000.0


def note(lane, scale):
    si = _scale_index(scale)
    surf = _notes.get((lane, si))
    if surf is None:
        surf = _build_note(lane, NOTE_SCALES[si]).convert_alpha()
        _notes[(lane, si)] = surf
    return surf


def ring(color, radius):
    radius = max(RING_RADII[0], min(RING_RADII[-1], int(radius) // 2 * 2))
    key = (color, radius)
    surf = _rings.get(key)
    if surf is None:
        surf = _build_ring(color, radius).convert_alpha()
        _rings[key] = surf
    return surf


def text(font_size, bold, value, color):
    key = (font_size, bold, value, color)
    surf = _texts.get(key)
    if surf is None:
        if len(_texts) >= TEXT_LIMIT:
            # сбрасываем только подписи, которых не было при прогреве (например, «+12 ms»)
            for k in [k for k in _texts if k not in _warm_keys]:
                del _texts[k]
        surf = _bake_text(font_size, bold, value, color)
        _texts[key] = surf
    return surf


def band(lane):
    return _bands[lane]


def stats():
    return {"notes": len(_notes), "rings": len(_rings), "texts": len(_texts), "bands": len(_bands)}


if __name__ == "__main__":
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.display.set_mode((C.WIDTH, C.HEIGHT))
    ms = warm()
    print(f"кэш готов за {ms:.1f} мс: {stats()}")
    sys.exit(0)
