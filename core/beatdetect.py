"""Авто-определение темпа (BPM) и сдвига первой доли по звуку песни.

Берём onset-огибающую из autochart (спектральный поток по полосам). Темп — пик автокорреляции огибающей в
диапазоне BPM_MIN..BPM_MAX (с небольшим предпочтением «обычных» темпов). Сдвиг — перебор фазы внутри одного
периода: выбираем фазу, при которой сумма огибающей в точках «доль» максимальна.

Результат — подсказка (bpm, offset_ms, confidence). Редактор применяет её обычной правкой сетки (отменяется
Ctrl+Z); ноты при этом не двигаются, потому что сетка не влияет на уже поставленные ноты.
"""
import numpy as np

import autochart as AC

BPM_MIN, BPM_MAX = 70.0, 180.0
PREFER = (90.0, 150.0)
PREFER_BOOST = 1.1
MIN_SECONDS = 8.0


def _envelope(y, sr):
    flux, _ = AC._band_analysis(y, sr)
    env = flux.sum(axis=0)
    fps = sr / AC.HOP
    k = max(1, int(fps))
    kern = np.ones(2 * k + 1) / (2 * k + 1)
    env = np.maximum(0.0, env - np.convolve(env, kern, mode="same"))
    return env, fps


def analyze(y, sr):
    """y — моно-сигнал (float), sr — частота. Возвращает dict или None, если данных мало или ритма не видно."""
    if len(y) < sr * MIN_SECONDS:
        return None
    env, fps = _envelope(y, sr)
    n = len(env)
    if n < fps * MIN_SECONDS or env.max() <= 0:
        return None
    size = 1 << int(np.ceil(np.log2(2 * n)))
    spec = np.fft.rfft(env, size)
    ac = np.fft.irfft(spec * np.conj(spec), size)[:n]
    ac = ac / np.maximum(1, n - np.arange(n))
    lag_lo = int(np.floor(fps * 60.0 / BPM_MAX))
    lag_hi = int(np.ceil(fps * 60.0 / BPM_MIN))
    if lag_hi + 2 >= n:
        return None
    lags = np.arange(max(1, lag_lo), lag_hi + 1)
    bpms = fps * 60.0 / lags
    score = ac[lags] * np.where((bpms >= PREFER[0]) & (bpms <= PREFER[1]), PREFER_BOOST, 1.0)
    best = int(np.argmax(score))
    lag = float(lags[best])
    if 0 < best < len(lags) - 1:
        a, b, c = ac[lags[best] - 1], ac[lags[best]], ac[lags[best] + 1]
        den = a - 2 * b + c
        if abs(den) > 1e-12:
            lag += float(np.clip(0.5 * (a - c) / den, -0.5, 0.5))
    bpm0 = fps * 60.0 / lag
    grid = np.arange(-0.02, 0.0201, 0.0002)
    best = (-1.0, bpm0, 0.0)
    ar = np.arange(n, dtype=float)
    for rel in grid:
        b_try = bpm0 * (1.0 + rel)
        if not (BPM_MIN <= b_try <= BPM_MAX):
            continue
        per = fps * 60.0 / b_try
        phases = np.arange(0.0, per, 0.5)
        K = int(n / per) + 2
        pos = phases[:, None] + per * np.arange(K)[None, :]
        valid = pos < n - 1
        vals = np.interp(pos.ravel(), ar, env).reshape(pos.shape) * valid
        total = vals.sum(axis=1)
        i = int(np.argmax(total))
        if total[i] > best[0]:
            best = (float(total[i]), b_try, float(phases[i]))
    _, bpm, ph = best
    offset_ms = (ph / fps + AC.N / (2.0 * sr)) * 1000.0
    beat_ms = 60000.0 / bpm
    offset_ms = offset_ms % beat_ms
    peak = float(ac[int(round(lag))]) if int(round(lag)) < n else 0.0
    confidence = max(0.0, min(1.0, peak / (ac[0] + 1e-12)))
    return {"bpm": round(bpm, 2), "offset_ms": round(offset_ms, 1), "confidence": round(confidence, 3)}


def analyze_path(path):
    """Декодирует песню (как для авторазметки) и анализирует. None — не удалось декодировать или ритма не видно."""
    dec = AC.decode(path)
    if dec is None:
        return None
    y, sr = dec
    return analyze(y, sr)
