"""Кинематографика: камера (масштаб и сдвиг кадра) и переходы (затемнение, диафрагма, шторка, вспышка-акцент).

Дорожка строится один раз из событий чарта (build) и дальше только читается по времени. Поэтому состояние в любой
момент, в том числе при старте теста с середины карты, совпадает с обычным проходом: ничего не нужно «догонять».

Правила конфликтов: новое событие камеры или перехода начинается с текущей позы (покрытия) и обрывает предыдущее;
переход в режиме «закрыть» держит экран закрытым до следующего перехода. Камера звук не трогает; закрытый экран
приглушает песню (см. Game._duck_music), но сама дорожка переходов звука не меняет.
"""
import bisect
import math

import pygame

import anim as AN

CAM_REST = (100.0, 0.0, 0.0)
ZOOM_MIN, ZOOM_MAX = 50, 300
PAN_MAX_X, PAN_MAX_Y = 600, 400
KINDS = ("fade", "iris", "wipe")
MODES = ("out", "in", "pulse")
COLOURS = ((0, 0, 0), (255, 255, 255), (255, 70, 70), (90, 230, 255))
COLOUR_NAMES = ("ЧЕРНЫЙ", "БЕЛЫЙ", "КРАСНЫЙ", "ГОЛУБОЙ")
KIND_NAMES = {"fade": "ЗАТЕМНЕНИЕ", "iris": "ДИАФРАГМА", "wipe": "ШТОРКА"}
MODE_NAMES = {"out": "ЗАКРЫТЬ", "in": "ОТКРЫТЬ", "pulse": "АКЦЕНТ"}
EPS = 0.002


def clamp01(v):
    return max(0.0, min(1.0, v))


class Seg:
    """Один отрезок дорожки. Для камеры a и b — кортежи (zoom, x, y), для переходов — покрытие 0…1."""
    __slots__ = ("t0", "dur", "a", "b", "ease", "mode", "kind", "colour", "skip", "eid")

    def __init__(self, t0, dur, a, b, ease=AN.DEFAULT_EASE, mode="", kind="fade", colour=0, skip=False, eid=None):
        self.t0 = t0
        self.dur = max(0, dur)
        self.a = a
        self.b = b
        self.ease = ease if ease in AN.EASES else AN.DEFAULT_EASE
        self.mode = mode
        self.kind = kind
        self.colour = colour
        self.skip = skip
        self.eid = eid

    @property
    def end(self):
        return self.t0 + self.dur


def _lerp(a, b, e):
    return a + (b - a) * e


def _progress(seg, now):
    if seg.dur <= 0:
        return 1.0
    return clamp01((now - seg.t0) / seg.dur)


def cam_at(seg, now):
    """Поза камеры по отрезку в момент now: интерполяция по переходу, после окончания держится конечная поза."""
    e = AN.ease(seg.ease, _progress(seg, now))
    return tuple(_lerp(x, y, e) for x, y in zip(seg.a, seg.b))


def cov_at(seg, now, skipped=()):
    """Покрытие перехода 0…1. Пропущенный переход сразу отдаёт конечное состояние."""
    if now >= seg.end or (seg.skip and seg.eid in skipped):
        return seg.b
    p = _progress(seg, now)
    if seg.mode == "pulse":
        if p < 0.5:
            return _lerp(seg.a, 1.0, AN.ease(seg.ease, p * 2.0))
        return _lerp(1.0, seg.b, AN.ease(seg.ease, (p - 0.5) * 2.0))
    return _lerp(seg.a, seg.b, AN.ease(seg.ease, p))


def _cam_value(segs, t):
    i = _last(segs, t)
    return CAM_REST if i is None else cam_at(segs[i], t)


def _cov_value(segs, t):
    i = _last(segs, t)
    return 0.0 if i is None else cov_at(segs[i], t)


def _last(segs, t):
    lo, hi = 0, len(segs)
    while lo < hi:
        mid = (lo + hi) // 2
        if segs[mid].t0 <= t:
            lo = mid + 1
        else:
            hi = mid
    return lo - 1 if lo > 0 else None


def _add(segs, seg):
    segs[:] = [s for s in segs if s.t0 < seg.t0]
    segs.append(seg)


class Cine:
    """Готовая дорожка. Читается только через camera_at, overlay_at и skippable_at."""

    def __init__(self, cam, ov):
        self.cam = cam
        self.ov = ov
        self.cam_t0 = [s.t0 for s in cam]
        self.ov_t0 = [s.t0 for s in ov]

    def __bool__(self):
        return bool(self.cam or self.ov)

    def camera_at(self, now):
        if not self.cam:
            return CAM_REST
        i = bisect.bisect_right(self.cam_t0, now) - 1
        return CAM_REST if i < 0 else cam_at(self.cam[i], now)

    def overlay_at(self, now, skipped=()):
        """(покрытие, вид, цвет) или None, если экран не закрыт."""
        i = bisect.bisect_right(self.ov_t0, now) - 1
        if i < 0:
            return None
        seg = self.ov[i]
        cov = cov_at(seg, now, skipped)
        if cov <= EPS:
            return None
        return cov, seg.kind, COLOURS[seg.colour]

    def skippable_at(self, now):
        """Номер события перехода, который сейчас можно пропустить, или None."""
        i = bisect.bisect_right(self.ov_t0, now) - 1
        if i < 0:
            return None
        seg = self.ov[i]
        if seg.skip and seg.t0 <= now < seg.end:
            return seg.eid
        return None


