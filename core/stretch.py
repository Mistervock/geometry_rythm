
#-- Импорт
import os
import re
import wave

import pygame

import config as C

try:
    import numpy as np
except ImportError:
    np = None

AVAILABLE = np is not None
DIR = C.root("data", "cache", "speed")


#-- Файлы

def _safe(name):
    return re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "_", name)[:60] or "song"


def path_for(song_path, speed):
    base = _safe(os.path.splitext(os.path.basename(song_path))[0])
    return os.path.join(DIR, f"{base}_{int(round(speed * 100))}.wav")


#-- Перерисовка песни с другой скоростью (тон меняется, как у пластинки)

def ensure(song_path, speed):
    if speed == 1.0:
        return song_path
    if not AVAILABLE or not pygame.mixer.get_init():
        return None
    out = path_for(song_path, speed)
    if os.path.exists(out):
        return out
    try:
        freq, _, ch = pygame.mixer.get_init()
        raw = pygame.mixer.Sound(song_path).get_raw()
        arr = np.frombuffer(raw, dtype=np.int16).reshape(-1, ch).astype(np.float32)
        n = len(arr)
        if n < 2:
            return None
        x = np.arange(int(n / speed)) * speed
        i0 = np.minimum(np.floor(x).astype(np.int64), n - 2)
        frac = (x - i0).astype(np.float32)[:, None]
        res = arr[i0] * (1.0 - frac) + arr[i0 + 1] * frac
        res = np.clip(res, -32768, 32767).astype(np.int16)
        os.makedirs(DIR, exist_ok=True)
        tmp = out + ".tmp"
        with wave.open(tmp, "wb") as w:
            w.setnchannels(ch)
            w.setsampwidth(2)
            w.setframerate(freq)
            w.writeframes(res.tobytes())
        os.replace(tmp, out)
        return out
    except Exception:
        return None
