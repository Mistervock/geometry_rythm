
#-- Импорт
import os

import pygame

import config as C

TYPES = ("glitch", "flash", "image", "bg")
TYPE_NAMES = {"glitch": "ГЛЮК", "flash": "ВСПЫШКА", "image": "КАРТИНКА (БЕТА)", "bg": "ФОН"}
TYPE_COLORS = {"glitch": C.RED_LIGHT, "flash": C.WHITE, "image": C.GOLD, "bg": (200, 200, 210)}
BASE_BG = tuple(C.BG_DARK)
ANIMS = ("pop", "fade", "drift")
ANIM_NAMES = {"pop": "РЕЗКО", "fade": "ПЛАВНО", "drift": "ДВИЖЕНИЕ"}
IMAGE_DIR = C.root("images")
IMAGE_EXT = (".png", ".jpg", ".jpeg")
MAX_T = 60 * 60 * 1000

FIELDS = {
    "glitch": (("dur", "Длительность, мс", 100, 5000, 100, 800),
               ("strength", "Сила, %", 10, 100, 5, 60)),
    "flash": (("attack", "Скорость появления, мс", 10, 500, 10, 40),
              ("dur", "Длительность, мс", 50, 3000, 50, 500)),
    "image": (("dur", "Длительность, мс", 200, 20000, 100, 3000),
              ("w", "Ширина, px", 80, 1280, 20, 480),
              ("x", "Смещение X, px", -600, 600, 10, 0),
              ("y", "Смещение Y, px", -400, 400, 10, 0),
              ("fade", "Плавность, мс", 50, 2000, 50, 300),
              ("dx", "Движение X, px", -600, 600, 10, 0),
              ("dy", "Движение Y, px", -400, 400, 10, 0)),
    "bg": (("r", "Красный", 0, 255, 8, BASE_BG[0]),
           ("g", "Зелёный", 0, 255, 8, BASE_BG[1]),
           ("b", "Синий", 0, 255, 8, BASE_BG[2]),
           ("fade", "Переход, мс", 0, 3000, 50, 500)),
}


def list_images():
    try:
        os.makedirs(IMAGE_DIR, exist_ok=True)
        names = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(IMAGE_EXT)]
    except OSError:
        return []
    return sorted(names, key=str.lower)


def _defaults(kind):
    ev = {"type": kind, "t": 0}
    for key, _, _, _, _, default in FIELDS[kind]:
        ev[key] = default
    if kind == "image":
        ev["file"] = ""
        ev["anim"] = "fade"
    if kind == "bg":
        ev["orig"] = False
    return ev


def make(kind, t):
    ev = _defaults(kind)
    ev["t"] = max(0, min(MAX_T, int(t)))
    if kind == "image":
        names = list_images()
        ev["file"] = names[0] if names else ""
    return ev


def _num(v, lo, hi, default):
    try:
        v = int(round(float(v)))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def normalize(raw):
    if not isinstance(raw, dict) or raw.get("type") not in TYPES:
        return None
    kind = raw["type"]
    ev = _defaults(kind)
    ev["t"] = _num(raw.get("t"), 0, MAX_T, 0)
    for key, _, lo, hi, _, default in FIELDS[kind]:
        ev[key] = _num(raw.get(key), lo, hi, default)
    if kind == "image":
        ev["file"] = str(raw.get("file", ""))[:120]
        ev["anim"] = raw.get("anim") if raw.get("anim") in ANIMS else "fade"
    if kind == "bg":
        ev["orig"] = bool(raw.get("orig", False))
    return ev


def total_ms(ev):
    if ev["type"] == "bg":
        return 0
    if ev["type"] == "flash":
        return ev["attack"] + ev["dur"]
    return ev["dur"]


def bg_target(ev):
    if ev.get("orig", False):
        return BASE_BG
    return (ev.get("r", BASE_BG[0]), ev.get("g", BASE_BG[1]), ev.get("b", BASE_BG[2]))


def bg_at(bg_events, ms):
    prev, active = BASE_BG, None
    for ev in bg_events:
        if ev.get("t", 0) > ms:
            break
        if active is not None:
            prev = bg_target(active)
        active = ev
    if active is None:
        return BASE_BG
    target = bg_target(active)
    fade = active.get("fade", 0)
    k = 1.0 if fade <= 0 else _clamp01((ms - active.get("t", 0)) / fade)
    return tuple(int(prev[i] + (target[i] - prev[i]) * k) for i in range(3))


def cycle(seq, cur, step):
    if not seq:
        return cur
    i = seq.index(cur) if cur in seq else 0
    return seq[(i + step) % len(seq)]


#-- Картинки: загрузка и кэш

_src = {}
_scaled = {}


def image_surface(name, width):
    if not name:
        return None
    key = (name, width)
    surf = _scaled.get(key)
    if surf is not None:
        return surf
    if name not in _src:
        try:
            _src[name] = pygame.image.load(os.path.join(IMAGE_DIR, name)).convert_alpha()
        except (pygame.error, OSError):
            _src[name] = None
    src = _src[name]
    if src is None:
        return None
    h = max(1, round(src.get_height() * width / src.get_width()))
    surf = pygame.transform.smoothscale(src, (width, h))
    _scaled[key] = surf
    return surf


#-- Состояние события в момент elapsed (мс от его t)

def _clamp01(v):
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def glitch_level(ev, elapsed):
    if elapsed < 0 or elapsed >= ev["dur"]:
        return 0.0
    k = 1.0 if elapsed < ev["dur"] * 0.8 else (ev["dur"] - elapsed) / (ev["dur"] * 0.2)
    return ev["strength"] / 100.0 * _clamp01(k)


def flash_alpha(ev, elapsed):
    if elapsed < 0 or elapsed >= ev["attack"] + ev["dur"]:
        return 0.0
    if elapsed < ev["attack"]:
        return _clamp01(elapsed / ev["attack"])
    return _clamp01(1.0 - (elapsed - ev["attack"]) / ev["dur"])


def image_state(ev, elapsed):
    dur = ev["dur"]
    if elapsed < 0 or elapsed >= dur:
        return 0.0, 0, 0
    fade = max(1, min(ev["fade"], dur // 2))
    if ev["anim"] == "pop":
        alpha = 1.0
    else:
        alpha = _clamp01(min(elapsed / fade, (dur - elapsed) / fade))
    p = elapsed / dur
    if ev["anim"] == "drift":
        p = p * p * (3 - 2 * p)
        return alpha, ev["x"] + ev["dx"] * p, ev["y"] + ev["dy"] * p
    return alpha, ev["x"], ev["y"]