APPEAR_MS = 1000
FINISH_MS = 900
DUCK_DEPTH = 0.8


def level_events(countdown_ms):
    """Появление уровня: экран закрыт с начала отсчёта и открывается за APPEAR_MS. Пропуск — Enter.

    Эти события добавляются только в обычной игре (не в практике и не в тесте)."""
    return [
        {"type": "transition", "t": -int(countdown_ms), "dur": 1, "mode": "out", "kind": "fade", "colour": 0,
         "ease": AN.DEFAULT_EASE, "skip": False},
        {"type": "transition", "t": -int(countdown_ms) + 1, "dur": APPEAR_MS, "mode": "in", "kind": "fade",
         "colour": 0, "ease": "ease_out", "skip": True},
    ]


def finish_event(t_ms):
    """Завершение уровня: экран закрывается от текущего состояния за FINISH_MS и остаётся закрытым."""
    return {"type": "transition", "t": int(t_ms), "dur": FINISH_MS, "mode": "out", "kind": "fade",
            "colour": 0, "ease": "ease_in", "skip": False}


def build(events):
    """Строит дорожку из нормализованных событий чарта. Порядок событий задаёт порядок конфликтов."""
    cam, ov = [], []
    order = sorted(range(len(events)), key=lambda i: (events[i]["t"], i))
    for idx in order:
        ev = events[idx]
        if ev.get("type") == "camera":
            start = _cam_value(cam, ev["t"])
            target = (float(ev["zoom"]), float(ev["x"]), float(ev["y"]))
            _add(cam, Seg(ev["t"], ev["dur"], start, target, ev.get("ease", AN.DEFAULT_EASE)))
        elif ev.get("type") == "transition":
            _add(ov, _transition_seg(ov, ev, idx))
    return Cine(cam, ov)


def _transition_seg(ov, ev, idx):
    t = ev["t"]
    start = _cov_value(ov, t)
    mode = ev.get("mode", "out")
    if mode == "out":
        target = 1.0
    elif mode == "in":
        target = 0.0
    else:
        target = start
    skip = bool(ev.get("skip", True)) and mode != "out"
    colour = int(ev.get("colour", 0))
    return Seg(t, ev["dur"], start, target, ev.get("ease", AN.DEFAULT_EASE), mode=mode,
               kind=ev.get("kind", "fade"), colour=colour if 0 <= colour < len(COLOURS) else 0,
               skip=skip, eid=idx)


#-- Отрисовка

_CACHE = {}


def _surface(key, size, flags=0):
    s = _CACHE.get(key)
    if s is None or s.get_size() != size:
        s = pygame.Surface(size, flags)
        _CACHE[key] = s
    return s


def apply_camera(scr, cam, smooth=True):
    """Масштаб относительно центра кадра и сдвиг картинки. Пустые края заливаются чёрным."""
    zoom, x, y = cam
    if abs(zoom - 100.0) < 0.05 and abs(x) < 0.5 and abs(y) < 0.5:
        return
    w, h = scr.get_size()
    z = max(ZOOM_MIN, min(ZOOM_MAX, zoom)) / 100.0
    scale = pygame.transform.smoothscale if smooth else pygame.transform.scale
    if z >= 1.0:
        cw, ch = max(1, int(w / z)), max(1, int(h / z))
        sub = scr.subsurface(pygame.Rect((w - cw) // 2, (h - ch) // 2, cw, ch))
        out = scale(sub, (w, h))
        scr.fill((0, 0, 0))
        scr.blit(out, (int(round(x)), int(round(y))))
    else:
        ow, oh = max(1, int(w * z)), max(1, int(h * z))
        out = scale(scr, (ow, oh))
        scr.fill((0, 0, 0))
        scr.blit(out, (int(round((w - ow) / 2 + x)), int(round((h - oh) / 2 + y))))


def apply_overlay(scr, state):
    """Накладывает переход. state — результат Cine.overlay_at."""
    if state is None:
        return
    cov, kind, colour = state
    w, h = scr.get_size()
    if kind == "fade":
        s = _surface(("fade", w, h), (w, h))
        s.fill(colour)
        s.set_alpha(int(255 * cov))
        scr.blit(s, (0, 0))
    elif kind == "wipe":
        cw = int(w * cov)
        if cw > 0:
            pygame.draw.rect(scr, colour, (0, 0, cw, h))
    elif kind == "iris":
        maxr = math.hypot(w / 2.0, h / 2.0)
        r = int(maxr * (1.0 - cov))
        mask = _surface(("iris", w, h), (w, h), pygame.SRCALPHA)
        mask.fill(colour + (255,))
        if r > 0:
            pygame.draw.circle(mask, (0, 0, 0, 0), (w // 2, h // 2), r)
        scr.blit(mask, (0, 0))
