
#-- Импорт
import hashlib
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


def _stamp(song_path):
    """Короткий отпечаток файла песни (размер + время изменения + путь): подменили песню — кэш устарел."""
    try:
        st = os.stat(song_path)
        raw = f"{os.path.abspath(song_path)}|{st.st_size}|{int(st.st_mtime)}"
    except OSError:
        raw = os.path.abspath(song_path)
    return hashlib.sha1(raw.encode("utf-8", "replace")).hexdigest()[:8]


def path_for(song_path, speed):
    base = _safe(os.path.splitext(os.path.basename(song_path))[0])
    return os.path.join(DIR, f"{base}_{_stamp(song_path)}_{int(round(speed * 100))}.wav")


#-- Единая временная шкала звука
#
# Потоковое воспроизведение сжатой музыки (MP3/OGG) и декодирование целиком дают РАЗНУЮ задержку начала
# (по измерениям 20-45 мс), а перемотка потока (play(start=...)) ещё и отличается от старта с нуля.
# Из-за этого при смене скорости в редакторе звук «уезжал» относительно нот. Поэтому ВСЕ скорости, включая
# обычную 1x, играют из одного и того же полного декодирования (PCM WAV в кэше): позиция в файле всегда
# точно соответствует времени чарта, а перемотка точная до сэмпла.

def ensure(song_path, speed):
    """Путь к PCM-WAV песни со скоростью speed (1.0 — точная копия декодирования). None — если нельзя."""
    if not AVAILABLE or not pygame.mixer.get_init():
        return None
    out = path_for(song_path, speed)
    if os.path.exists(out):
        try:
            os.utime(out)                      # «недавно использован» — prune удаляет самые давние
        except OSError:
            pass
        return out
    try:
        freq, _, ch = pygame.mixer.get_init()
        raw = pygame.mixer.Sound(song_path).get_raw()
        arr = np.frombuffer(raw, dtype=np.int16).reshape(-1, ch)
        n = len(arr)
        if n < 2:
            return None
        if speed == 1.0:
            res = arr
        else:
            arr = arr.astype(np.float32)
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


def playable(song_path, speed):
    """Что проигрывать: PCM-кэш; на обычной скорости при неудаче — сама песня (лучше, чем тишина)."""
    path = ensure(song_path, speed)
    if path is None and speed == 1.0:
        return song_path
    return path


def prune(max_bytes=1_500_000_000):
    """Кэш PCM растёт с каждой песней и скоростью: удаляем самые давние файлы сверх лимита (и «.tmp»)."""
    try:
        files = []
        for name in os.listdir(DIR):
            p = os.path.join(DIR, name)
            if name.endswith(".tmp"):
                os.remove(p)
            elif name.endswith(".wav"):
                st = os.stat(p)
                files.append((st.st_mtime, st.st_size, p))
        total = sum(f[1] for f in files)
        for _, size, p in sorted(files):
            if total <= max_bytes:
                break
            os.remove(p)
            total -= size
    except OSError:
        pass
