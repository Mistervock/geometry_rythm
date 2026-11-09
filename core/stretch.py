
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
    return os.path.join(DIR, f"{base}_{_stamp(song_path)}_{int(round(speed * 100))}_w{ALGO}.wav")


ALGO = 2


#-- Растяжение во времени без изменения тона (WSOLA)

WSOLA_N = 1024
WSOLA_SS = WSOLA_N // 4
WSOLA_TOL = 128


def wsola(arr, speed):
    """arr: (n, ch) int16 → (m, ch) int16, m ≈ n / speed. Поиск совпадения по моно-сумме, сдвиг общий для каналов."""
    n, ch = arr.shape
    x = arr.astype(np.float32)
    mono = x.mean(axis=1)
    out_len = int(round(n / speed))
    N, SS, TOL = WSOLA_N, WSOLA_SS, WSOLA_TOL
    OV = N - SS
    win = np.hanning(N).astype(np.float32)
    out = np.zeros((out_len + N, ch), dtype=np.float32)
    norm = np.zeros(out_len + N, dtype=np.float32)
    sa = SS * speed
    pad = np.zeros((n + N + 2 * TOL, ch), dtype=np.float32)
    pad[TOL:TOL + n] = x
    mono_pad = np.zeros(n + N + 2 * TOL, dtype=np.float32)
    mono_pad[TOL:TOL + n] = mono
    from numpy.lib.stride_tricks import sliding_window_view
    frames = sliding_window_view(mono_pad, OV)
    c_prev = 0
    k = 0
    while True:
        y = k * SS
        if y >= out_len:
            break
        if k == 0:
            c = 0
        else:
            tmpl = mono_pad[TOL + c_prev + SS: TOL + c_prev + SS + OV]
            ideal = int(round(k * sa))
            lo = max(0, ideal - TOL)
            hi = min(n - 1, ideal + TOL)
            if hi <= lo:
                c = max(0, min(n - 1, ideal))
            else:
                cands = frames[TOL + lo: TOL + hi + 1]
                num = cands @ tmpl
                den = np.sqrt((cands * cands).sum(axis=1)) * (np.sqrt((tmpl * tmpl).sum()) + 1e-9) + 1e-9
                offs = np.abs(np.arange(lo, hi + 1) - ideal)
                score = num / den - 1e-3 * offs / TOL
                c = lo + int(np.argmax(score))
        seg = pad[TOL + c: TOL + c + N]
        if seg.shape[0] < N:
            seg = np.pad(seg, ((0, N - seg.shape[0]), (0, 0)))
        out[y:y + N] += seg * win[:, None]
        norm[y:y + N] += win
        c_prev = c
        k += 1
    norm = np.maximum(norm, 1e-6)
    res = out[:out_len] / norm[:out_len, None]
    return np.clip(res, -32768, 32767).astype(np.int16)


#-- Единая временная шкала звука

def ensure(song_path, speed):
    """Путь к PCM-WAV песни со скоростью speed (1.0 — точная копия декодирования). None — если нельзя."""
    if not AVAILABLE or not pygame.mixer.get_init():
        return None
    out = path_for(song_path, speed)
    if os.path.exists(out):
        try:
            os.utime(out)
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
            res = wsola(arr, speed)
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
