
#-- Импорт
import json
import os

import pygame

import config as C

PATH = C.root("data", "settings.json")

DEFAULTS = {
    "latency_ms": 0,
    "scroll_ms": 900,
    "music_volume": 75,
    "sfx_volume": 60,
    "lane_keys": ["d", "f", "j", "k"],
    "lang": "en",
    "fullscreen": 0,
    "preview": 1,
    "media_dim": 45,
}

LIMITS = {
    "latency_ms": (-300, 300, 5),
    "scroll_ms": (500, 1500, 50),
    "music_volume": (0, 100, 5),
    "sfx_volume": (0, 100, 5),
    "media_dim": (0, 90, 5),
}

_data = None


def _load():
    global _data
    if _data is None:
        _data = dict(DEFAULTS)
        try:
            with open(PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                for key in DEFAULTS:
                    if key in raw:
                        _data[key] = raw[key]
        except Exception:
            pass
        _sanitize()
    return _data


def _sanitize():
    d = _data
    for key, (lo, hi, _) in LIMITS.items():
        try:
            d[key] = int(max(lo, min(hi, int(d[key]))))
        except (TypeError, ValueError):
            d[key] = DEFAULTS[key]
    keys = d.get("lane_keys")
    if not (isinstance(keys, list) and len(keys) == 4 and all(isinstance(k, str) and k for k in keys)):
        d["lane_keys"] = list(DEFAULTS["lane_keys"])
    if d.get("lang") not in ("en", "ru"):
        d["lang"] = "en"
    d["fullscreen"] = 1 if d.get("fullscreen") in (1, True) else 0
    d["preview"] = 1 if d.get("preview") in (1, True) else 0


def get(key):
    return _load()[key]


def set(key, value):
    _load()[key] = value
    _sanitize()
    save()


def step(key, direction):
    lo, hi, st = LIMITS[key]
    set(key, get(key) + direction * st)


def lane_keys():
    codes = []
    for name in get("lane_keys"):
        try:
            codes.append(pygame.key.key_code(name))
        except Exception:
            codes.append(None)
    if None in codes:
        return C.LANE_KEYS
    return tuple(codes)


def key_label(name):
    return name.upper() if len(name) == 1 else name


def reset():
    global _data
    _data = dict(DEFAULTS)
    save()


def save():
    try:
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(_load(), f, ensure_ascii=False, indent=2)
    except OSError:
        pass
