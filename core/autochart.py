
#-- Импорт
import bisect

import pygame

try:
    import numpy as np
    from numpy.lib.stride_tricks import sliding_window_view
    AVAILABLE = True
except ImportError:
    np = None
    AVAILABLE = False

N = 1024
HOP = 256
TARGET_SR = 22050
BANDS = ((30, 150), (150, 700), (700, 2500), (2500, 8000))
PEAK_HALF = 5
Z_THRESH = 2.4
MIN_GAP_S = 0.16
MIN_LANE_GAP_MS = 120
MAX_PER_SEC = 3.0
SKIP_START_S = 1.2
SKIP_END_S = 1.5
HOLD_MIN_MS = 600
HOLD_MAX_MS = 2500
HOLD_DROP_DB = 6
ENERGY_DECIM = 4
BLOCK = 2048


def decode(path):
    if not AVAILABLE or not pygame.mixer.get_init():
        return None
    freq, fmt, channels = pygame.mixer.get_init()
    if fmt != -16:
        return None
    try:
        raw = pygame.mixer.Sound(path).get_raw()
    except Exception:
        return None
    arr = np.frombuffer(raw, dtype=np.int16)
    if channels > 1:
        arr = arr.reshape(-1, channels).mean(axis=1)
    y = arr.astype(np.float64) / 32768.0
    step = max(1, round(freq / TARGET_SR))
    return y[::step], freq / step


def _band_analysis(y, sr):
    frames = 1 + (len(y) - N) // HOP
    freqs = np.fft.rfftfreq(N, 1 / sr)
    masks = [(freqs >= lo) & (freqs < hi) for lo, hi in BANDS]
    win = np.hanning(N)
    flux = np.zeros((len(BANDS), frames))
    db = np.zeros((len(BANDS), frames))
    prev = None
    for start in range(0, frames, BLOCK):
        stop = min(frames, start + BLOCK)
        idx = np.arange(N)[None, :] + HOP * np.arange(start, stop)[:, None]
        S = np.abs(np.fft.rfft(y[idx] * win, axis=1))
        E = np.stack([S[:, m].sum(axis=1) for m in masks], axis=1)
        L = np.log1p(E * 50)
        if prev is None:
            prev = L[0]
        seq = np.vstack([prev[None, :], L])
        flux[:, start:stop] = np.maximum(0, np.diff(seq, axis=0)).T
        db[:, start:stop] = (10 * np.log10(E + 1e-9)).T
        prev = L[-1]
    return flux, db


def _robust_z(x):
    med = np.median(x)
    mad = np.median(np.abs(x - med)) * 1.4826 + 1e-9
    return (x - med) / mad


def _candidates(flux, sr):
    out = []
    H = PEAK_HALF
    for b in range(len(BANDS)):
        z = _robust_z(flux[b])
        if len(z) < 2 * H + 1:
            continue
        win_max = sliding_window_view(z, 2 * H + 1).max(axis=1)
        center = z[H:len(z) - H]
        peaks = np.where((center == win_max) & (center > Z_THRESH))[0] + H
        out.extend((float(z[i]), int(i), b) for i in peaks)
    out.sort(key=lambda c: -c[0])
    return out


def _select(cands, sr, frames, dur):
    accepted = []
    all_t = []
    lane_t = [[] for _ in BANDS]
    min_gap = MIN_GAP_S
    lane_gap = MIN_LANE_GAP_MS / 1000.0
    for strength, frame, lane in cands:
        t = (frame * HOP + N // 2) / sr
        if t < SKIP_START_S or t > dur - SKIP_END_S:
            continue
        i = bisect.bisect_left(all_t, t)
        if i > 0 and t - all_t[i - 1] < min_gap:
            continue
        if i < len(all_t) and all_t[i] - t < min_gap:
            continue
        lo = bisect.bisect_left(all_t, t - 0.5)
        hi = bisect.bisect_right(all_t, t + 0.5)
        if hi - lo >= MAX_PER_SEC:
            continue
        lt = lane_t[lane]
        j = bisect.bisect_left(lt, t)
        if (j > 0 and t - lt[j - 1] < lane_gap) or (j < len(lt) and lt[j] - t < lane_gap):
            continue
        all_t.insert(i, t)
        lt.insert(j, t)
        accepted.append((t, frame, lane))
    accepted.sort()
    return accepted


def _holds(accepted, db, sr):
    fps = sr / HOP
    lane_next = {}
    last_on_lane = {}
    for k in range(len(accepted) - 1, -1, -1):
        t, frame, lane = accepted[k]
        lane_next[k] = last_on_lane.get(lane)
        last_on_lane[lane] = t
    notes = []
    for k, (t, frame, lane) in enumerate(accepted):
        dur_ms = 0
        seg_len = int(HOLD_MAX_MS / 1000 * fps) + 1
        seg = db[lane, frame:frame + seg_len]
        if seg.size > 4:
            level = float(seg[:4].max())
            below = np.where(seg < level - HOLD_DROP_DB)[0]
            run = int(below[0]) if below.size else seg.size
            sustain_ms = run / fps * 1000.0
            if sustain_ms >= HOLD_MIN_MS:
                limit = lane_next.get(k)
                cap = HOLD_MAX_MS
                if limit is not None:
                    cap = min(cap, (limit - t) * 1000.0 - MIN_LANE_GAP_MS)
                dur_ms = int(min(sustain_ms, cap))
                if dur_ms < HOLD_MIN_MS:
                    dur_ms = 0
        notes.append((int(round(t * 1000)), int(lane), dur_ms))
    return notes


def _energy(y, sr):
    blocks = len(y) // HOP
    rms = np.sqrt((y[:blocks * HOP].reshape(-1, HOP) ** 2).mean(axis=1))
    r = rms[: len(rms) // ENERGY_DECIM * ENERGY_DECIM].reshape(-1, ENERGY_DECIM).mean(axis=1)
    env = np.clip(r / (np.quantile(r, 0.95) + 1e-9), 0, 1)
    return [int(round(v * 100)) for v in env], round(sr / HOP / ENERGY_DECIM, 3)


def build(path):
    dec = decode(path)
    if dec is None:
        return None
    y, sr = dec
    dur = len(y) / sr
    flux, db = _band_analysis(y, sr)
    cands = _candidates(flux, sr)
    accepted = _select(cands, sr, flux.shape[1], dur)
    notes = _holds(accepted, db, sr)
    energy, energy_fps = _energy(y, sr)
    return {
        "duration_ms": int(dur * 1000),
        "notes": notes,
        "energy": energy,
        "energy_fps": energy_fps,
    }


def energy_only(path):
    res = build(path)
    if res is None:
        return None
    return {"duration_ms": res["duration_ms"], "energy": res["energy"],
            "energy_fps": res["energy_fps"]}
